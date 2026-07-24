import copy
import unittest

from tools.analyze_character_director_v10 import (
    EXPECTED_FRAME_COUNTS,
    EXPECTED_SCENARIOS,
    EXPECTED_TARGETS,
    EXPECTED_TOTAL_FRAMES,
    analyze_v10,
)


MANIFEST_SHA256 = "a" * 64
CANDIDATE = "b" * 40
RUN_ID = "visual-review-v10-fixture"


def fixture():
    manifest = {
        "source_epoch": RUN_ID,
        "provenance": {"head": CANDIDATE},
        "scenario_program": {
            "schema": "character_director_scenario_program_v2",
            "schema_version": 2,
            "program_id": "v10-responsive-framing",
            "acceptance_scenario": "V10",
            "scenario_count": 5,
            "maximum_capture_frame_count": EXPECTED_TOTAL_FRAMES,
        },
        "scenarios": [
            {
                "name": name,
                "kind": "reset" if name == "v10-center" else "move",
                "payload": {},
                "timing": {"capture_frames": EXPECTED_FRAME_COUNTS[name]},
            }
            for name in EXPECTED_SCENARIOS
        ],
        "init": {"cols": 240, "rows": 135, "fps": 24.0},
        "contact_verification": {"passed": True},
        "frames": [],
    }
    spans = {
        "v10-center": (79, 160, 22, 126, 1.125),
        "v10-near": (73, 166, 7, 126, 1.284),
        "v10-far": (95, 144, 25, 88, 0.675),
        "v10-left-edge": (12, 92, 22, 126, 1.125),
        "v10-right-edge": (148, 227, 22, 126, 1.125),
    }
    traces = []
    frame_index = 0
    for scenario in EXPECTED_SCENARIOS:
        min_x, max_x, min_y, max_y, scale = spans[scenario]
        root_x, root_z = EXPECTED_TARGETS[scenario]
        for _ in range(EXPECTED_FRAME_COUNTS[scenario]):
            manifest["frames"].append(
                {
                    "frame_index": frame_index,
                    "capture_owned": True,
                    "scenario": scenario,
                }
            )
            traces.append(
                {
                    "frame_index": frame_index,
                    "world_root_x": root_x,
                    "world_root_z": root_z,
                    "render_scale": scale,
                    "silhouette_raster_span": {
                        "min_x": min_x,
                        "max_x": max_x,
                        "min_y": min_y,
                        "max_y": max_y,
                    },
                }
            )
            frame_index += 1
    return manifest, traces, browser_profiles()


def browser_profile(name, width, height, dpr, mobile, canvas_rect, device_cell):
    canvas_x, canvas_y, canvas_width, canvas_height = canvas_rect
    backing_width = 240 * device_cell
    backing_height = 135 * device_cell
    toolbar = (
        {"x": 8, "y": 784, "width": 374, "height": 52}
        if mobile
        else {"x": 414, "y": 656, "width": 452, "height": 52}
    )
    status = (
        {"x": 8, "y": 8, "width": 374, "height": 52}
        if mobile
        else {"x": 548, "y": 12, "width": 183, "height": 52}
    )
    canvas = {
        "x": canvas_x,
        "y": canvas_y,
        "width": canvas_width,
        "height": canvas_height,
        "backingWidth": backing_width,
        "backingHeight": backing_height,
        "imageRendering": "pixelated",
        "imageSmoothingEnabled": False,
    }
    canvas_metrics = {
        "cols": 240,
        "rows": 135,
        "dpr": dpr,
        "deviceCell": device_cell,
        "backingWidth": backing_width,
        "backingHeight": backing_height,
        "cssWidth": "{}px".format(canvas_width),
        "cssHeight": "{}px".format(canvas_height),
        "verticalUiReserveCssPx": 144,
        "safeViewportHeight": height - 144,
    }
    return {
        "schema": "character_director_browser_layout_v1",
        "schema_version": 1,
        "run_id": RUN_ID,
        "candidate_commit": CANDIDATE,
        "capture_manifest_sha256": MANIFEST_SHA256,
        "viewport_profile": {
            "name": name,
            "width": width,
            "height": height,
            "device_scale_factor": dpr,
            "mobile": mobile,
        },
        "layout": {
            "viewport": {"width": width, "height": height, "dpr": dpr},
            "canvas": canvas,
            "toolbar": toolbar,
            "mediaStatus": status,
        },
        "frame_count": EXPECTED_TOTAL_FRAMES,
        "expected_frame_count": EXPECTED_TOTAL_FRAMES,
        "final_client_metrics": {
            "decodeErrorCount": 0,
            "droppedFrames": 0,
            "rawMessagesDropped": 0,
            "resyncCount": 0,
            "waitingForKeyframe": False,
            "canvas": canvas_metrics,
        },
        "page_errors": [],
        "console_events": [],
    }


