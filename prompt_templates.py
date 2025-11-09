# --- START OF FILE prompt_templates.py ---
"""Workflow templates for Tenos bot."""

from __future__ import annotations

import copy
from typing import List, Sequence

# style_prompt_templates.py


def _normalize_ref(ref: Sequence) -> List:
    """Ensure workflow references are stored as mutable lists."""

    return list(ref) if isinstance(ref, (list, tuple)) else [ref]


def build_power_lora_node(node_id: str, model_ref: Sequence, clip_ref: Sequence, *, title: str) -> dict:
    """Return the standard Power Lora Loader node entry."""

    return {
        str(node_id): {
            "inputs": {
                "PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},
                "lora_1": {"on": False, "lora": "None", "strength": 0},
                "lora_2": {"on": False, "lora": "None", "strength": 0},
                "lora_3": {"on": False, "lora": "None", "strength": 0},
                "lora_4": {"on": False, "lora": "None", "strength": 0},
                "lora_5": {"on": False, "lora": "None", "strength": 0},
                "➕ Add Lora": "",
                "model": _normalize_ref(model_ref),
                "clip": _normalize_ref(clip_ref),
            },
            "class_type": "Power Lora Loader (rgthree)",
            "_meta": {"title": title},
        }
    }


def build_bobs_latent_node(
    node_id: str,
    *,
    model_type: str,
    aspect_ratio: str = "1:1",
    mp_size_float: str = "1",
    upscale_by: float = 1.0,
    batch_size: int = 1,
    title: str,
) -> dict:
    """Return a BobsLatentNodeAdvanced configuration."""

    return {
        str(node_id): {
            "inputs": {
                "aspect_ratio": aspect_ratio,
                "mp_size_float": mp_size_float,
                "upscale_by": upscale_by,
                "model_type": model_type,
                "batch_size": batch_size,
            },
            "class_type": "BobsLatentNodeAdvanced",
            "_meta": {"title": title},
    }
}


def build_hunyuan_latent_node(
    node_id: str,
    *,
    width: int,
    height: int,
    length: int,
    batch_size: int = 1,
    title: str,
) -> dict:
    """Return an EmptyHunyuanLatentVideo node configuration."""

    return {
        str(node_id): {
            "inputs": {
                "width": width,
                "height": height,
                "length": length,
                "batch_size": batch_size,
            },
            "class_type": "EmptyHunyuanLatentVideo",
            "widgets_values": [width, height, length, batch_size],
            "_meta": {"title": title},
        }
    }


def build_tenos_resize_node(node_id: str, image_ref: Sequence, *, title: str) -> dict:
    """Return a TenosResizeToTargetPixels node entry."""

    return {
        str(node_id): {
            "inputs": {
                "interpolation": "bicubic",
                "image": _normalize_ref(image_ref),
            },
            "class_type": "TenosResizeToTargetPixels",
            "_meta": {"title": title},
        }
    }

# FLUX Workflow Node IDs
GENERATION_MODEL_NODE = "1"
VARIATION_MODEL_NODE = "1"
UPSCALE_MODEL_NODE = "8:0"

GENERATION_WORKFLOW_STEPS_NODE = "8"
VARIATION_WORKFLOW_STEPS_NODE = "7"

GENERATION_CLIP_NODE = "2"
VARIATION_CLIP_NODE = "2"
UPSCALE_CLIP_NODE = "8:1"

PROMPT_LORA_NODE = "10"
IMG2IMG_LORA_NODE = "17"
UPSCALE_LORA_NODE = "116"
VARY_LORA_NODE = "35"
FLUX_VAR_BATCH_NODE = "var_batcher"

GENERATION_LATENT_NODE = "99"
UPSCALE_HELPER_LATENT_NODE = "98"

# SDXL Workflow Node IDs
SDXL_CHECKPOINT_LOADER_NODE = "sdxl_1"
SDXL_LORA_NODE = "sdxl_lora"
SDXL_CLIP_SKIP_NODE = "sdxl_2"
SDXL_POS_PROMPT_NODE = "sdxl_3"
SDXL_NEG_PROMPT_NODE = "sdxl_4"
SDXL_KSAMPLER_NODE = "sdxl_5"
SDXL_VAE_DECODE_NODE = "sdxl_6"
SDXL_SAVE_IMAGE_NODE = "sdxl_7"
SDXL_LATENT_NODE = "sdxl_8"

# SDXL Img2Img specific node IDs (New)
SDXL_IMG2IMG_LOAD_IMAGE_NODE = "sdxl_i2i_load"
SDXL_IMG2IMG_RESIZE_NODE = "sdxl_i2i_resize"
SDXL_IMG2IMG_VAE_ENCODE_NODE = "sdxl_i2i_vae_encode"

SDXL_VAR_LOAD_IMAGE_NODE = "sdxl_var_load"
SDXL_VAR_RESIZE_NODE = "sdxl_var_resize"
SDXL_VAR_VAE_ENCODE_NODE = "sdxl_var_vae_encode"
SDXL_VAR_CLIP_SKIP_NODE = "sdxl_var_clip_skip"
SDXL_VAR_LORA_NODE = SDXL_LORA_NODE # Reusing
SDXL_VAR_POS_PROMPT_NODE = "sdxl_var_pos_prompt"
SDXL_VAR_NEG_PROMPT_NODE = "sdxl_var_neg_prompt"
SDXL_VAR_KSAMPLER_NODE = "sdxl_var_ksampler"
SDXL_VAR_VAE_DECODE_NODE = "sdxl_var_vae_decode"
SDXL_VAR_SAVE_IMAGE_NODE = "sdxl_var_save_image"
SDXL_VAR_BATCH_NODE = "sdxl_var_batcher"

SDXL_UPSCALE_LOAD_IMAGE_NODE = "sdxl_up_load"
SDXL_UPSCALE_MODEL_LOADER_NODE = "sdxl_up_model_loader"
SDXL_UPSCALE_ULTIMATE_NODE = "sdxl_up_ultimate"
SDXL_UPSCALE_HELPER_LATENT_NODE = "sdxl_up_helper_latent"
SDXL_UPSCALE_SAVE_IMAGE_NODE = "sdxl_up_save"
SDXL_UPSCALE_LORA_NODE = SDXL_LORA_NODE # Reusing
SDXL_UPSCALE_CLIP_SKIP_NODE = "sdxl_upscale_clip_skip"
SDXL_UPSCALE_POS_PROMPT_NODE = "sdxl_upscale_pos_prompt"
SDXL_UPSCALE_NEG_PROMPT_NODE = "sdxl_upscale_neg_prompt"


# Qwen Image Workflow Node IDs
QWEN_UNET_LOADER_NODE = "qwen_unet"
QWEN_CLIP_LOADER_NODE = "qwen_clip"
QWEN_VAE_LOADER_NODE = "qwen_vae"
QWEN_LORA_NODE = "qwen_lora"
QWEN_POS_PROMPT_NODE = "qwen_pos_prompt"
QWEN_NEG_PROMPT_NODE = "qwen_neg_prompt"
QWEN_KSAMPLER_NODE = "qwen_ksampler"
QWEN_VAE_DECODE_NODE = "qwen_vae_decode"
QWEN_SAVE_IMAGE_NODE = "qwen_save"
QWEN_LATENT_NODE = "qwen_latent"

QWEN_IMG2IMG_LOAD_IMAGE_NODE = "qwen_i2i_load"
QWEN_IMG2IMG_RESIZE_NODE = "qwen_i2i_resize"
QWEN_IMG2IMG_VAE_ENCODE_NODE = "qwen_i2i_encode"

