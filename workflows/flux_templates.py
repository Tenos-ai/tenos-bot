"""Flux ComfyUI workflow templates used across generation features."""
from __future__ import annotations

from copy import deepcopy
from typing import Dict

from prompt_templates import (
    FLUX_VAR_BATCH_NODE,
    GENERATION_CLIP_NODE,
    GENERATION_LATENT_NODE,
    GENERATION_MODEL_NODE,
    GENERATION_WORKFLOW_STEPS_NODE,
    IMG2IMG_LORA_NODE,
    PROMPT_LORA_NODE,
    UPSCALE_CLIP_NODE,
    UPSCALE_HELPER_LATENT_NODE,
    UPSCALE_LORA_NODE,
    UPSCALE_MODEL_NODE,
    VARIATION_CLIP_NODE,
    VARIATION_MODEL_NODE,
    VARIATION_WORKFLOW_STEPS_NODE,
    VARY_LORA_NODE,
)

Workflow = Dict[str, dict]


def _clone(template: Workflow) -> Workflow:
    return deepcopy(template)


_FLUX_TEXT_TO_IMAGE: Workflow = {
    "1": {
        "inputs": {"unet_name": ""},
        "class_type": "UnetLoaderGGUF",
        "_meta": {"title": "Unet Loader (GGUF)"},
    },
    "2": {
        "inputs": {
            "clip_name1": "t5xxl_fp16.safetensors",
            "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors",
            "type": "flux",
        },
        "class_type": "DualCLIPLoader",
        "_meta": {"title": "DualCLIPLoader"},
    },
    "3": {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader",
        "_meta": {"title": "Load VAE"},
    },
    "4": {
        "inputs": {
            "text": "PROMPT HERE",
            "clip": [str(PROMPT_LORA_NODE), 1],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Prompt)"},
    },
    "5": {
        "inputs": {
            "guidance": 3.5,
            "conditioning": ["4", 0],
        },
        "class_type": "FluxGuidance",
        "_meta": {"title": "FluxGuidance"},
    },
    "6": {
        "inputs": {
            "samples": [str(GENERATION_WORKFLOW_STEPS_NODE), 0],
            "vae": ["3", 0],
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode"},
    },
    "7": {
        "inputs": {
            "filename_prefix": "fluxbot/GEN",
            "images": ["6", 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image"},
    },
    "8": {
        "inputs": {
            "seed": 862810278327975,
            "steps": 32,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
            "denoise": 1,
            "model": [str(PROMPT_LORA_NODE), 0],
            "positive": ["5", 0],
            "negative": ["5", 0],
            "latent_image": [str(GENERATION_LATENT_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler"},
    },
    "9": {
        "inputs": {"images": ["6", 0]},
        "class_type": "PreviewImage",
        "_meta": {"title": "Flux Preview"},
    },
    str(PROMPT_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(GENERATION_MODEL_NODE), 0],
            "clip": [str(GENERATION_CLIP_NODE), 0],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (rgthree)"},
    },
    str(GENERATION_LATENT_NODE): {
        "inputs": {
            "aspect_ratio": "1:1",
            "mp_size_float": "1",
            "upscale_by": 1,
            "model_type": "FLUX",
            "batch_size": 1,
        },
        "class_type": "BobsLatentNodeAdvanced",
        "_meta": {"title": "Bobs Latent Optimizer (Advanced)"},
    },
}


_FLUX_IMG2IMG: Workflow = {
    "1": {
        "inputs": {"unet_name": ""},
        "class_type": "UnetLoaderGGUF",
        "_meta": {"title": "Unet Loader (GGUF)"},
    },
    "2": {
        "inputs": {
            "clip_name1": "t5xxl_fp16.safetensors",
            "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors",
            "type": "flux",
        },
        "class_type": "DualCLIPLoader",
        "_meta": {"title": "DualCLIPLoader"},
    },
    "3": {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader",
        "_meta": {"title": "Load VAE"},
    },
    "4": {
        "inputs": {
            "seed": 862810278327975,
            "steps": 28,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
            "denoise": 0.55,
            "model": [str(IMG2IMG_LORA_NODE), 0],
            "positive": ["5", 0],
            "negative": ["5", 0],
            "latent_image": [str(GENERATION_LATENT_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler"},
    },
    "5": {
        "inputs": {"text": "PROMPT HERE", "clip": [str(IMG2IMG_LORA_NODE), 1]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Prompt)"},
    },
    "6": {
        "inputs": {
            "conditioning": ["5", 0],
            "guidance": 3.5,
        },
        "class_type": "FluxGuidance",
        "_meta": {"title": "FluxGuidance"},
    },
    "7": {
        "inputs": {"samples": ["4", 0], "vae": ["3", 0]},
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode"},
    },
    "8": {
        "inputs": {"filename_prefix": "fluxbot/IMG2IMG", "images": ["7", 0]},
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image"},
    },
    "9": {
        "inputs": {"images": ["7", 0]},
        "class_type": "PreviewImage",
        "_meta": {"title": "Flux Preview"},
    },
    "10": {
        "inputs": {"url_or_path": "IMAGE URL HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "LoadImageFromUrlOrPath"},
    },
    "11": {
        "inputs": {"interpolation": "bicubic", "image": ["10", 0]},
        "class_type": "TenosResizeToTargetPixels",
        "_meta": {"title": "Tenos Resize to ~1M Pixels"},
    },
    "12": {
        "inputs": {"pixels": ["11", 0], "vae": ["3", 0]},
        "class_type": "VAEEncode",
        "_meta": {"title": "VAE Encode"},
    },
    str(IMG2IMG_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(GENERATION_MODEL_NODE), 0],
            "clip": [str(GENERATION_CLIP_NODE), 0],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (rgthree)"},
    },
    str(GENERATION_LATENT_NODE): {
        "inputs": {
            "samples": ["12", 0],
            "amount": 1,
            "latent": ["12", 0],
            "model_type": "FLUX",
        },
        "class_type": "RepeatLatentBatch",
        "_meta": {"title": "RepeatLatentBatch"},
    },
}


_FLUX_UPSCALE: Workflow = {
    "1": {
        "inputs": {"text": "PROMPT HERE", "clip": [str(UPSCALE_LORA_NODE), 1]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "PROMPT"},
    },
    "58": {
        "inputs": {
            "filename_prefix": "fluxbot/UPSCALES/GEN_UP",
            "images": ["104", 0],
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Upscaled Image"},
    },
    "103": {
        "inputs": {"model_name": "4x-UltraSharp.pth"},
        "class_type": "UpscaleModelLoader",
        "_meta": {"title": "Load Upscale Model"},
    },
    "104": {
        "inputs": {
            "seed": 763716328118238,
            "steps": 16,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
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
            "image": ["115", 0],
            "model": [str(UPSCALE_LORA_NODE), 0],
            "positive": ["1", 0],
            "negative": ["1", 0],
            "vae": ["8:2", 0],
            "upscale_model": ["103", 0],
            "upscale_by": [str(UPSCALE_HELPER_LATENT_NODE), 3],
            "tile_width": [str(UPSCALE_HELPER_LATENT_NODE), 1],
            "tile_height": [str(UPSCALE_HELPER_LATENT_NODE), 2],
        },
        "class_type": "UltimateSDUpscale",
        "_meta": {"title": "Ultimate SD Upscale"},
    },
    "115": {
        "inputs": {"url_or_path": "IMAGE URL HERE"},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "LoadImageFromUrlOrPath"},
    },
    str(UPSCALE_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(UPSCALE_MODEL_NODE), 0],
            "clip": [str(UPSCALE_CLIP_NODE), 0],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (rgthree)"},
    },
    "8:2": {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader",
        "_meta": {"title": "Load VAE"},
    },
    "8:0": {
        "inputs": {"unet_name": ""},
        "class_type": "UnetLoaderGGUF",
        "_meta": {"title": "Unet Loader (GGUF)"},
    },
    "8:1": {
        "inputs": {
            "clip_name1": "t5xxl_fp16.safetensors",
            "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors",
            "type": "flux",
        },
        "class_type": "DualCLIPLoader",
        "_meta": {"title": "DualCLIPLoader"},
    },
    str(UPSCALE_HELPER_LATENT_NODE): {
        "inputs": {
            "aspect_ratio": "1:1",
            "mp_size_float": "1",
            "upscale_by": 1.85,
            "model_type": "FLUX",
            "batch_size": 1,
        },
        "class_type": "BobsLatentNodeAdvanced",
        "_meta": {"title": "Bobs Upscale Param Calculator"},
    },
}


_FLUX_WEAK_VARIATION: Workflow = {
    "1": {
        "inputs": {"unet_name": ""},
        "class_type": "UnetLoaderGGUF",
        "_meta": {"title": "Unet Loader (GGUF)"},
    },
    "2": {
        "inputs": {
            "clip_name1": "t5xxl_fp16.safetensors",
            "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors",
            "type": "flux",
        },
        "class_type": "DualCLIPLoader",
        "_meta": {"title": "DualCLIPLoader"},
    },
    "3": {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader",
        "_meta": {"title": "Load VAE"},
    },
    "7": {
        "inputs": {
            "seed": 775752669305671,
            "steps": 32,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
            "denoise": 0.48,
            "control_after_generate": "increment",
            "model": [str(VARY_LORA_NODE), 0],
            "positive": ["8", 0],
            "negative": ["8", 0],
            "latent_image": [str(FLUX_VAR_BATCH_NODE), 0],
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler"},
    },
    "8": {
        "inputs": {"text": " ", "clip": [str(VARY_LORA_NODE), 1]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Prompt)"},
    },
    "11": {
        "inputs": {"samples": ["7", 0], "vae": ["3", 0]},
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode"},
    },
    "22": {
        "inputs": {"pixels": ["36", 0], "vae": ["3", 0]},
        "class_type": "VAEEncode",
        "_meta": {"title": "VAE Encode"},
    },
    "33": {
        "inputs": {"url_or_path": ""},
        "class_type": "LoadImageFromUrlOrPath",
        "_meta": {"title": "LoadImageFromUrlOrPath"},
    },
    "34": {
        "inputs": {"filename_prefix": "fluxbot/VARIATIONS", "images": ["11", 0]},
        "class_type": "SaveImage",
        "_meta": {"title": "Save Image"},
    },
    str(VARY_LORA_NODE): {
        "inputs": {
            "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
            "lora_1": {"on": False, "lora": "None", "strength": 0},
            "lora_2": {"on": False, "lora": "None", "strength": 0},
            "lora_3": {"on": False, "lora": "None", "strength": 0},
            "lora_4": {"on": False, "lora": "None", "strength": 0},
            "lora_5": {"on": False, "lora": "None", "strength": 0},
            "➕ Add Lora": "",
            "model": [str(VARIATION_MODEL_NODE), 0],
            "clip": [str(VARIATION_CLIP_NODE), 0],
        },
        "class_type": "Power Lora Loader (rgthree)",
        "_meta": {"title": "Power Lora Loader (rgthree)"},
    },
    "36": {
        "inputs": {"interpolation": "bicubic", "image": ["33", 0]},
        "class_type": "TenosResizeToTargetPixels",
        "_meta": {"title": "Tenos Resize to ~1M Pixels"},
    },
    str(FLUX_VAR_BATCH_NODE): {
        "inputs": {"amount": 1, "samples": ["22", 0]},
        "class_type": "RepeatLatentBatch",
        "_meta": {"title": "RepeatLatentBatch"},
    },
}


_FLUX_STRONG_VARIATION: Workflow = _clone(_FLUX_WEAK_VARIATION)
_FLUX_STRONG_VARIATION["7"]["inputs"]["denoise"] = 0.75


__all__ = [
    "flux_text_to_image_template",
    "flux_img2img_template",
    "flux_upscale_template",
    "flux_weak_variation_template",
    "flux_strong_variation_template",
]


def flux_text_to_image_template() -> Workflow:
    """Return a deep copy of the Flux text-to-image template."""

    return _clone(_FLUX_TEXT_TO_IMAGE)


def flux_img2img_template() -> Workflow:
    """Return a deep copy of the Flux img2img template."""

    return _clone(_FLUX_IMG2IMG)


def flux_upscale_template() -> Workflow:
    """Return a deep copy of the Flux upscale template."""

    return _clone(_FLUX_UPSCALE)


def flux_weak_variation_template() -> Workflow:
    """Return a deep copy of the Flux weak variation template."""

    return _clone(_FLUX_WEAK_VARIATION)


def flux_strong_variation_template() -> Workflow:
    """Return a deep copy of the Flux strong variation template."""

    return _clone(_FLUX_STRONG_VARIATION)
