import json
import tempfile
import unittest
from pathlib import Path

from wizard_avatar.animation_graph import (
    ANIMATION_GRAPH_V2_PATH,
    REFERENCE_POSE_LIBRARY_PATH,
    REFERENCE_POSE_MANIFEST_PATH,
    clear_animation_graph_cache,
    load_animation_graph,
    load_reference_animation_graph_v2,
)


class CharacterGraphPortabilityTests(unittest.TestCase):
    def test_cache_invalidation_clears_default_graph_wrapper(self):
        load_reference_animation_graph_v2()
        self.assertEqual(load_reference_animation_graph_v2.cache_info().currsize, 1)

        clear_animation_graph_cache()

        self.assertEqual(load_reference_animation_graph_v2.cache_info().currsize, 0)

    def test_graph_uses_package_owned_manifest_and_pose_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset_set_id = "portable-character-asset-set-v1"
            inputs = (
                (
                    REFERENCE_POSE_MANIFEST_PATH,
                    root / "manifest.json",
                ),
                (
                    REFERENCE_POSE_LIBRARY_PATH,
                    root / "poses.json",
                ),
                (
                    ANIMATION_GRAPH_V2_PATH,
                    root / "graph.json",
                ),
            )
            for source, destination in inputs:
                payload = json.loads(source.read_text(encoding="utf-8"))
                payload["asset_set_id"] = asset_set_id
                destination.write_text(
                    json.dumps(payload, sort_keys=True),
                    encoding="utf-8",
                )

            graph = load_animation_graph(
                root / "graph.json",
                pose_manifest_path=root / "manifest.json",
                pose_library_path=root / "poses.json",
            )

            self.assertEqual(graph.asset_set_id, asset_set_id)
            self.assertIn(graph.default_node_id, graph.nodes)
            self.assertEqual(
                set(graph.pose_catalog),
                set(
                    pose["id"]
                    for pose in json.loads(
                        (root / "poses.json").read_text(encoding="utf-8")
                    )["poses"]
                ),
            )


if __name__ == "__main__":
    unittest.main()
