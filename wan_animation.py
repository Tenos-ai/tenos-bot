# --- START OF FILE wan_animation.py ---
"""Helpers for preparing WAN animation follow-up workflows."""

from __future__ import annotations

import os
import uuid
import traceback
from typing import Any, Dict, Tuple

from bot_config_loader import config
from model_registry import get_model_spec, copy_animation_template
from settings_manager import load_settings, _get_default_settings
from utils.llm_enhancer import (
    enhance_prompt as util_enhance_prompt,
    WAN_ENHANCER_SYSTEM_PROMPT,
)
from utils.seed_utils import generate_seed


DEFAULT_ANIMATION_DIR = os.path.abspath(os.path.join("output", "TENOSAI-BOT", "ANIMATIONS"))


def _normalize_path_for_comfyui(path: str | None) -> str | None:
    """Convert Windows paths into forward-slash ComfyUI compatible strings."""

    if not path or not isinstance(path, str):
        return path

    normalized = path.replace("\\", "/")
    if normalized.startswith("//") and not normalized.startswith("\\\\"):
        normalized = "/" + normalized.lstrip("/")
    return normalized

def _apply_loader_filename(node: Dict[str, Any], *, field_name: str, file_name: str | None) -> None:
    """Update loader node inputs and widgets with a new filename."""

    if not node or not isinstance(node, dict) or not file_name:
        return

    inputs = node.setdefault("inputs", {})
    if isinstance(inputs, dict):
        inputs[field_name] = file_name

    widgets = node.get("widgets_values")
    if isinstance(widgets, list) and widgets:
        widgets[0] = file_name


def _extract_loader_default(template: Dict[str, Any], node_key: str, field_name: str) -> str | None:
    node = template.get(node_key)
    if not isinstance(node, dict):
        return None

    inputs = node.get("inputs")
    if isinstance(inputs, dict):
        candidate = inputs.get(field_name)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    widgets = node.get("widgets_values")
    if isinstance(widgets, list) and widgets:
        widget_candidate = widgets[0]
        if isinstance(widget_candidate, str) and widget_candidate.strip():
            return widget_candidate.strip()

    return None


def _pick_animation_asset(*candidates: Any) -> str | None:
    for candidate in candidates:
        if isinstance(candidate, str):
            value = candidate.strip()
            if value and "." in value:
                return value
    return None


