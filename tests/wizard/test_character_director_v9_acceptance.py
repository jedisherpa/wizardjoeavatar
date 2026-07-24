import copy
import unittest

from tools.analyze_character_director_v9 import (
    CAPTURE_FRAMES,
    PROFILE_ORDER,
    SCENARIOS,
    analyze_v9,
)
from tools.prepare_character_director_v9_fixture import build_scenario_program, load_score


def fixture():
    program = build_scenario_program(load_score())
    commands = []
    for source_sequence, operation in enumerate(
        [
            item
            for scenario in program["scenarios"]
            for item in [scenario]
            + [
                {
                    "kind": scheduled["kind"],
                    "payload": scheduled["payload"],
                }
                for scheduled in scenario["timing"]["scheduled_commands"]
            ]
        ],
        start=1,
    ):
        payload = operation["payload"]
        commands.append(
            {
                "kind": "media_session",
                "transport": "media_session",
                "source_sequence": source_sequence,
                "payload": payload,
                "ack": {
                    "disposition": "accepted",
                    "accepted_sequence": payload["sequence"],
                    "accepted_media_epoch": payload["media_epoch"],
                },
            }
        )

    manifest = {
        "scenario_program": {
            "schema": "character_director_scenario_program_v2",
            "schema_version": 2,
            "program_id": "v9-accessibility-profiles",
            "acceptance_scenario": "V9",
            "scenario_count": 3,
            "maximum_capture_frame_count": 648,
        },
        "commands": commands,
        "init": {"cols": 240, "rows": 135, "fps": 24.0},
        "contact_verification": {"passed": True},
        "frames": [],
    }
    traces = []
    global_frame = 0
    for profile, scenario in zip(PROFILE_ORDER, SCENARIOS):
        for local_frame in range(CAPTURE_FRAMES):
            manifest["frames"].append(
                {
                    "frame_index": global_frame,
                    "capture_owned": True,
                    "scenario": scenario,
                }
            )
            body_active = (
                12 <= local_frame < 53
                or 62 <= local_frame < 92
                or 100 <= local_frame < 125
                or 134 <= local_frame < 192
            )
            if profile == "full" and 12 <= local_frame < 53:
                action = "magic_cast"
            elif profile == "full" and 62 <= local_frame < 92:
                action = "explaining"
            elif profile == "full" and 100 <= local_frame < 125:
                action = "pointing"
            elif profile == "full" and 134 <= local_frame < 192:
                action = "walking"
            else:
                action = "idle"
            locomotion = (
                "walking"
                if profile == "full" and 134 <= local_frame < 192
                else "idle"
            )
            speech = 5 <= local_frame < 134
            gaze = 1 if local_frame >= 96 else 0
            if profile == "full":
                owned = (
                    ["body", "effects", "gesture"]
                    if local_frame < 53 and local_frame >= 12
                    else ["body", "gesture"]
                    if 62 <= local_frame < 125
                    else ["locomotion", "stage"]
                    if 134 <= local_frame < 192
                    else []
                )
            else:
                owned = []
            if speech:
                owned += ["face", "gaze", "eyes", "speech", "mouth"]
            owned = sorted(set(owned))
            suppressions = (
                ["accessibility_projection", "motion_profile_projection"]
                if profile != "full" and body_active
                else []
            )
            root_x = (
                120.0 + max(0, local_frame - 134) * 0.2
                if profile == "full"
                else 120.0
            )
            mouth_phase = (local_frame // 7) % 4
            traces.append(
                {
                    "frame_index": global_frame,
                    "performance_motion_profile": profile,
                    "performance_resolution_hash": "sha256:"
                    + {
                        "full": "1",
                        "reduced": "2",
                        "still": "3",
                    }[profile]
                    * 63
                    + str(mouth_phase),
                    "performance_owned_channels": owned,
                    "performance_suppression_codes": suppressions,
                    "rendered_pose_id": action,
                    "effect_intensity": (
                        0.8
                        if profile == "full" and 18 <= local_frame < 36
                        else 0.0
                    ),
                    "presented_root_stage": {"x": root_x, "y": 126.0},
                    "silhouette_raster_span": {
                        "min_x": 70,
                        "max_x": 170,
                        "min_y": 10,
                        "max_y": 126,
                    },
                    "presentation_channels": {
                        "action": action,
                        "locomotion": locomotion,
                        "body_pixel_sha256": (
                            "body-{}".format(local_frame)
                            if profile == "full" and body_active
                            else "body-stable"
                        ),
                        "mouth_pixel_sha256": (
                            "mouth-{}".format(mouth_phase)
                            if speech
                            else "mouth-rest"
                        ),
                        "mouth_painted_cells": 4 if speech else 0,
                        "gaze_aim": gaze,
                        "expression": "explaining" if speech else "neutral",
                    },
                }
            )
            global_frame += 1
    return manifest, traces


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV9AcceptanceTests(unittest.TestCase):
    def test_three_profile_accessibility_proof_passes(self):
        manifest, traces = fixture()

        report = analyze_v9(manifest, traces)

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["full"]["frame_count"], CAPTURE_FRAMES)

    def test_reduced_body_motion_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        reduced_start = CAPTURE_FRAMES
        broken[reduced_start + 80]["presentation_channels"][
            "body_pixel_sha256"
        ] = "body-moved"

        report = analyze_v9(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(
            check(report, "reduced_and_still_suppress_all_body_motion")["passed"]
        )

    def test_missing_mouth_acting_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        still_start = CAPTURE_FRAMES * 2
        for trace in broken[still_start : still_start + 134]:
            trace["presentation_channels"]["mouth_pixel_sha256"] = "mouth-rest"
            trace["presentation_channels"]["mouth_painted_cells"] = 0

        report = analyze_v9(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(
            check(
                report,
                "speech_face_mouth_and_gaze_intent_survive_projection",
            )["passed"]
        )

    def test_wrong_media_ack_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(manifest)
        broken["commands"][9]["ack"]["disposition"] = "applied"

        report = analyze_v9(broken, traces)

        self.assertFalse(report["passed"])
        self.assertFalse(
            check(report, "one_authenticated_score_bound_media_replay")["passed"]
        )


if __name__ == "__main__":
    unittest.main()
