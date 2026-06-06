"""CLI entry point: python -m tracker run [options]."""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time

from .config import Config, ConfigError, load_config
from .diff import TRACK_LABELS, compute_diff
from .instagram_client import InstagramClient, InstagramError
from .notifier import send as send_notification
from .storage import build_snapshot, load_snapshot, save_snapshot

logger = logging.getLogger("tracker")

_INTERVAL_RE = re.compile(r"^\s*(\d+)\s*([smhd]?)\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "": 1}


def parse_interval(value: str) -> int:
    """Parse '6h' / '30m' / '90s' / '3600' into seconds."""
    match = _INTERVAL_RE.match(value)
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid interval {value!r}. Use e.g. 6h, 30m, 90s, or seconds."
        )
    return int(match.group(1)) * _UNIT_SECONDS[match.group(2).lower()]


def run_once(cfg: Config, dry_run: bool = False) -> bool:
    """Run a single check. Returns True if a notification was sent."""
    client = InstagramClient(
        session_id=cfg.session_id,
        settings_path=cfg.data_path / "ig_settings.json",
    ).login()

    user_id, username = client.resolve_target_user_id(cfg.target_username)
    logger.info("Tracking @%s (id=%s)", username, user_id)

    followers = client.fetch_followers(user_id, amount=cfg.max_amount)
    following = client.fetch_following(user_id, amount=cfg.max_amount)
    logger.info(
        "Fetched %d followers, %d following.", len(followers), len(following)
    )

    current = build_snapshot(user_id, username, followers, following)
    previous = load_snapshot(cfg.data_path, user_id)

    if previous is None:
        if dry_run:
            logger.info("[dry-run] No baseline yet; nothing saved.")
            return False
        save_snapshot(cfg.data_path, current)
        logger.info("Baseline snapshot created. No notification on first run.")
        return False

    diff = compute_diff(previous, current, cfg.track)

    if not diff.has_changes:
        logger.info("No changes since last check. No notification.")
        if not dry_run:
            save_snapshot(cfg.data_path, current)
        return False

    # Summarize to the console regardless of notifier.
    for key, records in diff.changes.items():
        if records:
            logger.info(
                "%s: %d (%s)",
                TRACK_LABELS.get(key, key),
                len(records),
                ", ".join("@" + r["username"] for r in records[:10]),
            )

    if dry_run:
        logger.info("[dry-run] %d changes detected; not sending / not saving.", diff.total())
        return False

    sent = send_notification(cfg.notifier, username, diff)
    save_snapshot(cfg.data_path, current)
    return sent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tracker", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a follow/follower check.")
    run_p.add_argument("--config", default="config.json", help="Path to config JSON.")
    run_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and diff, but do not send notifications or save the snapshot.",
    )
    run_p.add_argument(
        "--loop",
        action="store_true",
        help="Run repeatedly at --interval instead of exiting after one check.",
    )
    run_p.add_argument(
        "--interval",
        type=parse_interval,
        default=parse_interval("6h"),
        help="Loop interval (e.g. 6h, 30m, 90s). Default: 6h.",
    )
    run_p.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        cfg = load_config(args.config)
        cfg.validate()
    except ConfigError as exc:
        logger.error("Config error: %s", exc)
        return 2

    if not args.loop:
        try:
            run_once(cfg, dry_run=args.dry_run)
        except (InstagramError, Exception) as exc:  # noqa: BLE001
            logger.error("Run failed: %s", exc)
            return 1
        return 0

    logger.info("Loop mode: checking every %d seconds. Ctrl-C to stop.", args.interval)
    while True:
        try:
            run_once(cfg, dry_run=args.dry_run)
        except KeyboardInterrupt:
            logger.info("Stopped.")
            return 0
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            logger.error("Run failed (will retry next interval): %s", exc)
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Stopped.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
