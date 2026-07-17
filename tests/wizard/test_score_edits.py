import json
import unittest

from wizard_avatar.score_edits import (
    EDIT_TYPES,
    MAX_SCORE_EDITS,
    SCORE_EDITS_SCHEMA_PATH,
    ScoreEditsV1,
    ScoreEditsValidationError,
)
from wizard_avatar.schema_validation import ContractValidationError, _validate_schema_node


HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64


def operation(index=1, edit_type="intensity_milli", value=500):
    return {
        "operation_id": "op:{:04d}".format(index),
        "cue_id": "cue:{:04d}".format(index),
        "edit_type": edit_type,
        "expected_value_sha256": HASH_C,
        "value": value,
        "reason_code": "director_choice",
    }


def content(operations=None):
    return {
        "schema_version": 1,
        "edit_set_id": "edits:director-001",
        "revision": 1,
        "character_id": "wizard-joe",
        "package_digest": HASH_A,
        "base_score_sha256": HASH_B,
        "parent_edit_set_sha256": None,
        "actor": {"kind": "human", "actor_id": "local:opaque"},
        "operations": [operation()] if operations is None else operations,
    }


class ScoreEditsV1Tests(unittest.TestCase):
    def assert_code(self, code, callback):
        with self.assertRaises(ScoreEditsValidationError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_build_is_immutable_canonical_and_order_independent(self):
        source = content()
        edits = ScoreEditsV1.build(source)
        reordered = {key: source[key] for key in reversed(tuple(source))}
        rebuilt = ScoreEditsV1.build(reordered)

        self.assertEqual(edits.edit_set_sha256, rebuilt.edit_set_sha256)
        self.assertEqual(edits.canonical_json(), rebuilt.canonical_json())
        self.assertEqual(edits.content_sha256(), edits.edit_set_sha256)
        self.assertIsInstance(edits.operations, tuple)

        source["operations"][0]["value"] = 1
        self.assertEqual(edits.operations[0].value, 500)

    def test_declared_hash_is_verified(self):
        edits = ScoreEditsV1.build(content())
        tampered = edits.to_dict()
        tampered["operations"][0]["value"] = 501
        error = self.assert_code("hash_mismatch", lambda: ScoreEditsV1.from_mapping(tampered))
        self.assertEqual(error.path, "$.edit_set_sha256")

    def test_json_rejects_duplicate_keys_floats_and_nonfinite_values(self):
        self.assert_code(
            "duplicate_json_key",
            lambda: ScoreEditsV1.from_json('{"schema_version":1,"schema_version":1}'),
        )

        encoded = ScoreEditsV1.build(content()).canonical_json().decode("utf-8")
        self.assert_code(
            "non_integer_identity_value",
            lambda: ScoreEditsV1.from_json(encoded.replace('"value":500', '"value":500.0')),
        )
        self.assert_code(
            "invalid_type",
            lambda: ScoreEditsV1.from_json(encoded.replace('"value":500', '"value":NaN')),
        )

    def test_root_actor_and_operation_fields_are_closed(self):
        root_extra = content()
        root_extra["private_prompt"] = "hidden"
        self.assert_code("unknown_field", lambda: ScoreEditsV1.build(root_extra))

        actor_extra = content()
        actor_extra["actor"]["display_name"] = "Director"
        self.assert_code("unknown_field", lambda: ScoreEditsV1.build(actor_extra))

        operation_extra = content()
        operation_extra["operations"][0]["raw_pixels"] = [[255, 0, 0]]
        self.assert_code("unknown_field", lambda: ScoreEditsV1.build(operation_extra))

    def test_only_bounded_timing_intensity_and_semantic_identifier_edits_are_allowed(self):
        accepted = (
            ("timing_offset_ms", -250),
            ("duration_ms", 1250),
            ("intensity_milli", 725),
            ("semantic_clip_id", "semantic:clip:welcoming_wave"),
            ("semantic_pose_id", "semantic:pose:attentive_front"),
            ("semantic_action_id", "semantic:action:explain_light"),
            ("semantic_expression_id", "semantic:expression:warm"),
            ("semantic_gaze_id", "semantic:gaze:direct_viewer"),
        )
        operations = [
            operation(index, edit_type, value)
            for index, (edit_type, value) in enumerate(accepted, 1)
        ]
        edits = ScoreEditsV1.build(content(operations))
        self.assertEqual({item.edit_type for item in edits.operations}, EDIT_TYPES)

        unsafe = content([operation(edit_type="add_cue", value="semantic:action:wave")])
        self.assert_code("unsafe_edit_type", lambda: ScoreEditsV1.build(unsafe))
        raw_pose = content([operation(edit_type="semantic_pose_id", value="pose:idle_front")])
        self.assert_code("invalid_semantic_id", lambda: ScoreEditsV1.build(raw_pose))
        renderer_pose = content(
            [operation(edit_type="semantic_pose_id", value="semantic:pose:renderer_idle_front")]
        )
        self.assert_code("raw_render_identifier", lambda: ScoreEditsV1.build(renderer_pose))

    def test_numeric_bounds_and_edit_count_are_enforced(self):
        for edit_type, value in (
            ("timing_offset_ms", 3600001),
            ("duration_ms", 0),
            ("intensity_milli", 1001),
        ):
            with self.subTest(edit_type=edit_type):
                invalid = content([operation(edit_type=edit_type, value=value)])
                self.assert_code(
                    "invalid_type",
                    lambda invalid=invalid: ScoreEditsV1.build(invalid),
                )

        self.assert_code(
            "edit_count_out_of_bounds",
            lambda: ScoreEditsV1.build(content([])),
        )
        too_many = [operation(index) for index in range(1, MAX_SCORE_EDITS + 2)]
        self.assert_code(
            "edit_count_out_of_bounds",
            lambda: ScoreEditsV1.build(content(too_many)),
        )

    def test_duplicate_operation_ids_and_targets_are_rejected(self):
        duplicated_id = [operation(1), operation(1, "duration_ms", 100)]
        self.assert_code("duplicate_id", lambda: ScoreEditsV1.build(content(duplicated_id)))

        duplicated_target = [operation(1), operation(2)]
        duplicated_target[1]["cue_id"] = duplicated_target[0]["cue_id"]
        self.assert_code(
            "duplicate_edit_target",
            lambda: ScoreEditsV1.build(content(duplicated_target)),
        )

    def test_private_values_are_rejected_even_when_they_fit_id_fields(self):
        private = content()
        private["actor"]["actor_id"] = "sk-secretvalue"
        self.assert_code("private_content", lambda: ScoreEditsV1.build(private))

    def test_character_package_and_base_score_binding_is_explicit(self):
        edits = ScoreEditsV1.build(content())
        edits.validate_binding(
            character_id="wizard-joe",
            package_digest=HASH_A,
            base_score_sha256=HASH_B,
        )
        for field, value in (
            ("character_id", "other-character"),
            ("package_digest", HASH_C),
            ("base_score_sha256", HASH_C),
        ):
            bindings = {
                "character_id": "wizard-joe",
                "package_digest": HASH_A,
                "base_score_sha256": HASH_B,
            }
            bindings[field] = value
            with self.subTest(field=field):
                self.assert_code(
                    "stale_binding",
                    lambda bindings=bindings: edits.validate_binding(**bindings),
                )

    def test_schema_is_closed_bounded_and_matches_the_safe_edit_union(self):
        schema = json.loads(SCORE_EDITS_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["title"], "ScoreEditsV1")
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(schema["properties"]["operations"]["maxItems"], MAX_SCORE_EDITS)

        operation_refs = schema["$defs"]["operation"]["oneOf"]
        self.assertEqual(len(operation_refs), len(EDIT_TYPES))
        schema_text = json.dumps(schema, sort_keys=True)
        for forbidden in ("add_cue", "remove_cue", "raw_pixels", "render_id"):
            self.assertNotIn(forbidden, schema_text)

        def assert_closed(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node.get("additionalProperties"), False)
                for child in node.values():
                    assert_closed(child)
            elif isinstance(node, list):
                for child in node:
                    assert_closed(child)

        assert_closed(schema)

        accepted = ScoreEditsV1.build(content()).to_dict()
        _validate_schema_node(accepted, schema, schema, "$")
        unsafe = accepted.copy()
        unsafe["operations"] = [dict(accepted["operations"][0])]
        unsafe["operations"][0]["edit_type"] = "add_cue"
        with self.assertRaises(ContractValidationError):
            _validate_schema_node(unsafe, schema, schema, "$")


if __name__ == "__main__":
    unittest.main()
