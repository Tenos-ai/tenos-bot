import json
import os
import sys
import tempfile
import types
import unittest

try:  # pragma: no cover - exercises the real dependency when available
    import requests  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    # Provide a stub requests module so UpdateCoordinator can be imported without
    # the optional third-party dependency in test environments.
    requests_stub = types.SimpleNamespace()

    def _unexpected_call(*_args, **_kwargs):
        raise AssertionError("requests.get should not be invoked during unit tests")

    class _UnexpectedSession:  # pragma: no cover - only used in dependency-less envs
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("requests.Session should not be invoked during unit tests")

    requests_stub.get = _unexpected_call  # type: ignore[attr-defined]
    requests_stub.Session = _UnexpectedSession  # type: ignore[attr-defined]
    requests_stub.RequestException = RuntimeError  # type: ignore[attr-defined]
    sys.modules["requests"] = requests_stub

from controllers import UpdateCoordinator


class UpdateCoordinatorTests(unittest.TestCase):
    def _build_coordinator(self, tmpdir: str, payload: dict | None = None) -> tuple[UpdateCoordinator, list[tuple[str, str]]]:
        state_file = os.path.join(tmpdir, "update_state.json")
        if payload is not None:
            with open(state_file, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)

        logs: list[tuple[str, str]] = []

        def log_callback(channel: str, message: str) -> None:
            logs.append((channel, message))

        coordinator = UpdateCoordinator(
            repo_owner="dummy",
            repo_name="dummy",
            current_version="1.2.3",
            app_base_dir=tmpdir,
            log_callback=log_callback,
        )
        return coordinator, logs

    def test_records_current_version_as_baseline_when_state_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            coordinator, _ = self._build_coordinator(tmp)
            self.assertEqual(coordinator.state.last_successful_tag, "1.2.3")
            self.assertIsNone(coordinator.state.pending_tag)

    def test_clears_pending_when_pending_matches_current_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = {"pending_tag": "v1.2.3", "last_successful_tag": None}
            coordinator, _ = self._build_coordinator(tmp, payload)
            self.assertEqual(coordinator.state.last_successful_tag, "v1.2.3")
            self.assertIsNone(coordinator.state.pending_tag)

    def test_clear_pending_update_resets_state_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = {"pending_tag": "v9.9.9", "last_successful_tag": "v1.2.2"}
            coordinator, logs = self._build_coordinator(tmp, payload)
            self.assertEqual(coordinator.state.pending_tag, "v9.9.9")

            coordinator.clear_pending_update()

            self.assertIsNone(coordinator.state.pending_tag)

            state_path = os.path.join(tmp, "update_state.json")
            with open(state_path, "r", encoding="utf-8") as fh:
                disk_state = json.load(fh)
            self.assertIsNone(disk_state.get("pending_tag"))

            self.assertTrue(any("Cleared pending update" in message for _, message in logs))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

