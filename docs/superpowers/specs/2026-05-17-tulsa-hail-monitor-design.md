# Tulsa Hail Monitor — Design Spec

**Date:** 2026-05-17
**Owner:** Drew (drew@bytedreams.ai)
**Status:** Approved, ready for implementation plan

---

## 1. Problem

Drew runs a Meta advertising campaign that must be activated whenever a hail
storm hits the Tulsa metro area. Missing a hail event means missing the
campaign's activation window, which is business-critical. There is currently
no automated alerting in place.

## 2. Goal

Email `drew@bytedreams.ai` every time the National Weather Service (NWS)
issues a Severe Thunderstorm Warning that:

1. Contains the word "hail" in its description, AND
2. Has a geographic polygon that intersects a 50-mile circle around
   downtown Tulsa, OK at coordinates `(36.154, -95.993)`.

## 3. Non-Goals

- Real-time (sub-minute) detection. 10-minute polling is acceptable.
- Predicting hail before NWS issues a warning.
- Filtering by hail size beyond what NWS already requires for an SVR
  warning (≥1" hail is the SVR criterion, so this is implicit).
- A web dashboard, alert history UI, or analytics.
- Multi-user notifications. Single recipient only.
- SMS, push, or any non-email channel for v1.

## 4. Cost

**$0/month, $0 setup.**

| Item | Cost |
| --- | --- |
| GitHub Actions (cron + compute) | $0 (free tier, well under 2,000 min/mo) |
| NWS API | $0 (no key required) |
| Gmail / Google Workspace SMTP | $0 (uses existing mailbox) |
| Hosting / domain / hardware | $0 (none needed) |

No paid third-party services. No domain purchases. No hardware.

## 5. Architecture

A single Python script (`monitor.py`) runs every 10 minutes via GitHub
Actions cron. It queries the NWS public API for active alerts in Oklahoma,
filters for relevant hail-bearing Severe Thunderstorm Warnings whose geometry
intersects the 50-mile Tulsa circle, deduplicates against a `seen_alerts.json`
state file committed to the repo, and emails new alerts via Gmail SMTP. The
workflow then commits the updated state file back to the repo so the next
run remembers what it already sent.

```
[GitHub Actions cron: */10 * * * *]
        ↓
  GET https://api.weather.gov/alerts/active?area=OK
        ↓
  filter: event == "Severe Thunderstorm Warning"
          AND "hail" in description (case-insensitive)
        ↓
  filter: alert polygon intersects 50-mi circle around (36.154, -95.993)
        ↓
  filter: alert ID not in seen_alerts.json
        ↓
  for each new alert: send email → drew@bytedreams.ai via Gmail SMTP
        ↓
  update and commit seen_alerts.json back to repo
```

## 6. Tech Stack

- **Python 3.11**
- **`requests`** — NWS API HTTP calls
- **`shapely`** — polygon intersection geometry
- **`smtplib`** (stdlib) — SMTP email send
- **GitHub Actions** — scheduled execution
- **NWS API** — `https://api.weather.gov/alerts/active`
- **Gmail SMTP** — `smtp.gmail.com:587` with STARTTLS

No database. No web framework. No third-party notification service.

## 7. File Structure

```
Hail Alert/
├── monitor.py                       # main script (~120 lines)
├── seen_alerts.json                 # state file, committed to repo
├── requirements.txt                 # requests, shapely
├── .env.example                     # template, no real secrets
├── .gitignore                       # excludes .env, __pycache__
├── README.md                        # setup instructions
└── .github/
    └── workflows/
        └── hail-monitor.yml         # cron workflow
```

## 8. Components

### 8.1 `fetch_alerts()`

- `GET https://api.weather.gov/alerts/active?area=OK`
- Headers: `User-Agent: Tulsa-Hail-Monitor/1.0 (drew@bytedreams.ai)` —
  NWS requires a polite UA or they will block the caller.
- Timeout: 30 seconds.
- Returns: list of alert feature dicts from `response.json()['features']`.
- On HTTP error or timeout: log the error, return an empty list. The next
  cron run will retry naturally.

### 8.2 `is_relevant_hail_alert(alert)`

Two combined checks. Both must pass.

**Content check:**
- `properties.event == "Severe Thunderstorm Warning"`
- AND `"hail" in properties.description.lower()`

**Geometry check:**
- If `alert['geometry']` is present:
  - Build a shapely Polygon from the alert GeoJSON.
  - Build a 50-mile "circle" around `(36.154, -95.993)` as a shapely
    ellipse using a latitude-corrected buffer:
    - 50 mi north–south ≈ 0.7246° latitude
    - 50 mi east–west at 36°N ≈ 0.8945° longitude
    - Constructed once at module load and cached.
  - Return `alert_polygon.intersects(tulsa_circle)`.
- If `alert['geometry']` is missing (rare but happens):
  - Fall back to substring matching against `properties.areaDesc` for any
    of these counties within the 50-mi radius: Tulsa, Rogers, Wagoner,
    Creek, Osage, Mayes, Okmulgee, Pawnee, Washington, Nowata.

### 8.3 `load_seen()` / `save_seen()`

- Schema for `seen_alerts.json`:
  ```json
  {
    "alerts": { "<alert_id>": "<ISO 8601 timestamp>" },
    "last_updated": "<ISO 8601 timestamp>"
  }
  ```
- On load: if file is missing or invalid JSON, return an empty dict and log
  a warning. Worst case: one duplicate email, which is acceptable.
- On save: prune entries older than 48 hours, write atomically (tempfile +
  rename) to avoid corruption on interrupted writes.

### 8.4 `send_email(alert)`

- Subject: `Hail Alert — {event} until {expiration_local_time}`
- Body (plain text):
  - Event type (e.g. "Severe Thunderstorm Warning")
  - NWS headline
  - Hail size extracted from description (regex for `\d+(\.\d+)?\s*inch`,
    "quarter-sized", "ping pong", etc. — best-effort, include raw text as
    fallback)
  - Affected areas (`properties.areaDesc`)
  - Expiration time in Central Time
  - Link to official NWS alert page:
    `https://alerts.weather.gov/cap/wwacapget.php?x={alert_id}`
- SMTP: `smtp.gmail.com:587`, STARTTLS, login with `SMTP_USER` and
  `SMTP_APP_PASSWORD`.
- Recipient: `ALERT_TO_EMAIL` env var.
- On failure: raise. The caller will NOT mark the alert as seen, so the
  next cron run retries. This is the only error path that propagates.

### 8.5 `main()`

- Load environment (CI provides via GitHub Secrets; local provides via `.env`).
- Load `seen_alerts.json`.
- Fetch alerts.
- For each alert: filter → dedupe → send email → mark as seen.
- Save `seen_alerts.json`.
- Flags:
  - `--dry-run` — run the full pipeline but print emails to stdout instead
    of sending. Used for local testing.
  - `--self-test` — send a single test email and exit. Used once after
    initial deploy to confirm SMTP wiring.

### 8.6 GitHub Actions Workflow (`hail-monitor.yml`)

- Triggers:
  - `schedule: cron: "*/10 * * * *"` (every 10 minutes UTC)
  - `workflow_dispatch:` (manual "Run workflow" button for ad-hoc tests)
- Steps:
  1. Checkout repo (with write permissions to push state file back).
  2. Setup Python 3.11.
  3. `pip install -r requirements.txt`.
  4. Run `python monitor.py`.
  5. If `seen_alerts.json` changed, commit and push using a bot identity
     (`github-actions[bot]`).
- Permissions: `contents: write` (to push state file commits).
- Secrets used:
  - `SMTP_USER` — drew@bytedreams.ai
  - `SMTP_APP_PASSWORD` — 16-character Google App Password
  - `ALERT_TO_EMAIL` — drew@bytedreams.ai

## 9. Error Handling

| Failure mode | Behavior |
| --- | --- |
| NWS API timeout or 5xx | Log, exit 0, next cron run retries naturally |
| NWS returns malformed alert | try/except per alert; skip and continue |
| SMTP send fails | Raise; alert not marked seen; retried next run |
| `seen_alerts.json` corrupt or missing | Treat as empty, rebuild |
| Geometry parsing fails on an alert | Fall back to county-name match in `areaDesc` |
| GitHub Actions outage | GitHub emails Drew about missed runs; auto-recovers |
| Concurrent runs racing on state file | Cron interval (10 min) >> run time (~15s); not a concern |

## 10. Testing

1. **Unit: geometry**
   - Polygon over Tulsa → True
   - Polygon over Dallas → False
   - Polygon clipping the 50-mi edge near Bartlesville → True
   - Null geometry with `areaDesc: "Tulsa, OK"` → True (county fallback)

2. **Unit: filter logic**
   - SVR warning + "hail" in description → pass
   - SVR warning, no "hail" → skip
   - Tornado warning that mentions hail → skip (v1 is SVR-only)
   - Flood warning → skip

3. **Integration: dry-run end-to-end**
   - Run `python monitor.py --dry-run` against live NWS data.
   - Manually inspect printed emails for an active OK alert.

4. **Self-test on first deploy**
   - Run `python monitor.py --self-test` once after secrets are configured
     to confirm SMTP works before relying on it.

5. **Historical validation**
   - Feed a known past Tulsa hail alert (we'll grab one from the NWS
     archive) through the filter functions to confirm we'd have caught it.

## 11. Latency Expectation

Worst case: ~10 minutes from NWS issuance to email delivery. NWS typically
issues SVR warnings minutes before or during a storm, so Drew will generally
receive the alert while hail is actively falling somewhere in the metro.
This is fast enough for a Meta campaign activation. True real-time
(<1 minute) would require a different architecture (NWS WebSocket or
always-on loop) and is not in scope for v1.

## 12. Storm Behavior

A single hail event typically generates 2–8 NWS warnings as the storm
moves across the metro. Drew will receive **one email per warning** (each
has a unique alert ID). NWS-issued updates to a warning generate a new
alert ID and therefore a new email — this is intentional, because updates
often contain new hail size information.

## 13. Prerequisites — What Drew Needs to Gather

This is the full prep list. Have these ready before implementation starts.

### 13.1 GitHub account

- If you don't have one, sign up at github.com (free).
- You will need to create a new private repo named something like
  `tulsa-hail-monitor` during implementation.

### 13.2 Google App Password for drew@bytedreams.ai

This is the trickiest prep step. Walk through it before we start coding.

1. Go to https://myaccount.google.com → **Security**.
2. Confirm **2-Step Verification** is **ON**. App Passwords are only
   available on accounts with 2SV enabled. If it's off, turn it on first.
3. Search for **"App passwords"** in the Google Account settings search
   bar (the link is hidden depending on Workspace policy).
   - If "App passwords" doesn't appear, your Workspace admin has disabled
     it. If you administer bytedreams.ai yourself, toggle it on in the
     Workspace admin console under Security → App passwords. If someone
     else administers your Workspace, ask them. As a fallback if App
     Passwords are blocked entirely, we can pivot to a free transactional
     email service (Resend, SendGrid free tier) — flag this if you hit
     a wall here.
4. Click **Create app password**. Name it `Tulsa Hail Monitor`.
5. Google will show you a **16-character password** (looks like
   `abcd efgh ijkl mnop`). **Copy it immediately — Google only shows it
   once.** Save it in a password manager.

### 13.3 Confirm sender identity

- Default assumption: sender = recipient = `drew@bytedreams.ai`. You email
  yourself. This is fine and the simplest setup.
- If you want a different sender (e.g. `alerts@bytedreams.ai`), say so
  before implementation — we'll need to provision that mailbox first.

### 13.4 That is the entire list

No Twilio account. No domain purchase. No credit card. No API keys other
than the Google App Password. The NWS API is open and requires no
registration.

## 14. Open Questions

None. Ready for implementation plan.
