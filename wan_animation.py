# --- START OF FILE wan_animation.py ---
"""Helpers for preparing WAN animation follow-up workflows."""

from __future__ import annotations

import os
import uuid
import traceback
from typing import Any, Dict, Tuple

from bot_config_loader import config
from model_registry import get_model_spec, copy_animation_template
from settings_manager import load_settings
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


def _apply_sampling_shift_overrides(prompt: Dict[str, Any], shift_value: float | None) -> None:
    if shift_value is None:
        return

    for node_data in prompt.values():
        if not isinstance(node_data, dict):
            continue
        if node_data.get("class_type") not in {"ModelSamplingAuraFlow", "ModelSamplingSD3"}:
            continue
        inputs = node_data.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            continue
        inputs.pop("clip", None)
        inputs.pop("model_b", None)
        inputs.pop("cfg_rescale", None)
        try:
            inputs["shift"] = float(shift_value)
        except (TypeError, ValueError):
            inputs["shift"] = 0.0


def _apply_loader_filename(node: Dict[str, Any], *, field_name: str, file_name: str | None) -> None:
    """Update loader node inputs and widgets with a new filename."""

    if not node or not isinstance(node, dict) or not file_name:
        return

    inputs = node.setdefault("inputs", {})
    if isinstance(inputs, dict) and field_name in inputs:
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

    source_model_type = str(
        source_job_data.get("model_type_for_enhancer")
        or source_job_data.get("model_type")
        or ""
    ).lower()

    default_high_unet = _extract_loader_default(template, "wan_unet_high", "unet_name")
    default_low_unet = _extract_loader_default(template, "wan_unet_low", "unet_name")
    default_clip_name = _extract_loader_default(template, "wan_clip", "clip_name")
    default_vision_clip = _extract_loader_default(template, "wan_i2v_vision_clip", "clip_name")
    default_vae_name = _extract_loader_default(template, "wan_vae", "vae_name")

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

    high_noise_unet = _pick_animation_asset(
        source_job_data.get("model_used") if source_model_type == "wan" else None,
        settings.get("default_wan_checkpoint"),
        default_high_unet,
    )
    low_noise_unet = _pick_animation_asset(
        settings.get("default_wan_low_noise_unet"),
        default_low_unet,
    )
    clip_name = _pick_animation_asset(
        settings.get("default_wan_clip"),
        default_clip_name,
    )
    vision_clip = _pick_animation_asset(
        settings.get("default_wan_vision_clip"),
        default_vision_clip,
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
        high_node = template.get("wan_unet_high")
        _apply_loader_filename(high_node, field_name="unet_name", file_name=high_noise_unet)

        low_node = template.get("wan_unet_low")
        _apply_loader_filename(low_node, field_name="unet_name", file_name=low_noise_unet)

        clip_node = template.get("wan_clip")
        if clip_node and clip_name:
            clip_inputs = clip_node.setdefault("inputs", {})
            clip_inputs["clip_name"] = clip_name
            widgets = clip_node.get("widgets_values")
            if isinstance(widgets, list) and widgets:
                widgets[0] = clip_name

        vision_node = template.get("wan_i2v_vision_clip")
        _apply_loader_filename(vision_node, field_name="clip_name", file_name=vision_clip)

        vae_node = template.get("wan_vae")
        _apply_loader_filename(vae_node, field_name="vae_name", file_name=vae_name)

        load_image_node = template.get("wan_i2v_image")
        if load_image_node and isinstance(load_image_node.get("widgets_values"), list):
            load_image_node["widgets_values"][0] = start_image_norm or ""

        pos_prompt_node = template.get("wan_pos_prompt")
        if pos_prompt_node:
            inputs = pos_prompt_node.setdefault("inputs", {})
            inputs["text"] = animation_prompt_text

        neg_prompt_node = template.get("wan_neg_prompt")
        if neg_prompt_node:
            inputs = neg_prompt_node.setdefault("inputs", {})
            inputs["text"] = negative_prompt_text

        ksampler_node = template.get("wan_i2v_ksampler")
        if ksampler_node and isinstance(ksampler_node.get("widgets_values"), list):
            widgets = ksampler_node["widgets_values"]
            if widgets:
                widgets[0] = int(animation_seed)
            if len(widgets) > 1:
                widgets[1] = "fixed"
            if len(widgets) > 2:
                widgets[2] = sampler_steps
            if len(widgets) > 3:
                widgets[3] = float(sampler_guidance)

        image_to_video_node = template.get("wan_image_to_video")
        if image_to_video_node and isinstance(image_to_video_node.get("widgets_values"), list):
            widgets = image_to_video_node["widgets_values"]
            if widgets:
                widgets[0] = width_val
            if len(widgets) > 1:
                widgets[1] = height_val
            if len(widgets) > 2:
                widgets[2] = duration_frames

        create_video_node = template.get("wan_i2v_create")
        if create_video_node and isinstance(create_video_node.get("widgets_values"), list) and create_video_node["widgets_values"]:
            # Keep fps default but ensure integer formatting
            create_video_node["widgets_values"][0] = int(create_video_node["widgets_values"][0] or 16)

        save_video_node = template.get("wan_i2v_save")
        if save_video_node and isinstance(save_video_node.get("widgets_values"), list) and save_video_node["widgets_values"]:
            save_video_node["widgets_values"][0] = save_prefix or "wanbot/ANIMATION"

        shift_candidate_anim = settings.get("default_wan_shift", 0.0)
        try:
            shift_value_anim = float(shift_candidate_anim)
        except (TypeError, ValueError):
            shift_value_anim = 0.0
        _apply_sampling_shift_overrides(template, shift_value_anim)
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
        "mp_size": "N/A",
        "image_url": start_image_norm,
        "img_strength_percent": None,
        "denoise": None,
        "style": style_used,
        "batch_size": 1,
        "image_index": 1,
        "selected_model": source_job_data.get("selected_model"),
        "model_used": high_noise_unet,
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
