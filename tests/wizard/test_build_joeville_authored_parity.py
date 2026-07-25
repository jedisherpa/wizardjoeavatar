import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.build_joeville_authored_parity import build_authored_parity
from wizard_avatar.hd_pose_artifact import HDPoseArtifact, write_pose_artifact


class JoeVilleAuthoredParityBuilderTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        output_root = root / "joeville"
        compiled = output_root / "compiled" / "orion-vale"
        compiled.mkdir(parents=True)
        profile = {
            "profile_id": "test-alpha",
            "canvas_width": 64,
            "canvas_height": 64,
            "baseline_y": 58,
            "minimum_margin": 4,
            "color_space": "sRGB",
            "alpha_mode": "straight",
        }
        authority_path = root / "authority.json"
        authority_path.write_text(
            json.dumps({"master_profile": profile}), encoding="utf-8"
        )
        supplied = {}
        supplied_records = []
        supplied_sequences = {}
        pose_number = 1
        for sequence_number in range(1, 7):
            sequence_id = f"g{sequence_number}"
            supplied_sequences[sequence_id] = []
            for frame_index in range(1, 7):
                pose_id = f"orion_vale_motion_{pose_number:03d}"
                image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle(
                    (24, 10, 39, 57), fill=(120, 60, pose_number, 255)
                )
                supplied[pose_id] = image
                supplied_sequences[sequence_id].append(pose_id)
                supplied_records.append(
                    {
                        "pose_id": pose_id,
                        "motion_slot_id": f"motion-{pose_number:03d}",
                        "sequence_id": sequence_id,
                        "source_frame_index": frame_index,
                        "rgba_sha256": hashlib.sha256(
                            image.tobytes()
                        ).hexdigest(),
                        "approval_state": "pending_visual_parity",
                        "runtime_admitted": False,
                    }
                )
                pose_number += 1
        artifact_path = compiled / "orion-source.wjpose"
        receipt = write_pose_artifact(
            artifact_path,
            supplied,
            profile=profile,
            provenance={"runtime_admitted": False},
        )
        existing_manifest_path = (
            output_root
            / "source-metadata"
            / "orion-vale"
            / "reconstruction-manifest-v001.json"
        )
        existing_manifest_path.parent.mkdir(parents=True)
        existing_manifest_path.write_text(
            json.dumps(
                {
                    "character_id": "orion-vale",
                    "display_name": "Orion Vale",
                    "runtime_admitted": False,
                    "compiled_pose_count": 36,
                    "missing_sequences": ["g7", "g8"],
                    "artifact": {
                        **receipt,
                        "path": str(artifact_path.relative_to(output_root)),
                    },
                    "sequences": supplied_sequences,
                    "poses": supplied_records,
                }
            ),
            encoding="utf-8",
        )
        authored_root = (
            output_root / "authored-source" / "orion-vale"
        )
        authored_root.mkdir(parents=True)
        authored_sequences = {}
        for sequence_number in (7, 8):
            sequence_id = f"g{sequence_number}"
            frames = []
            for frame_index in range(1, 7):
                pose_number = (
                    37 + (sequence_number - 7) * 6 + frame_index - 1
                )
                source_path = authored_root / f"{pose_number:03d}.png"
                image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                ImageDraw.Draw(image).rectangle(
                    (
                        25 - frame_index,
                        8,
                        48 + frame_index,
                        57,
                    ),
                    fill=(150, 70, pose_number, 255),
                )
                image.save(source_path)
                frames.append(
                    {
                        "pose_id": f"orion_vale_motion_{pose_number:03d}",
                        "slot_id": f"motion-{pose_number:03d}",
                        "frame_index": frame_index,
                        "source_path": source_path.name,
                        "source_sha256": hashlib.sha256(
                            source_path.read_bytes()
                        ).hexdigest(),
                        "rgba_sha256": hashlib.sha256(
                            image.tobytes()
                        ).hexdigest(),
                        "brief_id": f"orion-{sequence_id}-{frame_index:02d}",
                        "pose_summary": (
                            f"{sequence_id} authored frame {frame_index}"
                        ),
                        "authorship": "authored_full_size",
                    }
                )
            loop = sequence_id == "g7"
            authored_sequences[sequence_id] = {
                "intent": (
                    "listen_consider_explain"
                    if loop
                    else "boundary_verify_redirect"
                ),
                "fps": 8,
                "loop": loop,
                "motion_contract": {
                    "entry_handoffs": ["front_idle"],
                    "exit_handoffs": (
                        ["front_idle", "g8"]
                        if loop
                        else ["front_idle", "profile_walk"]
                    ),
                    "family": (
                        "communication" if loop else "governance_boundary"
                    ),
                    "hold_frame_indices": [3],
                    "interrupt_policy": "marker_safe",
                    "interruptible_frame_indices": [1, 3, 6],
                    "loop_mode": "loop" if loop else "hold_last",
                    "root_policy": "fixed",
                    "support_policy": "dual_foot_grounded",
                },
                "frames": frames,
            }
        authored_manifest_path = authored_root / "manifest.json"
        authored_manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "character_id": "orion-vale",
                    "runtime_admitted": False,
                    "profile_id": profile["profile_id"],
                    "authority_manifest_sha256": hashlib.sha256(
                        authority_path.read_bytes()
                    ).hexdigest(),
                    "existing_reconstruction_sha256": hashlib.sha256(
                        existing_manifest_path.read_bytes()
                    ).hexdigest(),
                    "existing_artifact_sha256": receipt["sha256"],
                    "sequences": authored_sequences,
                }
            ),
            encoding="utf-8",
        )
        return (
            authority_path,
            existing_manifest_path,
            authored_manifest_path,
            output_root,
        )

    def test_builds_deterministic_48_pose_review_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                authority,
                existing,
                authored,
                output_root,
            ) = self._fixture(root)

            first = build_authored_parity(
                character_id="orion-vale",
                authored_manifest_path=authored,
                existing_manifest_path=existing,
                authority_path=authority,
                output_root=output_root,
            )
            second = build_authored_parity(
                character_id="orion-vale",
                authored_manifest_path=authored,
                existing_manifest_path=existing,
                authority_path=authority,
                output_root=output_root,
            )

            self.assertEqual(first["pose_count"], 48)
            self.assertFalse(first["runtime_admitted"])
            self.assertEqual(
                first["artifact_sha256"], second["artifact_sha256"]
            )
            artifact = HDPoseArtifact(Path(first["artifact_path"]))
            self.assertEqual(len(artifact.records), 48)
            index = json.loads(
                Path(first["library_index_path"]).read_text(encoding="utf-8")
            )
            self.assertTrue(index["review_projection"])
            self.assertFalse(index["runtime_admitted"])
            self.assertEqual(len(index["sequences"]["g7"]["pose_ids"]), 6)
            self.assertEqual(len(index["sequences"]["g8"]["pose_ids"]), 6)
            self.assertTrue(index["sequences"]["g7"]["loop"])
            self.assertFalse(index["sequences"]["g8"]["loop"])
            self.assertEqual(
                index["sequences"]["g8"]["loop_mode"], "hold_last"
            )
            self.assertEqual(
                index["sequences"]["g8"]["pose_ids"][-1],
                "orion_vale_motion_048",
            )
            motion_contract = json.loads(
                Path(first["motion_contract_path"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(motion_contract["runtime_admitted"])
            self.assertEqual(
                motion_contract["sequences"]["g7"]["intent"],
                "listen_consider_explain",
            )
            self.assertEqual(
                motion_contract["sequences"]["g8"]["loop_mode"],
                "hold_last",
            )
            self.assertEqual(
                motion_contract["sequences"]["g8"]["frames"][-1][
                    "support_contact"
                ],
                "dual_foot_grounded",
            )
            for pose_number in range(1, 37):
                pose_id = f"orion_vale_motion_{pose_number:03d}"
                self.assertEqual(
                    artifact.load_rgba(pose_id),
                    HDPoseArtifact(
                        output_root
                        / "compiled"
                        / "orion-vale"
                        / "orion-source.wjpose"
                    ).load_rgba(pose_id),
                )
            frame_37 = Image.open(
                authored.parent / "037.png"
            ).convert("RGBA")
            self.assertEqual(
                artifact.load_rgba("orion_vale_motion_037"),
                frame_37.tobytes(),
            )

    def test_rejects_authored_source_checksum_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                authority,
                existing,
                authored,
                output_root,
            ) = self._fixture(root)
            manifest = json.loads(authored.read_text(encoding="utf-8"))
            manifest["sequences"]["g7"]["frames"][0][
                "source_sha256"
            ] = "0" * 64
            authored.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                build_authored_parity(
                    character_id="orion-vale",
                    authored_manifest_path=authored,
                    existing_manifest_path=existing,
                    authority_path=authority,
                    output_root=output_root,
                )

    def test_clean_rebuilds_match_for_every_published_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_fixture = self._fixture(root / "first")
            second_fixture = self._fixture(root / "second")
            first = build_authored_parity(
                character_id="orion-vale",
                authored_manifest_path=first_fixture[2],
                existing_manifest_path=first_fixture[1],
                authority_path=first_fixture[0],
                output_root=first_fixture[3],
            )
            second = build_authored_parity(
                character_id="orion-vale",
                authored_manifest_path=second_fixture[2],
                existing_manifest_path=second_fixture[1],
                authority_path=second_fixture[0],
                output_root=second_fixture[3],
            )
            for result_key in (
                "artifact_path",
                "library_index_path",
                "reconstruction_manifest_path",
                "contact_sheet_path",
                "motion_contract_path",
            ):
                first_hash = hashlib.sha256(
                    Path(first[result_key]).read_bytes()
                ).hexdigest()
                second_hash = hashlib.sha256(
                    Path(second[result_key]).read_bytes()
                ).hexdigest()
                self.assertEqual(first_hash, second_hash, result_key)

    def test_rejects_duplicate_authored_sources_and_loop_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, existing, authored, output_root = self._fixture(root)
            manifest = json.loads(authored.read_text(encoding="utf-8"))
            first = manifest["sequences"]["g7"]["frames"][0]
            duplicate = manifest["sequences"]["g8"]["frames"][0]
            for field in ("source_path", "source_sha256", "rgba_sha256"):
                duplicate[field] = first[field]
            authored.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "paths must be distinct"):
                build_authored_parity(
                    character_id="orion-vale",
                    authored_manifest_path=authored,
                    existing_manifest_path=existing,
                    authority_path=authority,
                    output_root=output_root,
                )

            _, existing, authored, output_root = self._fixture(
                root / "loop-conflict"
            )
            manifest = json.loads(authored.read_text(encoding="utf-8"))
            manifest["sequences"]["g8"]["motion_contract"][
                "loop_mode"
            ] = "loop"
            authored.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "contradicts loop flag"):
                build_authored_parity(
                    character_id="orion-vale",
                    authored_manifest_path=authored,
                    existing_manifest_path=existing,
                    authority_path=authority,
                    output_root=output_root,
                )


if __name__ == "__main__":
    unittest.main()
