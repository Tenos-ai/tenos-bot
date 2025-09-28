"""Qwen Image ComfyUI workflow templates used across Tenos.AI tooling."""
from __future__ import annotations

from copy import deepcopy
from typing import Dict

from prompt_templates import (
    QWEN_CHECKPOINT_LOADER_NODE,
    QWEN_CLIP_SKIP_NODE,
    QWEN_IMG2IMG_LOAD_IMAGE_NODE,
    QWEN_IMG2IMG_RESIZE_NODE,
    QWEN_IMG2IMG_VAE_ENCODE_NODE,
    QWEN_KSAMPLER_NODE,
    QWEN_LATENT_NODE,
    QWEN_LORA_NODE,
    QWEN_NEG_PROMPT_NODE,
    QWEN_POS_PROMPT_NODE,
    QWEN_SAVE_IMAGE_NODE,
    QWEN_UPSCALE_CLIP_SKIP_NODE,
    QWEN_UPSCALE_HELPER_LATENT_NODE,
    QWEN_UPSCALE_LOAD_IMAGE_NODE,
    QWEN_UPSCALE_LORA_NODE,
    QWEN_UPSCALE_MODEL_LOADER_NODE,
    QWEN_UPSCALE_NEG_PROMPT_NODE,
    QWEN_UPSCALE_POS_PROMPT_NODE,
    QWEN_UPSCALE_SAVE_IMAGE_NODE,
    QWEN_UPSCALE_ULTIMATE_NODE,
    QWEN_VAR_BATCH_NODE,
    QWEN_VAR_CLIP_SKIP_NODE,
    QWEN_VAR_KSAMPLER_NODE,
    QWEN_VAR_LORA_NODE,
    QWEN_VAR_LOAD_IMAGE_NODE,
    QWEN_VAR_NEG_PROMPT_NODE,
    QWEN_VAR_POS_PROMPT_NODE,
    QWEN_VAR_RESIZE_NODE,
    QWEN_VAR_SAVE_IMAGE_NODE,
    QWEN_VAR_VAE_DECODE_NODE,
    QWEN_VAR_VAE_ENCODE_NODE,
)

Workflow = Dict[str, dict]


def _clone(template: Workflow) -> Workflow:
    return deepcopy(template)


