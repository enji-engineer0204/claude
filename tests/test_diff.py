"""Tests for the snapshot diff logic and notification formatting.

Run with:  python -m unittest discover -s tests
These tests do not touch the network or instagrapi.
"""

import unittest

from tracker.diff import compute_diff
from tracker.notifier import format_message

ALL_TRACK = ["new_following", "lost_following", "new_followers", "lost_followers"]


def snap(followers, following):
    return {"followers": followers, "following": following}


def user(name):
    return {"username": name, "full_name": name.title()}


class DiffTest(unittest.TestCase):
    def test_no_change(self):
        prev = snap({"1": user("a")}, {"2": user("b")})
        cur = snap({"1": user("a")}, {"2": user("b")})
        diff = compute_diff(prev, cur, ALL_TRACK)
        self.assertFalse(diff.has_changes)
        self.assertEqual(diff.total(), 0)

    def test_new_and_lost_followers(self):
        prev = snap({"1": user("a"), "2": user("b")}, {})
        cur = snap({"1": user("a"), "3": user("c")}, {})
        diff = compute_diff(prev, cur, ALL_TRACK)
        self.assertTrue(diff.has_changes)
        self.assertEqual([r["username"] for r in diff.changes["new_followers"]], ["c"])
        self.assertEqual([r["username"] for r in diff.changes["lost_followers"]], ["b"])
        self.assertEqual(diff.changes["new_following"], [])

    def test_new_and_lost_following(self):
        prev = snap({}, {"1": user("a")})
        cur = snap({}, {"2": user("b")})
        diff = compute_diff(prev, cur, ALL_TRACK)
        self.assertEqual([r["username"] for r in diff.changes["new_following"]], ["b"])
        self.assertEqual([r["username"] for r in diff.changes["lost_following"]], ["a"])

    def test_track_subset_only_reports_selected(self):
        prev = snap({"1": user("a")}, {"1": user("a")})
        cur = snap({"2": user("b")}, {"2": user("b")})
        diff = compute_diff(prev, cur, ["new_followers"])
        self.assertEqual(set(diff.changes), {"new_followers"})
        self.assertEqual([r["username"] for r in diff.changes["new_followers"]], ["b"])

    def test_format_message_contains_changes(self):
        prev = snap({"1": user("a")}, {})
        cur = snap({"1": user("a"), "2": user("bob")}, {})
        diff = compute_diff(prev, cur, ALL_TRACK)
        msg = format_message("target", diff)
        self.assertIn("@target", msg)
        self.assertIn("新規フォロワー", msg)
        self.assertIn("@bob", msg)
        self.assertNotIn("フォロー解除", msg)  # empty categories are omitted


if __name__ == "__main__":
    unittest.main()
