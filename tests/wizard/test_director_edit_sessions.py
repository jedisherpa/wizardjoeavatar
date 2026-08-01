import copy
import unittest

from tests.wizard.test_performance_context import context_mapping
from wizard_avatar.director_edit_sessions import (
    DirectorEditSessionError,
    DirectorEditSessionStore,
)
from wizard_avatar.performance_context import PerformanceContextV1


def portable_score():
    return {
        "score_id": "score:director-session-test",
        "revision": 1,
        "tracks": [
            {
                "kind": "gesture",
                "cues": [
                    {
                        "cue_id": "cue:director-session-test",
                        "intent": "explain",
                        "start_ms": 100,
                        "end_ms": 400,
                        "amplitude_milli": 500,
                        "capability_requirements": ["clip:private-render-id"],
                        "manual": {"locked": False, "disabled": False},
                        "phase_ranges": {"stroke": [100, 400]},
                    }
                ],
            }
        ],
    }


class DirectorEditSessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.context = PerformanceContextV1.from_mapping(context_mapping())

    def create(self, store, suffix, now):
        return store.create(
            source_slot="main",
            media_id="media:sha256:" + suffix * 64,
            media_sha256="sha256:" + suffix * 64,
            snapshot_fingerprint=suffix * 64,
            portable_score=portable_score(),
            compiler_context=self.context,
            now_monotonic_us=now,
        )

    def test_capacity_expiry_and_content_safe_inspection(self):
        store = DirectorEditSessionStore(capacity=2, ttl_us=100)
        first = self.create(store, "1", 0)
        self.create(store, "2", 1)
        third = self.create(store, "3", 2)

        with self.assertRaises(DirectorEditSessionError) as evicted:
            store.require(first.session_id, 2)
        self.assertEqual(evicted.exception.code, "edit_session_not_found")
        inspection = third.safe_inspection(2)
        self.assertEqual(len(store), 2)
        self.assertEqual(inspection["expires_in_ms"], 0)
        self.assertIn("disabled", inspection["cues"][0]["edit_preconditions"])
        self.assertNotIn("capability_requirements", inspection["cues"][0])

        with self.assertRaises(DirectorEditSessionError) as expired:
            store.require(third.session_id, 102)
        self.assertEqual(expired.exception.code, "edit_session_not_found")

    def test_replacement_uses_new_revision_and_defensive_score_copy(self):
        store = DirectorEditSessionStore(capacity=2, ttl_us=1_000)
        session = self.create(store, "4", 10)
        revised = copy.deepcopy(portable_score())
        revised["revision"] = 2
        replacement = store.replace_score(
            session.session_id,
            portable_score=revised,
            compiler_context=self.context,
            now_monotonic_us=20,
        )
        revised["revision"] = 99

        self.assertEqual(replacement.portable_score["revision"], 2)
        self.assertEqual(
            store.require(session.session_id, 21).portable_score["revision"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