QWEN_SAMPLING_NODE = "qwen_sampling"
QWEN_VAR_SAMPLING_NODE = "qwen_var_sampling"
QWEN_UPSCALE_SAMPLING_NODE = "qwen_up_sampling"
QWEN_EDIT_SAMPLING_NODE = "qwen_edit_sampling"
QWEN_VAR_POS_PROMPT_NODE = "qwen_var_pos_prompt"
QWEN_VAR_NEG_PROMPT_NODE = "qwen_var_neg_prompt"

QWEN_VAR_LOAD_IMAGE_NODE = "qwen_var_load"
QWEN_VAR_RESIZE_NODE = "qwen_var_resize"
QWEN_VAR_VAE_ENCODE_NODE = "qwen_var_encode"
QWEN_VAR_KSAMPLER_NODE = "qwen_var_ksampler"
QWEN_VAR_VAE_DECODE_NODE = "qwen_var_vae_decode"
QWEN_VAR_SAVE_IMAGE_NODE = "qwen_var_save"
QWEN_VAR_BATCH_NODE = "qwen_var_batch"

QWEN_UPSCALE_LOAD_IMAGE_NODE = "qwen_up_load"
QWEN_UPSCALE_MODEL_LOADER_NODE = "qwen_up_model_loader"
QWEN_UPSCALE_ULTIMATE_NODE = "qwen_up_ultimate"
QWEN_UPSCALE_HELPER_LATENT_NODE = "qwen_up_helper_latent"
QWEN_UPSCALE_SAVE_IMAGE_NODE = "qwen_up_save"
QWEN_UPSCALE_POS_PROMPT_NODE = "qwen_up_pos_prompt"
QWEN_UPSCALE_NEG_PROMPT_NODE = "qwen_up_neg_prompt"


# WAN 2.2 Workflow Node IDs (WanVideoWrapper)
WAN_MODEL_LOADER_NODE = "wan_model_loader"
WAN_T5_LOADER_NODE = "wan_t5_loader"
WAN_TEXT_ENCODER_NODE = "wan_text_encode"
WAN_VAE_LOADER_NODE = "wan_vae"
WAN_IMAGE_EMBEDS_NODE = "wan_empty_embeds"
WAN_CACHE_ARGS_NODE = "wan_cache_args"
WAN_SLG_ARGS_NODE = "wan_slg_args"
WAN_EXPERIMENTAL_ARGS_NODE = "wan_experimental_args"
WAN_SAMPLER_NODE = "wan_sampler"
WAN_DECODE_NODE = "wan_decode"
WAN_VIDEO_SAVE_NODE = "wan_video_save"
WAN_IMAGE_LOADER_NODE = "wan_image_loader"
WAN_IMAGE_RESIZE_NODE = "wan_image_resize"
WAN_IMAGE_ENCODE_NODE = "wan_image_encode"

# --- WAN 2.2 Generation Template ---
wan_prompt = {
    str(WAN_MODEL_LOADER_NODE): {
        "inputs": {
            "model": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
            "base_precision": "fp16_fast",
            "quantization": "fp8_e4m3fn_scaled",
            "load_device": "offload_device",
            "attention_mode": "sageattn",
        },
        "class_type": "WanVideoModelLoader",
        "widgets_values": [
            "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
            "fp16_fast",
            "fp8_e4m3fn_scaled",
            "offload_device",
            "sageattn",
        ],
        "_meta": {"title": "Load WAN Model"},
    },
    str(WAN_T5_LOADER_NODE): {
        "inputs": {
            "model_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "precision": "fp8",
            "load_device": "offload_device",
            "quantization": "fp8_e4m3fn_scaled",
        },
        "class_type": "LoadWanVideoT5TextEncoder",
        "widgets_values": [
            "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "fp8",
            "offload_device",
            "fp8_e4m3fn_scaled",
        ],
        "_meta": {"title": "Load WAN T5 Text Encoder"},
    },
    str(WAN_TEXT_ENCODER_NODE): {
        "inputs": {
            "positive_prompt": "PROMPT HERE",
            "negative_prompt": "NEGATIVE PROMPT HERE",
            "t5": [str(WAN_T5_LOADER_NODE), 0],
            "model_to_offload": [str(WAN_MODEL_LOADER_NODE), 0],
            "force_offload": True,
            "use_disk_cache": False,
            "device": "gpu",
        },
        "class_type": "WanVideoTextEncode",
        "widgets_values": [
            "PROMPT HERE",
            "NEGATIVE PROMPT HERE",
            True,
            False,
            "gpu",
        ],
        "_meta": {"title": "WAN Text Encode"},
    },
    str(WAN_VAE_LOADER_NODE): {
        "inputs": {
            "model_name": "wan2.2_vae.safetensors",
            "precision": "bf16",
        },
        "class_type": "WanVideoVAELoader",
        "widgets_values": ["wan2.2_vae.safetensors", "bf16"],
        "_meta": {"title": "Load WAN VAE"},
    },
    str(WAN_IMAGE_EMBEDS_NODE): {
        "inputs": {
            "width": 832,
            "height": 480,
            "num_frames": 81,
        },
        "class_type": "WanVideoEmptyEmbeds",
        "widgets_values": [832, 480, 81],
        "_meta": {"title": "Create WAN Empty Embeds"},
    },
    str(WAN_CACHE_ARGS_NODE): {
        "inputs": {
            "easycache_thresh": 0.015,
            "start_step": 10,
            "end_step": -1,
            "cache_device": "offload_device",
        },
        "class_type": "WanVideoEasyCache",
        "widgets_values": [0.015, 10, -1, "offload_device"],
        "_meta": {"title": "WAN EasyCache"},
    },
    str(WAN_SLG_ARGS_NODE): {
        "inputs": {
            "blocks": "7,8,9",
            "start_percent": 0.1,
            "end_percent": 0.7,
        },
        "class_type": "WanVideoSLG",
        "widgets_values": ["7,8,9", 0.1, 0.7],
        "_meta": {"title": "WAN SLG Args"},
    },
    str(WAN_EXPERIMENTAL_ARGS_NODE): {
        "inputs": {
            "video_attention_split_steps": "",
            "cfg_zero_star": False,
            "use_zero_init": False,
            "zero_star_steps": 0,
            "use_fresca": False,
            "fresca_scale_low": 1.0,
            "fresca_scale_high": 1.25,
            "fresca_freq_cutoff": 20,
            "use_tcfg": False,
            "raag_alpha": 0.0,
            "bidirectional_sampling": False,
            "temporal_score_rescaling": False,
            "tsr_k": 0.95,
            "tsr_sigma": 1.0,
        },
        "class_type": "WanVideoExperimentalArgs",
        "widgets_values": [
            "",
            False,
            False,
            0,
            False,
            1.0,
            1.25,
            20,
            False,
            0.0,
            False,
            False,
            0.95,
            1.0,
        ],
        "_meta": {"title": "WAN Experimental Args"},
    },
    str(WAN_SAMPLER_NODE): {
        "inputs": {
            "model": [str(WAN_MODEL_LOADER_NODE), 0],
            "image_embeds": [str(WAN_IMAGE_EMBEDS_NODE), 0],
            "text_embeds": [str(WAN_TEXT_ENCODER_NODE), 0],
            "steps": 30,
            "cfg": 6.0,
            "shift": 8.0,
            "seed": 8640317771124281,
            "force_offload": True,
            "scheduler": "unipc",
            "riflex_freq_index": 0,
            "denoise_strength": 1.0,
            "cache_args": [str(WAN_CACHE_ARGS_NODE), 0],
            "slg_args": [str(WAN_SLG_ARGS_NODE), 0],
            "experimental_args": [str(WAN_EXPERIMENTAL_ARGS_NODE), 0],
            "batched_cfg": False,
            "rope_function": "comfy",
            "start_step": 0,
            "end_step": -1,
            "add_noise_to_samples": False,
        },
        "class_type": "WanVideoSampler",
        "widgets_values": [
            30,
            6.0,
            8.0,
            8640317771124281,
            "fixed",
            True,
            "unipc",
            0,
            1.0,
            False,
            "comfy",
            0,
            -1,
            False,
            "",
        ],
        "_meta": {"title": "WAN Video Sampler"},
    },
    str(WAN_DECODE_NODE): {
        "inputs": {
            "vae": [str(WAN_VAE_LOADER_NODE), 0],
            "samples": [str(WAN_SAMPLER_NODE), 0],
            "enable_vae_tiling": False,
            "tile_x": 272,
            "tile_y": 272,
            "tile_stride_x": 144,
            "tile_stride_y": 128,
            "normalization": "default",
        },
        "class_type": "WanVideoDecode",
        "widgets_values": [False, 272, 272, 144, 128, "default"],
        "_meta": {"title": "WAN Video Decode"},
    },
    str(WAN_VIDEO_SAVE_NODE): {
        "inputs": {
            "images": [str(WAN_DECODE_NODE), 0],
        },
        "class_type": "VHS_VideoCombine",
        "widgets_values": {
            "frame_rate": 16,
            "loop_count": 0,
            "filename_prefix": "wanbot/GEN",
            "format": "video/h264-mp4",
            "pix_fmt": "yuv420p",
            "crf": 19,
            "save_metadata": True,
            "trim_to_audio": False,
            "pingpong": False,
            "save_output": True,
        },
        "_meta": {"title": "Save WAN Video"},
    },
}

