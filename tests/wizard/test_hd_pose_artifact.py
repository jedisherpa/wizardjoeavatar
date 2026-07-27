import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from wizard_avatar.hd_pose_artifact import (
    HDPoseArtifact,
    HDPoseLibrary,
    write_pose_artifact,
    write_pose_artifact_from_loader,
)


class HDPoseArtifactTests(unittest.TestCase):
    def test_each_pose_round_trips_and_loads_lazily(self):
        first = Image.new("RGBA", (32, 24), (0, 0, 0, 0))
        second = Image.new("RGBA", (32, 24), (0, 0, 0, 0))
        ImageDraw.Draw(first).rectangle((2, 3, 20, 18), fill=(10, 80, 200, 255))
        ImageDraw.Draw(second).ellipse((8, 4, 25, 21), fill=(220, 60, 40, 255))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "poses.wjpose"
            receipt = write_pose_artifact(
                path,
                {"second": second, "first": first},
                profile={"profile_id": "test", "canvas_width": 32, "canvas_height": 24},
                provenance={"source_sha256": "abc"},
            )
            artifact = HDPoseArtifact(path, cache_size=1)

            self.assertEqual(receipt["pose_ids"], ["first", "second"])
            self.assertEqual(set(artifact.records), {"first", "second"})
            self.assertEqual(artifact.header["payload_encoding"], "rgba8-zlib")
            self.assertEqual(artifact._cache, {})
            self.assertEqual(artifact.load_rgba("first"), first.tobytes())
            self.assertEqual(artifact.load_pose("first").tobytes(), first.tobytes())
            self.assertEqual(list(artifact._cache), ["first"])
            self.assertEqual(artifact.load_pose("second").tobytes(), second.tobytes())
            self.assertEqual(list(artifact._cache), ["second"])

    def test_rejects_pose_with_wrong_canvas(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "does not match"):
                write_pose_artifact(
                    Path(directory) / "poses.wjpose",
                    {"bad": Image.new("RGBA", (2, 2))},
                    profile={"profile_id": "test", "canvas_width": 4, "canvas_height": 4},
                    provenance={},
                )

    def test_streaming_writer_loads_one_sorted_pose_at_a_time(self):
        active = 0
        maximum_active = 0
        load_order = []

        def load_pose(pose_id):
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            load_order.append(pose_id)
            image = Image.new("RGBA", (8, 8), (len(pose_id), 20, 30, 255))
            active -= 1
            return image

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "streamed.wjpose"
            receipt = write_pose_artifact_from_loader(
                path,
                ["third", "first", "second"],
                load_pose=load_pose,
                profile={
                    "profile_id": "streamed-test",
                    "canvas_width": 8,
                    "canvas_height": 8,
                },
                provenance={"source": "test"},
            )

            self.assertEqual(load_order, ["first", "second", "third"])
            self.assertEqual(maximum_active, 1)
            self.assertEqual(receipt["pose_ids"], load_order)
            self.assertEqual(
                set(HDPoseArtifact(path).records),
                {"first", "second", "third"},
            )

    def test_streaming_writer_rejects_duplicate_pose_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "must be unique"):
                write_pose_artifact_from_loader(
                    Path(directory) / "duplicate.wjpose",
                    ["same", "same"],
                    load_pose=lambda _: Image.new("RGBA", (8, 8)),
                    profile={
                        "profile_id": "streamed-test",
                        "canvas_width": 8,
                        "canvas_height": 8,
                    },
                    provenance={},
                )

    def test_sharded_library_indexes_poses_and_preserves_approval_state(self):
        image = Image.new("RGBA", (8, 8), (10, 20, 30, 255))
        profile = {"profile_id": "test", "canvas_width": 8, "canvas_height": 8}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_path = root / "approved.wjpose"
            receipt = write_pose_artifact(
                artifact_path,
                {"001_idle": image},
                profile=profile,
                provenance={"source": "test"},
            )
            index = {
                "profile": profile,
                "pose_count": 1,
                "shards": [
                    {
                        "shard_id": "approved",
                        "path": artifact_path.name,
                        "sha256": receipt["sha256"],
                        "pose_ids": ["001_idle"],
                        "source": "production",
                        "approval_state": "approved_production_alpha",
                        "runtime_admitted": False,
                    }
                ],
            }
            index_path = root / "library-index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")

            library = HDPoseLibrary(index_path)

            self.assertEqual(library.pose_ids, ("001_idle",))
            self.assertEqual(library.load_rgba("001_idle"), image.tobytes())
            self.assertEqual(
                library.pose_metadata["001_idle"]["approval_state"],
                "approved_production_alpha",
            )
            self.assertEqual(
                library.pose_metadata["001_idle"]["artifact_sha256"],
                hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            )

    def test_sharded_library_rejects_path_escape(self):
        profile = {"profile_id": "test", "canvas_width": 8, "canvas_height": 8}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "library-index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "profile": profile,
                        "pose_count": 1,
                        "shards": [
                            {
                                "shard_id": "escaped",
                                "path": "../escaped.wjpose",
                                "sha256": "0" * 64,
                                "pose_ids": ["escaped"],
                                "source": "test",
                                "approval_state": "candidate",
                                "runtime_admitted": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "escapes library root"):
                HDPoseLibrary(index_path)


if __name__ == "__main__":
    unittest.main()
