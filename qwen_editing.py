"""Prepare Qwen Image Edit workflows for ComfyUI queueing."""
from __future__ import annotations

import json
import os
import uuid
import traceback
from typing import Any, Dict, List, Tuple

from prompt_templates import (
    QWEN_UNET_LOADER_NODE,
    QWEN_CLIP_LOADER_NODE,
    QWEN_VAE_LOADER_NODE,
    QWEN_IMG2IMG_LOAD_IMAGE_NODE,
    QWEN_IMG2IMG_RESIZE_NODE,
    QWEN_IMG2IMG_VAE_ENCODE_NODE,
    QWEN_EDIT_SAMPLING_NODE,
    QWEN_KSAMPLER_NODE,
    QWEN_LORA_NODE,
    QWEN_NEG_PROMPT_NODE,
    QWEN_POS_PROMPT_NODE,
    QWEN_SAVE_IMAGE_NODE,
    QWEN_VAR_VAE_DECODE_NODE,
    qwen_edit_prompt,
)
from settings_manager import resolve_model_for_type


QWEN_IMAGE_EDIT_DIR = None


def _copy_qwen_edit_template() -> Dict[str, Any]:
    """Return a deep copy of the base Qwen Image Edit workflow template."""

    return json.loads(json.dumps(qwen_edit_prompt))


def _ensure_edit_directory() -> str:
    """Return the configured output directory for Qwen edits."""

    global QWEN_IMAGE_EDIT_DIR
    if QWEN_IMAGE_EDIT_DIR:
        return QWEN_IMAGE_EDIT_DIR

    default_dir = os.path.abspath(os.path.join("output", "TENOSAI-BOT", "GENERATIONS"))
    try:
        if os.path.exists("config.json"):
            import json

            with open("config.json", "r", encoding="utf-8") as config_fp:
                config_data = json.load(config_fp)
            outputs_cfg = config_data.get("OUTPUTS", {}) if isinstance(config_data, dict) else {}
            candidate = outputs_cfg.get("QWEN_EDITS") or outputs_cfg.get("GENERATIONS")
            if isinstance(candidate, str) and candidate.strip():
                default_dir = candidate.strip()
    except Exception as exc:  # pragma: no cover - defensive logging only
        print(f"Warning: Unable to read Qwen edit output path from config.json: {exc}")
        traceback.print_exc()

    QWEN_IMAGE_EDIT_DIR = os.path.abspath(default_dir)
    return QWEN_IMAGE_EDIT_DIR


def _normalise_path(path: str) -> str:
    return path.replace("\\", "/") if path else path


