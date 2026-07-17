import copy
import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from wizard_avatar.performance_score import CompiledScoreLoader, CompiledScoreRepository
from wizard_avatar.score_runtime import ScoreRuntime

from tests.wizard.test_performance_scheduler import bound_snapshot, runtime_score


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


if __name__ == "__main__":
    unittest.main()
