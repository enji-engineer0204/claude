"""Diff logic between two snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field

# Maps each track key to (which list it looks at, "added" or "removed").
TRACK_RULES: dict[str, tuple[str, str]] = {
    "new_following": ("following", "added"),
    "lost_following": ("following", "removed"),
    "new_followers": ("followers", "added"),
    "lost_followers": ("followers", "removed"),
}

# Human-readable labels for notifications.
TRACK_LABELS: dict[str, str] = {
    "new_following": "新規フォロー",
    "lost_following": "フォロー解除",
    "new_followers": "新規フォロワー",
    "lost_followers": "フォロワー減",
}


@dataclass
class Diff:
    # track_key -> list of user records ({"pk", "username", "full_name"})
    changes: dict[str, list[dict]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return any(self.changes.values())

    def total(self) -> int:
        return sum(len(v) for v in self.changes.values())


def _delta(
    previous: dict[str, dict], current: dict[str, dict], kind: str
) -> list[dict]:
    """Return records added or removed going from ``previous`` to ``current``."""
    if kind == "added":
        keys = current.keys() - previous.keys()
        source = current
    else:  # removed
        keys = previous.keys() - current.keys()
        source = previous
    return [{"pk": pk, **source[pk]} for pk in sorted(keys, key=lambda k: source[k].get("username", ""))]


def compute_diff(
    previous: dict, current: dict, track: list[str]
) -> Diff:
    """Compute the diff for the requested track keys.

    ``previous`` / ``current`` are snapshot dicts with ``followers`` and
    ``following`` maps ({pk: {username, full_name}}).
    """
    diff = Diff()
    for key in track:
        list_name, kind = TRACK_RULES[key]
        diff.changes[key] = _delta(
            previous.get(list_name, {}), current.get(list_name, {}), kind
        )
    return diff
