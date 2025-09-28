import tempfile
import unittest
from unittest.mock import patch

from services.system_diagnostics import collect_system_diagnostics


class _FakeWorkflowService:
    def __init__(self, count: int) -> None:
        self._count = count

    def list_workflows(self):
        return [object()] * self._count


class SystemDiagnosticsTests(unittest.TestCase):
    @patch("services.system_diagnostics.get_available_comfyui_models")
    def test_reports_qwen_ready_when_checkpoint_present(self, mock_models) -> None:
        mock_models.return_value = {
            "checkpoint": ["Qwen-Image.safetensors"],
            "unet": ["flux.gguf"],
            "clip": [],
            "vae": [],
            "upscaler": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            report = collect_system_diagnostics(
                app_base_dir=tmp,
                settings={"selected_model": "Qwen: Qwen-Image.safetensors"},
                workflow_service=_FakeWorkflowService(count=2),
                styles_config={"off": {}, "cinematic": {}},
            )

        self.assertTrue(report.comfy_connected)
        self.assertTrue(report.qwen_ready)
        self.assertEqual(report.qwen_workflow_count, 2)
        self.assertFalse(any(item.severity == "warning" for item in report.issues))

    @patch("services.system_diagnostics.get_available_comfyui_models", side_effect=RuntimeError("offline"))
    def test_handles_connection_failure(self, _mock_models) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = collect_system_diagnostics(
                app_base_dir=tmp,
                settings={},
                workflow_service=_FakeWorkflowService(count=0),
                styles_config={"off": {}},
            )

        self.assertFalse(report.comfy_connected)
        self.assertTrue(any(item.severity == "error" for item in report.issues))

    @patch("services.system_diagnostics.get_available_comfyui_models", return_value={"checkpoint": [], "unet": [], "clip": [], "vae": [], "upscaler": []})
    def test_flags_pending_update(self, _mock_models) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from utils.update_state import UpdateState

            state = UpdateState(pending_tag="v2.0.0")
            state.save(base_dir=tmp)

            report = collect_system_diagnostics(
                app_base_dir=tmp,
                settings={},
                workflow_service=_FakeWorkflowService(count=1),
                styles_config={"off": {}, "warm": {}},
            )

        self.assertTrue(any("Update" in item.label for item in report.issues))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
