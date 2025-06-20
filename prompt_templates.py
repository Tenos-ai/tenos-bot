# --- START OF FILE prompt_templates.py ---
# style_prompt_templates.py

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

SDXL_UPSCALE_LOAD_IMAGE_NODE = "sdxl_up_load"
SDXL_UPSCALE_MODEL_LOADER_NODE = "sdxl_up_model_loader"
SDXL_UPSCALE_ULTIMATE_NODE = "sdxl_up_ultimate"
SDXL_UPSCALE_HELPER_LATENT_NODE = "sdxl_up_helper_latent"
SDXL_UPSCALE_SAVE_IMAGE_NODE = "sdxl_up_save"
SDXL_UPSCALE_LORA_NODE = SDXL_LORA_NODE # Reusing
SDXL_UPSCALE_CLIP_SKIP_NODE = "sdxl_upscale_clip_skip"
SDXL_UPSCALE_POS_PROMPT_NODE = "sdxl_upscale_pos_prompt"
SDXL_UPSCALE_NEG_PROMPT_NODE = "sdxl_upscale_neg_prompt"


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
  "9": {"inputs": {"images": ["6", 0]},"class_type": "PreviewImage","_meta": {"title": "Flux Preview"}},
  str(PROMPT_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"},"lora_1": {"on": False,"lora": "None","strength": 0},"lora_2": {"on": False,"lora": "None","strength": 0},"lora_3": {"on": False,"lora": "None","strength": 0},"lora_4": {"on": False,"lora": "None","strength": 0},"lora_5": {"on": False,"lora": "None","strength": 0},"➕ Add Lora": "","model": [str(GENERATION_MODEL_NODE), 0],"clip": [str(GENERATION_CLIP_NODE), 0]},"class_type": "Power Lora Loader (rgthree)","_meta": {"title": "Power Lora Loader (rgthree)"}},
  str(GENERATION_LATENT_NODE): {"inputs": {"aspect_ratio": "1:1","mp_size_float": "1","upscale_by": 1,"model_type": "FLUX","batch_size": 1},"class_type": "BobsLatentNodeAdvanced","_meta": {"title": "Bobs Latent Optimizer (Advanced)"}}
}

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
  "15": {"inputs": {"url_or_path": ""}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}},
  "16": {"inputs": {"interpolation": "bicubic", "image": ["15",0]}, "class_type": "TenosResizeToTargetPixels", "_meta": {"title": "Image Resize to 1M Pixels"}},
  str(IMG2IMG_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": ["1",0], "clip": ["2",0]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (rgthree)"}}
}

# --- Flux Upscale Template ---
upscale_prompt = {
  "1": {"inputs": {"text": "PROMPT HERE", "clip": [str(UPSCALE_LORA_NODE),1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "PROMPT"}},
  "58": {"inputs": {"filename_prefix": "fluxbot/UPSCALES/GEN_UP", "images": ["104",0]}, "class_type": "SaveImage", "_meta": {"title": "Save Upscaled Image"}},
  "103": {"inputs": {"model_name": "4x-UltraSharp.pth"}, "class_type": "UpscaleModelLoader", "_meta": {"title": "Load Upscale Model"}},
  "104": {"inputs": {"seed": 763716328118238, "steps": 16, "cfg": 1, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 0.2, "mode_type": "Linear", "mask_blur": 16, "tile_padding": 32, "seam_fix_mode": "None", "seam_fix_denoise": 0.15, "seam_fix_width": 64, "seam_fix_mask_blur": 8, "seam_fix_padding": 16, "force_uniform_tiles": False, "tiled_decode": False, "image": ["115",0], "model": [str(UPSCALE_LORA_NODE),0], "positive": ["1",0], "negative": ["1",0], "vae": ["8:2",0], "upscale_model": ["103",0], "upscale_by": [str(UPSCALE_HELPER_LATENT_NODE),3], "tile_width": [str(UPSCALE_HELPER_LATENT_NODE),1], "tile_height": [str(UPSCALE_HELPER_LATENT_NODE),2]}, "class_type": "UltimateSDUpscale", "_meta": {"title": "Ultimate SD Upscale"}},
  "115": {"inputs": {"url_or_path": "IMAGE URL HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}},
  str(UPSCALE_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": ["8:0",0], "clip": ["8:1",0]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (rgthree)"}},
  "8:2": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}},
  "8:0": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}, "class_type": "UnetLoaderGGUF", "_meta": {"title": "Unet Loader (GGUF)"}},
  "8:1": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader", "_meta": {"title": "DualCLIPLoader"}},
  str(UPSCALE_HELPER_LATENT_NODE): {"inputs": {"aspect_ratio": "1:1", "mp_size_float": "1", "upscale_by": 1.85, "model_type": "FLUX", "batch_size": 1}, "class_type": "BobsLatentNodeAdvanced", "_meta": {"title": "Bobs Upscale Param Calculator"}}
}