# --- WAN 2.2 Img2Img Template ---
wan_img2img_prompt = copy.deepcopy(wan_prompt)
wan_img2img_prompt.update(
    {
        str(WAN_IMAGE_LOADER_NODE): {
            "inputs": {"url_or_path": "IMAGE_URL_HERE"},
            "class_type": "LoadImageFromUrlOrPath",
            "_meta": {"title": "Load WAN Img2Video Source"},
        },
        str(WAN_IMAGE_ENCODE_NODE): {
            "inputs": {
                "vae": [str(WAN_VAE_LOADER_NODE), 0],
                "image": [str(WAN_IMAGE_RESIZE_NODE), 0],
                "enable_vae_tiling": False,
                "tile_x": 272,
                "tile_y": 272,
                "tile_stride_x": 144,
                "tile_stride_y": 128,
                "noise_aug_strength": 0.0,
                "latent_strength": 1.0,
            },
            "class_type": "WanVideoEncode",
            "widgets_values": [False, 272, 272, 144, 128, 0.0, 1.0],
            "_meta": {"title": "WAN Video Encode"},
        },
    }
)
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["inputs"]["model"] = (
    "wan2.2_i2v_high_noise_14B_fp16.safetensors"
)
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["widgets_values"][0] = (
    "wan2.2_i2v_high_noise_14B_fp16.safetensors"
)
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["inputs"]["base_precision"] = (
    "fp16_fast"
)
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["inputs"]["quantization"] = (
    "disabled"
)
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["inputs"]["attention_mode"] = (
    "sageattn"
)
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["widgets_values"][1] = "fp16_fast"
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["widgets_values"][2] = "disabled"
wan_img2img_prompt[str(WAN_MODEL_LOADER_NODE)]["widgets_values"][4] = "sageattn"
wan_img2img_prompt.update(
    build_tenos_resize_node(
        WAN_IMAGE_RESIZE_NODE,
        image_ref=[str(WAN_IMAGE_LOADER_NODE), 0],
        title="Tenos Resize Source (WAN)",
    )
)
wan_img2img_prompt[str(WAN_IMAGE_EMBEDS_NODE)]["inputs"]["extra_latents"] = [
    str(WAN_IMAGE_ENCODE_NODE),
    0,
]
wan_img2img_prompt[str(WAN_SAMPLER_NODE)]["inputs"]["samples"] = [
    str(WAN_IMAGE_ENCODE_NODE),
    0,
]
wan_img2img_prompt[str(WAN_VIDEO_SAVE_NODE)]["widgets_values"]["filename_prefix"] = (
    "wanbot/IMG2IMG"
)

# --- WAN 2.2 Variation Template ---
wan_variation_prompt = copy.deepcopy(wan_img2img_prompt)
wan_variation_prompt[str(WAN_VIDEO_SAVE_NODE)]["widgets_values"]["filename_prefix"] = (
    "wanbot/VARIATION"
)

# --- WAN Image-to-Video Template ---
wan_image_to_video_prompt = copy.deepcopy(wan_img2img_prompt)
wan_image_to_video_prompt[str(WAN_VIDEO_SAVE_NODE)]["widgets_values"][
    "filename_prefix"
] = "wanbot/ANIMATION"
# --- Flux Generation Template ---
prompt = {
  "1": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"},"class_type": "UnetLoaderGGUF","_meta": {"title": "Unet Loader (GGUF)"}},
  "2": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"},"class_type": "DualCLIPLoader","_meta": {"title": "DualCLIPLoader"}},
  "3": {"inputs": {"vae_name": "ae.safetensors"},"class_type": "VAELoader","_meta": {"title": "Load VAE"}},
  "4": {"inputs": {"text": "PROMPT HERE", "clip": [str(PROMPT_LORA_NODE), 1]},"class_type": "CLIPTextEncode","_meta": {"title": "CLIP Text Encode (Prompt)"}},
  "5": {"inputs": {"guidance": 3.5, "conditioning": ["4", 0]},"class_type": "FluxGuidance","_meta": {"title": "FluxGuidance"}},
  "6": {"inputs": {"samples": [str(GENERATION_WORKFLOW_STEPS_NODE), 0], "vae": ["3", 0]},"class_type": "VAEDecode","_meta": {"title": "VAE Decode"}},
  "7": {"inputs": {"filename_prefix": "fluxbot/GEN", "images": ["6", 0]},"class_type": "SaveImage","_meta": {"title": "Save Image"}},
  "8": {"inputs": {"seed": 862810278327975,"steps": 32,"cfg": 1,"sampler_name": "euler","scheduler": "sgm_uniform","denoise": 1,"model": [str(PROMPT_LORA_NODE), 0],"positive": ["5", 0],"negative": ["5", 0],"latent_image": [str(GENERATION_LATENT_NODE), 0]},"class_type": "KSampler","_meta": {"title": "KSampler"}},
  "9": {"inputs": {"images": ["6", 0]},"class_type": "PreviewImage","_meta": {"title": "Flux Preview"}}
}

prompt.update(
    build_power_lora_node(
        PROMPT_LORA_NODE,
        model_ref=[str(GENERATION_MODEL_NODE), 0],
        clip_ref=[str(GENERATION_CLIP_NODE), 0],
        title="Power Lora Loader (rgthree)",
    )
)
prompt.update(
    build_bobs_latent_node(
        GENERATION_LATENT_NODE,
        model_type="FLUX",
        title="Bobs Latent Optimizer (Advanced)",
    )
)

