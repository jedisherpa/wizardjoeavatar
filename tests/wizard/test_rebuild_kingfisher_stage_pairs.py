import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.rebuild_kingfisher_stage_pairs import rebuild_stage_pairs


class RebuildKingfisherStagePairsTests(unittest.TestCase):
    def test_rebuilds_all_twenty_two_plan_bound_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alpha_root = root / "alphas"
            audit_root = root / "audits"
            alpha_root.mkdir()
            performance_keys = []
            for pair_index, resting_ordinal in enumerate(
                range(67, 111, 2),
                start=1,
            ):
                speaking_ordinal = resting_ordinal + 1
                rest_slug = f"test-{pair_index:02d}-resting-beak"
                speak_slug = f"test-{pair_index:02d}-speaking-beak"
                performance_keys.append(
                    {
                        "key": f"test_{pair_index:02d}",
                        "articulation_region": [420, 200, 540, 320],
                        "poses": [
                            {
                                "ordinal": resting_ordinal,
                                "slug": rest_slug,
                            },
                            {
                                "ordinal": speaking_ordinal,
                                "slug": speak_slug,
                            },
                        ],
                    }
                )
                resting = Image.new(
                    "RGBA",
                    (960, 540),
                    (0, 0, 0, 0),
                )
                ImageDraw.Draw(resting).rectangle(
                    (410, 100, 550, 528),
                    fill=(20, 30, 40, 255),
                )
                candidate = resting.copy()
                ImageDraw.Draw(candidate).rectangle(
                    (430, 220, 530, 300),
                    fill=(170, 20, 30, 255),
                )
                resting_name = (
                    f"{resting_ordinal:03d}_ACT{resting_ordinal:03d}_"
                    f"{rest_slug.replace('-', '_')}_alpha.png"
                )
                speaking_stem = (
                    f"{speaking_ordinal:03d}_ACT{speaking_ordinal:03d}_"
                    f"{speak_slug.replace('-', '_')}"
                )
                resting.save(alpha_root / resting_name)
                candidate.save(
                    alpha_root / f"{speaking_stem}_candidate.png"
                )

            plan_path = root / "pose-plan.json"
            plan_path.write_text(
                json.dumps({"performance_keys": performance_keys}),
                encoding="utf-8",
            )

            report = rebuild_stage_pairs(
                plan_path,
                alpha_root,
                audit_root,
            )

            self.assertTrue(report["passed"])
            self.assertEqual(report["pair_count"], 22)
            self.assertEqual(len(list(audit_root.glob("*_pair.json"))), 22)
            first_audit = json.loads(
                (audit_root / "067_068_pair.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(first_audit["passed"])
            self.assertEqual(
                first_audit["mouth_region"],
                [420, 200, 540, 320],
            )
            self.assertEqual(first_audit["outside_mouth_mean_abs"], 0.0)


if __name__ == "__main__":
    unittest.main()