async def prepare_wan_animation_prompt(
    source_job_data: Dict[str, Any],
    *,
    animation_image_path: str,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """Prepare a WAN animation workflow payload for a previously completed job."""

    settings = load_settings()
    wan_spec = get_model_spec("wan")
    template = copy_animation_template(wan_spec)

    motion_profile = str(
        source_job_data.get(
            "wan_animation_motion_profile",
            settings.get("wan_animation_motion_profile", "medium"),
        )
        or "medium"
    ).lower()

    resolution_value = str(
        source_job_data.get(
            "wan_animation_resolution",
            settings.get("wan_animation_resolution", "512x512"),
        )
        or "512x512"
    ).lower()

    duration_frames = int(
        source_job_data.get(
            "wan_animation_duration",
            settings.get("wan_animation_duration", 33),
        )
        or 33
    )

    try:
        width_str, height_str = resolution_value.lower().split("x", 1)
        width_val = max(64, int(width_str))
        height_val = max(64, int(height_str))
    except (ValueError, AttributeError):
        width_val, height_val = (512, 512)
        resolution_value = "512x512"

    style_used = source_job_data.get("style", "off")

    base_prompt_text = (
        source_job_data.get("enhanced_prompt")
        or source_job_data.get("prompt")
        or source_job_data.get("original_prompt")
        or "Describe the scene vividly."
    )

    motion_guidance = {
        "slowmo": "slow, lingering cinematography with gentle motion cues",
        "low": "understated, graceful motion with subtle camera drift",
        "medium": "cinematic pacing with balanced subject and camera movement",
        "high": "energetic, high-intensity motion with bold camera moves",
    }.get(motion_profile, "cinematic pacing with balanced subject and camera movement")

    llm_input = (
        "Create a WAN 2.2 animation direction based on the following still-image prompt.\n"
        "Describe the opening, evolving motion, and ending in two or three sentences.\n"
        f"Match the requested motion profile ({motion_profile} = {motion_guidance}).\n"
        f"Target roughly {duration_frames} frames at {resolution_value} resolution.\n"
        "Maintain subject fidelity and atmosphere from the source prompt while adding motion.\n\n"
        f"Still prompt:\n{base_prompt_text.strip()}"
    ).strip()

    animation_prompt_text, llm_error = await util_enhance_prompt(
        llm_input,
        system_prompt_text_override=WAN_ENHANCER_SYSTEM_PROMPT,
        target_model_type="wan",
    )

    llm_used = bool(animation_prompt_text)
    if not animation_prompt_text:
        animation_prompt_text = (
            f"{base_prompt_text.strip()} — captured with {motion_guidance}, unfolding over {duration_frames} frames."
        )

    llm_provider = settings.get("llm_provider", "gemini") if llm_used else None

    negative_prompt_text = (
        source_job_data.get("negative_prompt")
        or settings.get("default_wan_negative_prompt")
        or ""
    )

    model_loader_node_id = wan_spec.generation.model_loader_node
    t5_loader_node_id = wan_spec.generation.t5_loader_node
    text_encoder_node_id = wan_spec.generation.text_encoder_node
    vae_loader_node_id = wan_spec.generation.vae_loader_node
    image_loader_node_id = wan_spec.generation.image_loader_node
    image_resize_node_id = wan_spec.generation.image_resize_node
    image_encode_node_id = wan_spec.generation.image_encode_node
    image_embeds_node_id = wan_spec.generation.latent_node
    sampler_node_id = wan_spec.generation.ksampler_node
    decode_node_id = getattr(wan_spec.generation, "video_decode_node", None)
    save_node_id = wan_spec.generation.save_node

    default_model_name = _extract_loader_default(template, model_loader_node_id, "model")
    default_t5_name = _extract_loader_default(template, t5_loader_node_id, "model_name")
    default_vae_name = _extract_loader_default(template, vae_loader_node_id, "model_name")

    model_name = _pick_animation_asset(
        settings.get("default_wan_checkpoint"),
        default_model_name,
    )
    t5_model_name = _pick_animation_asset(
        settings.get("default_wan_clip"),
        default_t5_name,
    )
    vae_name = _pick_animation_asset(
        settings.get("default_wan_vae"),
        default_vae_name,
    )

    animation_seed = generate_seed()
    sampler_steps = int(settings.get("wan_steps", 30) or 30)
    sampler_guidance = float(settings.get("default_guidance_wan", 6.0) or 6.0)

    save_config = config.get("OUTPUTS", {})
    animations_dir = save_config.get("ANIMATIONS", DEFAULT_ANIMATION_DIR)
    if not isinstance(animations_dir, str) or not animations_dir.strip():
        animations_dir = DEFAULT_ANIMATION_DIR
    try:
        os.makedirs(animations_dir, exist_ok=True)
    except OSError as exc:
        print(f"Warning: Could not create animations directory '{animations_dir}': {exc}")

    job_id = str(uuid.uuid4())[:8]

    start_image_norm = _normalize_path_for_comfyui(animation_image_path)
    save_prefix = _normalize_path_for_comfyui(os.path.join(animations_dir, f"WAN_ANIM_{job_id}"))

    try:
        model_node = template.get(model_loader_node_id)
        _apply_loader_filename(model_node, field_name="model", file_name=model_name)

        t5_node = template.get(t5_loader_node_id)
        _apply_loader_filename(t5_node, field_name="model_name", file_name=t5_model_name)

        vae_node = template.get(vae_loader_node_id)
        _apply_loader_filename(vae_node, field_name="model_name", file_name=vae_name)

        if text_encoder_node_id and text_encoder_node_id in template:
            text_node = template[text_encoder_node_id]
            encoder_inputs = text_node.setdefault("inputs", {})
            encoder_inputs["positive_prompt"] = animation_prompt_text
            encoder_inputs["negative_prompt"] = negative_prompt_text

        if image_loader_node_id and image_loader_node_id in template:
            load_image_node = template[image_loader_node_id]
            load_inputs = load_image_node.setdefault("inputs", {})
            load_inputs["url_or_path"] = start_image_norm or ""
            widgets = load_image_node.get("widgets_values")
            if isinstance(widgets, list) and widgets:
                widgets[0] = start_image_norm or ""

        if image_resize_node_id and image_resize_node_id in template:
            resize_inputs = template[image_resize_node_id].setdefault("inputs", {})
            resize_inputs["image"] = [str(image_loader_node_id), 0]

        if image_encode_node_id and image_encode_node_id in template:
            encode_node = template[image_encode_node_id]
            encode_inputs = encode_node.setdefault("inputs", {})
            encode_inputs.update(
                {
                    "vae": [str(vae_loader_node_id), 0],
                    "image": [str(image_resize_node_id), 0],
                    "enable_vae_tiling": False,
                    "tile_x": 272,
                    "tile_y": 272,
                    "tile_stride_x": 144,
                    "tile_stride_y": 128,
                    "noise_aug_strength": 0.0,
                    "latent_strength": 1.0,
                }
            )
            encode_node["widgets_values"] = [False, 272, 272, 144, 128, 0.0, 1.0]

        if image_embeds_node_id and image_embeds_node_id in template:
            embed_node = template[image_embeds_node_id]
            embed_inputs = embed_node.setdefault("inputs", {})
            embed_inputs.update({
                "width": width_val,
                "height": height_val,
                "num_frames": duration_frames,
                "extra_latents": [str(image_encode_node_id), 0],
            })
            embed_node["widgets_values"] = [width_val, height_val, duration_frames]

        sampler_node = template.get(sampler_node_id)
        if sampler_node:
            sampler_inputs = sampler_node.setdefault("inputs", {})
            default_settings = _get_default_settings()
            default_shift = default_settings.get("default_wan_shift", 8.0)
            shift_candidate_anim = settings.get("default_wan_shift", default_shift)
            try:
                shift_value_anim = float(shift_candidate_anim)
            except (TypeError, ValueError):
                shift_value_anim = float(default_shift)

            sampler_inputs.update(
                {
                    "seed": int(animation_seed),
                    "steps": sampler_steps,
                    "cfg": float(sampler_guidance),
                    "shift": float(shift_value_anim),
                    "denoise_strength": 1.0,
                    "samples": [str(image_encode_node_id), 0],
                    "add_noise_to_samples": False,
                }
            )

            widgets = sampler_node.setdefault("widgets_values", [])
            default_widgets = [
                sampler_steps,
                float(sampler_guidance),
                float(shift_value_anim),
                int(animation_seed),
                "fixed",
                True,
                sampler_inputs.get("scheduler", "unipc"),
                sampler_inputs.get("riflex_freq_index", 0),
                1.0,
                sampler_inputs.get("batched_cfg", False),
                sampler_inputs.get("rope_function", "comfy"),
                sampler_inputs.get("start_step", 0),
                sampler_inputs.get("end_step", -1),
                False,
                "",
            ]
            if not widgets:
                widgets.extend(default_widgets)
            else:
                while len(widgets) < len(default_widgets):
                    widgets.append(default_widgets[len(widgets)])
                widgets[0] = sampler_steps
                widgets[1] = float(sampler_guidance)
                widgets[2] = float(shift_value_anim)
                widgets[3] = int(animation_seed)
                widgets[8] = 1.0
                widgets[13] = False

        if decode_node_id and decode_node_id in template:
            decode_entry = template[decode_node_id]
            decode_inputs = decode_entry.setdefault("inputs", {})
            decode_inputs["samples"] = [str(sampler_node_id), 0]
            decode_inputs.setdefault("vae", [str(vae_loader_node_id), 0])

        save_video_node = template.get(save_node_id)
        if save_video_node:
            widgets = save_video_node.get("widgets_values")
            if isinstance(widgets, dict):
                widgets["filename_prefix"] = save_prefix or "wanbot/ANIMATION"
            save_inputs = save_video_node.setdefault("inputs", {})
            save_inputs["filename_prefix"] = save_prefix or "wanbot/ANIMATION"
    except Exception as template_error:
        print(f"Error while configuring WAN animation template: {template_error}")
        traceback.print_exc()
        raise

    job_details: Dict[str, Any] = {
        "job_id": job_id,
        "prompt": animation_prompt_text,
        "negative_prompt": negative_prompt_text,
        "seed": int(animation_seed),
        "steps": sampler_steps,
        "guidance": sampler_guidance,
        "guidance_wan": sampler_guidance,
        "guidance_sdxl": None,
        "guidance_qwen": None,
        "width": width_val,
        "height": height_val,
        "aspect_ratio_str": resolution_value,
        "mp_size": f"{width_val}x{height_val}",
        "image_url": start_image_norm,
        "img_strength_percent": None,
        "denoise": None,
        "style": style_used,
        "batch_size": 1,
        "image_index": 1,
        "selected_model": source_job_data.get("selected_model"),
        "model_used": model_name,
        "type": "wan_animation",
        "model_type_for_enhancer": "wan",
        "enhancer_used": llm_used,
        "llm_provider": llm_provider,
        "enhancer_error": llm_error,
        "original_prompt": base_prompt_text,
        "enhanced_prompt": animation_prompt_text,
        "style_warning_message": None,
        "supports_animation": False,
        "followup_animation_workflow": None,
        "wan_animation_resolution": resolution_value,
        "wan_animation_duration": duration_frames,
        "wan_animation_motion_profile": motion_profile,
        "original_job_id": source_job_data.get("job_id"),
        "parameters_used": {
            "source_job_id": source_job_data.get("job_id"),
            "resolution": resolution_value,
            "frames": duration_frames,
            "motion_profile": motion_profile,
            "animation_prompt": animation_prompt_text,
            "seed": int(animation_seed),
            "steps": sampler_steps,
            "guidance": sampler_guidance,
            "input_image_path": start_image_norm,
        },
        "animation_prompt_text": animation_prompt_text,
    }

    return job_id, template, job_details


__all__ = ["prepare_wan_animation_prompt"]
# --- END OF FILE wan_animation.py ---