# --- Flux Variation Templates ---
weakvary_prompt = {
  "1": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}, "class_type": "UnetLoaderGGUF", "_meta": {"title": "Unet Loader (GGUF)"}},
  "2": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader", "_meta": {"title": "DualCLIPLoader"}},
  "3": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}},
  "7": {"inputs": {"seed": 775752669305671, "steps": 32, "cfg": 1, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 0.40, "model": [str(VARY_LORA_NODE),0], "positive": ["8",0], "negative": ["8",0], "latent_image": ["22",0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
  "8": {"inputs": {"text": " ", "clip": [str(VARY_LORA_NODE),1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Prompt)"}},
  "11": {"inputs": {"samples": ["7",0], "vae": ["3",0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
  "22": {"inputs": {"pixels": ["36",0], "vae": ["3",0]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode"}},
  "33": {"inputs": {"url_or_path": ""}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}},
  "34": {"inputs": {"filename_prefix": "fluxbot/VARIATIONS", "images": ["11",0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
  str(VARY_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": ["1",0], "clip": ["2",0]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (rgthree)"}},
  "36": {"inputs": {"interpolation": "bicubic", "image": ["33",0]}, "class_type": "TenosResizeToTargetPixels", "_meta": {"title": "Tenos Resize to ~1M Pixels"}}
}
strongvary_prompt = {
  "1": {"inputs": {"unet_name": "flux1-dev-Q8_0.gguf"}, "class_type": "UnetLoaderGGUF", "_meta": {"title": "Unet Loader (GGUF)"}},
  "2": {"inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors", "type": "flux"}, "class_type": "DualCLIPLoader", "_meta": {"title": "DualCLIPLoader"}},
  "3": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader", "_meta": {"title": "Load VAE"}},
  "7": {"inputs": {"seed": 775752669305671, "steps": 32, "cfg": 1, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 0.70, "model": [str(VARY_LORA_NODE),0], "positive": ["8",0], "negative": ["8",0], "latent_image": ["22",0]}, "class_type": "KSampler", "_meta": {"title": "KSampler"}},
  "8": {"inputs": {"text": " ", "clip": [str(VARY_LORA_NODE),1]}, "class_type": "CLIPTextEncode", "_meta": {"title": "CLIP Text Encode (Prompt)"}},
  "11": {"inputs": {"samples": ["7",0], "vae": ["3",0]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode"}},
  "22": {"inputs": {"pixels": ["36",0], "vae": ["3",0]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode"}},
  "33": {"inputs": {"url_or_path": ""}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "LoadImageFromUrlOrPath"}},
  "34": {"inputs": {"filename_prefix": "fluxbot/VARIATIONS", "images": ["11",0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image"}},
  str(VARY_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": ["1",0], "clip": ["2",0]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (rgthree)"}},
  "36": {"inputs": {"interpolation": "bicubic", "image": ["33",0]}, "class_type": "TenosResizeToTargetPixels", "_meta": {"title": "Tenos Resize to ~1M Pixels"}}
}


# --- SDXL Generation Template (with LoRA) ---
sdxl_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0], "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (SDXL)"}},
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
  },
  str(SDXL_LATENT_NODE): {"inputs": {"aspect_ratio": "1:1", "mp_size_float": "1", "upscale_by": 1.0, "model_type": "SDXL", "batch_size": 1}, "class_type": "BobsLatentNodeAdvanced", "_meta": {"title": "Bobs Latent Optimizer (SDXL)"}}
}

# --- SDXL Img2Img Template (New) ---
sdxl_img2img_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_IMG2IMG_LOAD_IMAGE_NODE): {"inputs": {"url_or_path": "IMAGE_URL_HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "Load Image for Img2Img"}},
  str(SDXL_IMG2IMG_RESIZE_NODE): {"inputs": {"interpolation": "bicubic", "image": [str(SDXL_IMG2IMG_LOAD_IMAGE_NODE), 0]}, "class_type": "TenosResizeToTargetPixels", "_meta": {"title": "Tenos Resize to ~1M Pixels (Img2Img)"}},
  str(SDXL_IMG2IMG_VAE_ENCODE_NODE): {"inputs": {"pixels": [str(SDXL_IMG2IMG_RESIZE_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode for Img2Img"}},
  str(SDXL_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0], "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (SDXL Img2Img)"}},
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


# --- SDXL Variation Template (with LoRA and denoise placeholder) ---
sdxl_variation_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_VAR_LOAD_IMAGE_NODE): {"inputs": {"url_or_path": "IMAGE_URL_HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "Load Image for Variation"}},
  str(SDXL_VAR_RESIZE_NODE): {"inputs": {"interpolation": "bicubic", "image": [str(SDXL_VAR_LOAD_IMAGE_NODE), 0]}, "class_type": "TenosResizeToTargetPixels", "_meta": {"title": "Tenos Resize to ~1M Pixels"}},
  str(SDXL_VAR_VAE_ENCODE_NODE): {"inputs": {"pixels": [str(SDXL_VAR_RESIZE_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEEncode", "_meta": {"title": "VAE Encode for Variation"}},
  str(SDXL_VAR_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0], "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (SDXL Variation)"}},
  str(SDXL_VAR_CLIP_SKIP_NODE): {"inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_VAR_LORA_NODE), 1]}, "class_type": "CLIPSetLastLayer", "_meta": {"title": "CLIP Skip -2"}},
  str(SDXL_VAR_POS_PROMPT_NODE): {"inputs": {"text": "POSITIVE PROMPT HERE", "clip": [str(SDXL_VAR_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Positive Prompt (SDXL)"}},
  str(SDXL_VAR_NEG_PROMPT_NODE): {"inputs": {"text": "NEGATIVE PROMPT HERE", "clip": [str(SDXL_VAR_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Negative Prompt (SDXL)"}},
  str(SDXL_VAR_KSAMPLER_NODE): {"inputs": {"seed": 12345, "steps": 30, "cfg": 6.0, "sampler_name": "euler_ancestral", "scheduler": "karras", "denoise": 0.70, "model": [str(SDXL_VAR_LORA_NODE), 0], "positive": [str(SDXL_VAR_POS_PROMPT_NODE), 0], "negative": [str(SDXL_VAR_NEG_PROMPT_NODE), 0], "latent_image": [str(SDXL_VAR_VAE_ENCODE_NODE), 0]}, "class_type": "KSampler", "_meta": {"title": "KSampler (SDXL Variation)"}},
  str(SDXL_VAR_VAE_DECODE_NODE): {"inputs": {"samples": [str(SDXL_VAR_KSAMPLER_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2]}, "class_type": "VAEDecode", "_meta": {"title": "VAE Decode (SDXL)"}},
  str(SDXL_VAR_SAVE_IMAGE_NODE): {"inputs": {"filename_prefix": "sdxlbot/VAR", "images": [str(SDXL_VAR_VAE_DECODE_NODE), 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Image (SDXL Variation)"}}
}


# --- SDXL Upscale Template (with LoRA) ---
sdxl_upscale_prompt = {
  str(SDXL_CHECKPOINT_LOADER_NODE): {"inputs": {"ckpt_name": "sdxl_model.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "Load SDXL Checkpoint"}},
  str(SDXL_UPSCALE_LORA_NODE): {"inputs": {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}, "lora_1": {"on": False, "lora": "None", "strength": 0}, "lora_2": {"on": False, "lora": "None", "strength": 0}, "lora_3": {"on": False, "lora": "None", "strength": 0}, "lora_4": {"on": False, "lora": "None", "strength": 0}, "lora_5": {"on": False, "lora": "None", "strength": 0}, "➕ Add Lora": "", "model": [str(SDXL_CHECKPOINT_LOADER_NODE), 0], "clip": [str(SDXL_CHECKPOINT_LOADER_NODE), 1]}, "class_type": "Power Lora Loader (rgthree)", "_meta": {"title": "Power Lora Loader (SDXL Upscale)"}},
  str(SDXL_UPSCALE_CLIP_SKIP_NODE): {"inputs": {"stop_at_clip_layer": -2, "clip": [str(SDXL_UPSCALE_LORA_NODE), 1]}, "class_type": "CLIPSetLastLayer", "_meta": {"title": "CLIP Skip -2 (Upscale)"}},
  str(SDXL_UPSCALE_POS_PROMPT_NODE): {"inputs": {"text": "UPSCALE PROMPT HERE", "clip": [str(SDXL_UPSCALE_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Upscale Positive Prompt (SDXL)"}},
  str(SDXL_UPSCALE_NEG_PROMPT_NODE): {"inputs": {"text": "UPSCALE NEGATIVE HERE", "clip": [str(SDXL_UPSCALE_CLIP_SKIP_NODE), 0]}, "class_type": "CLIPTextEncode", "_meta": {"title": "Upscale Negative Prompt (SDXL)"}},
  str(SDXL_UPSCALE_LOAD_IMAGE_NODE): {"inputs": {"url_or_path": "IMAGE_URL_HERE"}, "class_type": "LoadImageFromUrlOrPath", "_meta": {"title": "Load Image for Upscaling"}},
  str(SDXL_UPSCALE_MODEL_LOADER_NODE): {"inputs": {"model_name": "4x-UltraSharp.pth"}, "class_type": "UpscaleModelLoader", "_meta": {"title": "Load Upscale Model"}},
  str(SDXL_UPSCALE_ULTIMATE_NODE): {"inputs": {"seed": 12345, "steps": 16, "cfg": 5.0, "sampler_name": "euler", "scheduler": "karras", "denoise": 0.15, "mode_type": "Linear", "mask_blur": 16, "tile_padding": 32, "seam_fix_mode": "Half Tile + Intersections", "seam_fix_denoise": 0.4, "seam_fix_width": 64, "seam_fix_mask_blur": 8, "seam_fix_padding": 32, "force_uniform_tiles": True, "tiled_decode": True, "image": [str(SDXL_UPSCALE_LOAD_IMAGE_NODE), 0], "model": [str(SDXL_UPSCALE_LORA_NODE), 0], "positive": [str(SDXL_UPSCALE_POS_PROMPT_NODE), 0], "negative": [str(SDXL_UPSCALE_NEG_PROMPT_NODE), 0], "vae": [str(SDXL_CHECKPOINT_LOADER_NODE), 2], "upscale_model": [str(SDXL_UPSCALE_MODEL_LOADER_NODE), 0], "upscale_by": [str(SDXL_UPSCALE_HELPER_LATENT_NODE),3], "tile_width": [str(SDXL_UPSCALE_HELPER_LATENT_NODE),1], "tile_height": [str(SDXL_UPSCALE_HELPER_LATENT_NODE),2]}, "class_type": "UltimateSDUpscale", "_meta": {"title": "Ultimate SD Upscale (SDXL)"}},
  str(SDXL_UPSCALE_HELPER_LATENT_NODE): {"inputs": {"aspect_ratio": "1:1", "mp_size_float": "1", "upscale_by": 1.85, "model_type": "SDXL", "batch_size": 1}, "class_type": "BobsLatentNodeAdvanced", "_meta": {"title": "Bobs Upscale Param Calculator (SDXL)"}},
  str(SDXL_UPSCALE_SAVE_IMAGE_NODE): {"inputs": {"filename_prefix": "sdxlbot/UPSCALES", "images": [str(SDXL_UPSCALE_ULTIMATE_NODE), 0]}, "class_type": "SaveImage", "_meta": {"title": "Save Upscaled Image (SDXL)"}}
}

# --- END OF FILE prompt_templates.py ---