def browser_profiles():
    return [
        browser_profile(
            "desktop-dpr1",
            1280,
            720,
            1.0,
            False,
            (160, 90, 960, 540),
            4,
        ),
        browser_profile(
            "desktop-dpr2",
            1280,
            720,
            2.0,
            False,
            (160, 90, 960, 540),
            8,
        ),
        browser_profile(
            "mobile-390x844-dpr3",
            390,
            844,
            3.0,
            True,
            (35, 332, 320, 180),
            4,
        ),
    ]


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


class CharacterDirectorV10AcceptanceTests(unittest.TestCase):
    def test_responsive_framing_matrix_passes(self):
        manifest, traces, profiles = fixture()

        report = analyze_v10(manifest, traces, profiles, MANIFEST_SHA256)

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["metrics"]["owned_frame_count"], 528)

    def test_cropped_silhouette_fails_closed(self):
        manifest, traces, profiles = fixture()
        broken = copy.deepcopy(traces)
        broken[0]["silhouette_raster_span"]["min_x"] = 3

        report = analyze_v10(manifest, broken, profiles, MANIFEST_SHA256)

        self.assertFalse(report["passed"])
        self.assertFalse(check(report, "canonical_silhouette_margins")["passed"])

    def test_wrong_device_profile_fails_closed(self):
        manifest, traces, profiles = fixture()
        broken = copy.deepcopy(profiles)
        broken[1]["layout"]["viewport"]["dpr"] = 1.0

        report = analyze_v10(manifest, traces, broken, MANIFEST_SHA256)

        self.assertFalse(report["passed"])
        matrix = check(report, "responsive_browser_profile_matrix")
        self.assertFalse(matrix["passed"])

    def test_avatar_control_overlap_fails_closed(self):
        manifest, traces, profiles = fixture()
        broken = copy.deepcopy(profiles)
        broken[0]["layout"]["mediaStatus"] = {
            "x": 500,
            "y": 100,
            "width": 280,
            "height": 100,
        }

        report = analyze_v10(manifest, traces, broken, MANIFEST_SHA256)

        self.assertFalse(report["passed"])
        desktop = report["metrics"]["browser_profiles"][0]
        self.assertFalse(desktop["checks"]["avatar_avoids_controls"])

    def test_nonintegral_physical_projection_fails_closed(self):
        manifest, traces, profiles = fixture()
        broken = copy.deepcopy(profiles)
        broken[1]["final_client_metrics"]["canvas"]["backingWidth"] = 1919

        report = analyze_v10(manifest, traces, broken, MANIFEST_SHA256)

        self.assertFalse(report["passed"])
        desktop = report["metrics"]["browser_profiles"][1]
        self.assertFalse(
            desktop["checks"]["integer_physical_pixel_projection"]
        )

    def test_browser_transport_drop_fails_closed(self):
        manifest, traces, profiles = fixture()
        broken = copy.deepcopy(profiles)
        broken[2]["final_client_metrics"]["droppedFrames"] = 1

        report = analyze_v10(manifest, traces, broken, MANIFEST_SHA256)

        self.assertFalse(report["passed"])
        mobile = report["metrics"]["browser_profiles"][2]
        self.assertFalse(mobile["checks"]["runtime_integrity"])


if __name__ == "__main__":
    unittest.main()
