import unittest

from tools.run_wizard_avatar_server import ServerShutdownSignal


class FakeServer:
    should_exit = False


class CompanionRunnerTests(unittest.TestCase):
    def test_shutdown_signal_requests_graceful_uvicorn_exit(self):
        server = FakeServer()
        signal = ServerShutdownSignal()
        signal.attach(server)

        signal.request()

        self.assertTrue(signal.requested)
        self.assertTrue(server.should_exit)

    def test_early_shutdown_request_is_applied_when_server_attaches(self):
        server = FakeServer()
        signal = ServerShutdownSignal()

        signal.request()
        signal.attach(server)

        self.assertTrue(server.should_exit)


if __name__ == "__main__":
    unittest.main()
