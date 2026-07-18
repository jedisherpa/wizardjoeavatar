import json
import shutil
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.character_package import WIZARD_JOE_PACKAGE_PATH, load_character_package
from wizard_avatar.commanding import CommandEnvelopeV1
from wizard_avatar.frame_source import ProceduralWizardFrameSource
from wizard_avatar.models import WizardCommand
from wizard_avatar.runtime import canonical_sha256
from wizard_avatar.stream import WizardFrameHub


class RuntimeProductionPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_frame_hub_command_flows_through_runtime_inbox_and_replay_log(self):
        source = ProceduralWizardFrameSource()
        hub = WizardFrameHub(source)
        command_id = "production-runtime-action-1"
        envelope = CommandEnvelopeV1(
            schema_version=1,
            command_id=command_id,
            source_id="production-contract-test",
            source_kind="api",
            source_sequence=1,
            source_epoch="production-contract-session",
            kind="action",
            payload={"action": "explaining", "duration_ms": 900},
            issued_tick=0,
            priority_class="user",
        )

        try:
            ack, result = await hub.apply_envelope(envelope)

            self.assertTrue(result.ok, result.message)
            self.assertEqual(ack.disposition, "applied")
            self.assertIs(hub.runtime.inbox, hub.command_inbox)
            self.assertEqual(hub.command_inbox.ack_for(command_id), ack)
            self.assertEqual(hub.command_inbox.pending_count, 0)
            self.assertGreaterEqual(hub.runtime.clock.simulation_tick, 1)
            self.assertEqual(
                hub.runtime.clock.state_revision,
                hub.runtime.clock.simulation_tick,
            )
            self.assertEqual(result.state["state_revision"], ack.state_revision)
            self.assertEqual(result.state["simulation_tick"], ack.apply_tick)
            self.assertEqual(source.current_state().action, "explaining")

            records = hub.replay_log.records
            command_records = [
                record
                for record in records
                if record["record_type"] == "command_ack"
                and record["payload"]["command"]["command_id"] == command_id
            ]
            applied_records = [
                record
                for record in records
                if record["record_type"] == "tick_state"
                and command_id in record["payload"]["applied_commands"]
            ]
            self.assertEqual(len(command_records), 1)
            self.assertEqual(len(applied_records), 1)
            self.assertEqual(applied_records[0]["payload"]["state"]["action"], "explaining")
            self.assertEqual(
                applied_records[0]["payload"]["state_hash"],
                canonical_sha256(applied_records[0]["payload"]["state"]),
            )
        finally:
            await hub.stop()

    async def test_invalid_ordered_command_is_rejected_without_stopping_runtime(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource())
        envelope = CommandEnvelopeV1(
            schema_version=1,
            command_id="production-invalid-move-1",
            source_id="production-contract-test",
            source_kind="api",
            source_sequence=1,
            source_epoch="production-invalid-session",
            kind="move",
            payload={"z": 4.0},
            issued_tick=0,
            priority_class="user",
        )

        try:
            ack, result = await hub.apply_envelope(envelope)

            self.assertFalse(result.ok)
            self.assertEqual(ack.disposition, "rejected")
            self.assertEqual(ack.error_code, "command_validation_failed")
            self.assertIsNotNone(hub._task)
            self.assertFalse(hub._task.done())
            tick_records = [
                record
                for record in hub.replay_log.records
                if record["record_type"] == "tick_state"
                and envelope.command_id in record["payload"]["applied_commands"]
            ]
            self.assertEqual(len(tick_records), 1)
            rejected_acks = tick_records[0]["payload"]["applied_acks"]
            self.assertEqual(rejected_acks[0]["disposition"], "rejected")
        finally:
            await hub.stop()

    async def test_browser_control_intent_survives_canonical_runtime_freezing(self):
        hub = WizardFrameHub(ProceduralWizardFrameSource())
        command = WizardCommand(
            "control",
            {
                "command_id": "browser-control-0",
                "source_id": "browser-production-test",
                "source_kind": "keyboard",
                "source_sequence": 0,
                "source_epoch": "browser-production-session",
                "lease_id": "browser-production-lease",
                "ttl_ms": 250,
                "intent": {
                    "move_x": 0.0,
                    "move_z": 0.0,
                    "ascend": 0.0,
                    "speed_mode": "walk",
                    "mobility_request": "keep",
                    "held_actions": [],
                },
            },
        )

        try:
            result = await hub.apply_command(command)

            self.assertTrue(result.ok, result.message)
            control_records = [
                record
                for record in hub.replay_log.records
                if record["record_type"] == "command_ack"
                and record["payload"]["command"]["kind"] == "control_intent"
            ]
            self.assertEqual(len(control_records), 1)
            self.assertEqual(
                control_records[0]["payload"]["command"]["payload"]["intent"]["speed_mode"],
                "walk",
            )
        finally:
            await hub.stop()

    async def test_ordered_speech_stop_preserves_performance_state_in_place(self):
        source = ProceduralWizardFrameSource()
        controller = source.controller
        controller.state.world_position = {"x": 0.42, "z": 4.25}
        controller.state.velocity = {"x": 0.35, "z": -0.1}
        controller.state.locomotion = "walking"
        controller.state.set_facing("east")
        controller.apply_command(WizardCommand("gaze", {"target": "right"}))
        controller.apply_command(
            WizardCommand(
                "action",
                {"action": "magic_cast", "duration_ms": 1800},
            )
        )
        controller.apply_command(
            WizardCommand(
                "speak",
                {"speech_id": "ordered-line", "text": "Hold the stage.", "duration_ms": 1800},
            )
        )
        before = controller.current_state().as_public_dict()
        hub = WizardFrameHub(source)
        envelope = CommandEnvelopeV1(
            schema_version=1,
            command_id="production-speech-stop-1",
            source_id="production-contract-test",
            source_kind="api",
            source_sequence=1,
            source_epoch="production-speech-stop-session",
            kind="speech_stop",
            payload={},
            issued_tick=0,
            priority_class="user",
        )

        try:
            ack, result = await hub.apply_envelope(envelope)

            self.assertTrue(result.ok, result.message)
            self.assertEqual(ack.disposition, "applied")
            state = source.current_state()
            self.assertIsNone(state.speech_id)
            self.assertIsNone(state.speech_text)
            self.assertEqual(state.mouth, "closed")
            self.assertLess(
                abs(state.world_position["x"] - before["world_position"]["x"]),
                0.02,
            )
            self.assertLess(
                abs(state.world_position["z"] - before["world_position"]["z"]),
                0.02,
            )
            self.assertNotEqual(state.world_position, {"x": 0.0, "z": 5.0})
            self.assertEqual(state.facing, before["facing"])
            self.assertEqual(state.gaze_aim, before["gaze_aim"])
            self.assertEqual(state.gaze_vertical_aim, before["gaze_vertical_aim"])
            self.assertEqual(state.gaze_authoritative, before["gaze_authoritative"])
            self.assertEqual(state.locomotion, before["locomotion"])
            self.assertEqual(state.action, before["action"])
        finally:
            await hub.stop()


