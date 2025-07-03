# --- START OF FILE kontext_templates.py ---
import json

# This contains all the nodes that are common to all Kontext edits.
# THIS VERSION IS CORRECTED based on user-provided workflow examples.
# It uses a standard KSampler and provides the missing 'weight_dtype' for the UNETLoader.
# It also correctly defines all required inputs for the ImageStitch node.
BASE_WORKFLOW = {
    "kontext_model_loader": {
        "inputs": {
            "unet_name": "%%KONTEXT_MODEL%%",
            "weight_dtype": "default"
        },
        "class_type": "UNETLoader",
        "_meta": {"title": "Load Kontext Model"}
    },
    "vae_loader": {
        "inputs": {"vae_name": "%%VAE_MODEL%%"},
        "class_type": "VAELoader",
        "_meta": {"title": "Load VAE"}
    },
    "clip_loader": {
        "inputs": {
            "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
            "clip_name2": "Long-ViT-L-14-GmP-SAE-full-model.safetensors",
            "type": "flux"
        },
        "class_type": "DualCLIPLoader",
        "_meta": {"title": "DualCLIPLoader"}
    },
    "instruction_encoder": {
        "inputs": {
            "text": "%%EDIT_COMMAND%%",
            "clip": ["clip_loader", 0]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "Encode Edit Command"}
    },
    "image_resizer": {
        "inputs": {
            "image": None, 
            "interpolation": "bilinear",
        },
        "class_type": "TenosResizeToTargetPixels",
        "_meta": {"title": "Resize to Target Pixels"}
    },
    "vae_encoder": {
        "inputs": {
            "pixels": ["image_resizer", 0],
            "vae": ["vae_loader", 0]
        },
        "class_type": "VAEEncode",
        "_meta": {"title": "VAE Encode Source Image"}
    },
    "latent_optimizer": {
        "inputs": {
            "aspect_ratio": "%%ASPECT_RATIO%%",
            "mp_size_float": 1.15,
            "upscale_by": 1,
            "model_type": "FLUX",
            "batch_size": 1
        },
        "class_type": "BobsLatentNodeAdvanced",
        "_meta": {"title": "Bobs Latent Optimizer (Kontext)"}
    },
    "reference_latent_node": {
        "inputs": {
            "conditioning": ["instruction_encoder", 0],
            "latent": ["vae_encoder", 0]
        },
        "class_type": "ReferenceLatent",
        "_meta": {"title": "ReferenceLatent"}
    },
    "flux_guidance": {
        "inputs": {
            "guidance": 3.0,
            "conditioning": ["reference_latent_node", 0]
        },
        "class_type": "FluxGuidance",
        "_meta": {"title": "FluxGuidance"}
    },
    "ksampler": {
        "inputs": {
            "seed": "%%SEED%%",
            "steps": "%%STEPS%%",
            "cfg": 1.0,
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
            "denoise": 1.0,
            "model": ["kontext_model_loader", 0],
            "positive": ["flux_guidance", 0],
            "negative": ["flux_guidance", 0],
            "latent_image": ["latent_optimizer", 0]
        },
        "class_type": "KSampler",
        "_meta": {"title": "KSampler"}
    },
    "vae_decoder": {
        "inputs": {
            "samples": ["ksampler", 0],
            "vae": ["vae_loader", 0]
        },
        "class_type": "VAEDecode",
        "_meta": {"title": "VAE Decode"}
    },
    "save_image": {
        "inputs": {
            "filename_prefix": "%%FILENAME_PREFIX%%",
            "images": ["vae_decoder", 0]
        },
        "class_type": "SaveImage",
        "_meta": {"title": "Save Edited Image"}
    }
}

def get_kontext_workflow(num_images: int):
    """
    Dynamically generates a ComfyUI workflow for FLUX Kontext editing
    based on the number of input images.
    """
    if not 1 <= num_images <= 4:
        raise ValueError("Number of images must be between 1 and 4.")

    workflow = json.loads(json.dumps(BASE_WORKFLOW))

    for i in range(1, num_images + 1):
        node_id = f"load_image_{i}"
        workflow[node_id] = {
            "inputs": {"url_or_path": f"%%IMAGE_URL_{i}%%"},
            "class_type": "LoadImageFromUrlOrPath",
            "_meta": {"title": f"Load Source Image {i}"}
        }
    
    final_image_source_node = "load_image_1"
    
    # Common inputs for all ImageStitch nodes, matching the user's example
    stitch_inputs = {
        "match_image_size": True,
        "spacing_width": 0,
        "spacing_color": "white",
        "feathering": 0
    }

    if num_images == 2:
        workflow["stitch_1_2"] = {
            "inputs": {**stitch_inputs, "image1": ["load_image_1", 0], "image2": ["load_image_2", 0], "direction": "right"},
            "class_type": "ImageStitch", "_meta": {"title": "Stitch 1 & 2"}
        }
        final_image_source_node = "stitch_1_2"
    elif num_images >= 3:
        image_4_input = ["load_image_4", 0] if num_images == 4 else ["load_image_3", 0]
        
        workflow["stitch_1_2"] = {
            "inputs": {**stitch_inputs, "image1": ["load_image_1", 0], "image2": ["load_image_2", 0], "direction": "right"},
            "class_type": "ImageStitch", "_meta": {"title": "Stitch 1 & 2"}
        }
        workflow["stitch_3_4"] = {
            "inputs": {**stitch_inputs, "image1": ["load_image_3", 0], "image2": image_4_input, "direction": "right"},
            "class_type": "ImageStitch", "_meta": {"title": "Stitch 3 & 4"}
        }
        workflow["stitch_final_vertical"] = {
            "inputs": {**stitch_inputs, "image1": ["stitch_1_2", 0], "image2": ["stitch_3_4", 0], "direction": "down"},
            "class_type": "ImageStitch", "_meta": {"title": "Stitch Final Grid"}
        }
        final_image_source_node = "stitch_final_vertical"

    workflow["image_resizer"]["inputs"]["image"] = [final_image_source_node, 0]

    return workflow