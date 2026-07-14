import ast
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from tools.performance_authoring.cache import CacheIdentityError, build_cache_key
from tools.performance_authoring.media import (
    AuthoringToolError,
    build_media_asset,
    canonicalize_pcm,
    inspect_tool,
    probe_media,
    require_local_input,
)
from tools.performance_authoring.music import (
    build_music_score,
    extract_fixed_hop_features,
)
from wizard_avatar.performance_compiler import canonical_artifact_bytes
from wizard_avatar.schema_validation import SchemaRegistry


ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "audiobook_performance"


def write_synthetic_wav(spec_path, output_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    samples = []
    for sample_index in range(spec["duration_samples"]):
        phase = sample_index % spec["pulse_interval_samples"]
        value = spec["pulse_amplitude"] if phase < spec["pulse_duration_samples"] else 0
        samples.append(value.to_bytes(2, "little", signed=True))
    with wave.open(str(output_path), "wb") as output:
        output.setnchannels(spec["channels"])
        output.setsampwidth(spec["sample_width_bytes"])
        output.setframerate(spec["sample_rate_hz"])
        output.writeframes(b"".join(samples))


class PerformanceAuthoringTests(unittest.TestCase):
    def test_ffprobe_and_pcm_canonicalization_are_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "synthetic.wav"
            write_synthetic_wav(FIXTURES / "synthetic_music_spec.json", source)
            probe = probe_media(source)
            first = canonicalize_pcm(source, root / "first.wav")
            second = canonicalize_pcm(source, root / "second.wav")

            self.assertEqual(probe.duration_ms, 4000)
            self.assertEqual(probe.sample_rate_hz, 16000)
            self.assertEqual(first.pcm_sha256, second.pcm_sha256)
            self.assertEqual(first.cache_key.digest, second.cache_key.digest)
            self.assertEqual((root / "first.wav").read_bytes(), (root / "second.wav").read_bytes())
            asset = build_media_asset(
                probe,
                storage_ref="prism-media:synthetic",
                title="Synthetic pulse track",
                media_kind="music",
                canonical_pcm=first,
            )
            self.assertNotIn(str(root), json.dumps(asset, sort_keys=True))
            self.assertEqual(asset["identity"]["source_sha256"], probe.source_sha256)
            SchemaRegistry().validate("MediaAssetV1", asset)

    def test_music_analysis_is_repeatable_and_abstains_from_meter_and_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "synthetic.wav"
            write_synthetic_wav(FIXTURES / "synthetic_music_spec.json", source)
            media_sha256 = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
            media_id = "media:sha256:" + media_sha256.split(":", 1)[1]
            features_first = extract_fixed_hop_features(source)
            features_second = extract_fixed_hop_features(source)
            first = build_music_score(
                source,
                media_id=media_id,
                media_sha256=media_sha256,
            )
            second = build_music_score(
                source,
                media_id=media_id,
                media_sha256=media_sha256,
            )

            self.assertEqual(features_first, features_second)
            self.assertIsNotNone(features_first.tempo_bpm_milli)
            self.assertEqual(first.cache_key.digest, second.cache_key.digest)
            self.assertEqual(
                canonical_artifact_bytes(first.music_score),
                canonical_artifact_bytes(second.music_score),
            )
            self.assertEqual(first.music_score["meter_regions"], [])
            self.assertEqual(first.music_score["downbeats"], [])
            self.assertEqual(first.music_score["sections"][0]["label"], "unknown")
            SchemaRegistry().validate("MusicScoreV1", first.music_score)

    def test_missing_tools_and_nonlocal_inputs_report_explicit_failures(self):
        missing = inspect_tool("ffmpeg", "/definitely/missing/ffmpeg")
        self.assertFalse(missing.available)
        self.assertEqual(missing.reason_code, "tool_not_executable")

        with self.assertRaises(AuthoringToolError) as local_error:
            require_local_input("https://example.test/audio.wav")
        self.assertEqual(local_error.exception.code, "network_forbidden")

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "synthetic.wav"
            write_synthetic_wav(FIXTURES / "synthetic_music_spec.json", source)
            with self.assertRaises(AuthoringToolError) as tool_error:
                probe_media(source, ffprobe_executable="/definitely/missing/ffprobe")
            self.assertEqual(tool_error.exception.code, "tool_unavailable")
            self.assertIsNotNone(tool_error.exception.capability)

    def test_cache_identity_rejects_floats_and_changes_with_inputs(self):
        first = build_cache_key("test", {"digest": "a", "count": 1})
        second = build_cache_key("test", {"digest": "b", "count": 1})

        self.assertNotEqual(first.digest, second.digest)
        with self.assertRaises(CacheIdentityError):
            build_cache_key("test", {"rate": 1.0})

    def test_authoring_modules_import_no_network_clients(self):
        banned = {"requests", "urllib", "httpx", "aiohttp", "socket", "ftplib"}
        files = list((ROOT / "tools" / "performance_authoring").glob("*.py"))
        files.extend(
            [
                ROOT / "wizard_avatar" / "transcript_ingest.py",
                ROOT / "wizard_avatar" / "performance_compiler.py",
            ]
        )
        imported = set()
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".", 1)[0])

        self.assertEqual(imported & banned, set())


if __name__ == "__main__":
    unittest.main()
