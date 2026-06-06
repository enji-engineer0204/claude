"""Orchestration tests for run_once using a fake Instagram client.

Verifies the baseline -> no-change -> change flow and that notifications are
only sent when there is a diff. No network / no instagrapi required.

Run with:  python -m unittest discover -s tests
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tracker import __main__ as main_mod
from tracker.config import Config, NotifierConfig


def _user(name):
    return {"username": name, "full_name": name.title()}


class FakeClient:
    """Stands in for InstagramClient. State is set per-test."""

    followers = {}
    following = {}

    def __init__(self, *args, **kwargs):
        pass

    def login(self):
        return self

    def resolve_target_user_id(self, target_username):
        return "999", target_username or "me"

    def fetch_followers(self, user_id, amount=0):
        return dict(FakeClient.followers)

    def fetch_following(self, user_id, amount=0):
        return dict(FakeClient.following)


class RunOnceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(
            session_id="dummy",
            target_username="",
            track=["new_following", "lost_following", "new_followers", "lost_followers"],
            notifier=NotifierConfig(type="discord", webhook_url="https://example/wh"),
            data_dir=self.tmp.name,
        )
        FakeClient.followers = {"1": _user("alice")}
        FakeClient.following = {"2": _user("bob")}

    def run_with_fakes(self, dry_run=False):
        with mock.patch.object(main_mod, "InstagramClient", FakeClient), \
             mock.patch.object(main_mod, "send_notification") as send:
            sent = main_mod.run_once(self.cfg, dry_run=dry_run)
        return sent, send

    def test_first_run_is_baseline_no_notify(self):
        sent, send = self.run_with_fakes()
        self.assertFalse(sent)
        send.assert_not_called()
        self.assertTrue((Path(self.tmp.name) / "snapshot_999.json").exists())

    def test_no_change_no_notify(self):
        self.run_with_fakes()  # baseline
        sent, send = self.run_with_fakes()
        self.assertFalse(sent)
        send.assert_not_called()

    def test_change_triggers_notification(self):
        self.run_with_fakes()  # baseline
        FakeClient.followers = {"1": _user("alice"), "3": _user("carol")}
        sent, send = self.run_with_fakes()
        send.assert_called_once()
        # The diff passed to the notifier should contain the new follower.
        _cfg, _username, diff = send.call_args.args
        self.assertEqual(
            [r["username"] for r in diff.changes["new_followers"]], ["carol"]
        )

    def test_dry_run_does_not_save_or_notify(self):
        FakeClient.followers = {"1": _user("alice")}
        sent, send = self.run_with_fakes(dry_run=True)
        self.assertFalse(sent)
        send.assert_not_called()
        self.assertFalse((Path(self.tmp.name) / "snapshot_999.json").exists())


if __name__ == "__main__":
    unittest.main()
