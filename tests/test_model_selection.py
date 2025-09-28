import asyncio
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.modules.setdefault("discord", MagicMock())
sys.modules.setdefault("PIL", SimpleNamespace(Image=MagicMock()))
sys.modules.setdefault("numpy", MagicMock())
sys.modules.setdefault("aiohttp", MagicMock())

from prompt_templates import GENERATION_MODEL_NODE


class ModelSelectionTests(unittest.TestCase):
    """Ensure user-selected models drive every workflow."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    @patch("image_generation.os.makedirs")
    @patch("image_generation.check_available_models_api")
    @patch("image_generation.load_styles_config")
    @patch("image_generation.load_settings")
    def test_generation_applies_selected_model_even_when_missing_from_comfy(
        self,
        mock_load_settings,
        mock_load_styles,
        mock_check_models,
        mock_makedirs,
    ):
        import image_generation
        from settings_manager import _get_default_settings

        base_settings = _get_default_settings()
        base_settings["selected_model"] = "Flux: custom-model.gguf"
        mock_load_settings.return_value = base_settings
        mock_load_styles.return_value = {"off": {}}
        mock_check_models.return_value = {"unet": ["other-model.gguf"], "checkpoint": [], "clip": []}

        job_id, prompt, _, job_details = self.loop.run_until_complete(
            image_generation.modify_prompt(
                original_prompt_text="A scenic vista",
                params_dict={},
                enhancer_info={"used": False, "provider": None, "enhanced_text": None, "error": None},
                is_img2img=False,
                explicit_seed=42,
                selected_model_name_with_prefix=None,
                negative_prompt_text=None,
            )
        )

        self.assertIsNotNone(job_id)
        loader_node = prompt[str(GENERATION_MODEL_NODE)]
        self.assertEqual(loader_node["inputs"]["unet_name"], "custom-model.gguf")
        warning = job_details.get("model_warning_message")
        self.assertIsNotNone(warning)
        self.assertIn("custom-model.gguf", warning)

    @patch("image_generation.load_styles_config", return_value={"off": {}})
    @patch("image_generation.load_settings")
    def test_generation_errors_when_no_model_selected(self, mock_load_settings, _mock_styles):
        import image_generation
        from settings_manager import _get_default_settings

        base_settings = _get_default_settings()
        base_settings["selected_model"] = ""
        mock_load_settings.return_value = base_settings

        job_id, _, message, _ = self.loop.run_until_complete(
            image_generation.modify_prompt(
                original_prompt_text="Test",
                params_dict={},
                enhancer_info={"used": False, "provider": None, "enhanced_text": None, "error": None},
                is_img2img=False,
                explicit_seed=None,
                selected_model_name_with_prefix=None,
                negative_prompt_text=None,
            )
        )

        self.assertIsNone(job_id)
        self.assertIn("No base model", message)

    @patch("variation.load_styles_config", return_value={"off": {}})
    @patch("variation.load_settings")
    def test_variation_errors_when_no_model_selected(self, mock_load_settings, _mock_styles):
        import variation
        from settings_manager import _get_default_settings

        base_settings = _get_default_settings()
        base_settings["selected_model"] = ""
        mock_load_settings.return_value = base_settings

        result = variation.modify_variation_prompt(
            message_content_or_obj="/vary",
            referenced_message=None,
            variation_type="strong",
            target_image_url="http://example.com/image.png",
            image_index=1,
        )

        self.assertTrue(result)
        job_id, _, message, _ = result[0]
        self.assertIsNone(job_id)
        self.assertIn("No base model", message)

    @patch("upscaling.load_styles_config", return_value={"off": {}})
    @patch("upscaling.load_settings")
    def test_upscale_errors_when_no_model_selected(self, mock_load_settings, _mock_styles):
        import upscaling
        from settings_manager import _get_default_settings

        base_settings = _get_default_settings()
        base_settings["selected_model"] = ""
        mock_load_settings.return_value = base_settings

        job_id, _, message, _ = upscaling.modify_upscale_prompt(
            message_content_or_obj="/upscale",
            referenced_message=None,
            target_image_url="http://example.com/image.png",
            image_index=1,
        )

        self.assertIsNone(job_id)
        self.assertIn("No base model", message)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
