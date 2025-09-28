"""SDXL ComfyUI workflow templates extracted for modular reuse."""
from __future__ import annotations

from copy import deepcopy
from typing import Dict

from prompt_templates import (
    SDXL_CHECKPOINT_LOADER_NODE,
    SDXL_CLIP_SKIP_NODE,
    SDXL_IMG2IMG_LOAD_IMAGE_NODE,
    SDXL_IMG2IMG_RESIZE_NODE,
    SDXL_IMG2IMG_VAE_ENCODE_NODE,
    SDXL_KSAMPLER_NODE,
    SDXL_LATENT_NODE,
    SDXL_LORA_NODE,
    SDXL_NEG_PROMPT_NODE,
    SDXL_POS_PROMPT_NODE,
    SDXL_SAVE_IMAGE_NODE,
    SDXL_UPSCALE_CLIP_SKIP_NODE,
    SDXL_UPSCALE_HELPER_LATENT_NODE,
    SDXL_UPSCALE_LOAD_IMAGE_NODE,
    SDXL_UPSCALE_LORA_NODE,
    SDXL_UPSCALE_MODEL_LOADER_NODE,
    SDXL_UPSCALE_NEG_PROMPT_NODE,
    SDXL_UPSCALE_POS_PROMPT_NODE,
    SDXL_UPSCALE_SAVE_IMAGE_NODE,
    SDXL_UPSCALE_ULTIMATE_NODE,
    SDXL_VAR_BATCH_NODE,
    SDXL_VAE_DECODE_NODE,
    SDXL_VAR_CLIP_SKIP_NODE,
    SDXL_VAR_KSAMPLER_NODE,
    SDXL_VAR_LORA_NODE,
    SDXL_VAR_LOAD_IMAGE_NODE,
    SDXL_VAR_NEG_PROMPT_NODE,
    SDXL_VAR_POS_PROMPT_NODE,
    SDXL_VAR_RESIZE_NODE,
    SDXL_VAR_SAVE_IMAGE_NODE,
    SDXL_VAR_VAE_DECODE_NODE,
    SDXL_VAR_VAE_ENCODE_NODE,
)

Workflow = Dict[str, dict]


def _clone(template: Workflow) -> Workflow:
    return deepcopy(template)


