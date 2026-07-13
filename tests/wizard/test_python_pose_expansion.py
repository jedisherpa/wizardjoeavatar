import json
import unittest

from tools.integrate_feelings_into_python import (
    EXPECTED_NEW_POSES,
    EXPECTED_TOTAL_POSES,
    METADATA_PATH,
    integrate,
)


class PythonPoseExpansionTests(unittest.TestCase):
    def test_expansion_is_complete_and_python_owned(self):
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(metadata["pose_count"], EXPECTED_NEW_POSES)
        self.assertEqual(len(metadata["poses"]), EXPECTED_NEW_POSES)
        self.assertTrue(
            all(not str(pose["source"]).startswith("rust/") for pose in metadata["poses"])
        )

        result = integrate(check_only=True)
        self.assertEqual(result["python_pose_count"], EXPECTED_TOTAL_POSES)
        self.assertEqual(len(result["pose_ids"]), EXPECTED_TOTAL_POSES)


if __name__ == "__main__":
    unittest.main()
