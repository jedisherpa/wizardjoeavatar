import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.build_joeville_supplemental_character import (
    _resolve_output_shard,
    build_supplemental_character,
)
from tools.prepare_joeville_supplemental_manifest import prepare_manifest
from wizard_avatar.hd_pose_artifact import HDPoseArtifact, HDPoseLibrary


CANONICAL_PROFILE = {
    "profile_id": "wizardjoe_hd_alpha_1254_v001",
    "canvas_width": 1254,
    "canvas_height": 1254,
    "baseline_y": 1185,
    "minimum_margin": 69,
    "color_space": "sRGB",
    "alpha_mode": "straight",
}


class JoeVilleSupplementalCharacterTests(unittest.TestCase):
    def _fixture(self, project_root: Path) -> tuple[Path, Path, Path, Path]:
        authority_path = (
            project_root
            / "assets"
            / "reference"
            / "hd_canonical"
            / "manifest.json"
        )
        authority_path.parent.mkdir(parents=True)
        authority_path.write_text(
            json.dumps({"master_profile": CANONICAL_PROFILE}),
            encoding="utf-8",
        )
        character_root = (
            project_root
            / "assets"
            / "reference"
            / "joeville_supplemental"
            / "liana"
        )
        authored_root = character_root / "authored-source"
        sequences = {}
        pose_number = 1
        for sequence_number in range(1, 9):
            sequence_id = f"g{sequence_number}"
            frames = []
            for frame_index in range(1, 7):
                pose_id = f"liana_motion_{pose_number:03d}"
                filename = f"{pose_id}.png"
                frame_path = authored_root / "frames" / filename
                alpha_path = authored_root / "alpha-extracted" / filename
                chroma_path = authored_root / "chroma-source" / filename
                extraction_receipt_path = (
                    authored_root
                    / "alpha-extraction-receipts"
                    / f"{pose_id}.json"
                )
                canonical_receipt_path = (
                    authored_root
                    / "canonicalization-receipts"
                    / f"{pose_id}.json"
                )
                for path in (
                    frame_path,
                    alpha_path,
                    chroma_path,
                    extraction_receipt_path,
                    canonical_receipt_path,
                ):
                    path.parent.mkdir(parents=True, exist_ok=True)

                image = Image.new(
                    "RGBA", (1254, 1254), (0, 0, 0, 0)
                )
                ImageDraw.Draw(image).rectangle(
                    (
                        390 + pose_number,
                        110 + (pose_number % 5),
                        760 + pose_number,
                        1184,
                    ),
                    fill=(
                        20 + pose_number,
                        80 + pose_number,
                        130 + pose_number,
                        255,
                    ),
                )
                image.save(frame_path)
                image.save(alpha_path)
                chroma = Image.new(
                    "RGB", (1254, 1254), (251, 2, 250)
                )
                chroma.paste(
                    image.convert("RGB"),
                    mask=image.getchannel("A"),
                )
                chroma.save(chroma_path)

                frame_project_path = frame_path.relative_to(
                    project_root
                ).as_posix()
                alpha_project_path = alpha_path.relative_to(
                    project_root
                ).as_posix()
                chroma_project_path = chroma_path.relative_to(
                    project_root
                ).as_posix()
                extraction_receipt_path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "pose_id": pose_id,
                            "source_path": chroma_project_path,
                            "destination_path": alpha_project_path,
                        },
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                canonical_receipt_path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "pose_id": pose_id,
                            "source_path": alpha_project_path,
                            "destination_path": frame_project_path,
                        },
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                frames.append(
                    {
                        "brief_id": f"liana-{pose_number:03d}",
                        "pose_id": pose_id,
                        "slot_id": f"motion-{pose_number:03d}",
                        "frame_index": frame_index,
                        "pose_summary": (
                            f"Liana group {sequence_number} frame "
                            f"{frame_index}"
                        ),
                    }
                )
                pose_number += 1
            loop = sequence_number not in (4, 8)
            sequences[sequence_id] = {
                "intent": f"liana_motion_group_{sequence_number}",
                "fps": 8,
                "loop": loop,
                "motion_contract": {
                    "entry_handoffs": ["front_idle"],
                    "exit_handoffs": ["front_idle"],
                    "family": f"liana_group_{sequence_number}",
                    "hold_frame_indices": [3],
                    "interrupt_policy": "marker_safe",
                    "interruptible_frame_indices": [1, 3, 6],
                    "loop_mode": "loop" if loop else "hold_last",
                    "root_policy": "fixed",
                    "support_policy": "dual_foot_grounded",
                },
                "frames": frames,
            }
        brief_path = character_root / "authoring-brief-v001.json"
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "character_id": "liana",
                    "display_name": "Liana",
                    "roster_state": "supplemental_authored_character",
                    "profile_id": CANONICAL_PROFILE["profile_id"],
                    "sequence_order": list(sequences),
                    "sequences": sequences,
                    "review_projection": True,
                    "runtime_admitted": False,
                }
            ),
            encoding="utf-8",
        )
        manifest_path = character_root / "motion-manifest-v001.json"
        output_dir = character_root / "compiled-motion"
        return authority_path, brief_path, manifest_path, output_dir

    def test_repeatable_48_pose_build_is_review_only_and_portable(self):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            authority, brief, manifest, output = self._fixture(project_root)
            first_prepare = prepare_manifest(
                character_id="liana",
                brief_plan_path=brief,
                authority_path=authority,
                output_path=manifest,
                project_root=project_root,
            )
            second_prepare = prepare_manifest(
                character_id="liana",
                brief_plan_path=brief,
                authority_path=authority,
                output_path=manifest,
                project_root=project_root,
            )
            self.assertEqual(
                first_prepare["sha256"], second_prepare["sha256"]
            )

            first = build_supplemental_character(
                character_id="liana",
                manifest_path=manifest,
                output_dir=output,
                authority_path=authority,
                project_root=project_root,
            )
            second = build_supplemental_character(
                character_id="liana",
                manifest_path=manifest,
                output_dir=output,
                authority_path=authority,
                project_root=project_root,
            )
            self.assertEqual(first["pose_count"], 48)
            self.assertTrue(first["review_projection"])
            self.assertFalse(first["runtime_admitted"])
            self.assertEqual(
                first["artifact_sha256"], second["artifact_sha256"]
            )
            self.assertEqual(
                first["library_index_sha256"],
                second["library_index_sha256"],
            )
            self.assertEqual(
                first["build_receipt_sha256"],
                second["build_receipt_sha256"],
            )

            library = HDPoseLibrary(Path(first["library_index_path"]))
            artifact = HDPoseArtifact(Path(first["artifact_path"]))
            self.assertEqual(len(library.pose_ids), 48)
            self.assertEqual(len(artifact.records), 48)
            self.assertEqual(library.canvas_size, (1254, 1254))
            self.assertEqual(
                set(library.pose_ids),
                {
                    f"liana_motion_{number:03d}"
                    for number in range(1, 49)
                },
            )
            self.assertTrue(library.index["review_projection"])
            self.assertFalse(library.index["runtime_admitted"])
            self.assertTrue(
                all(
                    not metadata["runtime_admitted"]
                    for metadata in library.pose_metadata.values()
                )
            )

            receipt = json.loads(
                Path(first["build_receipt_path"]).read_text(
                    encoding="utf-8"
                )
            )
            for record in (
                receipt["supplemental_manifest"],
                receipt["authority_manifest"],
                receipt["artifact"],
                receipt["library_index"],
            ):
                self.assertFalse(Path(record["path"]).is_absolute())
                self.assertNotIn("..", Path(record["path"]).parts)
            self.assertNotIn(str(project_root), json.dumps(receipt))

    def test_prepare_rejects_nonportable_receipt_and_duplicate_rgba(self):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            authority, brief, manifest, _ = self._fixture(project_root)
            receipt_path = next(
                (
                    manifest.parent
                    / "authored-source"
                    / "alpha-extraction-receipts"
                ).glob("*.json")
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["source_path"] = "/tmp/not-portable.png"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, "project-relative path"
            ):
                prepare_manifest(
                    character_id="liana",
                    brief_plan_path=brief,
                    authority_path=authority,
                    output_path=manifest,
                    project_root=project_root,
                )

        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            authority, brief, manifest, _ = self._fixture(project_root)
            frames = sorted(
                (
                    manifest.parent / "authored-source" / "frames"
                ).glob("*.png")
            )
            frames[1].write_bytes(frames[0].read_bytes())
            with self.assertRaisesRegex(ValueError, "RGBA poses must be unique"):
                prepare_manifest(
                    character_id="liana",
                    brief_plan_path=brief,
                    authority_path=authority,
                    output_path=manifest,
                    project_root=project_root,
                )

    def test_builder_fails_closed_and_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            authority, brief, manifest, output = self._fixture(project_root)
            prepare_manifest(
                character_id="liana",
                brief_plan_path=brief,
                authority_path=authority,
                output_path=manifest,
                project_root=project_root,
            )
            value = json.loads(manifest.read_text(encoding="utf-8"))
            value["runtime_admitted"] = True
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "deny runtime admission"):
                build_supplemental_character(
                    character_id="liana",
                    manifest_path=manifest,
                    output_dir=output,
                    authority_path=authority,
                    project_root=project_root,
                )

        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            authority, brief, manifest, output = self._fixture(project_root)
            prepare_manifest(
                character_id="liana",
                brief_plan_path=brief,
                authority_path=authority,
                output_path=manifest,
                project_root=project_root,
            )
            value = json.loads(manifest.read_text(encoding="utf-8"))
            value["sequences"]["g1"]["frames"][0][
                "source_path"
            ] = "../escape.png"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "project-relative path"):
                build_supplemental_character(
                    character_id="liana",
                    manifest_path=manifest,
                    output_dir=output,
                    authority_path=authority,
                    project_root=project_root,
                )
            with self.assertRaisesRegex(ValueError, "contained"):
                _resolve_output_shard(
                    output / "library-index.json", "../escape.wjpose"
                )
            with self.assertRaisesRegex(ValueError, "safe slug"):
                build_supplemental_character(
                    character_id="../liana",
                    manifest_path=manifest,
                    output_dir=output,
                    authority_path=authority,
                    project_root=project_root,
                )

    def test_real_liana_identity_uses_required_canonical_profile(self):
        root = Path(__file__).resolve().parents[2]
        identity_manifest = json.loads(
            (
                root
                / "assets"
                / "reference"
                / "joeville_supplemental"
                / "liana"
                / "identity-manifest-v001.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(identity_manifest["profile"], CANONICAL_PROFILE)
        self.assertTrue(identity_manifest["review_projection"])
        self.assertFalse(identity_manifest["runtime_admitted"])


if __name__ == "__main__":
    unittest.main()
