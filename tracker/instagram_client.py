"""Thin wrapper around instagrapi that authenticates via a sessionid cookie.

We reuse the ``sessionid`` from an already-logged-in browser session of the
*consenting* account. This avoids storing a password and reduces the chance of
triggering a login challenge.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# instagrapi is imported lazily inside the methods so that the rest of the
# package (config, storage, diff) can be imported / unit-tested without the
# dependency installed.


class InstagramError(Exception):
    """Raised on login or fetch failures."""


class InstagramClient:
    def __init__(self, session_id: str, settings_path: Path):
        self.session_id = session_id
        self.settings_path = settings_path
        self._client = None

    def login(self):
        """Authenticate using the sessionid cookie.

        Device/session settings are cached on disk so repeated runs reuse the
        same device fingerprint instead of looking like a brand-new login.
        """
        try:
            from instagrapi import Client
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise InstagramError(
                "instagrapi is not installed. Run: pip install -r requirements.txt"
            ) from exc

        client = Client()
        client.delay_range = [1, 3]  # polite, randomized delay between requests

        if self.settings_path.exists():
            try:
                client.load_settings(self.settings_path)
                logger.debug("Loaded cached settings from %s", self.settings_path)
            except Exception as exc:  # noqa: BLE001 - corrupt cache is non-fatal
                logger.warning("Could not load cached settings: %s", exc)

        try:
            client.login_by_sessionid(self.session_id)
        except Exception as exc:  # noqa: BLE001
            raise InstagramError(
                f"Login via sessionid failed: {exc}. The sessionid may be "
                "expired — grab a fresh one from Chrome."
            ) from exc

        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            client.dump_settings(self.settings_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not persist settings: %s", exc)

        self._client = client
        logger.info("Logged in as @%s", client.username or "<unknown>")
        return self

    @property
    def client(self):
        if self._client is None:
            raise InstagramError("login() must be called before use.")
        return self._client

    def resolve_target_user_id(self, target_username: str) -> tuple[str, str]:
        """Return ``(user_id, username)`` for the account to track.

        If ``target_username`` is empty, the logged-in account is used.
        """
        if target_username:
            user_id = self.client.user_id_from_username(target_username)
            return str(user_id), target_username
        return str(self.client.user_id), self.client.username

    def fetch_followers(self, user_id: str, amount: int = 0) -> dict[str, dict]:
        return self._to_records(self.client.user_followers(user_id, amount=amount))

    def fetch_following(self, user_id: str, amount: int = 0) -> dict[str, dict]:
        return self._to_records(self.client.user_following(user_id, amount=amount))

    @staticmethod
    def _to_records(users: dict) -> dict[str, dict]:
        """Normalize instagrapi's {pk: UserShort} into plain JSON records."""
        records: dict[str, dict] = {}
        for pk, user in users.items():
            records[str(pk)] = {
                "username": getattr(user, "username", ""),
                "full_name": getattr(user, "full_name", ""),
            }
        return records
