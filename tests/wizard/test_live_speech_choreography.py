import copy
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
import tempfile
import unittest

from tests.wizard.test_live_speech_score import speech_context
from wizard_avatar.character_capabilities import derive_character_capability_manifest
from wizard_avatar.character_choreography import (
    load_character_choreography_dictionary,
)
from wizard_avatar.character_registry import load_character_registry
from wizard_avatar.direction_compiler import (
    HighLevelDirectionRequestV1,
    compile_high_level_direction,
)
from wizard_avatar.live_speech_score import (
    LiveSpeechScoreError,
    compile_live_speech_score,
    publish_live_speech_score,
)
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.performance_release import GovernedSpeechError
from wizard_avatar.performance_score import CompiledScoreRepository


ROOT = Path(__file__).resolve().parents[2]
DICTIONARY_PATH = (
    ROOT
    / "wizard_avatar"
    / "definitions"
    / "wizard_joe_choreography_dictionary_v1.json"
)


class LiveSpeechChoreographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = derive_character_capability_manifest()
        cls.dictionary = load_character_choreography_dictionary(DICTIONARY_PATH)
        cls.context = speech_context(cls.manifest)

    def compile(self, *, manifest=None, dictionary=None, duration_ms=875):
        return compile_live_speech_score(
            self.context,
            duration_ms=duration_ms,
            capability_manifest=self.manifest if manifest is None else manifest,
            choreography_dictionary=(
                self.dictionary if dictionary is None else dictionary
            ),
        )

    def test_live_speech_uses_exact_speak_binding_and_replayable_policy(self):
        compiled = self.compile()
        cue = compiled.score.track("live-speech-body").index.cues[0]

        self.assertEqual(cue.intent, "speak")
        self.assertEqual(cue.get("mapping_id"), "clip:idle_front")
        self.assertEqual(cue.get("clip_id"), "idle_front")
        self.assertEqual(cue.get("interrupt_policy"), "at_phase_boundary")
        self.assertEqual(
            compiled.choreography_dictionary_id,
            self.dictionary.dictionary_id,
        )
        self.assertRegex(
            compiled.choreography_policy_sha256,
            r"^sha256:[0-9a-f]{64}$",
        )
        with tempfile.TemporaryDirectory() as temporary:
            prepared = publish_live_speech_score(
                compiled,
                repository=CompiledScoreRepository(temporary),
            )
        self.assertEqual(
            prepared.score_binding.choreography_dictionary_id,
            self.dictionary.dictionary_id,
        )
        self.assertEqual(
            prepared.score_binding.choreography_policy_sha256,
            compiled.choreography_policy_sha256,
        )

    def test_dictionary_speech_incompatibility_fails_closed(self):
        speak = self.dictionary.intent_bindings["speak"]
        bindings = dict(self.dictionary.intent_bindings)
        bindings["speak"] = replace(speak, speech_compatible=False)
        incompatible = replace(
            self.dictionary,
            intent_bindings=MappingProxyType(bindings),
        )

        with self.assertRaises(LiveSpeechScoreError) as caught:
            self.compile(dictionary=incompatible)

        self.assertEqual(
            caught.exception.code,
            "live_score_speak_binding_speech_incompatible",
        )

    def test_capability_speech_incompatibility_fails_closed(self):
        manifest = copy.deepcopy(self.manifest)
        idle = next(
            item
            for item in manifest["capabilities"]
            if item["capability_id"] == "clip:idle_front"
        )
        idle["compatibility"]["speech"] = "incompatible"

        with self.assertRaises(LiveSpeechScoreError) as caught:
            self.compile(manifest=manifest)

        self.assertEqual(
            caught.exception.code,
            "live_score_speak_capability_speech_incompatible",
        )

    def test_application_forwards_package_choreography_policy(self):
        speak = self.dictionary.intent_bindings["speak"]
        bindings = dict(self.dictionary.intent_bindings)
        bindings["speak"] = replace(speak, speech_compatible=False)
        incompatible = replace(
            self.dictionary,
            intent_bindings=MappingProxyType(bindings),
        )
        registry = load_character_registry()
        with tempfile.TemporaryDirectory() as temporary:
            application = PerformanceApplication(
                self.context.runtime.wizard_runtime_epoch,
                score_repository=CompiledScoreRepository(temporary),
                character_id=self.context.character.character_id,
                package_digest=self.context.character.package_digest,
                manifest_digest=self.context.character.manifest_digest,
                capability_manifest=self.manifest,
                choreography_dictionary=incompatible,
                character_registry=registry,
            )

            with self.assertRaises(GovernedSpeechError) as caught:
                application.compile_live_speech_score(
                    self.context,
                    duration_ms=875,
                )

        self.assertEqual(
            caught.exception.code,
            "live_score_speak_binding_speech_incompatible",
        )

    def test_dictionary_policy_change_changes_score_and_policy_identity(self):
        changed_instructions = replace(
            self.dictionary.instructions,
            minimum_stillness_ms=self.dictionary.instructions.minimum_stillness_ms + 1,
        )
        changed_dictionary = replace(
            self.dictionary,
            instructions=changed_instructions,
        )

        first = self.compile()
        changed = self.compile(dictionary=changed_dictionary)

        self.assertNotEqual(
            first.choreography_policy_sha256,
            changed.choreography_policy_sha256,
        )
        self.assertNotEqual(first.score.score_id, changed.score.score_id)
        self.assertNotEqual(first.score.artifact_sha256, changed.score.artifact_sha256)

    def test_manual_speaks_direction_keeps_existing_explain_mapping(self):
        request = HighLevelDirectionRequestV1.from_mapping(
            {
                "schema_version": 1,
                "direction_id": "direction:test:manual-speaks",
                "direction_text": "speaks",
                "context_sha256": self.context.context_sha256,
                "intent": "speak",
                "duration_ms": 875,
                "media_id": self.context.source.media_id,
                "media_sha256": self.context.source.media_sha256,
                "seed": 1,
            }
        )

        compilation = compile_high_level_direction(
            request,
            self.context,
            self.manifest,
        )
        cue = compilation.compiled_score["tracks"][0]["cues"][0]

        self.assertEqual(cue["intent"], "explain")
        self.assertEqual(cue["mapping_id"], "clip:explain_front")


if __name__ == "__main__":
    unittest.main()
