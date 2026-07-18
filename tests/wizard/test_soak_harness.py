import os
import unittest
import urllib.parse
from unittest import mock

from tools.run_python_avatar_soak import (
    BoundedLatencyStats,
    RuntimeSample,
    build_rolling_windows,
    parse_args,
    read_process_rss_bytes,
    resolve_server_pid,
    summarize_process_samples,
)


def sample(elapsed, tick, rss, *, fps=24.0, queue_drops=0, overruns=0):
    return RuntimeSample(
        elapsed_seconds=float(elapsed),
        simulation_tick=tick,
        state_latency_ms=10.0,
        event_loop_lag_ms=1.0,
        hub_actual_fps=fps,
        hub_window_fps=fps,
        hub_queue_drops=queue_drops,
        schedule_overruns=overruns,
        rss_bytes=rss,
    )


class SoakHarnessMeasurementTests(unittest.TestCase):
    def test_latency_histogram_is_full_run_and_recent_values_are_bounded(self):
        stats = BoundedLatencyStats(recent_capacity=2)
        for value in (1.5, 21.0, 49.0, 90.0):
            stats.add(value)

        mapping = stats.to_mapping()

        self.assertEqual(mapping["request_count"], 4)
        self.assertEqual(mapping["retained_recent_latency_count"], 2)
        self.assertEqual(mapping["latency_ms_p50_upper_bound"], 25.0)
        self.assertEqual(mapping["latency_ms_p95_upper_bound"], 100.0)
        self.assertEqual(sum(mapping["histogram"]["bucket_counts"]), 4)
        self.assertEqual(mapping["latency_ms_max"], 90.0)
        with self.assertRaises(ValueError):
            stats.add(float("nan"))

    def test_local_process_rss_is_positive_and_pid_is_strict(self):
        self.assertGreater(read_process_rss_bytes(os.getpid()), 0)
        for invalid in (0, -1, True, "42"):
            with self.assertRaises(ValueError):
                read_process_rss_bytes(invalid)

    def test_process_summary_uses_post_warmup_baseline_and_bounded_counts(self):
        samples = [
            sample(0, 0, 1000),
            sample(10, 600, 2000),
            sample(20, 1200, 3000),
            sample(30, 1800, 4000),
        ]

        summary = summarize_process_samples(samples, 10.0, total_sample_count=7)

        self.assertEqual(summary["sample_count"], 3)
        self.assertEqual(summary["baseline_rss_bytes"], 2000)
        self.assertEqual(summary["final_rss_bytes"], 4000)
        self.assertEqual(summary["rss_growth_bytes"], 2000)
        self.assertEqual(summary["peak_growth_bytes"], 2000)
        self.assertEqual(summary["retained_sample_count"], 4)
        self.assertEqual(summary["dropped_sample_count"], 3)
        self.assertEqual(summary["measurement_seconds"], 20.0)
        self.assertGreater(summary["rss_slope_bytes_per_hour"], 0)

    def test_rolling_windows_measure_cadence_latency_queue_and_memory(self):
        samples = [
            sample(0, 0, 1000),
            sample(10, 600, 1100, overruns=1),
            sample(20, 1200, 1200, overruns=2),
            sample(30, 1800, 1300, overruns=3),
            sample(40, 2400, 1400, queue_drops=1, overruns=5),
        ]

        windows = build_rolling_windows(samples, 30.0)

        self.assertEqual(len(windows), 2)
        self.assertTrue(windows[0].complete)
        self.assertEqual(windows[0].simulation_hz, 60.0)
        self.assertEqual(windows[0].presentation_fps_mean, 24.0)
        self.assertEqual(windows[0].schedule_overruns, 3)
        self.assertEqual(windows[0].rss_bytes_start, 1000)
        self.assertEqual(windows[0].rss_bytes_end, 1300)
        self.assertFalse(windows[1].complete)
        self.assertEqual(windows[1].hub_queue_drops, 1)

    def test_rolling_windows_reject_invalid_window(self):
        with self.assertRaises(ValueError):
            build_rolling_windows([], 0)

    def test_cli_rejects_a_sample_capacity_that_cannot_retain_the_run(self):
        argv = [
            "run_python_avatar_soak.py",
            "--duration-seconds",
            "100",
            "--sample-interval-seconds",
            "5",
            "--max-runtime-samples",
            "10",
        ]

        with mock.patch("sys.argv", argv), self.assertRaises(SystemExit):
            parse_args()


class SoakHarnessPidBindingTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_pid_is_required_and_explicit_pid_must_match(self):
        parsed = urllib.parse.urlparse("http://127.0.0.1:8875")
        health = {
            "pid": 123,
            "status": "ready",
            "runtime_epoch": "epoch-test",
            "frame_hub_running": True,
        }
        with mock.patch(
            "tools.run_python_avatar_soak.request_json_async",
            new=mock.AsyncMock(return_value=(health, 1.0)),
        ):
            pid, returned = await resolve_server_pid(
                "http://127.0.0.1:8875", parsed, 123
            )
            self.assertEqual(pid, 123)
            self.assertEqual(returned, health)
            with self.assertRaises(RuntimeError):
                await resolve_server_pid("http://127.0.0.1:8875", parsed, 124)

    async def test_resource_sampling_rejects_nonliteral_or_remote_hosts(self):
        for url in ("http://localhost:8875", "https://192.0.2.10:8875"):
            with self.assertRaises(RuntimeError):
                await resolve_server_pid(url, urllib.parse.urlparse(url), None)


if __name__ == "__main__":
    unittest.main()
