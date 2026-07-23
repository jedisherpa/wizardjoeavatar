import copy
import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from wizard_avatar.performance_score import CompiledScoreLoader, CompiledScoreRepository
from wizard_avatar.score_runtime import SCORE_ADMISSION_MISMATCH, ScoreRuntime

from tests.wizard.test_performance_scheduler import bound_snapshot, runtime_score
from tests.wizard.test_performance_score import digest


def make_repository(root):
    return CompiledScoreRepository(
        root,
        CompiledScoreLoader(contract_validator=lambda _name, _value: None),
    )


def changed_snapshot(snapshot, **changes):
    value = copy.deepcopy(snapshot.to_dict())
    for dotted_name, replacement in changes.items():
        section, name = dotted_name.split(".", 1)
        value[section][name] = replacement
    return type(snapshot).from_mapping(value)


def score_with_references(score, **references):
    document = copy.deepcopy(score.to_dict())
    document["tracks"][0]["cues"][1].update(references)
    return CompiledScoreLoader(
        contract_validator=lambda _name, _value: None
    ).from_mapping(document)


class ScoreRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = make_repository(self.temporary.name)
        self.runtime = ScoreRuntime(self.repository)
        self.score = runtime_score()
        self.snapshot = bound_snapshot(self.score)

    def test_prepare_loads_once_and_resolver_is_memory_only(self):
        self.repository.publish(self.score)

        prepared = self.runtime.prepare_snapshot(self.snapshot)
        self.assertTrue(prepared.ready)
        self.assertEqual(prepared.code, "score_ready")
        self.assertIs(self.runtime.resolve(self.snapshot), prepared.score)

        def disk_access_is_forbidden(_media_sha256):
            raise AssertionError("runtime resolution touched disk")

        self.repository.load_current = disk_access_is_forbidden
        self.assertIs(self.runtime.resolve(self.snapshot), prepared.score)
        self.assertEqual(self.runtime.diagnostics_for(self.snapshot).code, "score_ready")

    def test_loaded_score_and_nested_document_are_immutable(self):
        self.repository.publish(self.score)
        loaded = self.runtime.prepare_snapshot(self.snapshot).score
        self.assertIsNotNone(loaded)
        with self.assertRaises(FrozenInstanceError):
            loaded.revision = 99
        with self.assertRaises(TypeError):
            loaded.document["runtime_api_version"] = 99
        with self.assertRaises(TypeError):
            loaded.tracks[0].index.cues[0].data["intent"] = "changed"

    def test_missing_corrupt_and_mismatched_scores_have_stable_diagnostics(self):
        missing = self.runtime.prepare_snapshot(self.snapshot)
        self.assertEqual(missing.code, "score_not_ready")
        self.assertIsNone(self.runtime.resolve(self.snapshot))

        self.repository.publish(self.score)
        pointer = (
            Path(self.temporary.name)
            / "media"
            / self.score.media_sha256.split(":", 1)[1]
            / "current.json"
        )
        pointer.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
        corrupt_runtime = ScoreRuntime(self.repository)
        corrupt = corrupt_runtime.prepare_snapshot(self.snapshot)
        self.assertEqual(corrupt.code, "score_corrupt")
        self.assertIsNone(corrupt_runtime.resolve(self.snapshot))

        other = runtime_score(compiled_id="compiled:other")
        second_root = tempfile.TemporaryDirectory()
        self.addCleanup(second_root.cleanup)
        other_repository = make_repository(second_root.name)
        other_repository.publish(other)
        mismatched_runtime = ScoreRuntime(other_repository)
        mismatch = mismatched_runtime.prepare_snapshot(self.snapshot)
        self.assertEqual(mismatch.code, "score_mismatch")
        self.assertIsNone(mismatched_runtime.resolve(self.snapshot))

    def test_cache_key_binds_all_runtime_identities(self):
        self.repository.publish(self.score)
        prepared = self.runtime.prepare_snapshot(self.snapshot)
        self.assertTrue(prepared.ready)

        mutations = {
            "performance.score_id": "compiled:different",
            "performance.score_sha256": "sha256:" + "0" * 64,
            "performance.score_revision": 2,
            "performance.character_id": "wizard-other",
            "performance.character_package_sha256": "sha256:" + "2" * 64,
            "media.media_sha256": None,
            "media.duration_ms": self.score.duration_ms + 1,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                changed = changed_snapshot(self.snapshot, **{field: value})
                self.assertIsNone(self.runtime.resolve(changed))
                self.assertEqual(
                    self.runtime.diagnostics_for(changed).code,
                    "score_not_ready",
                )
        changed_media = changed_snapshot(
            self.snapshot,
            **{
                "media.media_id": "media:different",
                "media.media_sha256": None,
            }
        )
        self.assertIsNone(self.runtime.resolve(changed_media))

    def test_scoreless_snapshot_needs_no_repository_access(self):
        scoreless = bound_snapshot(self.score, with_score=False, mode="narrative")

        def disk_access_is_forbidden(_media_sha256):
            raise AssertionError("scoreless preparation touched disk")

        self.repository.load_current = disk_access_is_forbidden
        prepared = self.runtime.prepare_snapshot(scoreless)
        self.assertEqual(prepared.code, "scoreless_v1")
        self.assertIsNone(prepared.score)
        self.assertIsNone(self.runtime.resolve(scoreless))

    def test_capacity_must_be_a_positive_integer(self):
        for capacity in (0, -1, True, 1.5):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    ScoreRuntime(self.repository, capacity=capacity)

    def test_ready_scores_share_bounded_lru_retention_with_results(self):
        runtime = ScoreRuntime(self.repository, capacity=2)
        scores = [
            runtime_score(
                media_id="media:sha256:" + character * 64,
                media_hash=digest(character),
            )
            for character in ("1", "2", "3")
        ]
        snapshots = [bound_snapshot(score) for score in scores]
        for score, snapshot in zip(scores[:2], snapshots[:2]):
            self.repository.publish(score)
            self.assertTrue(runtime.prepare_snapshot(snapshot).ready)
        self.assertIsNotNone(runtime.resolve(snapshots[0]))
        self.repository.publish(scores[2])
        self.assertTrue(runtime.prepare_snapshot(snapshots[2]).ready)

        self.assertIsNotNone(runtime.resolve(snapshots[0]))
        self.assertIsNone(runtime.resolve(snapshots[1]))
        self.assertIsNotNone(runtime.resolve(snapshots[2]))
        diagnostics = runtime.diagnostics_mapping(snapshots[2])
        self.assertEqual(diagnostics["cache_entries"], 2)
        self.assertEqual(diagnostics["result_entries"], 2)
        self.assertEqual(diagnostics["evictions"], 1)
        self.assertEqual(diagnostics["capacity"], 2)

    def test_failure_results_are_bounded_across_one_thousand_bindings(self):
        capacity = 31
        runtime = ScoreRuntime(self.repository, capacity=capacity)
        last_snapshot = None
        for index in range(1000):
            last_snapshot = changed_snapshot(
                self.snapshot,
                **{"performance.score_id": f"compiled:missing-{index:04d}"},
            )
            self.assertEqual(
                runtime.prepare_snapshot(last_snapshot).code,
                "score_not_ready",
            )

        self.assertIsNotNone(last_snapshot)
        diagnostics = runtime.diagnostics_mapping(last_snapshot)
        self.assertEqual(diagnostics["cache_entries"], 0)
        self.assertEqual(diagnostics["result_entries"], capacity)
        self.assertEqual(diagnostics["evictions"], 1000 - capacity)
        self.assertEqual(diagnostics["capacity"], capacity)

    def test_active_package_pose_graph_and_manifest_identities_fail_closed(self):
        document = copy.deepcopy(self.score.to_dict())
        document["character"]["manifest_digest"] = digest("e")
        score = CompiledScoreLoader(
            contract_validator=lambda _name, _value: None
        ).from_mapping(document)
        snapshot = bound_snapshot(score)
        self.repository.publish(score)
        character = score.document["character"]
        matching = {
            "package_digest": character["package_digest"],
            "manifest_digest": character["manifest_digest"],
            "pose_library_digest": character["pose_library_digest"],
            "graph_digest": character["graph_digest"],
        }
        self.assertTrue(
            ScoreRuntime(self.repository, **matching)
            .prepare_snapshot(snapshot)
            .ready
        )

        mutations = {
            "package_digest": digest("0"),
            "manifest_digest": digest("1"),
            "pose_library_digest": digest("2"),
            "graph_digest": digest("3"),
        }
        for field, stale_digest in mutations.items():
            with self.subTest(field=field):
                active = dict(matching)
                active[field] = stale_digest
                runtime = ScoreRuntime(self.repository, **active)
                prepared = runtime.prepare_snapshot(snapshot)
                self.assertFalse(prepared.ready)
                self.assertEqual(prepared.code, SCORE_ADMISSION_MISMATCH)
                self.assertIsNone(runtime.resolve(snapshot))

    def test_configured_manifest_identity_is_required_in_score_document(self):
        self.repository.publish(self.score)
        runtime = ScoreRuntime(
            self.repository,
            manifest_digest=digest("e"),
        )

        prepared = runtime.prepare_snapshot(self.snapshot)

        self.assertFalse(prepared.ready)
        self.assertEqual(prepared.code, SCORE_ADMISSION_MISMATCH)
        self.assertIsNone(runtime.resolve(self.snapshot))

    def test_unknown_pose_clip_and_node_ids_fail_closed(self):
        admitted = {
            "admitted_pose_ids": {"pose:known"},
            "admitted_clip_ids": {"clip:known"},
            "admitted_node_ids": {"node:known"},
        }
        known = {
            "pose_id": "pose:known",
            "clip_id": "clip:known",
            "node_id": "node:known",
        }
        for field in ("pose_id", "clip_id", "node_id"):
            with self.subTest(field=field):
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                repository = make_repository(temporary.name)
                references = dict(known)
                references[field] = field + ":unknown"
                score = score_with_references(self.score, **references)
                snapshot = bound_snapshot(score)
                repository.publish(score)
                runtime = ScoreRuntime(repository, **admitted)

                prepared = runtime.prepare_snapshot(snapshot)

                self.assertFalse(prepared.ready)
                self.assertEqual(prepared.code, SCORE_ADMISSION_MISMATCH)
                self.assertIsNone(runtime.resolve(snapshot))

    def test_admitted_pose_clip_and_node_ids_prepare_normally(self):
        score = score_with_references(
            self.score,
            pose_id="pose:known",
            clip_id="clip:known",
            node_id="node:known",
        )
        snapshot = bound_snapshot(score)
        self.repository.publish(score)
        runtime = ScoreRuntime(
            self.repository,
            admitted_pose_ids={"pose:known"},
            admitted_clip_ids={"clip:known"},
            admitted_node_ids={"node:known"},
        )

        prepared = runtime.prepare_snapshot(snapshot)

        self.assertTrue(prepared.ready)
        self.assertIs(runtime.resolve(snapshot), prepared.score)


if __name__ == "__main__":
    unittest.main()
