import copy
import json
import unittest
from pathlib import Path

from wizard_avatar.character_registry import CharacterAdmissionV1, load_character_registry
from wizard_avatar.media_session import (
    MediaSessionAckV2,
    MediaSessionCoordinator,
    MediaSessionError,
    MediaSessionSnapshotV1,
    MediaSessionSnapshotV2,
    parse_media_session_snapshot,
)
from wizard_avatar.performance_application import PerformanceApplication
from wizard_avatar.schema_validation import ContractValidationError, SchemaRegistry


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "audiobook_contracts"
SNAPSHOT_V2 = FIXTURE_DIR / "media_session_snapshot_v2.json"
ACK_V2 = FIXTURE_DIR / "media_session_ack_v2.json"
SNAPSHOT_V1 = FIXTURE_DIR / "media_session_snapshot_v1.json"


def fixture(path):
    return json.loads(path.read_text(encoding="utf-8"))


def runtime():
    registry = load_character_registry()
    package = registry.get("wizard-joe-v1")
    admission = registry.admission_for_character(package.character_id)
    application = PerformanceApplication(
        "wizard-runtime-v2-test",
        character_id=package.character_id,
        package_digest=package.package_sha256,
        character_registry=registry,
    )
    return registry, package, admission, application


class MediaSessionV2Tests(unittest.TestCase):
    def test_snapshot_and_ack_fixtures_round_trip_through_dispatchers(self):
        snapshot_bytes = SNAPSHOT_V2.read_bytes()
        snapshot = parse_media_session_snapshot(snapshot_bytes)
        self.assertIsInstance(snapshot, MediaSessionSnapshotV2)
        self.assertEqual(
            snapshot.to_dict(),
            fixture(SNAPSHOT_V2),
        )

        ack = MediaSessionAckV2.from_json(ACK_V2.read_bytes())
        self.assertEqual(ack.to_dict(), fixture(ACK_V2))

    def test_duplicate_keys_and_tampered_admission_hash_fail_closed(self):
        duplicate = SNAPSHOT_V2.read_text(encoding="utf-8").replace(
            '"schema_version": 2,',
            '"schema_version": 2, "schema_version": 2,',
            1,
        )
        with self.assertRaisesRegex(MediaSessionError, "duplicate JSON object key"):
            parse_media_session_snapshot(duplicate.encode("utf-8"))

        value = fixture(SNAPSHOT_V2)
        value["performance"]["admission"]["admission_sha256"] = (
            "sha256:" + "0" * 64
        )
        with self.assertRaisesRegex(MediaSessionError, "canonical content"):
            MediaSessionSnapshotV2.from_mapping(value)

    def test_coordinator_returns_runtime_admission_and_reconciles_identity_change(self):
        value = fixture(SNAPSHOT_V2)
        snapshot = MediaSessionSnapshotV2.from_mapping(value)
        admission = snapshot.performance.admission
        coordinator = MediaSessionCoordinator(
            "wizard-runtime-v2-test",
            runtime_admission=admission,
        )

        ack = coordinator.accept(snapshot, 1_000_000)

        self.assertIsInstance(ack, MediaSessionAckV2)
        self.assertEqual(ack.disposition, "accepted")
        self.assertEqual(ack.runtime_admission, admission)
        self.assertEqual(
            ack.capabilities["supported_media_session_schemas"],
            (1, 2),
        )

        changed = copy.deepcopy(value)
        changed["message_id"] = "00000000-0000-4000-8000-000000000103"
        changed["sequence"] += 1
        changed_admission = dict(changed["performance"]["admission"])
        changed_admission["persona_id"] = "persona:other"
        unsigned = dict(changed_admission)
        unsigned.pop("admission_sha256")
        changed_admission["admission_sha256"] = CharacterAdmissionV1.build(
            persona_id=unsigned["persona_id"],
            character_id=unsigned["character_id"],
            package_sha256=unsigned["package_digest"],
        ).admission_sha256
        changed["performance"]["admission"] = changed_admission

        conflict = coordinator.accept(
            MediaSessionSnapshotV2.from_mapping(changed),
            1_100_000,
        )
        self.assertEqual(conflict.disposition, "resync_required")
        self.assertEqual(conflict.error_code, "reconcile_required")

    def test_application_accepts_only_exact_admitted_v2_identity(self):
        _registry, package, admission, application = runtime()
        value = fixture(SNAPSHOT_V2)
        value["performance"]["admission"] = admission.to_dict()
        snapshot = MediaSessionSnapshotV2.from_mapping(value)

        ack = application.accept_snapshot(snapshot, 1_000_000)

        self.assertEqual(ack.disposition, "accepted")
        self.assertEqual(ack.runtime_admission.to_dict(), admission.to_dict())
        self.assertIs(
            application.scheduler.coordinator.accepted_snapshot,
            snapshot,
        )

        for field, expected_code, replacement in (
            ("persona_id", "persona_mismatch", "persona:other"),
            ("character_id", "character_mismatch", "other-character"),
            ("package_digest", "package_mismatch", "sha256:" + "1" * 64),
        ):
            _registry, _package, admission, application = runtime()
            changed = fixture(SNAPSHOT_V2)
            admission_value = dict(admission.to_dict())
            admission_value[field] = replacement
            unsigned = dict(admission_value)
            unsigned.pop("admission_sha256")
            admission_value["admission_sha256"] = CharacterAdmissionV1.build(
                persona_id=unsigned["persona_id"],
                character_id=unsigned["character_id"],
                package_sha256=unsigned["package_digest"],
            ).admission_sha256
            changed["performance"]["admission"] = admission_value
            candidate = MediaSessionSnapshotV2.from_mapping(changed)

            rejected = application.accept_snapshot(candidate, 1_000_000)

            self.assertEqual(rejected.disposition, "rejected")
            self.assertEqual(rejected.error_code, expected_code)
            self.assertIsNone(
                application.scheduler.coordinator.accepted_snapshot
            )

    def test_v1_is_frozen_to_exact_legacy_wizard_identity(self):
        _registry, package, _admission, application = runtime()
        value = fixture(SNAPSHOT_V1)
        value["performance"]["character_id"] = package.character_id
        value["performance"]["character_package_sha256"] = package.package_sha256
        value["performance"]["score_id"] = None
        value["performance"]["score_revision"] = None
        value["performance"]["score_sha256"] = None
        snapshot = MediaSessionSnapshotV1.from_mapping(value)
        self.assertEqual(
            application.accept_snapshot(snapshot, 1_000_000).disposition,
            "accepted",
        )

        value["performance"]["character_package_sha256"] = None
        rejected = application.accept_snapshot(
            MediaSessionSnapshotV1.from_mapping(value),
            1_100_000,
        )
        self.assertEqual(rejected.disposition, "rejected")
        self.assertEqual(rejected.error_code, "legacy_schema_not_allowed")

    def test_schema_registry_validates_v2_and_rejects_tampering(self):
        registry = SchemaRegistry()
        registry.validate("MediaSessionSnapshotV2", fixture(SNAPSHOT_V2))
        registry.validate("MediaSessionAckV2", fixture(ACK_V2))

        changed = fixture(SNAPSHOT_V2)
        changed["performance"]["admission"]["persona_id"] = "persona:other"
        with self.assertRaises(ContractValidationError) as caught:
            registry.validate("MediaSessionSnapshotV2", changed)
        self.assertEqual(caught.exception.code, "hash_mismatch")


if __name__ == "__main__":
    unittest.main()