class CharacterPackageGraphProductionPathTests(unittest.TestCase):
    def test_frame_source_uses_the_graph_declared_by_its_character_package(self):
        default_package = load_character_package()
        sentinel_pose = "feeling_joy_full"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pose_library_path = root / "poses.json"
            graph_path = root / "graph.json"
            package_path = root / "package.json"
            shutil.copy2(default_package.pose_library, pose_library_path)

            graph = json.loads(default_package.animation_graph.read_text(encoding="utf-8"))
            graph["pose_classification"][sentinel_pose] = dict(
                graph["pose_classification"]["front_idle"]
            )
            graph["clips"]["idle_front"]["samples"][0]["pose_id"] = sentinel_pose
            graph_path.write_text(json.dumps(graph), encoding="utf-8")

            package = json.loads(WIZARD_JOE_PACKAGE_PATH.read_text(encoding="utf-8"))
            package["pose_library"] = pose_library_path.name
            package["animation_graph"] = graph_path.name
            package_path.write_text(json.dumps(package), encoding="utf-8")

            source = ProceduralWizardFrameSource(character_package_path=package_path)
            source.render_current_frame()

        self.assertEqual(source.current_state().pose_id, sentinel_pose)


class SemanticActionProductionPathTests(unittest.TestCase):
    def test_every_action_declared_by_package_graph_is_reachable_through_action_api(self):
        source = ProceduralWizardFrameSource()
        graph = json.loads(source.character_package.animation_graph.read_text(encoding="utf-8"))
        declared_actions = sorted(
            {
                action
                for node in graph["nodes"].values()
                for action in node.get("actions", [])
            }
        )
        self.assertTrue(declared_actions)

        for action in declared_actions:
            with self.subTest(action=action):
                try:
                    result = source.apply_command_sync(
                        WizardCommand("action", {"action": action, "duration_ms": 900})
                    )
                except Exception as exc:  # The API contract must reject safely, never crash.
                    self.fail(
                        "package graph declares {!r}, but the action API crashed: {!r}".format(
                            action,
                            exc,
                        )
                    )
                self.assertTrue(
                    result.ok,
                    "package graph declares {!r}, but the action API rejected it: {}".format(
                        action,
                        result.message,
                    ),
                )
                self.assertEqual(source.current_state().action, action)


class ReferenceFaceProductionPathTests(unittest.TestCase):
    def test_reference_expression_command_changes_rendered_pixels(self):
        source = ProceduralWizardFrameSource()
        neutral_cells = source.render_current_frame().cells

        result = source.apply_command_sync(
            WizardCommand("expression", {"expression": "happy"})
        )
        happy_cells = source.render_current_frame().cells

        self.assertTrue(result.ok, result.message)
        self.assertEqual(source.current_state().expression, "happy")
        self.assertFalse(
            neutral_cells == happy_cells,
            msg="reference-pose expression state changed, but the rendered pixels did not",
        )

    def test_reference_blink_state_changes_rendered_pixels(self):
        source = ProceduralWizardFrameSource()
        state = source.current_state()
        state.time_seconds = 1.0
        state.blink_phase = 0.0
        open_cells = source.render_current_frame().cells

        state.time_seconds = 0.08
        state.blink_phase = 0.99
        blink_cells = source.render_current_frame().cells

        self.assertFalse(
            open_cells == blink_cells,
            msg="reference-pose blink state changed, but the rendered pixels did not",
        )


if __name__ == "__main__":
    unittest.main()
