"""Configuration loading.

Config is read from a JSON file (default: ``config.json``) and can be
overridden by environment variables so that secrets need not be written to
disk:

- ``INSTAGRAM_SESSIONID`` -> ``session_id``
- ``WEBHOOK_URL``         -> ``notifier.webhook_url``
- ``TARGET_USERNAME``     -> ``target_username``
- ``NOTIFIER_TYPE``       -> ``notifier.type``

This lets the tool run from just environment variables (e.g. in Docker)
without a ``config.json`` on disk.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

VALID_TRACK_KEYS = {
    "new_following",
    "lost_following",
    "new_followers",
    "lost_followers",
}

VALID_NOTIFIERS = {"discord", "slack", "none"}


@dataclass
class NotifierConfig:
    type: str = "discord"
    webhook_url: str = ""


@dataclass
class Config:
    session_id: str = ""
    target_username: str = ""
    track: list[str] = field(default_factory=lambda: sorted(VALID_TRACK_KEYS))
    notifier: NotifierConfig = field(default_factory=NotifierConfig)
    data_dir: str = "data"
    max_amount: int = 0

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    def validate(self) -> None:
        if not self.session_id:
            raise ConfigError(
                "session_id is empty. Set it in config.json or the "
                "INSTAGRAM_SESSIONID environment variable."
            )

        unknown = set(self.track) - VALID_TRACK_KEYS
        if unknown:
            raise ConfigError(
                f"Unknown track keys: {sorted(unknown)}. "
                f"Valid keys: {sorted(VALID_TRACK_KEYS)}"
            )
        if not self.track:
            raise ConfigError("track is empty; nothing would ever be notified.")

        if self.notifier.type not in VALID_NOTIFIERS:
            raise ConfigError(
                f"notifier.type must be one of {sorted(VALID_NOTIFIERS)}, "
                f"got {self.notifier.type!r}"
            )
        if self.notifier.type != "none" and not self.notifier.webhook_url:
            raise ConfigError(
                f"notifier.type is {self.notifier.type!r} but webhook_url is "
                "empty. Set it in config.json or the WEBHOOK_URL environment "
                "variable (or set notifier.type to 'none')."
            )


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


def load_config(path: str | os.PathLike[str] = "config.json") -> Config:
    path = Path(path)
    raw: dict = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    elif not os.environ.get("INSTAGRAM_SESSIONID"):
        raise ConfigError(
            f"Config file {path} not found and INSTAGRAM_SESSIONID is not set. "
            "Copy config.example.json to config.json and fill it in."
        )

    notifier_raw = raw.get("notifier", {}) or {}
    notifier = NotifierConfig(
        type=notifier_raw.get("type", "discord"),
        webhook_url=notifier_raw.get("webhook_url", ""),
    )

    cfg = Config(
        session_id=raw.get("session_id", ""),
        target_username=raw.get("target_username", ""),
        track=list(raw.get("track", sorted(VALID_TRACK_KEYS))),
        notifier=notifier,
        data_dir=raw.get("data_dir", "data"),
        max_amount=int(raw.get("max_amount", 0)),
    )

    # Environment variables win over the file (keeps secrets off disk).
    cfg.session_id = os.environ.get("INSTAGRAM_SESSIONID", cfg.session_id).strip()
    cfg.notifier.webhook_url = os.environ.get(
        "WEBHOOK_URL", cfg.notifier.webhook_url
    ).strip()
    cfg.target_username = os.environ.get(
        "TARGET_USERNAME", cfg.target_username
    ).strip()
    cfg.notifier.type = os.environ.get("NOTIFIER_TYPE", cfg.notifier.type).strip()

    return cfg
