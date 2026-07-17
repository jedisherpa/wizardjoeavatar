import unittest
from unittest import mock

from wizard_avatar import character_capabilities


class CharacterCapabilityPortabilityTests(unittest.TestCase):
    def test_runtime_manifest_does_not_read_workstation_source_images(self):
        with mock.patch.object(
            character_capabilities,
            "_source_asset_path",
            side_effect=AssertionError("runtime attempted to resolve a source PNG"),
        ):
            manifest = character_capabilities.derive_character_capability_manifest()

        self.assertGreater(manifest["counts"]["pose_count"], 0)
        self.assertTrue(
            all(pose["source_asset_sha256"] is None for pose in manifest["poses"])
        )


if __name__ == "__main__":
    unittest.main()
