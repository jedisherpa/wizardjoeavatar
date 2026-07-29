from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from tools.recover_kingfisher_review_library import (
    _load_archive_frames,
    _validate_live_profile,
    recover_library,
)


def _runtime_png() -> bytes:
    payload = io.BytesIO()
    Image.new("RGBA", (960, 540), (0, 0, 0, 0)).save(
        payload,
        format="PNG",
    )
    return payload.getvalue()


def _frame_metadata(runtime_id: int) -> dict[str, object]:
    return {
        "runtime_id": runtime_id,
        "source_pack": "kingfisher",
        "pose_id": (
            f"kingfisher_{runtime_id:03d}_act{runtime_id:03d}_test_"
            "alpha_registered_v001"
        ),
        "runtime_size": [960, 540],
    }


def _profile(pose_count: int) -> dict[str, object]:
    pose_ids = [
        f"kingfisher.act.{runtime_id:03d}.test"
        for runtime_id in range(1, pose_count + 1)
    ]
    return {
        "asset_set_id": "kingfisher-test",
        "character_id": "kingfisher",
        "display_name": "Kingfisher",
        "pose_count": pose_count,
        "pose_ids": pose_ids,
        "profile": {
            "profile_id": "kingfisher_test",
            "canvas_width": 960,
            "canvas_height": 540,
            "color_space": "sRGB",
            "alpha_mode": "binary_straight",
        },
        "sequences": {
            "all": {
                "fps": 6,
                "loop": True,
                "pose_ids": pose_ids,
            }
        },
    }


def _write_archive(
    path: Path,
    runtime_ids: list[int],
    *,
    metadata_overrides: dict[int, dict[str, object]] | None = None,
) -> None:
    png = _runtime_png()
    metadata_overrides = metadata_overrides or {}
    with zipfile.ZipFile(path, "w") as archive:
        for index, runtime_id in enumerate(runtime_ids):
            directory = f"{index:04d}_frame"
            metadata = _frame_metadata(runtime_id)
            metadata.update(metadata_overrides.get(index, {}))
            archive.writestr(
                f"{directory}/meta.json",
                json.dumps(metadata),
            )
            archive.writestr(
                f"{directory}/runtime-960x540.png",
                png,
            )


class RecoverKingfisherReviewLibraryTests(unittest.TestCase):
    def test_accepts_original_66_pose_profile(self):
        base_pose_ids, sequences = _validate_live_profile(_profile(66))

        self.assertEqual(len(base_pose_ids), 66)
        self.assertEqual(sequences["all"]["pose_ids"], base_pose_ids)

    def test_rejects_duplicate_runtime_id_before_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "duplicate.zip"
            _write_archive(
                archive_path,
                [*range(1, 67), 1],
            )

            with self.assertRaisesRegex(
                ValueError,
                "duplicate runtime id 1",
            ):
                _load_archive_frames(archive_path)

    def test_rejects_profile_identity_mismatch(self):
        profile = _profile(66)

        for field, wrong_value in (
            ("character_id", "robin"),
            ("display_name", "Robin"),
        ):
            with self.subTest(field=field):
                mismatched = {**profile, field: wrong_value}
                with self.assertRaisesRegex(ValueError, f"{field} mismatch"):
                    _validate_live_profile(mismatched)

    def test_recovers_base_library_from_current_110_pose_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "kingfisher.zip"
            profile_path = root / "library-index.json"
            output_root = root / "recovered"
            _write_archive(archive_path, list(range(1, 67)))

            profile = _profile(110)
            pose_ids = profile["pose_ids"]
            assert isinstance(pose_ids, list)
            profile["sequences"] = {
                "all": {
                    "fps": 6,
                    "loop": True,
                    "pose_ids": pose_ids,
                },
                "mixed": {
                    "fps": 8,
                    "loop": False,
                    "pose_ids": [pose_ids[0], pose_ids[66], pose_ids[1]],
                },
                "stage-only": {
                    "fps": 8,
                    "loop": True,
                    "pose_ids": pose_ids[66:],
                },
            }
            profile_path.write_text(json.dumps(profile), encoding="utf-8")

            result = recover_library(
                archive_path,
                profile_path,
                output_root,
            )

            recovered = json.loads(
                (output_root / "library-index.json").read_text(
                    encoding="utf-8"
                )
            )
            expected_base_ids = pose_ids[:66]
            self.assertEqual(result["pose_count"], 66)
            self.assertEqual(recovered["pose_count"], 66)
            self.assertEqual(recovered["pose_ids"], expected_base_ids)
            self.assertEqual(
                sum(shard["pose_count"] for shard in recovered["shards"]),
                66,
            )
            self.assertEqual(
                set(recovered["sequences"]),
                {"all", "mixed"},
            )
            self.assertEqual(
                recovered["sequences"]["all"]["pose_ids"],
                expected_base_ids,
            )
            self.assertEqual(
                recovered["sequences"]["mixed"]["pose_ids"],
                pose_ids[:2],
            )
            self.assertTrue(
                all(
                    pose_id in set(expected_base_ids)
                    for sequence in recovered["sequences"].values()
                    for pose_id in sequence["pose_ids"]
                )
            )

    def test_rejects_pose_count_and_sequence_reference_mismatches(self):
        profile = _profile(66)
        profile["pose_count"] = 65
        with self.assertRaisesRegex(ValueError, "pose_count must match"):
            _validate_live_profile(profile)

        profile = _profile(66)
        sequences = profile["sequences"]
        assert isinstance(sequences, dict)
        sequences["unknown"] = {
            "pose_ids": ["kingfisher.act.067.not-declared"]
        }
        with self.assertRaisesRegex(ValueError, "references unknown pose id"):
            _validate_live_profile(profile)

        profile = _profile(66)
        sequences = profile["sequences"]
        assert isinstance(sequences, dict)
        sequences["malformed"] = {"pose_ids": [7]}
        with self.assertRaisesRegex(ValueError, "pose_ids must be strings"):
            _validate_live_profile(profile)

    def test_rejects_archive_frame_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "identity-mismatch.zip"
            _write_archive(
                archive_path,
                list(range(1, 67)),
                metadata_overrides={40: {"source_pack": "robin"}},
            )

            with self.assertRaisesRegex(
                ValueError,
                "frame 41 source_pack mismatch",
            ):
                _load_archive_frames(archive_path)


if __name__ == "__main__":
    unittest.main()
