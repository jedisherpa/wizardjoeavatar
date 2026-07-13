import asyncio
import unittest

from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.protocol import TAG_DELTA, decode_frame
from wizard_avatar.stream import WizardFrameHub


class StreamHubTests(unittest.IsolatedAsyncioTestCase):
    async def test_commands_can_contend_with_frame_loop(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource(fps=60))
        subscriber = await hub.subscribe()
        try:
            poses = ("front_idle", "back_idle", "profile_left", "profile_right")
            for _ in range(4):
                for pose_id in poses:
                    result = await asyncio.wait_for(
                        hub.apply_command(
                            WizardCommand("pose", {"pose_id": pose_id, "duration_ms": 300})
                        ),
                        timeout=1.0,
                    )
                    self.assertTrue(result.ok, result.message)
            self.assertIs(hub._lock_loop, asyncio.get_running_loop())
        finally:
            hub.unsubscribe(subscriber)
            await hub.stop()

    async def test_subscribers_receive_decodable_contiguous_frames(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource(fps=24))
        first = await hub.subscribe()
        second = await hub.subscribe()
        try:
            messages_a = [await asyncio.wait_for(first.queue.get(), timeout=1.0) for _ in range(4)]
            messages_b = [await asyncio.wait_for(second.queue.get(), timeout=1.0) for _ in range(4)]
            prev_a = None
            prev_b = None
            frames_a = []
            frames_b = []
            for message_a, message_b in zip(messages_a, messages_b):
                index_a, prev_a = decode_frame(message_a, prev_a)
                index_b, prev_b = decode_frame(message_b, prev_b)
                frames_a.append(index_a)
                frames_b.append(index_b)
                self.assertEqual(prev_a, prev_b)
            self.assertEqual(frames_a, frames_b)
            self.assertEqual(frames_a, list(range(frames_a[0], frames_a[0] + 4)))
        finally:
            hub.unsubscribe(first)
            hub.unsubscribe(second)
            await hub.stop()

    async def test_resync_enqueues_keyframe_for_one_subscriber(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource(fps=24))
        subscriber = await hub.subscribe()
        try:
            await asyncio.wait_for(subscriber.queue.get(), timeout=1.0)
            await hub.enqueue_keyframe(subscriber)
            message = await asyncio.wait_for(subscriber.queue.get(), timeout=1.0)
            self.assertNotEqual(message[4], TAG_DELTA)
            _, decoded = decode_frame(message, None)
            self.assertEqual(len(decoded), 240 * 135 * 4)
        finally:
            hub.unsubscribe(subscriber)
            await hub.stop()

    async def test_frame_loop_does_not_replay_missed_deadlines(self):
        source = ProceduralWizardFrameSource(fps=24)
        original_next_frame = source.next_encoded_frame

        async def delayed_next_frame(*args, **kwargs):
            await asyncio.sleep(0.06)
            return await original_next_frame(*args, **kwargs)

        source.next_encoded_frame = delayed_next_frame
        hub = WizardFrameHub(source)
        subscriber = await hub.subscribe()
        try:
            await asyncio.sleep(0.34)
            published = hub._published_frames
            self.assertGreaterEqual(hub._schedule_overruns, 1)
            self.assertGreaterEqual(published, 3)
            self.assertLessEqual(published, 5)

            before = source.current_state().time_seconds
            await asyncio.sleep(0.12)
            elapsed_simulation = source.current_state().time_seconds - before
            self.assertLess(elapsed_simulation, 0.13)
        finally:
            hub.unsubscribe(subscriber)
            await hub.stop()


if __name__ == "__main__":
    unittest.main()