def modify_qwen_edit_prompt(
    *,
    image_urls: List[str],
    instruction: str,
    user_settings: Dict[str, Any],
    base_seed: int,
    steps_override: int,
    guidance_override: float,
    denoise_override: float,
    source_job_id: str = "unknown",
) -> Tuple[str | None, Dict | None, str | None, Dict | None]:
    """Prepare a Qwen Image Edit workflow and metadata for queueing."""

    if not image_urls:
        return None, None, "At least one reference image is required for Qwen edits.", None

    if len(image_urls) > 1:
        return None, None, "Qwen Image Edit currently supports a single base image.", None

    model_setting = resolve_model_for_type(user_settings, "qwen_edit")
    if not model_setting:
        return None, None, "Configure a Qwen Edit checkpoint in settings before running an edit.", None

    actual_model_name = model_setting.split(":", 1)[-1].strip()
    try:
        workflow = _copy_qwen_edit_template()
    except Exception as exc:  # pragma: no cover - defensive copy guard
        return None, None, f"Internal error: {exc}", None

    unet_key = str(QWEN_UNET_LOADER_NODE)
    workflow.setdefault(unet_key, {}).setdefault("inputs", {})["unet_name"] = actual_model_name

    clip_key = str(QWEN_CLIP_LOADER_NODE)
    clip_inputs = workflow.setdefault(clip_key, {}).setdefault("inputs", {})
    clip_override = user_settings.get("default_qwen_edit_clip")
    if isinstance(clip_override, str) and clip_override.strip():
        clip_inputs["clip_name"] = clip_override.strip()
    else:
        clip_inputs.setdefault("clip_name", "qwen_2.5_vl_7b_fp8_scaled.safetensors")

    vae_key = str(QWEN_VAE_LOADER_NODE)
    vae_inputs = workflow.setdefault(vae_key, {}).setdefault("inputs", {})
    vae_override = user_settings.get("default_qwen_edit_vae")
    if isinstance(vae_override, str) and vae_override.strip():
        vae_inputs["vae_name"] = vae_override.strip()
    else:
        vae_inputs.setdefault("vae_name", "qwen_image_vae.safetensors")

    lora_key = str(QWEN_LORA_NODE)
    lora_inputs = workflow.get(lora_key, {}).get("inputs") if isinstance(workflow.get(lora_key), dict) else None
    has_lora_node = isinstance(lora_inputs, dict)
    if has_lora_node:
        lora_inputs["model"] = [unet_key, 0]
        lora_inputs["clip"] = [clip_key, 0]

    sampling_key = str(QWEN_EDIT_SAMPLING_NODE)
    if sampling_key in workflow and "inputs" in workflow[sampling_key]:
        sampling_inputs = workflow[sampling_key]["inputs"]
        sampling_inputs["model"] = [lora_key, 0] if has_lora_node else [unet_key, 0]
        edit_shift = user_settings.get("qwen_edit_shift", 0.0)
        try:
            sampling_inputs["shift"] = float(edit_shift)
        except (TypeError, ValueError):
            sampling_inputs["shift"] = 0.0

    load_key = str(QWEN_IMG2IMG_LOAD_IMAGE_NODE)
    workflow.setdefault(load_key, {}).setdefault("inputs", {})["url_or_path"] = image_urls[0]

    resize_key = str(QWEN_IMG2IMG_RESIZE_NODE)
    if resize_key in workflow:
        workflow[resize_key].setdefault("inputs", {})["image"] = [load_key, 0]

    encode_key = str(QWEN_IMG2IMG_VAE_ENCODE_NODE)
    if encode_key in workflow:
        workflow[encode_key].setdefault("inputs", {})["pixels"] = [resize_key, 0]
        workflow[encode_key]["inputs"]["vae"] = [vae_key, 0]

    pos_key = str(QWEN_POS_PROMPT_NODE)
    workflow.setdefault(pos_key, {}).setdefault("inputs", {})["text"] = instruction.strip()
    workflow[pos_key]["inputs"]["clip"] = [lora_key, 1] if has_lora_node else [clip_key, 0]

    neg_prompt = (
        user_settings.get("default_qwen_edit_negative_prompt")
        or user_settings.get("default_qwen_negative_prompt")
        or ""
    )
    neg_key = str(QWEN_NEG_PROMPT_NODE)
    workflow.setdefault(neg_key, {}).setdefault("inputs", {})["text"] = neg_prompt
    workflow[neg_key]["inputs"]["clip"] = [lora_key, 1] if has_lora_node else [clip_key, 0]

    sampler_key = str(QWEN_KSAMPLER_NODE)
    sampler_inputs = workflow.setdefault(sampler_key, {}).setdefault("inputs", {})
    sampler_inputs.update(
        {
            "seed": base_seed,
            "steps": steps_override,
            "cfg": guidance_override,
            "denoise": denoise_override,
            "model": [sampling_key, 0],
            "positive": [pos_key, 0],
            "negative": [neg_key, 0],
            "latent_image": [encode_key, 0],
        }
    )

    decode_key = str(QWEN_VAR_VAE_DECODE_NODE)
    if decode_key in workflow:
        workflow[decode_key].setdefault("inputs", {})["samples"] = [sampler_key, 0]
        workflow[decode_key]["inputs"]["vae"] = [vae_key, 0]

    edits_dir = _ensure_edit_directory()
    os.makedirs(edits_dir, exist_ok=True)
    job_id = str(uuid.uuid4())[:8]
    filename_suffix = f"_from_{source_job_id}" if source_job_id != "unknown" else ""
    filename_prefix = _normalise_path(os.path.join(edits_dir, f"QWEN_EDIT_{job_id}{filename_suffix}"))

    save_key = str(QWEN_SAVE_IMAGE_NODE)
    workflow.setdefault(save_key, {}).setdefault("inputs", {})["filename_prefix"] = filename_prefix

    job_details = {
        "job_id": job_id,
        "type": "qwen_image_edit",
        "prompt": instruction,
        "seed": base_seed,
        "steps": steps_override,
        "guidance_qwen": guidance_override,
        "guidance_qwen_edit": guidance_override,
        "guidance": guidance_override,
        "denoise": denoise_override,
        "image_urls": image_urls,
        "qwen_model_used": actual_model_name,
        "model_used": actual_model_name,
        "source_job_id": source_job_id,
        "model_type_for_enhancer": "qwen",
    }

    status_message = f"Qwen edit job {job_id} prepared."
    return job_id, workflow, status_message, job_details

