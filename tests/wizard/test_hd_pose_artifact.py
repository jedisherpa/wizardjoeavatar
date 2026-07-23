import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from wizard_avatar.hd_pose_artifact import HDPoseArtifact, HDPoseLibrary, write_pose_artifact


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


if __name__ == "__main__":
    unittest.main()