_SDXL_TEXT_TO_IMAGE: Workflow = {
    str(SDXL_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load SDXL Checkpoint"},
    },
    str(SDXL_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (SDXL)"},
    },
    str(SDXL_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2"},
    },
    str(SDXL_POS_PROMPT_NODE): {
        "inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt (SDXL)"},
    },
    str(SDXL_NEG_PROMPT_NODE): {
        "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt (SDXL)"},
    },
    str(SDXL_KSAMPLER_NODE): {
        "inputs": {
            "seed": 12345,
            "steps": 30,
            "cfg": 6.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": [str(SDXL_LORA_NODE), 0],
            "positive": [str(SDXL_POS_PROMPT_NODE), 0],
            "negative": [str(SDXL_NEG_PROMPT_NODE), 0],
            "latent_image": [str(SDXL_LATENT_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler (SDXL)"},
    },
    str(SDXL_VAE_DECODE_NODE): {
        "inputs": {
            "samples": [str(SDXL_KSAMPLER_NODE), 0],
            "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode (SDXL)"},
    },
    str(SDXL_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "sdxlbot/GEN",
            "images": [str(SDXL_VAE_DECODE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image (SDXL)"},
    },
    "sdxl_preview": {
        "inputs": {"images": [str(SDXL_VAE_DECODE_NODE), 0]},
        "class_type": "PreviewImage",
        "_meta": {"title": "SDXL Preview"},
    },
    str(SDXL_LATENT_NODE): {
        "inputs": {
            "aspect_ratio": "1:1",
            "mp_size_float": "1",
            "upscale_by": 1.0,
            "model_type": "SDXL",
            "batch_size": 1,
        },
        "class_type": "BobsLatentNodeAdvanced",
        "_meta": {"title": "Bobs Latent Optimizer (SDXL)"},
    },
}


_SDXL_IMG2IMG: Workflow = {
    str(SDXL_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load SDXL Checkpoint"},
    },
    str(SDXL_IMG2IMG_LOAD_IMAGE_NODE): {
        "inputs": {"url_or_path": "IMAGE_URL_HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "Load Image for Img2Img"},
    },
    str(SDXL_IMG2IMG_RESIZE_NODE): {
        "inputs": {"interpolation": "bicubic", "image": [str(SDXL_IMG2IMG_LOAD_IMAGE_NODE), 0]},
        "class_type": "TenosResizeToTargetPixels",
        "_meta": {"title": "Tenos Resize to ~1M Pixels (Img2Img)"},
    },
    str(SDXL_IMG2IMG_VAE_ENCODE_NODE): {
        "inputs": {"pixels": [str(SDXL_IMG2IMG_RESIZE_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]},
        "class_type": "VAEEncode",
        "_meta": {"title": "VAE Encode (SDXL Img2Img)"},
    },
    str(SDXL_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (SDXL Img2Img)"},
    },
    str(SDXL_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2 (Img2Img)"},
    },
    str(SDXL_POS_PROMPT_NODE): {
        "inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt (SDXL Img2Img)"},
    },
    str(SDXL_NEG_PROMPT_NODE): {
        "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt (SDXL Img2Img)"},
    },
    str(SDXL_KSAMPLER_NODE): {
        "inputs": {
            "seed": 12345,
            "steps": 30,
            "cfg": 6.0,
            "sampler_name": "euler",
            "scheduler": "karras",
            "denoise": 0.75,
            "model": [str(SDXL_LORA_NODE), 0],
            "positive": [str(SDXL_POS_PROMPT_NODE), 0],
            "negative": [str(SDXL_NEG_PROMPT_NODE), 0],
            "latent_image": [str(SDXL_IMG2IMG_VAE_ENCODE_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler (SDXL Img2Img)"},
    },
    "sdxl_i2i_preview": {
        "inputs": {"images": [str(SDXL_VAE_DECODE_NODE), 0]},
        "class_type": "PreviewImage",
        "_meta": {"title": "SDXL Img2Img Preview"},
    },
    str(SDXL_VAE_DECODE_NODE): {
        "inputs": {
            "samples": [str(SDXL_KSAMPLER_NODE), 0],
            "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode (SDXL Img2Img)"},
    },
    str(SDXL_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "sdxlbot/GEN_I2I",
            "images": [str(SDXL_VAE_DECODE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image (SDXL Img2Img)"},
    },
}


_SDXL_VARIATION: Workflow = {
    str(SDXL_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load SDXL Checkpoint"},
    },
    str(SDXL_VAR_LOAD_IMAGE_NODE): {
        "inputs": {"url_or_path": "IMAGE_URL_HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "Load Image for Variation"},
    },
    str(SDXL_VAR_RESIZE_NODE): {
        "inputs": {"interpolation": "bicubic", "image": [str(SDXL_VAR_LOAD_IMAGE_NODE), 0]},
        "class_type": "TenosResizeToTargetPixels",
        "_meta": {"title": "Tenos Resize to ~1M Pixels"},
    },
    str(SDXL_VAR_VAE_ENCODE_NODE): {
        "inputs": {"pixels": [str(SDXL_VAR_RESIZE_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]},
        "class_type": "VAEEncode",
        "_meta": {"title": "VAE Encode for Variation"},
    },
    str(SDXL_VAR_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (SDXL Variation)"},
    },
    str(SDXL_VAR_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_VAR_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2"},
    },
    str(SDXL_VAR_POS_PROMPT_NODE): {
        "inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(SDXL_VAR_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Positive Prompt (SDXL)"},
    },
    str(SDXL_VAR_NEG_PROMPT_NODE): {
        "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(SDXL_VAR_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Negative Prompt (SDXL)"},
    },
    str(SDXL_VAR_KSAMPLER_NODE): {
        "inputs": {
            "seed": 12345,
            "steps": 30,
            "cfg": 6.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "karras",
            "denoise": 0.70,
            "control_after_generate": "increment",
            "model": [str(SDXL_VAR_LORA_NODE), 0],
            "positive": [str(SDXL_VAR_POS_PROMPT_NODE), 0],
            "negative": [str(SDXL_VAR_NEG_PROMPT_NODE), 0],
            "latent_image": [str(SDXL_VAR_BATCH_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler (SDXL Variation)"},
    },
    str(SDXL_VAR_VAE_DECODE_NODE): {
        "inputs": {
            "samples": [str(SDXL_VAR_KSAMPLER_NODE), 0],
            "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode (SDXL)"},
    },
    str(SDXL_VAR_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "sdxlbot/VAR",
            "images": [str(SDXL_VAE_DECODE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image (SDXL Variation)"},
    },
    str(SDXL_VAR_BATCH_NODE): {
        "inputs": {"amount": 1, "samples": [str(SDXL_VAR_VAE_ENCODE_NODE), 0]},
        "class_type": "RepeatLatentBatch",
        "_meta": {"title": "RepeatLatentBatch"},
    },
}


_SDXL_UPSCALE: Workflow = {
    str(SDXL_CHECKPOINT_LOADER_NODE): {
        "inputs": {"ckpt_name": ""},
        "class_type": "CheckpointLoaderSimple",
        "_meta": {"title": "Load SDXL Checkpoint"},
    },
    str(SDXL_UPSCALE_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0],
            "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (SDXL Upscale)"},
    },
    str(SDXL_UPSCALE_CLIP_SKIP_NODE): {
        "inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_UPSCALE_LORA_NODE), 1]},
        "class_type": "CLIPSetLastLayer",
        "_meta": {"title": "CLIP Skip -2 (Upscale)"},
    },
    str(SDXL_UPSCALE_POS_PROMPT_NODE): {
        "inputs": {"text": "UPSCALE PROMPT HERE", "clip": [str(SDXL_UPSCALE_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Upscale Positive Prompt (SDXL)"},
    },
    str(SDXL_UPSCALE_NEG_PROMPT_NODE): {
        "inputs": {"text": "UPSCALE NEGATIVE HERE", "clip": [str(SDXL_UPSCALE_CLIP_SKIP_NODE), 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Upscale Negative Prompt (SDXL)"},
    },
    str(SDXL_UPSCALE_LOAD_IMAGE_NODE): {
        "inputs": {"url_or_path": "IMAGE_URL_HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "Load Image for Upscaling"},
    },
    str(SDXL_UPSCALE_MODEL_LOADER_NODE): {
        "inputs": {"model_name": "4x-UltraSharp.pth"},
        "class_type": "UpscaleModelLoader",
        "_meta": {"title": "Load Upscale Model"},
    },
    str(SDXL_UPSCALE_ULTIMATE_NODE): {
        "inputs": {
            "seed": 12345,
            "steps": 16,
            "cfg": 5.0,
            "sampler_name": "euler",
            "scheduler": "karras",
            "denoise": 0.15,
            "mode_type": "Linear",
            "mask_blur": 16,
            "tile_padding": 32,
            "seam_fix_mode": "Half Tile + Intersections",
            "seam_fix_denoise": 0.4,
            "seam_fix_width": 64,
            "seam_fix_mask_blur": 8,
            "seam_fix_padding": 32,
            "force_uniform_tiles": True,
            "tiled_decode": True,
            "image": [str(SDXL_UPSCALE_LOAD_IMAGE_NODE), 0],
            "model": [str(SDXL_UPSCALE_LORA_NODE), 0],
            "positive": [str(SDXL_UPSCALE_POS_PROMPT_NODE), 0],
            "negative": [str(SDXL_UPSCALE_NEG_PROMPT_NODE), 0],
            "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2],
            "upscale_model": [str(SDXL_UPSCALE_MODEL_LOADER_NODE), 0],
            "upscale_by": [str(SDXL_UPSCALE_HELPER_LATENT_NODE), 3],
            "tile_width": [str(SDXL_UPSCALE_HELPER_LATENT_NODE), 1],
            "tile_height": [str(SDXL_UPSCALE_HELPER_LATENT_NODE), 2],
        },
        "class_type": "UltimateSDUpscale",
        "_meta": {"title": "Ultimate SD Upscale (SDXL)"},
    },
    str(SDXL_UPSCALE_HELPER_LATENT_NODE): {
        "inputs": {
            "aspect_ratio": "1:1",
            "mp_size_float": "1",
            "upscale_by": 1.85,
            "model_type": "SDXL",
            "batch_size": 1,
        },
        "class_type": "BobsLatentNodeAdvanced",
        "_meta": {"title": "Bobs Upscale Param Calculator (SDXL)"},
    },
    str(SDXL_UPSCALE_SAVE_IMAGE_NODE): {
        "inputs": {
            "filename_prefix": "sdxlbot/UPSCALES",
            "images": [str(SDXL_UPSCALE_ULTIMATE_NODE), 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Upscaled Image (SDXL)"},
    },
}


__all__ = [
    "sdxl_text_to_image_template",
    "sdxl_img2img_template",
    "sdxl_variation_template",
    "sdxl_upscale_template",
]


def sdxl_text_to_image_template() -> Workflow:
    return _clone(_SDXL_TEXT_TO_IMAGE)


def sdxl_img2img_template() -> Workflow:
    return _clone(_SDXL_IMG2IMG)


def sdxl_variation_template() -> Workflow:
    return _clone(_SDXL_VARIATION)


def sdxl_upscale_template() -> Workflow:
    return _clone(_SDXL_UPSCALE)
