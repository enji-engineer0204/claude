"""Send diff notifications to Discord or Slack via incoming webhooks."""

from __future__ import annotations

import logging

import requests

from .config import NotifierConfig
from .diff import TRACK_LABELS, Diff

logger = logging.getLogger(__name__)

# Avoid flooding the channel / hitting message size limits.
MAX_USERS_PER_CATEGORY = 25


def format_message(target_username: str, diff: Diff) -> str:
    lines = [f"📸 @{target_username} のフォロー/フォロワーに変化がありました"]
    for key, records in diff.changes.items():
        if not records:
            continue
        label = TRACK_LABELS.get(key, key)
        lines.append(f"\n**{label}** ({len(records)}件)")
        shown = records[:MAX_USERS_PER_CATEGORY]
        for rec in shown:
            name = rec.get("full_name") or ""
            suffix = f" ({name})" if name else ""
            lines.append(f"・@{rec.get('username', '?')}{suffix}")
        if len(records) > MAX_USERS_PER_CATEGORY:
            lines.append(f"…ほか {len(records) - MAX_USERS_PER_CATEGORY} 件")
    return "\n".join(lines)


def _payload(notifier_type: str, text: str) -> dict:
    # Discord uses "content"; Slack uses "text".
    return {"content": text} if notifier_type == "discord" else {"text": text}


def send(config: NotifierConfig, target_username: str, diff: Diff) -> bool:
    """Send the notification. Returns True if something was sent."""
    if not diff.has_changes:
        return False
    if config.type == "none":
        logger.info("notifier.type is 'none'; skipping send.")
        return False

    text = format_message(target_username, diff)
    resp = requests.post(
        config.webhook_url,
        json=_payload(config.type, text),
        timeout=30,
    )
    resp.raise_for_status()
    logger.info("Notification sent (%d changes).", diff.total())
    return True
