"""Tulsa Hail Monitor — entry point and main pipeline.

Fetches active NWS alerts for Oklahoma, filters for hail-bearing
Severe Thunderstorm Warnings inside a 50-mile circle around downtown
Tulsa, deduplicates against state, and emails new alerts via Resend.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from nws import fetch_alerts, is_relevant_hail_alert
from notify import DEFAULT_SENDER, format_alert_email, send_email
from state import load_seen, save_seen, mark_seen, prune_old

log = logging.getLogger("hail-monitor")


@dataclass(frozen=True)
class Config:
    state_file: Path
    sender: str
    recipient: str
    api_key: str
    dry_run: bool = False


def run_once(cfg: Config) -> None:
    """Run one polling cycle: fetch, filter, dedupe, notify, save."""
    seen = load_seen(cfg.state_file)
    prune_old(seen)

    alerts = fetch_alerts()
    log.info("Fetched %d active OK alerts", len(alerts))

    new_count = 0
    for alert in alerts:
        try:
            if not is_relevant_hail_alert(alert):
                continue
            alert_id = (alert.get("properties") or {}).get("id") or alert.get("id")
            if not alert_id:
                continue
            if alert_id in seen:
                continue

            subject, body = format_alert_email(alert)

            if cfg.dry_run:
                print("=" * 70)
                print(f"[DRY-RUN] Would send to {cfg.recipient}:")
                print(f"Subject: {subject}")
                print()
                print(body)
                print("=" * 70)
            else:
                send_email(
                    subject=subject,
                    body=body,
                    sender=cfg.sender,
                    recipient=cfg.recipient,
                    api_key=cfg.api_key,
                )
                mark_seen(seen, alert_id)
                log.info("Sent hail alert email for %s", alert_id)
            new_count += 1
        except Exception as exc:
            log.exception("Failed to handle alert %s: %s",
                          (alert.get("properties") or {}).get("id", "?"), exc)

    save_seen(cfg.state_file, seen)
    log.info("Run complete: %d new alerts processed", new_count)


def _config_from_env(dry_run: bool) -> Config:
    return Config(
        state_file=Path("seen_alerts.json"),
        sender=os.environ.get("RESEND_FROM_EMAIL", DEFAULT_SENDER),
        recipient=os.environ["ALERT_TO_EMAIL"],
        api_key=os.environ["RESEND_API_KEY"],
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tulsa Hail Monitor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print emails instead of sending them.")
    parser.add_argument("--self-test", action="store_true",
                        help="Send a single test email and exit.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv()

    if args.self_test:
        cfg = _config_from_env(dry_run=False)
        send_email(
            subject="Hail Alert — Self-test email",
            body="If you got this, the Tulsa Hail Monitor is wired up correctly.\n",
            sender=cfg.sender,
            recipient=cfg.recipient,
            api_key=cfg.api_key,
        )
        log.info("Self-test email sent to %s", cfg.recipient)
        return 0

    cfg = _config_from_env(dry_run=args.dry_run)
    run_once(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
