import unittest

from tools.validate_pose_expansion_workflow import validate


class PoseExpansionWorkflowTests(unittest.TestCase):
    def test_registry_tracker_and_item_records_are_consistent(self):
        result = validate()
        self.assertEqual(result["candidate_count"], 30)
        self.assertEqual(result["archive_count"], 30)
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
