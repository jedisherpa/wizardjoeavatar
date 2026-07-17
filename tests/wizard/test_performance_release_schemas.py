import copy
import json
import unittest
from pathlib import Path

from wizard_avatar.governed_performance import GovernedPerformanceApprovalV1
from wizard_avatar.performance_context import PerformanceContextError, PerformanceContextV1
from wizard_avatar.performance_release import (
    GovernedSpeechError,
    GovernedSpeechRegistrationV1,
    GovernedSpeechRevocationV1,
    PerformanceContextRequestV1,
)

from tests.wizard.test_performance_context import context_mapping
from tests.wizard.test_performance_release import (
    MEDIA_DIGEST,
    TEXT,
    alignment_mapping,
    context_request_mapping,
    text_digest,
)


try:
    from jsonschema import Draft202012Validator, RefResolver, ValidationError, validators
except ImportError:  # The runtime project does not require jsonschema.
    Draft202012Validator = None
    RefResolver = None
    ValidationError = None
    validators = None


ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS = ROOT / "wizard_avatar" / "definitions"
NEW_SCHEMA_NAMES = (
    "performance_context_v1.schema.json",
    "performance_context_request_v1.schema.json",
    "governed_speech_registration_v1.schema.json",
    "governed_speech_revocation_v1.schema.json",
)


def load_schema(name):
    with (DEFINITIONS / name).open(encoding="utf-8") as source:
        return json.load(source)


