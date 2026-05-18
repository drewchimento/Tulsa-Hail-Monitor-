# Tulsa Hail Monitor

Emails drew@bytedreams.ai every time the National Weather Service issues a
Severe Thunderstorm Warning mentioning hail inside a 50-mile circle around
downtown Tulsa, OK.

Runs free on GitHub Actions cron every 10 minutes. Total monthly cost: $0.

## How it works

```
NWS API → filter for SVR-warning + "hail" + Tulsa 50-mi radius
        → dedupe against seen_alerts.json
        → email new alerts via Gmail SMTP
```

## Local development

1. Create venv: `python -m venv .venv`
2. Activate it: PowerShell `.venv\Scripts\Activate.ps1`, or Git Bash `source .venv/Scripts/activate`
3. Install deps: `pip install -r requirements-dev.txt`
4. Copy `.env.example` to `.env` and fill in your real Gmail App Password.
5. Run tests: `python -m pytest tests/ -v`
6. Dry-run against live NWS: `python monitor.py --dry-run`
7. Send a real self-test email: `python monitor.py --self-test`

## Production deploy

Runs on GitHub Actions. The workflow at `.github/workflows/hail-monitor.yml`
triggers every 10 minutes and uses three repository secrets:

- `SMTP_USER` = drew@bytedreams.ai
- `SMTP_APP_PASSWORD` = 16-character Google App Password
- `ALERT_TO_EMAIL` = drew@bytedreams.ai

To regenerate the App Password (if compromised or expired):

1. https://myaccount.google.com/apppasswords
2. Revoke "Tulsa Hail Monitor", create a new one
3. Update the `SMTP_APP_PASSWORD` secret in GitHub Settings → Secrets and variables → Actions

## Files

- `monitor.py` — entry point, CLI, orchestration
- `nws.py` — NWS API client + filter logic + hail size extraction
- `geo.py` — 50-mile Tulsa polygon + geometry checks + county fallback
- `notify.py` — email formatting + SMTP send
- `state.py` — seen_alerts.json persistence (load/save/prune)
- `seen_alerts.json` — committed state of which alerts have already been emailed
- `.github/workflows/hail-monitor.yml` — cron workflow

## Manual triggers in GitHub Actions

From the Actions tab → "Tulsa Hail Monitor" → "Run workflow":

- **mode = normal** — runs the full pipeline against current NWS data
- **mode = dry-run** — prints what would be sent without sending
- **mode = self-test** — sends a single confirmation email

Each mode is useful for verifying wiring without waiting for a real storm.
