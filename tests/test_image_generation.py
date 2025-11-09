import asyncio
import pytest

import image_generation
from prompt_templates import SDXL_CHECKPOINT_LOADER_NODE


def test_modify_prompt_hydrates_sdxl_checkpoint(monkeypatch):
    """Ensure the SDXL template uses the selected checkpoint name."""

    selected_model = "sdxl::custom_model.safetensors"

    fake_settings = {
        "default_guidance_sdxl": 6.5,
        "sdxl_steps": 24,
        "default_style_sdxl": "off",
        "default_mp_size": "1",
        "default_batch_size": 1,
        "selected_model": selected_model,
    }

    monkeypatch.setattr(image_generation, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(image_generation, "load_styles_config", lambda: {})
    monkeypatch.setattr(image_generation, "generate_seed", lambda: 42)
    monkeypatch.setattr(
        image_generation,
        "check_available_models_api",
        lambda suppress_summary_print=True: {"checkpoint": [], "unet": [], "clip": []},
    )

    enhancer_info = {"used": False, "provider": None, "enhanced_text": None, "error": None}

    job_id, prompt_payload, status_message, job_details = asyncio.run(
        image_generation.modify_prompt(
            original_prompt_text="test prompt",
            params_dict={},
            enhancer_info=enhancer_info,
            is_img2img=False,
            explicit_seed=None,
            selected_model_name_with_prefix=selected_model,
            negative_prompt_text=None,
        )
    )

    assert job_id is not None
    assert status_message is not None
    loader_node = prompt_payload[str(SDXL_CHECKPOINT_LOADER_NODE)]
    assert loader_node["inputs"]["ckpt_name"] == "custom_model.safetensors"
    assert job_details["model_used"] == "custom_model.safetensors"