# --- Flux Img2Img Template ---
img2img = {
  "1": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}, "class_type": "UnetLoaderGGUF", "_meta": {"title": "Unet Loader (GGUF)"}},
  "2": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader", "_meta": {"title": "DualCLIPLoader"}},
  "3": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}},
  "4": {"inputs": {"text": "PROMPT HERE", "clip": [str(IMG2IMG_LORA_NODE),1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Prompt)"}},
  "5": {"inputs": {"guidance": 3.5, "conditioning": ["4",0]}, "class_type": "FluxGuidance", "_meta": {"title": "FluxGuidance"}},
  "6": {"inputs": {"samples": ["8",0], "vae": ["3",0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
  "7": {"inputs": {"filename_prefix": "fluxbot/GEN", "images": ["6",0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
  "8": {"inputs": {"seed": 321292115380751, "steps": 32, "cfg": 1, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 0.75, "model": [str(IMG2IMG_LORA_NODE),0], "positive": ["5",0], "negative": ["5",0], "latent_image": ["14",0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
  "9": {"inputs": {"images": ["6", 0]}, "class_type": "PreviewImage", "_meta": {"title": "Flux Img2Img Preview"}},
  "14": {"inputs": {"pixels": ["16",0], "vae": ["3",0]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode"}},
  "15": {"inputs": {"url_or_path": ""}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}}
}

img2img.update(
    build_tenos_resize_node(
        "16",
        image_ref=["15", 0],
        title="Image Resize to 1M Pixels",
    )
)
img2img.update(
    build_power_lora_node(
        IMG2IMG_LORA_NODE,
        model_ref=["1", 0],
        clip_ref=["2", 0],
        title="Power Lora Loader (rgthree)",
    )
)

# --- Flux Upscale Template ---
upscale_prompt = {
  "1": {"inputs": {"text": "PROMPT HERE", "clip": [str(UPSCALE_LORA_NODE),1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "PROMPT"}},
  "58": {"inputs": {"filename_prefix": "fluxbot/UPSCALES/GEN_UP", "images": ["104",0]}, "class_type": "SaveImage", "_meta": {"title": "Save Upscaled Image"}},
  "103": {"inputs": {"model_name": "4x-UltraSharp.pth"}, "class_type": "UpscaleModelLoader", "_meta": {"title": "Load Upscale Model"}},
  "104": {"inputs": {"seed": 763716328118238, "steps": 16, "cfg": 1, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 0.2, "mode_type": "linear", "mask_blur": 16, "tile_padding": 32, "seam_fix_mode": "None", "seam_fix_denoise": 0.15, "seam_fix_width": 64, "seam_fix_mask_blur": 8, "seam_fix_padding": 16, "force_uniform_tiles": False, "tiled_decode": False, "image": ["115",0], "model": [str(UPSCALE_LORA_NODE),0], "positive": ["1",0], "negative": ["1",0], "vae": ["8:2",0], "upscale_model": ["103",0], "upscale_by": [str(UPSCALE_HELPER_LATENT_NODE),3], "tile_width": [str(UPSCALE_HELPER_LATENT_NODE),1], "tile_height": [str(UPSCALE_HELPER_LATENT_NODE),2]}, "class_type": "UltimateSDUpscale", "_meta": {"title": "Ultimate SD Upscale"}},
  "115": {"inputs": {"url_or_path": "IMAGE URL HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}},
  "8:2": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}},
  "8:0": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}, "class_type": "UnetLoaderGGUF", "_meta": {"title": "Unet Loader (GGUF)"}},
  "8:1": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader", "_meta": {"title": "DualCLIPLoader"}}
}

upscale_prompt.update(
    build_power_lora_node(
        UPSCALE_LORA_NODE,
        model_ref=["8:0", 0],
        clip_ref=["8:1", 0],
        title="Power Lora Loader (rgthree)",
    )
)
upscale_prompt.update(
    build_bobs_latent_node(
        UPSCALE_HELPER_LATENT_NODE,
        model_type="FLUX",
        upscale_by=1.85,
        title="Bobs Upscale Param Calculator",
    )
)

# --- Flux Variation Templates ---
weakvary_prompt = {
  "1": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}, "class_type": "UnetLoaderGGUF", "_meta": {"title": "Unet Loader (GGUF)"}},
  "2": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader", "_meta": {"title": "DualCLIPLoader"}},
  "3": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}},
  "7": {"inputs": {"seed": 775752669305671, "steps": 32, "cfg": 1, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 0.48, "control_after_generate": "increment", "model": [str(VARY_LORA_NODE),0], "positive": ["8",0], "negative": ["8",0], "latent_image": [str(FLUX_VAR_BATCH_NODE), 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
  "8": {"inputs": {"text": " ", "clip": [str(VARY_LORA_NODE),1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Prompt)"}},
  "11": {"inputs": {"samples": ["7",0], "vae": ["3",0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
  "22": {"inputs": {"pixels": ["36",0], "vae": ["3",0]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode"}},
  "33": {"inputs": {"url_or_path": ""}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}},
  "34": {"inputs": {"filename_prefix": "fluxbot/VARIATIONS", "images": ["11",0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
  str(FLUX_VAR_BATCH_NODE): {"inputs": {"amount": 1, "samples": ["22", 0]}, "class_type": "RepeatLatentBatch", "_meta": {"title": "RepeatLatentBatch"}}
}

weakvary_prompt.update(
    build_power_lora_node(
        VARY_LORA_NODE,
        model_ref=["1", 0],
        clip_ref=["2", 0],
        title="Power Lora Loader (rgthree)",
    )
)
weakvary_prompt.update(
    build_tenos_resize_node(
        "36",
        image_ref=["33", 0],
        title="Tenos Resize to ~1M Pixels",
    )
)
strongvary_prompt = {
  "1": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}, "class_type": "UnetLoaderGGUF", "_meta": {"title": "Unet Loader (GGUF)"}},
  "2": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader", "_meta": {"title": "DualCLIPLoader"}},
  "3": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}},
  "7": {"inputs": {"seed": 775752669305671, "steps": 32, "cfg": 1, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 0.75, "control_after_generate": "increment", "model": [str(VARY_LORA_NODE),0], "positive": ["8",0], "negative": ["8",0], "latent_image": [str(FLUX_VAR_BATCH_NODE), 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
  "8": {"inputs": {"text": " ", "clip": [str(VARY_LORA_NODE),1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Prompt)"}},
  "11": {"inputs": {"samples": ["7",0], "vae": ["3",0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
  "22": {"inputs": {"pixels": ["36",0], "vae": ["3",0]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode"}},
  "33": {"inputs": {"url_or_path": ""}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}},
  "34": {"inputs": {"filename_prefix": "fluxbot/VARIATIONS", "images": ["11",0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
  str(FLUX_VAR_BATCH_NODE): {"inputs": {"amount": 1, "samples": ["22", 0]}, "class_type": "RepeatLatentBatch", "_meta": {"title": "RepeatLatentBatch"}}
}

strongvary_prompt.update(
    build_power_lora_node(
        VARY_LORA_NODE,
        model_ref=["1", 0],
        clip_ref=["2", 0],
        title="Power Lora Loader (rgthree)",
    )
)
strongvary_prompt.update(
    build_tenos_resize_node(
        "36",
        image_ref=["33", 0],
        title="Tenos Resize to ~1M Pixels",
    )
)


# --- SDXL Generation Template (with LoRA) ---
sdxl_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_CLIP_SKIP_NODE): {"inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_LORA_NODE), 1]}, "class_type": "CLIPSetLastLayer", "_meta": {"title": "CLIP Skip -2"}},
  str(SDXL_POS_PROMPT_NODE): {"inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt (SDXL)"}},
  str(SDXL_NEG_PROMPT_NODE): {"inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt (SDXL)"}},
  str(SDXL_KSAMPLER_NODE): {"inputs": {"seed": 12345, "steps": 30, "cfg": 6.0, "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 1.0, "model": [str(SDXL_LORA_NODE), 0], "positive": [str(SDXL_POS_PROMPT_NODE), 0], "negative": [str(SDXL_NEG_PROMPT_NODE), 0], "latent_image": [str(SDXL_LATENT_NODE), 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler (SDXL)"}},
  str(SDXL_VAE_DECODE_NODE): {"inputs": {"samples": [str(SDXL_KSAMPLER_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode (SDXL)"}},
  str(SDXL_SAVE_IMAGE_NODE): {"inputs": {"filename_prefix": "sdxlbot/GEN", "images": [str(SDXL_VAE_DECODE_NODE), 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image (SDXL)"}},
  "sdxl_preview": {
    "inputs": {"images": [str(SDXL_VAE_DECODE_NODE), 0]},
    "class_type": "PreviewImage",
    "_meta": {"title": "SDXL Preview"}
  }
}

sdxl_prompt.update(
    build_power_lora_node(
        SDXL_LORA_NODE,
        model_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 0],
        clip_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        title="Power Lora Loader (SDXL)",
    )
)
sdxl_prompt.update(
    build_bobs_latent_node(
        SDXL_LATENT_NODE,
        model_type="SDXL",
        title="Bobs Latent Optimizer (SDXL)",
    )
)

# --- SDXL Img2Img Template (New) ---
sdxl_img2img_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_IMG2IMG_LOAD_IMAGE_NODE): {"inputs": {"url_or_path": "IMAGE_URL_HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "Load Image for Img2Img"}},
  str(SDXL_IMG2IMG_VAE_ENCODE_NODE): {"inputs": {"pixels": [str(SDXL_IMG2IMG_RESIZE_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode for Img2Img"}},
  str(SDXL_CLIP_SKIP_NODE): {"inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_LORA_NODE), 1]}, "class_type": "CLIPSetLastLayer", "_meta": {"title": "CLIP Skip -2 (Img2Img)"}},
  str(SDXL_POS_PROMPT_NODE): {"inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt (SDXL Img2Img)"}},
  str(SDXL_NEG_PROMPT_NODE): {"inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(SDXL_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt (SDXL Img2Img)"}},
  str(SDXL_KSAMPLER_NODE): {"inputs": {"seed": 12345, "steps": 30, "cfg": 6.0, "sampler_name": "euler", "scheduler": "karras", "denoise": 0.75, "model": [str(SDXL_LORA_NODE), 0], "positive": [str(SDXL_POS_PROMPT_NODE), 0], "negative": [str(SDXL_NEG_PROMPT_NODE), 0], "latent_image": [str(SDXL_IMG2IMG_VAE_ENCODE_NODE), 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler (SDXL Img2Img)"}},
  "sdxl_i2i_preview": {
    "inputs": {"images": [str(SDXL_VAE_DECODE_NODE), 0]},
    "class_type": "PreviewImage",
    "_meta": {"title": "SDXL Img2Img Preview"}
  },
  str(SDXL_VAE_DECODE_NODE): {"inputs": {"samples": [str(SDXL_KSAMPLER_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode (SDXL Img2Img)"}},
  str(SDXL_SAVE_IMAGE_NODE): {"inputs": {"filename_prefix": "sdxlbot/GEN_I2I", "images": [str(SDXL_VAE_DECODE_NODE), 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image (SDXL Img2Img)"}}
}

sdxl_img2img_prompt.update(
    build_tenos_resize_node(
        SDXL_IMG2IMG_RESIZE_NODE,
        image_ref=[str(SDXL_IMG2IMG_LOAD_IMAGE_NODE), 0],
        title="Tenos Resize to ~1M Pixels (Img2Img)",
    )
)
sdxl_img2img_prompt.update(
    build_power_lora_node(
        SDXL_LORA_NODE,
        model_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 0],
        clip_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        title="Power Lora Loader (SDXL Img2Img)",
    )
)


# --- SDXL Variation Template (with LoRA and denoise placeholder) ---
sdxl_variation_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_VAR_LOAD_IMAGE_NODE): {"inputs": {"url_or_path": "IMAGE_URL_HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "Load Image for Variation"}},
  str(SDXL_VAR_VAE_ENCODE_NODE): {"inputs": {"pixels": [str(SDXL_VAR_RESIZE_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode for Variation"}},
  str(SDXL_VAR_CLIP_SKIP_NODE): {"inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_VAR_LORA_NODE), 1]}, "class_type": "CLIPSetLastLayer", "_meta": {"title": "CLIP Skip -2"}},
  str(SDXL_VAR_POS_PROMPT_NODE): {"inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(SDXL_VAR_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt (SDXL)"}},
  str(SDXL_VAR_NEG_PROMPT_NODE): {"inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(SDXL_VAR_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt (SDXL)"}},
  str(SDXL_VAR_KSAMPLER_NODE): {"inputs": {"seed": 12345, "steps": 30, "cfg": 6.0, "sampler_name": "euler_ancestral", "scheduler": "karras", "denoise": 0.70, "control_after_generate": "increment", "model": [str(SDXL_VAR_LORA_NODE), 0], "positive": [str(SDXL_VAR_POS_PROMPT_NODE), 0], "negative": [str(SDXL_VAR_NEG_PROMPT_NODE), 0], "latent_image": [str(SDXL_VAR_BATCH_NODE), 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler (SDXL Variation)"}},
  str(SDXL_VAR_VAE_DECODE_NODE): {"inputs": {"samples": [str(SDXL_VAR_KSAMPLER_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode (SDXL)"}},
  str(SDXL_VAR_SAVE_IMAGE_NODE): {"inputs": {"filename_prefix": "sdxlbot/VAR", "images": [str(SDXL_VAR_VAE_DECODE_NODE), 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image (SDXL Variation)"}},
  str(SDXL_VAR_BATCH_NODE): {"inputs": {"amount": 1, "samples": [str(SDXL_VAR_VAE_ENCODE_NODE), 0]}, "class_type": "RepeatLatentBatch", "_meta": {"title": "RepeatLatentBatch"}}
}

sdxl_variation_prompt.update(
    build_tenos_resize_node(
        SDXL_VAR_RESIZE_NODE,
        image_ref=[str(SDXL_VAR_LOAD_IMAGE_NODE), 0],
        title="Tenos Resize to ~1M Pixels",
    )
)
sdxl_variation_prompt.update(
    build_power_lora_node(
        SDXL_VAR_LORA_NODE,
        model_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 0],
        clip_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        title="Power Lora Loader (SDXL Variation)",
    )
)


# --- SDXL Upscale Template (with LoRA) ---
sdxl_upscale_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_UPSCALE_CLIP_SKIP_NODE): {"inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_UPSCALE_LORA_NODE), 1]}, "class_type": "CLIPSetLastLayer", "_meta": {"title": "CLIP Skip -2 (Upscale)"}},
  str(SDXL_UPSCALE_POS_PROMPT_NODE): {"inputs": {"text": "UPSCALE PROMPT HERE", "clip": [str(SDXL_UPSCALE_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Upscale Positive Prompt (SDXL)"}},
  str(SDXL_UPSCALE_NEG_PROMPT_NODE): {"inputs": {"text": "UPSCALE NEGATIVE HERE", "clip": [str(SDXL_UPSCALE_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Upscale Negative Prompt (SDXL)"}},
  str(SDXL_UPSCALE_LOAD_IMAGE_NODE): {"inputs": {"url_or_path": "IMAGE_URL_HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "Load Image for Upscaling"}},
  str(SDXL_UPSCALE_MODEL_LOADER_NODE): {"inputs": {"model_name": "4x-UltraSharp.pth"}, "class_type": "UpscaleModelLoader", "_meta": {"title": "Load Upscale Model"}},
  str(SDXL_UPSCALE_ULTIMATE_NODE): {"inputs": {"seed": 12345, "steps": 16, "cfg": 6.0, "sampler_name": "euler_ancestral", "scheduler": "normal", "denoise": 0.15, "mode_type": "linear", "mask_blur": 16, "tile_padding": 32, "seam_fix_mode": "None", "seam_fix_denoise": 0.4, "seam_fix_width": 64, "seam_fix_mask_blur": 8, "seam_fix_padding": 32, "force_uniform_tiles": True, "tiled_decode": True, "image": [str(SDXL_UPSCALE_LOAD_IMAGE_NODE), 0], "model": [str(SDXL_UPSCALE_LORA_NODE), 0], "positive": [str(SDXL_UPSCALE_POS_PROMPT_NODE), 0], "negative": [str(SDXL_UPSCALE_NEG_PROMPT_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2], "upscale_model": [str(SDXL_UPSCALE_MODEL_LOADER_NODE), 0], "upscale_by": [str(SDXL_UPSCALE_HELPER_LATENT_NODE),3], "tile_width": [str(SDXL_UPSCALE_HELPER_LATENT_NODE),1], "tile_height": [str(SDXL_UPSCALE_HELPER_LATENT_NODE),2]}, "class_type": "UltimateSDUpscale", "_meta": {"title": "Ultimate SD Upscale (SDXL)"}},
  str(SDXL_UPSCALE_SAVE_IMAGE_NODE): {"inputs": {"filename_prefix": "sdxlbot/UPSCALES", "images": [str(SDXL_UPSCALE_ULTIMATE_NODE), 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Upscaled Image (SDXL)"}}
}

sdxl_upscale_prompt.update(
    build_power_lora_node(
        SDXL_UPSCALE_LORA_NODE,
        model_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 0],
        clip_ref=[str(SDXL_CHECKPOINT_LOADER_NODE), 1],
        title="Power Lora Loader (SDXL Upscale)",
    )
)
sdxl_upscale_prompt.update(
    build_bobs_latent_node(
        SDXL_UPSCALE_HELPER_LATENT_NODE,
        model_type="SDXL",
        upscale_by=1.85,
        title="Bobs Upscale Param Calculator (SDXL)",
    )
)

# --- Qwen Image Generation Template ---
qwen_prompt = {
  str(QWEN_UNET_LOADER_NODE): {
      "inputs": {"unet_name": "qwen_image_fp8_e4m3fn.safetensors", "weight_dtype": "default"},
      "class_type": "UNETLoader",
      "widgets_values": ["qwen_image_fp8_e4m3fn.safetensors", "default"],
      "_meta": {"title": "Load Qwen UNet"},
  },
  str(QWEN_CLIP_LOADER_NODE): {
      "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "embedding_directory": "default"},
      "class_type": "CLIPLoader",
      "widgets_values": ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "qwen_image", "default"],
      "_meta": {"title": "Load Qwen CLIP"},
  },
  str(QWEN_VAE_LOADER_NODE): {
      "inputs": {"vae_name": "qwen_image_vae.safetensors"},
      "class_type": "VAELoader",
      "widgets_values": ["qwen_image_vae.safetensors"],
      "_meta": {"title": "Load Qwen VAE"},
  },
  str(QWEN_POS_PROMPT_NODE): {
      "inputs": {"text": "PROMPT HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Positive Prompt"},
  },
  str(QWEN_NEG_PROMPT_NODE): {
      "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Negative Prompt"},
  },
  str(QWEN_SAMPLING_NODE): {
      "inputs": {
          "model": [str(QWEN_LORA_NODE), 0],
          "shift": 0.0,
      },
      "class_type": "ModelSamplingAuraFlow",
      "widgets_values": [0.0],
      "_meta": {"title": "Qwen Model Sampling"},
  },
  str(QWEN_KSAMPLER_NODE): {
      "inputs": {
          "seed": 12345,
          "steps": 28,
          "cfg": 5.5,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 1.0,
          "model": [str(QWEN_SAMPLING_NODE), 0],
          "positive": [str(QWEN_POS_PROMPT_NODE), 0],
          "negative": [str(QWEN_NEG_PROMPT_NODE), 0],
          "latent_image": [str(QWEN_LATENT_NODE), 0],
      },
      "class_type": "KSampler",
      "_meta": {"title": "KSampler (Qwen)"},
  },
  str(QWEN_VAE_DECODE_NODE): {
      "inputs": {
          "samples": [str(QWEN_KSAMPLER_NODE), 0],
          "vae": [str(QWEN_VAE_LOADER_NODE), 0],
      },
      "class_type": "VAEDecode",
      "_meta": {"title": "Qwen VAE Decode"},
  },
  str(QWEN_SAVE_IMAGE_NODE): {
      "inputs": {"filename_prefix": "qwenbot/GEN", "images": [str(QWEN_VAE_DECODE_NODE), 0]},
      "class_type": "SaveImage",
      "_meta": {"title": "Save Qwen Image"},
  },
  "qwen_preview": {
      "inputs": {"images": [str(QWEN_VAE_DECODE_NODE), 0]},
      "class_type": "PreviewImage",
      "_meta": {"title": "Qwen Preview"},
  },
}

qwen_prompt.update(
    build_power_lora_node(
        QWEN_LORA_NODE,
        model_ref=[str(QWEN_UNET_LOADER_NODE), 0],
        clip_ref=[str(QWEN_CLIP_LOADER_NODE), 0],
        title="Power Lora Loader (Qwen)",
    )
)
qwen_prompt.update(
    build_bobs_latent_node(
        QWEN_LATENT_NODE,
        model_type="QWEN",
        title="Bobs Latent Optimizer (Qwen)",
    )
)


# --- Qwen Image Img2Img Template ---
qwen_img2img_prompt = {
  str(QWEN_UNET_LOADER_NODE): {
      "inputs": {"unet_name": "qwen_image_fp8_e4m3fn.safetensors", "weight_dtype": "default"},
      "class_type": "UNETLoader",
      "widgets_values": ["qwen_image_fp8_e4m3fn.safetensors", "default"],
      "_meta": {"title": "Load Qwen UNet"},
  },
  str(QWEN_CLIP_LOADER_NODE): {
      "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "embedding_directory": "default"},
      "class_type": "CLIPLoader",
      "widgets_values": ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "qwen_image", "default"],
      "_meta": {"title": "Load Qwen CLIP"},
  },
  str(QWEN_VAE_LOADER_NODE): {
      "inputs": {"vae_name": "qwen_image_vae.safetensors"},
      "class_type": "VAELoader",
      "widgets_values": ["qwen_image_vae.safetensors"],
      "_meta": {"title": "Load Qwen VAE"},
  },
  str(QWEN_IMG2IMG_LOAD_IMAGE_NODE): {
      "inputs": {"url_or_path": "IMAGE_URL_HERE"},
      "class_type": "LoadImageFromUrlOrPath",
      "_meta": {"title": "Load Image for Qwen Img2Img"},
  },
  str(QWEN_IMG2IMG_VAE_ENCODE_NODE): {
      "inputs": {"pixels": [str(QWEN_IMG2IMG_RESIZE_NODE), 0], "vae": [str(QWEN_VAE_LOADER_NODE), 0]},
      "class_type": "VAEEncode",
      "_meta": {"title": "Qwen Img2Img Encode"},
  },
  str(QWEN_POS_PROMPT_NODE): {
      "inputs": {"text": "PROMPT HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Positive Prompt"},
  },
  str(QWEN_NEG_PROMPT_NODE): {
      "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Negative Prompt"},
  },
  str(QWEN_SAMPLING_NODE): {
      "inputs": {
          "model": [str(QWEN_LORA_NODE), 0],
          "shift": 0.0,
      },
      "class_type": "ModelSamplingAuraFlow",
      "widgets_values": [0.0],
      "_meta": {"title": "Qwen Model Sampling"},
  },
  str(QWEN_KSAMPLER_NODE): {
      "inputs": {
          "seed": 987654321,
          "steps": 24,
          "cfg": 5.0,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 0.7,
          "model": [str(QWEN_SAMPLING_NODE), 0],
          "positive": [str(QWEN_POS_PROMPT_NODE), 0],
          "negative": [str(QWEN_NEG_PROMPT_NODE), 0],
          "latent_image": [str(QWEN_IMG2IMG_VAE_ENCODE_NODE), 0],
      },
      "class_type": "KSampler",
      "_meta": {"title": "KSampler (Qwen Img2Img)"},
  },
  str(QWEN_VAE_DECODE_NODE): {
      "inputs": {"samples": [str(QWEN_KSAMPLER_NODE), 0], "vae": [str(QWEN_VAE_LOADER_NODE), 0]},
      "class_type": "VAEDecode",
      "_meta": {"title": "Qwen VAE Decode"},
  },
  str(QWEN_SAVE_IMAGE_NODE): {
      "inputs": {"filename_prefix": "qwenbot/IMG2IMG", "images": [str(QWEN_VAE_DECODE_NODE), 0]},
      "class_type": "SaveImage",
      "_meta": {"title": "Save Qwen Img2Img"},
  },
}

qwen_img2img_prompt.update(
    build_power_lora_node(
        QWEN_LORA_NODE,
        model_ref=[str(QWEN_UNET_LOADER_NODE), 0],
        clip_ref=[str(QWEN_CLIP_LOADER_NODE), 0],
        title="Power Lora Loader (Qwen)",
    )
)
qwen_img2img_prompt.update(
    build_tenos_resize_node(
        QWEN_IMG2IMG_RESIZE_NODE,
        image_ref=[str(QWEN_IMG2IMG_LOAD_IMAGE_NODE), 0],
        title="Tenos Resize to ~1M Pixels (Qwen Img2Img)",
    )
)


# --- Qwen Image Variation Template ---
qwen_variation_prompt = {
  str(QWEN_UNET_LOADER_NODE): {
      "inputs": {"unet_name": "qwen_image_fp8_e4m3fn.safetensors", "weight_dtype": "default"},
      "class_type": "UNETLoader",
      "widgets_values": ["qwen_image_fp8_e4m3fn.safetensors", "default"],
      "_meta": {"title": "Load Qwen UNet"},
  },
  str(QWEN_CLIP_LOADER_NODE): {
      "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "embedding_directory": "default"},
      "class_type": "CLIPLoader",
      "widgets_values": ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "qwen_image", "default"],
      "_meta": {"title": "Load Qwen CLIP"},
  },
  str(QWEN_VAE_LOADER_NODE): {
      "inputs": {"vae_name": "qwen_image_vae.safetensors"},
      "class_type": "VAELoader",
      "widgets_values": ["qwen_image_vae.safetensors"],
      "_meta": {"title": "Load Qwen VAE"},
  },
  str(QWEN_VAR_LOAD_IMAGE_NODE): {
      "inputs": {"url_or_path": "IMAGE_URL_HERE"},
      "class_type": "LoadImageFromUrlOrPath",
      "_meta": {"title": "Load Image for Qwen Variation"},
  },
  str(QWEN_VAR_VAE_ENCODE_NODE): {
      "inputs": {"pixels": [str(QWEN_VAR_RESIZE_NODE), 0], "vae": [str(QWEN_VAE_LOADER_NODE), 0]},
      "class_type": "VAEEncode",
      "_meta": {"title": "Qwen Variation Encode"},
  },
  str(QWEN_VAR_POS_PROMPT_NODE): {
      "inputs": {"text": "PROMPT HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Variation Positive"},
  },
  str(QWEN_VAR_NEG_PROMPT_NODE): {
      "inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Variation Negative"},
  },
  str(QWEN_VAR_SAMPLING_NODE): {
      "inputs": {
          "model": [str(QWEN_LORA_NODE), 0],
          "shift": 0.0,
      },
      "class_type": "ModelSamplingAuraFlow",
      "widgets_values": [0.0],
      "_meta": {"title": "Qwen Variation Model Sampling"},
  },
  str(QWEN_VAR_KSAMPLER_NODE): {
      "inputs": {
          "seed": 13579,
          "steps": 20,
          "cfg": 5.0,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 0.6,
          "control_after_generate": "increment",
          "model": [str(QWEN_VAR_SAMPLING_NODE), 0],
          "positive": [str(QWEN_VAR_POS_PROMPT_NODE), 0],
          "negative": [str(QWEN_VAR_NEG_PROMPT_NODE), 0],
          "latent_image": [str(QWEN_VAR_BATCH_NODE), 0],
      },
      "class_type": "KSampler",
      "_meta": {"title": "KSampler (Qwen Variation)"},
  },
  str(QWEN_VAR_BATCH_NODE): {
      "inputs": {"amount": 1, "samples": [str(QWEN_VAR_VAE_ENCODE_NODE), 0]},
      "class_type": "RepeatLatentBatch",
      "_meta": {"title": "RepeatLatentBatch (Qwen)"},
  },
  str(QWEN_VAR_VAE_DECODE_NODE): {
      "inputs": {"samples": [str(QWEN_VAR_KSAMPLER_NODE), 0], "vae": [str(QWEN_VAE_LOADER_NODE), 0]},
      "class_type": "VAEDecode",
      "_meta": {"title": "Qwen Variation Decode"},
  },
  str(QWEN_VAR_SAVE_IMAGE_NODE): {
      "inputs": {"filename_prefix": "qwenbot/VAR", "images": [str(QWEN_VAR_VAE_DECODE_NODE), 0]},
      "class_type": "SaveImage",
      "_meta": {"title": "Save Qwen Variation"},
  },
}

qwen_variation_prompt.update(
    build_power_lora_node(
        QWEN_LORA_NODE,
        model_ref=[str(QWEN_UNET_LOADER_NODE), 0],
        clip_ref=[str(QWEN_CLIP_LOADER_NODE), 0],
        title="Power Lora Loader (Qwen)",
    )
)
qwen_variation_prompt.update(
    build_tenos_resize_node(
        QWEN_VAR_RESIZE_NODE,
        image_ref=[str(QWEN_VAR_LOAD_IMAGE_NODE), 0],
        title="Tenos Resize to ~1M Pixels (Qwen Variation)",
    )
)


# --- Qwen Image Upscale Template ---
qwen_upscale_prompt = {
  str(QWEN_UNET_LOADER_NODE): {
      "inputs": {"unet_name": "qwen_image_fp8_e4m3fn.safetensors", "weight_dtype": "default"},
      "class_type": "UNETLoader",
      "widgets_values": ["qwen_image_fp8_e4m3fn.safetensors", "default"],
      "_meta": {"title": "Load Qwen UNet"},
  },
  str(QWEN_CLIP_LOADER_NODE): {
      "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "embedding_directory": "default"},
      "class_type": "CLIPLoader",
      "widgets_values": ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "qwen_image", "default"],
      "_meta": {"title": "Load Qwen CLIP"},
  },
  str(QWEN_VAE_LOADER_NODE): {
      "inputs": {"vae_name": "qwen_image_vae.safetensors"},
      "class_type": "VAELoader",
      "widgets_values": ["qwen_image_vae.safetensors"],
      "_meta": {"title": "Load Qwen VAE"},
  },
  str(QWEN_UPSCALE_POS_PROMPT_NODE): {
      "inputs": {"text": "UPSCALE PROMPT HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Upscale Positive"},
  },
  str(QWEN_UPSCALE_NEG_PROMPT_NODE): {
      "inputs": {"text": "UPSCALE NEGATIVE HERE", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Upscale Negative"},
  },
  str(QWEN_UPSCALE_SAMPLING_NODE): {
      "inputs": {
          "model": [str(QWEN_LORA_NODE), 0],
          "shift": 0.0,
      },
      "class_type": "ModelSamplingAuraFlow",
      "widgets_values": [0.0],
      "_meta": {"title": "Qwen Upscale Model Sampling"},
  },
  str(QWEN_UPSCALE_LOAD_IMAGE_NODE): {
      "inputs": {"url_or_path": "IMAGE_URL_HERE"},
      "class_type": "LoadImageFromUrlOrPath",
      "_meta": {"title": "Load Qwen Upscale Image"},
  },
  str(QWEN_UPSCALE_MODEL_LOADER_NODE): {
      "inputs": {"model_name": "4x-UltraSharp.pth"},
      "class_type": "UpscaleModelLoader",
      "_meta": {"title": "Load Upscale Model"},
  },
  str(QWEN_UPSCALE_ULTIMATE_NODE): {
      "inputs": {
          "seed": 55555,
          "steps": 16,
          "cfg": 5.5,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 0.2,
          "mode_type": "linear",
          "mask_blur": 16,
          "tile_padding": 32,
          "seam_fix_mode": "None",
          "seam_fix_denoise": 0.35,
          "seam_fix_width": 64,
          "seam_fix_mask_blur": 8,
          "seam_fix_padding": 32,
          "force_uniform_tiles": True,
          "tiled_decode": True,
          "image": [str(QWEN_UPSCALE_LOAD_IMAGE_NODE), 0],
          "model": [str(QWEN_UPSCALE_SAMPLING_NODE), 0],
          "positive": [str(QWEN_UPSCALE_POS_PROMPT_NODE), 0],
          "negative": [str(QWEN_UPSCALE_NEG_PROMPT_NODE), 0],
          "vae": [str(QWEN_VAE_LOADER_NODE), 0],
          "upscale_model": [str(QWEN_UPSCALE_MODEL_LOADER_NODE), 0],
          "upscale_by": [str(QWEN_UPSCALE_HELPER_LATENT_NODE), 3],
          "tile_width": [str(QWEN_UPSCALE_HELPER_LATENT_NODE), 1],
          "tile_height": [str(QWEN_UPSCALE_HELPER_LATENT_NODE), 2],
      },
      "class_type": "UltimateSDUpscale",
      "_meta": {"title": "Ultimate SD Upscale (Qwen)"},
  },
  str(QWEN_UPSCALE_SAVE_IMAGE_NODE): {
      "inputs": {"filename_prefix": "qwenbot/UPSCALE", "images": [str(QWEN_UPSCALE_ULTIMATE_NODE), 0]},
      "class_type": "SaveImage",
      "_meta": {"title": "Save Qwen Upscale"},
  },
}

qwen_upscale_prompt.update(
    build_power_lora_node(
        QWEN_LORA_NODE,
        model_ref=[str(QWEN_UNET_LOADER_NODE), 0],
        clip_ref=[str(QWEN_CLIP_LOADER_NODE), 0],
        title="Power Lora Loader (Qwen)",
    )
)
qwen_upscale_prompt.update(
    build_bobs_latent_node(
        QWEN_UPSCALE_HELPER_LATENT_NODE,
        model_type="QWEN",
        upscale_by=1.85,
        title="Bobs Upscale Param Calculator (Qwen)",
    )
)


# --- Qwen Image Edit Template ---
qwen_edit_prompt = {
  str(QWEN_UNET_LOADER_NODE): {
      "inputs": {"unet_name": "qwen_image_fp8_e4m3fn.safetensors", "weight_dtype": "default"},
      "class_type": "UNETLoader",
      "widgets_values": ["qwen_image_fp8_e4m3fn.safetensors", "default"],
      "_meta": {"title": "Load Qwen UNet"},
  },
  str(QWEN_CLIP_LOADER_NODE): {
      "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "embedding_directory": "default"},
      "class_type": "CLIPLoader",
      "widgets_values": ["qwen_2.5_vl_7b_fp8_scaled.safetensors", "qwen_image", "default"],
      "_meta": {"title": "Load Qwen CLIP"},
  },
  str(QWEN_VAE_LOADER_NODE): {
      "inputs": {"vae_name": "qwen_image_vae.safetensors"},
      "class_type": "VAELoader",
      "widgets_values": ["qwen_image_vae.safetensors"],
      "_meta": {"title": "Load Qwen VAE"},
  },
  str(QWEN_IMG2IMG_LOAD_IMAGE_NODE): {
      "inputs": {"url_or_path": "IMAGE_URL_HERE"},
      "class_type": "LoadImageFromUrlOrPath",
      "_meta": {"title": "Load Base Image (Qwen Edit)"},
  },
  str(QWEN_IMG2IMG_VAE_ENCODE_NODE): {
      "inputs": {"pixels": [str(QWEN_IMG2IMG_RESIZE_NODE), 0], "vae": [str(QWEN_VAE_LOADER_NODE), 0]},
      "class_type": "VAEEncode",
      "_meta": {"title": "Encode Base Image (Qwen Edit)"},
  },
  str(QWEN_POS_PROMPT_NODE): {
      "inputs": {"text": "EDIT PROMPT", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Edit Positive"},
  },
  str(QWEN_NEG_PROMPT_NODE): {
      "inputs": {"text": "NEGATIVE PROMPT", "clip": [str(QWEN_LORA_NODE), 1]},
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Qwen Edit Negative"},
  },
  str(QWEN_EDIT_SAMPLING_NODE): {
      "inputs": {
          "model": [str(QWEN_LORA_NODE), 0],
          "shift": 0.0,
          "cfg_rescale": 1.0,
      },
      "class_type": "ModelSamplingAuraFlow",
      "widgets_values": [0.0],
      "_meta": {"title": "Qwen Edit Model Sampling"},
  },
  str(QWEN_KSAMPLER_NODE): {
      "inputs": {
          "seed": 24680,
          "steps": 24,
          "cfg": 5.5,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 0.6,
          "model": [str(QWEN_EDIT_SAMPLING_NODE), 0],
          "positive": [str(QWEN_POS_PROMPT_NODE), 0],
          "negative": [str(QWEN_NEG_PROMPT_NODE), 0],
          "latent_image": [str(QWEN_IMG2IMG_VAE_ENCODE_NODE), 0],
      },
      "class_type": "KSampler",
      "_meta": {"title": "KSampler (Qwen Edit)"},
  },
  str(QWEN_VAR_VAE_DECODE_NODE): {
      "inputs": {"samples": [str(QWEN_KSAMPLER_NODE), 0], "vae": [str(QWEN_VAE_LOADER_NODE), 0]},
      "class_type": "VAEDecode",
      "_meta": {"title": "Decode Qwen Edit"},
  },
  str(QWEN_SAVE_IMAGE_NODE): {
      "inputs": {"filename_prefix": "qwenbot/EDIT", "images": [str(QWEN_VAR_VAE_DECODE_NODE), 0]},
      "class_type": "SaveImage",
      "_meta": {"title": "Save Qwen Edit"},
  },
}

qwen_edit_prompt.update(
    build_power_lora_node(
        QWEN_LORA_NODE,
        model_ref=[str(QWEN_UNET_LOADER_NODE), 0],
        clip_ref=[str(QWEN_CLIP_LOADER_NODE), 0],
        title="Power Lora Loader (Qwen)",
    )
)
qwen_edit_prompt.update(
    build_tenos_resize_node(
        QWEN_IMG2IMG_RESIZE_NODE,
        image_ref=[str(QWEN_IMG2IMG_LOAD_IMAGE_NODE), 0],
        title="Tenos Resize to ~1M Pixels (Qwen Edit)",
    )
)


# --- END OF FILE prompt_templates.py ---
