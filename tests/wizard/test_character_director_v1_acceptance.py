import copy
import unittest

from tools.analyze_character_director_v1 import EXPECTED_SCENARIOS, analyze_v1


def channels(gaze, authoritative, blink, phase):
    return {
        "head_eye_phase": phase,
        "gaze_aim": gaze,
        "gaze_vertical_aim": 0,
        "gaze_authoritative": authoritative,
        "blink_closed": blink,
        "expression": "neutral",
        "rendered_mouth_shape": "closed",
        "speech_mouth_authority": "none",
        "locomotion": "idle",
        "action": "idle",
    }


class V1MachineAcceptanceTests(unittest.TestCase):
    def fixture(self):
        records = []

        def add(scenario, gaze, authoritative, blink, facing="south", phase="steady"):
            index = len(records)
            timestamp = "2026-07-18T00:00:{:02d}.000Z".format(index)
            records.append(
                {
                    "frame_index": index,
                    "scenario": scenario,
                    "received_at_utc": timestamp,
                    "world_root_x": 0.0,
                    "world_root_z": 5.0,
                    "presented_facing": facing,
                    "presentation_channels": channels(
                        gaze, authoritative, blink, phase
                    ),
                }
            )

        add(EXPECTED_SCENARIOS[0], 0, False, False)
        add(EXPECTED_SCENARIOS[0], 0, False, True)
        add(EXPECTED_SCENARIOS[0], 0, False, True)
        add(EXPECTED_SCENARIOS[1], -1, True, False)
        add(EXPECTED_SCENARIOS[1], -1, True, False)
        add(EXPECTED_SCENARIOS[2], 0, True, False)
        add(EXPECTED_SCENARIOS[2], 0, True, True)
        add(EXPECTED_SCENARIOS[2], 0, True, True)
        add(EXPECTED_SCENARIOS[3], 0, False, False)
        add(EXPECTED_SCENARIOS[4], -1, False, False, "south", "leading")
        add(EXPECTED_SCENARIOS[4], -1, False, False, "southwest", "turning")
        add(EXPECTED_SCENARIOS[4], 0, False, False, "west", "turning")
        add(EXPECTED_SCENARIOS[4], 0, False, False, "west", "settling")
        add(EXPECTED_SCENARIOS[4], 0, False, False, "west", "steady")

        scenarios = [{"name": name} for name in EXPECTED_SCENARIOS]
        commands = []
        for name in EXPECTED_SCENARIOS:
            selected = [item for item in records if item["scenario"] == name]
            commands.append(
                {
                    "scenario": name,
                    "capture_started_at_utc": selected[0]["received_at_utc"],
                    "capture_completed_at_utc": selected[-1]["received_at_utc"],
                }
            )
        manifest = {
            "scenario_program": {
                "program_id": "v1-listening",
                "acceptance_scenario": "V1",
                "total_duration_seconds": 12.0,
            },
            "scenarios": scenarios,
            "frames": [
                {
                    "frame_index": item["frame_index"],
                    "scenario": item["scenario"],
                    "received_at_utc": item["received_at_utc"],
                }
                for item in records
            ],
            "commands": commands,
            "init": {"fps": 24.0},
        }
        return manifest, records

    def test_accepts_complete_machine_verifiable_v1_sequence(self):
        manifest, records = self.fixture()

        report = analyze_v1(manifest, records)

        self.assertTrue(report["passed"])
        self.assertEqual(report["metrics"]["blink_count"], 2)
        self.assertEqual(
            report["metrics"]["turn_facing_sequence"],
            ["south", "southwest", "west"],
        )

    def test_rejects_late_gaze_snap_after_head_arrival(self):
        manifest, records = self.fixture()
        damaged = copy.deepcopy(records)
        first_west = next(
            item for item in damaged if item["presented_facing"] == "west"
        )
        first_west["presentation_channels"]["gaze_aim"] = -1

        report = analyze_v1(manifest, damaged)

        self.assertFalse(report["passed"])
        turn_check = next(
            item
            for item in report["checks"]
            if item["name"] == "ninety_degree_eye_lead_head_follow_settle"
        )
        self.assertFalse(turn_check["passed"])


if __name__ == "__main__":
    unittest.main()

