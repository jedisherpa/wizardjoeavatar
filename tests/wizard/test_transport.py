import json
import unittest

from wizard_avatar.transport import (
    TransportMessageV1,
    TransportValidationError,
    parse_transport_message,
    serialize_transport_message,
)


class TransportMessageTests(unittest.TestCase):
    def test_canonical_round_trip_preserves_strict_envelope(self):
        message = TransportMessageV1.from_mapping(
            {
                "schema_version": 1,
                "type": "state",
                "runtime_epoch": "runtime-a",
                "sequence": 7,
                "payload": {"revision": 3, "flags": ["ready", True]},
            }
        )

        encoded = serialize_transport_message(message)

        self.assertEqual(
            encoded,
            '{"payload":{"flags":["ready",true],"revision":3},'
            '"runtime_epoch":"runtime-a","schema_version":1,"sequence":7,"type":"state"}',
        )
        self.assertEqual(parse_transport_message(encoded), message)
        self.assertEqual(parse_transport_message(encoded.encode("utf-8")), message)

    def test_payload_is_immutable_and_to_dict_is_detached(self):
        message = TransportMessageV1(
            schema_version=1,
            message_type="metrics",
            runtime_epoch="runtime-a",
            sequence=0,
            payload={"nested": {"values": [1, 2]}},
        )

        with self.assertRaises(TypeError):
            message.payload["new"] = True
        result = message.to_dict()
        result["payload"]["nested"]["values"].append(3)
        self.assertEqual(message.payload["nested"]["values"], (1, 2))

    def test_parser_rejects_unknown_missing_and_coerced_fields(self):
        base = {
            "schema_version": 1,
            "type": "command",
            "runtime_epoch": "runtime-a",
            "sequence": 1,
            "payload": {},
        }
        invalid = (
            {**base, "extra": 1},
            {key: value for key, value in base.items() if key != "payload"},
            {**base, "schema_version": True},
            {**base, "sequence": "1"},
            {**base, "type": "not-supported"},
            {**base, "runtime_epoch": ""},
            {**base, "payload": []},
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(TransportValidationError):
                    TransportMessageV1.from_mapping(value)

    def test_json_parser_rejects_duplicates_constants_and_invalid_utf8(self):
        duplicate = (
            '{"schema_version":1,"type":"resync","runtime_epoch":"a",'
            '"sequence":1,"sequence":2,"payload":{}}'
        )
        non_finite = json.dumps(
            {
                "schema_version": 1,
                "type": "metrics",
                "runtime_epoch": "a",
                "sequence": 1,
                "payload": {"value": float("nan")},
            }
        )
        for raw in (duplicate, non_finite, b"\xff"):
            with self.subTest(raw=raw):
                with self.assertRaises(TransportValidationError):
                    parse_transport_message(raw)

    def test_serializer_validates_mappings_and_rejects_non_json_payloads(self):
        with self.assertRaises(TransportValidationError):
            serialize_transport_message(
                {
                    "schema_version": 1,
                    "type": "state",
                    "runtime_epoch": "runtime-a",
                    "sequence": 0,
                    "payload": {"unsupported": object()},
                }
            )


if __name__ == "__main__":
    unittest.main()