_QWEN_TEXT_TO_IMAGE: Workflow = {
    str(QWEN_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load Qwen Checkpoint"},
    },
    str(QWEN_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(QWEN_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(QWEN_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (Qwen)"},
    },
    str(QWEN_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(QWEN_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2 (Qwen)"},
    },
    str(QWEN_POS_PROMPT_NODE): {
        "inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(QWEN_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt (Qwen)"},
    },
    str(QWEN_NEG_PROMPT_NODE): {
        "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(QWEN_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt (Qwen)"},
    },
    str(QWEN_KSAMPLER_NODE): {
        "inputs": {
            "seed": 12345,
            "steps": 30,
            "cfg": 6.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": [str(QWEN_LORA_NODE), 0],
            "positive": [str(QWEN_POS_PROMPT_NODE), 0],
            "negative": [str(QWEN_NEG_PROMPT_NODE), 0],
            "latent_image": [str(QWEN_LATENT_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler (Qwen)"},
    },
    str(QWEN_VAR_VAE_DECODE_NODE): {
        "inputs": {
            "samples": [str(QWEN_KSAMPLER_NODE), 0],
            "vae": [str(QWEN_CHECKPOINT_LOADER_NODE), 2],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode (Qwen)"},
    },
    str(QWEN_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "qwenbot/GEN",
            "images": [str(QWEN_VAR_VAE_DECODE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image (Qwen)"},
    },
    "qwen_preview": {
        "inputs": {"images": [str(QWEN_VAR_VAE_DECODE_NODE), 0]},
        "class_type": "PreviewImage",
        "_meta": {"title": "Qwen Preview"},
    },
    str(QWEN_LATENT_NODE): {
        "inputs": {
            "aspect_ratio": "1:1",
            "mp_size_float": "1",
            "upscale_by": 1.0,
            "model_type": "QWEN",
            "batch_size": 1,
        },
        "class_type": "BobsLatentNodeAdvanced",
        "_meta": {"title": "Bobs Latent Optimizer (Qwen)"},
    },
}


_QWEN_IMG2IMG: Workflow = {
    str(QWEN_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load Qwen Checkpoint"},
    },
    str(QWEN_IMG2IMG_LOAD_IMAGE_NODE): {
        "inputs": {"url_or_path": "IMAGE_URL_HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "Load Image (Qwen Img2Img)"},
    },
    str(QWEN_IMG2IMG_RESIZE_NODE): {
        "inputs": {"interpolation": "bicubic", "image": [str(QWEN_IMG2IMG_LOAD_IMAGE_NODE), 0]},
        "class_type": "TenosResizeToTargetPixels",
        "_meta": {"title": "Resize Input (Qwen Img2Img)"},
    },
    str(QWEN_IMG2IMG_VAE_ENCODE_NODE): {
        "inputs": {"pixels": [str(QWEN_IMG2IMG_RESIZE_NODE), 0], "vae": [str(QWEN_CHECKPOINT_LOADER_NODE), 2]},
        "class_type": "VAEEncode",
        "_meta": {"title": "VAE Encode (Qwen Img2Img)"},
    },
    str(QWEN_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(QWEN_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(QWEN_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (Qwen Img2Img)"},
    },
    str(QWEN_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(QWEN_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2 (Qwen Img2Img)"},
    },
    str(QWEN_POS_PROMPT_NODE): {
        "inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(QWEN_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt (Qwen Img2Img)"},
    },
    str(QWEN_NEG_PROMPT_NODE): {
        "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(QWEN_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt (Qwen Img2Img)"},
    },
    str(QWEN_KSAMPLER_NODE): {
        "inputs": {
            "seed": 12345,
            "steps": 30,
            "cfg": 6.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 0.75,
            "model": [str(QWEN_LORA_NODE), 0],
            "positive": [str(QWEN_POS_PROMPT_NODE), 0],
            "negative": [str(QWEN_NEG_PROMPT_NODE), 0],
            "latent_image": [str(QWEN_IMG2IMG_VAE_ENCODE_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler (Qwen Img2Img)"},
    },
    str(QWEN_VAR_VAE_DECODE_NODE): {
        "inputs": {
            "samples": [str(QWEN_KSAMPLER_NODE), 0],
            "vae": [str(QWEN_CHECKPOINT_LOADER_NODE), 2],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode (Qwen Img2Img)"},
    },
    str(QWEN_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "qwenbot/GEN_I2I",
            "images": [str(QWEN_VAR_VAE_DECODE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image (Qwen Img2Img)"},
    },
    "qwen_i2i_preview": {
        "inputs": {"images": [str(QWEN_VAR_VAE_DECODE_NODE), 0]},
        "class_type": "PreviewImage",
        "_meta": {"title": "Qwen Img2Img Preview"},
    },
}


_QWEN_VARIATION: Workflow = {
    str(QWEN_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load Qwen Checkpoint"},
    },
    str(QWEN_VAR_LOAD_IMAGE_NODE): {
        "inputs": {"url_or_path": "IMAGE_URL_HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "Load Image (Qwen Variation)"},
    },
    str(QWEN_VAR_RESIZE_NODE): {
        "inputs": {"interpolation": "bicubic", "image": [str(QWEN_VAR_LOAD_IMAGE_NODE), 0]},
        "class_type": "TenosResizeToTargetPixels",
        "_meta": {"title": "Resize Input (Qwen Variation)"},
    },
    str(QWEN_VAR_VAE_ENCODE_NODE): {
        "inputs": {"pixels": [str(QWEN_VAR_RESIZE_NODE), 0], "vae": [str(QWEN_CHECKPOINT_LOADER_NODE), 2]},
        "class_type": "VAEEncode",
        "_meta": {"title": "VAE Encode (Qwen Variation)"},
    },
    str(QWEN_VAR_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(QWEN_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(QWEN_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (Qwen Variation)"},
    },
    str(QWEN_VAR_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(QWEN_VAR_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2 (Qwen Variation)"},
    },
    str(QWEN_VAR_POS_PROMPT_NODE): {
        "inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(QWEN_VAR_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt (Qwen Variation)"},
    },
    str(QWEN_VAR_NEG_PROMPT_NODE): {
        "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(QWEN_VAR_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt (Qwen Variation)"},
    },
    str(QWEN_VAR_KSAMPLER_NODE): {
        "inputs": {
            "seed": 12345,
            "steps": 30,
            "cfg": 6.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 0.7,
            "control_after_generate": "increment",
            "model": [str(QWEN_VAR_LORA_NODE), 0],
            "positive": [str(QWEN_VAR_POS_PROMPT_NODE), 0],
            "negative": [str(QWEN_VAR_NEG_PROMPT_NODE), 0],
            "latent_image": [str(QWEN_VAR_BATCH_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler (Qwen Variation)"},
    },
    str(QWEN_VAR_VAE_DECODE_NODE): {
        "inputs": {
            "samples": [str(QWEN_VAR_KSAMPLER_NODE), 0],
            "vae": [str(QWEN_CHECKPOINT_LOADER_NODE), 2],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode (Qwen Variation)"},
    },
    str(QWEN_VAR_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "qwenbot/VAR",
            "images": [str(QWEN_VAR_VAE_DECODE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image (Qwen Variation)"},
    },
    str(QWEN_VAR_BATCH_NODE): {
        "inputs": {"amount": 1, "samples": [str(QWEN_VAR_VAE_ENCODE_NODE), 0]},
        "class_type": "RepeatLatentBatch",
        "_meta": {"title": "RepeatLatentBatch (Qwen Variation)"},
    },
}


_QWEN_UPSCALE: Workflow = {
    str(QWEN_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load Qwen Checkpoint"},
    },
    str(QWEN_UPSCALE_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(QWEN_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(QWEN_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (Qwen Upscale)"},
    },
    str(QWEN_UPSCALE_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(QWEN_UPSCALE_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2 (Qwen Upscale)"},
    },
    str(QWEN_UPSCALE_POS_PROMPT_NODE): {
        "inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(QWEN_UPSCALE_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt (Qwen Upscale)"},
    },
    str(QWEN_UPSCALE_NEG_PROMPT_NODE): {
        "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(QWEN_UPSCALE_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt (Qwen Upscale)"},
    },
    str(QWEN_UPSCALE_ULTIMATE_NODE): {
        "inputs": {
            "seed": 987654321,
            "steps": 16,
            "cfg": 1.5,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 0.2,
            "mode_type": "Linear",
            "mask_blur": 16,
            "tile_padding": 32,
            "seam_fix_mode": "None",
            "seam_fix_denoise": 0.15,
            "seam_fix_width": 64,
            "seam_fix_mask_blur": 8,
            "seam_fix_padding": 16,
            "force_uniform_tiles": False,
            "tiled_decode": False,
            "image": [str(QWEN_UPSCALE_LOAD_IMAGE_NODE), 0],
            "model": [str(QWEN_UPSCALE_LORA_NODE), 0],
            "positive": [str(QWEN_UPSCALE_POS_PROMPT_NODE), 0],
            "negative": [str(QWEN_UPSCALE_NEG_PROMPT_NODE), 0],
            "vae": [str(QWEN_CHECKPOINT_LOADER_NODE), 2],
            "upscale_model": [str(QWEN_UPSCALE_MODEL_LOADER_NODE), 0],
            "upscale_by": [str(QWEN_UPSCALE_HELPER_LATENT_NODE), 3],
            "tile_width": [str(QWEN_UPSCALE_HELPER_LATENT_NODE), 1],
            "tile_height": [str(QWEN_UPSCALE_HELPER_LATENT_NODE), 2],
        },
        "class_type": "UltimateSDUpscale",
        "_meta": {"title": "Ultimate Upscale (Qwen)"},
    },
    str(QWEN_UPSCALE_MODEL_LOADER_NODE): {
        "inputs": {"model_name": "4x-UltraSharp.pth"},
        "class_type": "UpscaleModelLoader",
        "_meta": {"title": "Load Upscale Model (Qwen)"},
    },
    str(QWEN_UPSCALE_LOAD_IMAGE_NODE): {
        "inputs": {"url_or_path": "IMAGE_URL_HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "Load Image (Qwen Upscale)"},
    },
    str(QWEN_UPSCALE_HELPER_LATENT_NODE): {
        "inputs": {
            "aspect_ratio": "1:1",
            "mp_size_float": "1",
            "upscale_by": 2.0,
            "model_type": "QWEN",
            "batch_size": 1,
        },
        "class_type": "BobsLatentNodeAdvanced",
        "_meta": {"title": "Bobs Upscale Param Calculator (Qwen)"},
    },
    str(QWEN_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "qwenbot/UPSCALE",
            "images": [str(QWEN_UPSCALE_ULTIMATE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image (Qwen Upscale)"},
    },
}


__all__ = [
    "qwen_text_to_image_template",
    "qwen_img2img_template",
    "qwen_image_edit_template",
    "qwen_variation_template",
    "qwen_upscale_template",
]


def qwen_text_to_image_template() -> Workflow:
    return _clone(_QWEN_TEXT_TO_IMAGE)


def qwen_img2img_template() -> Workflow:
    return _clone(_QWEN_IMG2IMG)


def qwen_image_edit_template() -> Workflow:
    template = _clone(_QWEN_IMG2IMG)
    loader_key = str(QWEN_IMG2IMG_LOAD_IMAGE_NODE)
    if loader_key in template and "_meta" in template[loader_key]:
        template[loader_key]["_meta"]["title"] = "Load Image (Qwen Edit)"
    save_key = str(QWEN_SAVE_IMAGE_NODE)
    if save_key in template and "inputs" in template[save_key]:
        template[save_key]["inputs"]["filename_prefix"] = "qwenbot/EDIT"
        template[save_key]["_meta"] = {"title": "Save Image (Qwen Edit)"}
    return template


def qwen_variation_template() -> Workflow:
    return _clone(_QWEN_VARIATION)


def qwen_upscale_template() -> Workflow:
    return _clone(_QWEN_UPSCALE)
