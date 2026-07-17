import asyncio
import copy
import threading
import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardState
from wizard_avatar.runtime import canonical_sha256
from wizard_avatar.stream import WizardFrameHub


class WizardStateSerializationPurityTests(unittest.TestCase):
    def test_as_public_dict_reconciles_compatibility_without_mutating_state(self):
        state = WizardState(
            action="walking",
            locomotion="idle",
            upper_body_action="explain",
            staff_state="point",
            action_until=4.5,
            action_restore={"action": "explaining"},
        )
        before = copy.deepcopy(state)
        before_hash = canonical_sha256(state)

        public = state.as_public_dict()

        self.assertEqual(state, before)
        self.assertEqual(canonical_sha256(state), before_hash)
        self.assertEqual(public["action"], "idle")
        self.assertEqual(public["upper_body_action"], "none")
        self.assertEqual(public["staff_state"], "held")
        self.assertEqual(public["action_until"], 0.0)
        self.assertIsNone(public["action_restore"])


class FrameSourceSnapshotPurityTests(unittest.TestCase):
    def setUp(self):
        self.source = ProceduralWizardFrameSource(180, 101, 24)
        state = self.source.current_state()
        state.action = "walking"
        state.locomotion = "idle"
        state.upper_body_action = "explain"
        state.staff_state = "point"
        state.action_until = 4.5
        state.action_restore = {"action": "explaining"}

    def _assert_state_unchanged(self, operation):
        state = self.source.current_state()
        before = copy.deepcopy(state)
        before_hash = canonical_sha256(state)

        result = operation()

        self.assertIs(self.source.current_state(), state)
        self.assertEqual(state, before)
        self.assertEqual(canonical_sha256(state), before_hash)
        return result

    def test_render_current_frame_does_not_mutate_authoritative_state(self):
        frame = self._assert_state_unchanged(self.source.render_current_frame)
        self.assertGreater(frame.raw_size, 0)

    def test_diagnostics_dict_does_not_mutate_authoritative_state(self):
        diagnostics = self._assert_state_unchanged(self.source.diagnostics_dict)
        self.assertIn("pose_id", diagnostics)

    def test_public_serialization_does_not_diverge_runtime_hash(self):
        hub = WizardFrameHub(self.source)
        snapshot = hub.runtime.current_snapshot()
        self.assertEqual(
            canonical_sha256(self.source.current_state()),
            snapshot.state_hash,
        )

        self._assert_state_unchanged(self.source.render_current_frame)
        self._assert_state_unchanged(self.source.diagnostics_dict)
        self._assert_state_unchanged(self.source.current_state().as_public_dict)

        self.assertEqual(hub.runtime.current_snapshot().state_hash, snapshot.state_hash)
        self.assertEqual(
            canonical_sha256(self.source.current_state()),
            snapshot.state_hash,
        )


class SynchronousEncodedFrameTests(unittest.TestCase):
    def test_sync_encoded_frame_matches_async_wrapper(self):
        sync_source = ProceduralWizardFrameSource(180, 101, 24)
        async_source = ProceduralWizardFrameSource(180, 101, 24)

        sync_message, sync_frame = sync_source.next_encoded_frame_sync(
            codec="adaptive",
            advance=True,
        )

        async def get_frame():
            return await async_source.next_encoded_frame(
                codec="adaptive",
                advance=True,
            )

        async_message, async_frame = asyncio.run(get_frame())

        self.assertEqual(sync_message, async_message)
        self.assertEqual(sync_frame, async_frame)
        self.assertEqual(
            sync_source.current_state().as_public_dict(),
            async_source.current_state().as_public_dict(),
        )

    def test_sync_encoded_frame_needs_no_worker_event_loop(self):
        source = ProceduralWizardFrameSource(180, 101, 24)
        results = []

        def render_in_worker():
            with self.assertRaises(RuntimeError):
                asyncio.get_running_loop()
            results.append(source.next_encoded_frame_sync(advance=False))

        worker = threading.Thread(target=render_in_worker)
        worker.start()
        worker.join(timeout=10)

        self.assertFalse(worker.is_alive())
        self.assertEqual(len(results), 1)
        self.assertGreater(len(results[0][0]), 0)


if __name__ == "__main__":
    unittest.main()
