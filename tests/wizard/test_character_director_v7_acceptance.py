import copy
import unittest

from tools.analyze_character_director_v7 import (
    EXPECTED_FRAME_COUNTS,
    EXPECTED_MARKERS,
    EXPECTED_SCENARIOS,
    analyze_v7,
)


def fixture():
    manifest = {
        "scenario_program": {
            "program_id": "v7-cast-interruption",
            "acceptance_scenario": "V7",
            "total_duration_seconds": 6.375,
        },
        "scenarios": [{"name": name} for name in EXPECTED_SCENARIOS],
        "init": {"cols": 240, "rows": 135, "fps": 24.0},
        "frames": [],
    }
    traces = []
    frame_index = 0

    def append(scenario, *, clip="idle_front", action="idle", authority="none",
               effect_phase="inactive", effect_intensity=0.0, markers=()):
        nonlocal frame_index
        manifest["frames"].append(
            {"frame_index": frame_index, "capture_owned": True, "scenario": scenario}
        )
        traces.append(
            {
                "frame_index": frame_index,
                "animation_clip_id": clip,
                "rendered_pose_id": "cast_front_08" if clip == "cast_front" else "front_idle",
                "effect_phase": effect_phase,
                "effect_intensity": effect_intensity,
                "presentation_marker_events": [
                    {
                        "marker_id": marker,
                        "animation_authored_frame": authored,
                    }
                    for marker, authored in markers
                ],
                "presented_root_stage": {"x": 120.0, "y": 126.0},
                "silhouette_raster_span": {
                    "min_x": 78,
                    "max_x": 164,
                    "min_y": 18,
                    "max_y": 126,
                },
                "presentation_channels": {
                    "action": action,
                    "speech_mouth_authority": authority,
                },
            }
        )
        frame_index += 1

    for scenario in EXPECTED_SCENARIOS:
        count = EXPECTED_FRAME_COUNTS[scenario]
        for local in range(count):
            if scenario == "v7-precommit-cast":
                append(scenario, clip="cast_front", action="magic_cast")
            elif scenario == "v7-precommit-new-turn" and local < 22:
                append(scenario, action="speaking", authority="local_fallback")
            elif scenario == "v7-postcommit-cast":
                markers = ()
                if local == 4:
                    markers = (("action_commit", 10),)
                if local == 5:
                    markers = (("action_effect", 14),)
                append(
                    scenario,
                    clip="cast_front",
                    action="magic_cast",
                    effect_phase="stroke" if local == 5 else "inactive",
                    effect_intensity=1.0 if local == 5 else 0.0,
                    markers=markers,
                )
            elif scenario == "v7-postcommit-new-turn":
                if local == 2:
                    append(
                        scenario,
                        clip="cast_front",
                        action="magic_cast",
                        effect_phase="recovery",
                        effect_intensity=0.4,
                        markers=(("action_recoverable", 23),),
                    )
                elif local == 4:
                    append(
                        scenario,
                        clip="cast_front",
                        action="magic_cast",
                        markers=(("action_settled", 28),),
                    )
                elif 5 <= local < 27:
                    append(scenario, action="speaking", authority="local_fallback")
                else:
                    append(scenario)
            else:
                append(scenario)
    return manifest, traces


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV7AcceptanceTests(unittest.TestCase):
    def test_pre_and_post_commit_interruptions_pass(self):
        manifest, traces = fixture()
        report = analyze_v7(manifest, traces)
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["postcommit_marker_count"], 4)

    def test_precommit_stale_effect_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        target = next(
            trace
            for trace in broken
            if trace["frame_index"] == EXPECTED_FRAME_COUNTS["v7-ready"] + 4
        )
        target["effect_phase"] = "stroke"
        target["effect_intensity"] = 1.0
        target["presentation_marker_events"] = [
            {"marker_id": "action_effect", "animation_authored_frame": 14}
        ]

        report = analyze_v7(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "precommit_interrupt_cancels_without_effect")["passed"])

    def test_postcommit_speech_before_settle_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        start = sum(
            EXPECTED_FRAME_COUNTS[name]
            for name in EXPECTED_SCENARIOS[:6]
        )
        broken[start]["presentation_channels"] = {
            "action": "speaking",
            "speech_mouth_authority": "local_fallback",
        }
        broken[start]["animation_clip_id"] = "idle_front"

        report = analyze_v7(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(
            check(report, "postcommit_interrupt_finishes_recovery_then_speaks")["passed"]
        )

    def test_missing_recovery_marker_fails_closed(self):
        manifest, traces = fixture()
        broken = copy.deepcopy(traces)
        event_trace = next(
            trace
            for trace in broken
            if any(
                event["marker_id"] == EXPECTED_MARKERS[2]
                for event in trace["presentation_marker_events"]
            )
        )
        event_trace["presentation_marker_events"] = []

        report = analyze_v7(manifest, broken)

        self.assertFalse(report["passed"])
        self.assertFalse(
            check(report, "postcommit_interrupt_finishes_recovery_then_speaks")["passed"]
        )


if __name__ == "__main__":
    unittest.main()
