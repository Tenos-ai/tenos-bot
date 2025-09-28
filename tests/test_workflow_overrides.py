import json
import tempfile
import unittest
from pathlib import Path

from workflows import load_workflow_template
from settings_manager import _sanitize_custom_workflows, _get_default_settings


class WorkflowOverrideTests(unittest.TestCase):
    def test_custom_workflow_overrides_default_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "flux_custom.json"
            custom_path.write_text(json.dumps({"1": {"class_type": "CustomLoader"}}))

            settings = {
                "custom_workflows": {
                    "flux": {"text_to_image": str(custom_path)},
                }
            }

            result = load_workflow_template("flux", "text_to_image", settings=settings)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["1"]["class_type"], "CustomLoader")

    def test_invalid_override_falls_back_to_default(self):
        settings = {
            "custom_workflows": {
                "flux": {"text_to_image": "nonexistent.json"},
            }
        }
        result = load_workflow_template("flux", "text_to_image", settings=settings)
        self.assertIn("1", result)
        self.assertEqual(result["1"]["class_type"], "UnetLoaderGGUF")

    def test_unknown_slot_raises_value_error(self):
        with self.assertRaises(ValueError):
            load_workflow_template("flux", "unknown")


class SettingsSanitiseTests(unittest.TestCase):
    def test_sanitises_custom_workflow_structure(self):
        defaults = _get_default_settings()["custom_workflows"]
        overrides = {
            "flux": {"text_to_image": ""},
            "sdxl": {"text_to_image": "custom.json", "extra": "ignored"},
            "unexpected": {"slot": "value"},
        }
        cleaned = _sanitize_custom_workflows(overrides, defaults)
        self.assertIsNone(cleaned["flux"]["text_to_image"])
        self.assertEqual(cleaned["sdxl"]["text_to_image"], "custom.json")
        self.assertIn("unexpected", cleaned)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
