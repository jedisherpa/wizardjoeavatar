import tempfile
import unittest
from unittest import mock

from tests.wizard.test_media_session import snapshot
from tests.wizard.test_performance_context import context_mapping
from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.controller import WizardAvatarController
from wizard_avatar.live_speech_score import (
    LiveSpeechScoreError,
    compile_live_speech_score,
    publish_live_speech_score,
)
from wizard_avatar.performance_context import PerformanceContextV1
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.performance_release import GovernedSpeechError
from wizard_avatar.performance_score import CompiledScoreRepository


def speech_context(manifest, *, intent="speak", score_bound=False):
    raw = context_mapping()
    raw.pop("context_sha256")
    raw["conversation"]["intent"] = intent
    raw["governance"]["allowed_semantic_actions"] = ["listen", "speak"]
    raw["character"].update(
        {
            "character_id": manifest["character"]["character_id"],
            "package_digest": manifest["sources"]["package_sha256"],
            "manifest_digest": manifest["manifest_sha256"],
        }
    )
    raw["evidence"]["package_digest"] = manifest["sources"]["package_sha256"]
    raw["evidence"]["score_binding"] = (
        {
            "score_id": "compiled:existing",
            "score_revision": 1,
            "score_sha256": "sha256:" + "f" * 64,
        }
        if score_bound
        else {
            "score_id": None,
            "score_revision": None,
            "score_sha256": None,
        }
    )
    return PerformanceContextV1.build(raw)


class LiveSpeechScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = derive_character_capability_manifest()

    def test_compiles_publishes_and_reuses_deterministic_content_free_score(self):
        context = speech_context(self.manifest)
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            first_compiled = compile_live_speech_score(
                context,
                duration_ms=875,
                capability_manifest=self.manifest,
            )
            second_compiled = compile_live_speech_score(
                context,
                duration_ms=875,
                capability_manifest=self.manifest,
            )
            first = publish_live_speech_score(
                first_compiled,
                repository=repository,
            )
            second = publish_live_speech_score(
                second_compiled,
                repository=repository,
            )
            loaded = repository.load_current(context.source.media_sha256)

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.preliminary_context.context_sha256, context.context_sha256)
        self.assertEqual(first.score_binding.score_id, loaded.score_id)
        self.assertEqual(first.score_binding.score_revision, loaded.revision)
        self.assertEqual(first.score_binding.score_sha256, loaded.artifact_sha256)
        self.assertEqual(first.score_binding.media_id, context.source.media_id)
        self.assertEqual(
            first.score_binding.prepared_from_context_sha256,
            context.context_sha256,
        )
        self.assertEqual(
            first.score_binding.compiled_from_context_sha256,
            first_compiled.compiler_context_sha256,
        )
        self.assertNotEqual(
            first.score_binding.compiled_from_context_sha256,
            context.context_sha256,
        )
        self.assertEqual(loaded.duration_ms, 875)
        self.assertNotIn("approved_text", str(first.to_dict()))

    def test_rejects_non_speech_and_already_bound_preliminary_contexts(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            with self.assertRaises(LiveSpeechScoreError) as wrong_intent:
                compile_live_speech_score(
                    speech_context(self.manifest, intent="explain"),
                    duration_ms=1000,
                    capability_manifest=self.manifest,
                )
            with self.assertRaises(LiveSpeechScoreError) as already_bound:
                compile_live_speech_score(
                    speech_context(self.manifest, score_bound=True),
                    duration_ms=1000,
                    capability_manifest=self.manifest,
                )

        self.assertEqual(wrong_intent.exception.code, "live_score_intent_unsupported")
        self.assertEqual(already_bound.exception.code, "live_score_already_bound")

    def test_rejects_missing_or_nonpositive_media_duration(self):
        context = speech_context(self.manifest)
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            for duration in (None, 0, -1, True):
                with self.subTest(duration=duration):
                    with self.assertRaises(LiveSpeechScoreError) as caught:
                        compile_live_speech_score(
                            context,
                            duration_ms=duration,
                            capability_manifest=self.manifest,
                        )
                    self.assertEqual(caught.exception.code, "media_duration_not_ready")

    def test_published_preparation_grant_expires_monotonically(self):
        context = speech_context(self.manifest)
        with tempfile.TemporaryDirectory() as temporary:
            repository = CompiledScoreRepository(temporary)
            application = PerformanceApplication(
                context.runtime.wizard_runtime_epoch,
                score_repository=repository,
                character_id=context.character.character_id,
                package_digest=context.character.package_digest,
                manifest_digest=context.character.manifest_digest,
                capability_manifest=self.manifest,
            )
            compiled = application.compile_live_speech_score(
                context,
                duration_ms=875,
            )
            with mock.patch(
                "wizard_avatar.performance_application.time.perf_counter_ns",
                return_value=1_000_000,
            ):
                prepared = application.publish_live_speech_score(compiled)
            key = (
                prepared.score_binding.score_id,
                prepared.score_binding.score_revision,
                prepared.score_binding.score_sha256,
            )
            grant = application._live_score_preparations[key]

            application._reconcile_live_score_preparations(
                snapshot(with_hashes=False),
                grant.expires_at_monotonic_us + 1,
            )

            self.assertNotIn(key, application._live_score_preparations)

    def test_stale_revocation_does_not_destroy_newer_preparation_grant(self):
        context = speech_context(self.manifest)
        with tempfile.TemporaryDirectory() as temporary:
            application = PerformanceApplication(
                context.runtime.wizard_runtime_epoch,
                score_repository=CompiledScoreRepository(temporary),
                character_id=context.character.character_id,
                package_digest=context.character.package_digest,
                manifest_digest=context.character.manifest_digest,
                capability_manifest=self.manifest,
            )
            controller = WizardAvatarController()
            application.revoke_governed_speech(1, controller)
            prepared = application.publish_live_speech_score(
                application.compile_live_speech_score(
                    context,
                    duration_ms=875,
                )
            )
            key = (
                prepared.score_binding.score_id,
                prepared.score_binding.score_revision,
                prepared.score_binding.score_sha256,
            )

            with self.assertRaises(GovernedSpeechError) as stale:
                application.revoke_governed_speech(1, controller)

            self.assertEqual(stale.exception.code, "revocation_generation_stale")
            self.assertIn(key, application._live_score_preparations)
            application.revoke_governed_speech(2, controller)
            self.assertNotIn(key, application._live_score_preparations)


if __name__ == "__main__":
    unittest.main()
