"""Snapshot persistence.

A snapshot is stored per target account as JSON:

    {
      "target_user_id": "123",
      "target_username": "someone",
      "captured_at": "2026-06-06T12:00:00+00:00",
      "followers": {"<pk>": {"username": ..., "full_name": ...}, ...},
      "following": {"<pk>": {...}, ...}
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _snapshot_path(data_dir: Path, user_id: str) -> Path:
    return data_dir / f"snapshot_{user_id}.json"


def load_snapshot(data_dir: Path, user_id: str) -> dict | None:
    path = _snapshot_path(data_dir, user_id)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_snapshot(
    user_id: str,
    username: str,
    followers: dict[str, dict],
    following: dict[str, dict],
) -> dict:
    return {
        "target_user_id": user_id,
        "target_username": username,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "followers": followers,
        "following": following,
    }


def save_snapshot(data_dir: Path, snapshot: dict) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(data_dir, snapshot["target_user_id"])
    # Write atomically to avoid corrupting the snapshot on interruption.
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)
    tmp.replace(path)
    return path