def walk_schema(value, path="$"):
    if isinstance(value, dict):
        yield path, value
        for key, item in value.items():
            yield from walk_schema(item, path + "." + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_schema(item, "{}[{}]".format(path, index))


def registration_mapping():
    context = context_mapping()
    alignment = alignment_mapping()
    approval = GovernedPerformanceApprovalV1.build(
        {
            "schema_version": 1,
            "approval_id": "approval:turn-0042:schema-test",
            "turn_id": "turn:0042",
            "reply_sha256": text_digest(),
            "speech_media": {
                "kind": "speech",
                "identity": "speech:turn-0042",
                "sha256": MEDIA_DIGEST,
            },
            "performance_context_sha256": context["context_sha256"],
            "character_id": context["character"]["character_id"],
            "package_digest": context["character"]["package_digest"],
            "allowed_sinks": ["animation", "speech", "text"],
            "issued_at_ms": 1_000,
            "expires_at_ms": 5_000,
            "revocation_generation": 0,
            "reconciliation_generation": context["runtime"]["reconciliation_generation"],
        }
    )
    return {
        "schema_version": 1,
        "approved_text": TEXT,
        "approval": approval.to_dict(),
        "performance_context": context,
        "alignment": alignment,
    }


class PerformanceReleaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {name: load_schema(name) for name in NEW_SCHEMA_NAMES}
        cls.schema_store = {}
        for path in DEFINITIONS.glob("*.schema.json"):
            schema = load_schema(path.name)
            if "$id" in schema:
                cls.schema_store[schema["$id"]] = schema

        cls.validator_class = None
        if Draft202012Validator is not None:
            strict_types = Draft202012Validator.TYPE_CHECKER.redefine(
                "integer", lambda _checker, instance: type(instance) is int
            )
            cls.validator_class = validators.extend(
                Draft202012Validator,
                type_checker=strict_types,
            )

    def validator(self, name):
        schema = self.schemas[name]
        resolver = RefResolver.from_schema(schema, store=self.schema_store)
        return self.validator_class(schema, resolver=resolver)

    def assert_schema_valid(self, name, value):
        if self.validator_class is not None:
            self.validator(name).validate(value)
            return
        schema = self.schemas[name]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(value))

    def assert_schema_invalid(self, name, value):
        if self.validator_class is not None:
            with self.assertRaises(ValidationError):
                self.validator(name).validate(value)

    def test_documents_are_draft_2020_12_and_external_refs_resolve_locally(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertTrue(schema["$id"].endswith(name))
                if Draft202012Validator is not None:
                    Draft202012Validator.check_schema(schema)
                for path, node in walk_schema(schema):
                    reference = node.get("$ref")
                    if reference and not reference.startswith("#"):
                        self.assertIn(reference, self.schema_store, path)

    def test_object_array_string_and_integer_surfaces_are_closed_and_bounded(self):
        for name, schema in self.schemas.items():
            for path, node in walk_schema(schema):
                with self.subTest(schema=name, path=path):
                    if node.get("type") == "object" and "required" in node:
                        self.assertIs(node.get("additionalProperties"), False)
                    if node.get("type") == "array":
                        self.assertIn("maxItems", node)
                    if node.get("type") == "string":
                        self.assertTrue("maxLength" in node or "pattern" in node)
                    if node.get("type") == "integer" and "const" not in node:
                        self.assertIn("minimum", node)
                        self.assertIn("maximum", node)

        registration = self.schemas["governed_speech_registration_v1.schema.json"]
        alignment_overlay = registration["properties"]["alignment"]["allOf"][1]
        for field in ("word_spans", "character_spans", "phoneme_spans"):
            self.assertEqual(alignment_overlay["properties"][field]["maxItems"], 65536)

    def test_existing_valid_fixtures_satisfy_runtime_and_schema_contracts(self):
        context = context_mapping()
        request = context_request_mapping()
        registration = registration_mapping()
        revocation = {
            "schema_version": 1,
            "approval_id": registration["approval"]["approval_id"],
            "revocation_generation": 1,
        }

        PerformanceContextV1.from_mapping(context)
        PerformanceContextRequestV1.from_mapping(request)
        GovernedSpeechRegistrationV1.from_mapping(registration)
        GovernedSpeechRevocationV1.from_mapping(revocation)

        for name, value in (
            ("performance_context_v1.schema.json", context),
            ("performance_context_request_v1.schema.json", request),
            ("governed_speech_registration_v1.schema.json", registration),
            ("governed_speech_revocation_v1.schema.json", revocation),
        ):
            with self.subTest(schema=name):
                self.assert_schema_valid(name, value)

    def test_unknown_float_and_oversized_context_data_are_rejected(self):
        unknown = context_mapping()
        unknown["unexpected"] = True
        self.assert_schema_invalid("performance_context_v1.schema.json", unknown)
        with self.assertRaises(PerformanceContextError):
            PerformanceContextV1.from_mapping(unknown)

        floating = context_mapping()
        floating["runtime"]["simulation_tick"] = 4242.0
        self.assert_schema_invalid("performance_context_v1.schema.json", floating)
        with self.assertRaises(PerformanceContextError):
            PerformanceContextV1.from_mapping(floating)

        oversized = context_mapping()
        item = oversized["character"]["recent_performance"][0]
        oversized["character"]["recent_performance"] = [
            dict(item, performance_id="performance:{:04d}".format(index))
            for index in range(17)
        ]
        self.assert_schema_invalid("performance_context_v1.schema.json", oversized)
        with self.assertRaises(PerformanceContextError):
            PerformanceContextV1.from_mapping(oversized)

    def test_request_and_registration_reject_unknown_float_and_oversized_data(self):
        unknown_request = context_request_mapping()
        unknown_request["unexpected"] = True
        self.assert_schema_invalid(
            "performance_context_request_v1.schema.json", unknown_request
        )
        with self.assertRaises(GovernedSpeechError):
            PerformanceContextRequestV1.from_mapping(unknown_request)

        floating_request = context_request_mapping()
        floating_request["schema_version"] = 1.0
        self.assert_schema_invalid(
            "performance_context_request_v1.schema.json", floating_request
        )
        with self.assertRaises(GovernedSpeechError):
            PerformanceContextRequestV1.from_json(
                json.dumps(floating_request).encode("utf-8")
            )

        unknown_registration = registration_mapping()
        unknown_registration["unexpected"] = True
        self.assert_schema_invalid(
            "governed_speech_registration_v1.schema.json", unknown_registration
        )
        with self.assertRaises(GovernedSpeechError):
            GovernedSpeechRegistrationV1.from_mapping(unknown_registration)

        oversized_registration = registration_mapping()
        oversized_registration["approved_text"] = "x" * 32769
        self.assert_schema_invalid(
            "governed_speech_registration_v1.schema.json", oversized_registration
        )
        with self.assertRaises(GovernedSpeechError):
            GovernedSpeechRegistrationV1.from_mapping(oversized_registration)

    def test_revocation_requires_a_closed_positive_integer_generation(self):
        valid = {
            "schema_version": 1,
            "approval_id": "approval:turn-0042",
            "revocation_generation": 1,
        }
        for changes in (
            {"revocation_generation": 0},
            {"revocation_generation": 1.0},
            {"unexpected": True},
        ):
            invalid = copy.deepcopy(valid)
            invalid.update(changes)
            with self.subTest(changes=changes):
                self.assert_schema_invalid(
                    "governed_speech_revocation_v1.schema.json", invalid
                )
                with self.assertRaises(GovernedSpeechError):
                    GovernedSpeechRevocationV1.from_mapping(invalid)


if __name__ == "__main__":
    unittest.main()
