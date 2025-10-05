import json
import random
import uuid
import math
import requests
from io import BytesIO
from PIL import Image
import os
import re
import traceback
import asyncio

from queue_manager import queue_manager

from prompt_templates import (
    upscale_prompt as flux_upscale_template,
    sdxl_upscale_prompt,
    UPSCALE_MODEL_NODE as FLUX_UPSCALE_BASE_MODEL_NODE, 
    UPSCALE_CLIP_NODE as FLUX_UPSCALE_CLIP_NODE,      
    UPSCALE_LORA_NODE as FLUX_UPSCALE_LORA_NODE,
    UPSCALE_HELPER_LATENT_NODE as FLUX_UPSCALE_HELPER_LATENT_NODE,
    SDXL_CHECKPOINT_LOADER_NODE as SDXL_UPSCALE_BASE_MODEL_NODE, 
    SDXL_UPSCALE_LORA_NODE, 
    SDXL_UPSCALE_LOAD_IMAGE_NODE, 
    SDXL_UPSCALE_MODEL_LOADER_NODE, 
    SDXL_UPSCALE_ULTIMATE_NODE, 
    SDXL_UPSCALE_HELPER_LATENT_NODE,
    SDXL_UPSCALE_SAVE_IMAGE_NODE,
    SDXL_UPSCALE_CLIP_SKIP_NODE, 
    SDXL_UPSCALE_POS_PROMPT_NODE,
    SDXL_UPSCALE_NEG_PROMPT_NODE
)
from utils.seed_utils import parse_seed_from_message, generate_seed
from settings_manager import load_settings, load_styles_config, _get_default_settings
from modelnodes import get_model_node
from comfyui_api import get_available_comfyui_models as check_available_models_api


try:
    if not os.path.exists('config.json'):
        raise FileNotFoundError("config.json not found.")
    with open('config.json', 'r') as config_file:
        config_data = json.load(config_file)
    if not isinstance(config_data, dict):
         raise ValueError("config.json is not a valid dictionary.")
    UPSCALES_DIR = config_data.get('OUTPUTS', {}).get('UPSCALES', os.path.join('output','TENOSAI-BOT','UPSCALES'))
    if not isinstance(UPSCALES_DIR, str) or not UPSCALES_DIR:
        print("Warning: Invalid 'UPSCALES' path in config. Using default.")
        UPSCALES_DIR = os.path.join('output','TENOSAI-BOT','UPSCALES')
    if not os.path.isabs(UPSCALES_DIR):
        UPSCALES_DIR = os.path.abspath(UPSCALES_DIR)
except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError) as e:
    print(f"Error loading config.json in upscaling.py: {e}")
    config_data = {"OUTPUTS": {}}
    UPSCALES_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','UPSCALES'))
except Exception as e:
    print(f"Unexpected error loading config.json in upscaling.py: {e}")
    traceback.print_exc()
    config_data = {"OUTPUTS": {}}
    UPSCALES_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','UPSCALES'))

def normalize_path_for_comfyui(path):
    if not path or not isinstance(path, str): return path
    if path.startswith('\\\\'):
        parts = path.split('\\', 3)
        if len(parts) > 2 :
            server_share = '\\\\' + parts[2]
            rest_of_path = parts[3] if len(parts) > 3 else ""
            normalized = server_share.replace('\\', '/') + ('/' + rest_of_path.replace('\\', '/') if rest_of_path else "")
            if not rest_of_path and path.count('\\') == 3 and path.endswith('\\'):
                 normalized = server_share.replace('\\', '/') + '/'
            elif not rest_of_path and path.count('\\') == 3 and not path.endswith('\\'):
                 normalized = server_share.replace('\\', '/')
        else: normalized = path.replace('\\', '/')
    else: normalized = path.replace('\\', '/')
    return normalized

def get_image_dimensions(url):
    try:
        response = requests.get(url, timeout=10, stream=True, headers={'User-Agent': 'TenosAIBot/1.0'})
        response.raise_for_status()
        
        image_data = BytesIO()
        bytes_read = 0
        chunk_size = 8192 
        max_read_for_dims = 2 * 1024 * 1024 

        for chunk in response.iter_content(chunk_size=chunk_size):
            image_data.write(chunk)
            bytes_read += len(chunk)
            if bytes_read > max_read_for_dims:
                break
        
        image_data.seek(0) 
        img = Image.open(image_data)
        return img.size
    except requests.RequestException as e: 
        print(f"Error fetching image URL {url} for dimensions: {e}")
        if e.response is not None:
            print(f"Response status: {e.response.status_code}, Response text: {e.response.text[:200]}")
    except Image.UnidentifiedImageError:
        print(f"Error: Pillow could not identify image from URL {url}. It might not be a valid image or the format is unsupported/corrupt.")
    except Exception as e: 
        print(f"Error getting image dimensions from {url}: {e}")
        traceback.print_exc()
    return None


def modify_upscale_prompt(
    message_content_or_obj,
    referenced_message,    
    target_image_url: str, 
    image_index: int = 1   
):
    settings = load_settings()
    styles_config = load_styles_config() 
    upscale_job_id = str(uuid.uuid4())[:8]

    current_base_model_type = "flux" 
    actual_base_model_filename = None
    selected_base_model_setting = settings.get('selected_model')

    if selected_base_model_setting and isinstance(selected_base_model_setting, str):
        selected_base_model_stripped = selected_base_model_setting.strip()
        if ":" in selected_base_model_stripped:
            prefix, name = selected_base_model_stripped.split(":", 1)
            current_base_model_type = prefix.strip().lower()
            actual_base_model_filename = name.strip()
        else: 
            actual_base_model_filename = selected_base_model_stripped
            if actual_base_model_filename.endswith((".gguf", ".sft")): current_base_model_type = "flux"
            else: current_base_model_type = "sdxl"
    else:
        print("Upscaling: No model selected in settings. Defaulting to Flux (this might cause issues).")
        default_settings = _get_default_settings()
        fallback_model_setting = default_settings.get('selected_model')
        if fallback_model_setting and isinstance(fallback_model_setting, str):
             selected_base_model_stripped = fallback_model_setting.strip()
             if ":" in selected_base_model_stripped:
                prefix, name = selected_base_model_stripped.split(":", 1)
                current_base_model_type = prefix.strip().lower()
                actual_base_model_filename = name.strip()

    model_name_to_print_in_log = actual_base_model_filename if actual_base_model_filename else "Settings Default (or ComfyUI Default)"
    print(f"Upscale job {upscale_job_id}: Using CURRENTLY SELECTED model type '{current_base_model_type.upper()}' and model '{model_name_to_print_in_log}'.")

    original_job_data = queue_manager.get_job_data(referenced_message.id, referenced_message.channel.id)
    if not original_job_data and referenced_message.attachments:
        from file_management import extract_job_id 
        job_id_from_filename = extract_job_id(referenced_message.attachments[0].filename)
        if job_id_from_filename:
            original_job_data = queue_manager.get_job_data_by_id(job_id_from_filename)

    prompt_for_upscaler_text_node = "photo, masterpiece, best quality, very_detailed" 
    original_unenhanced_prompt_from_source = None
    original_style_from_source = "off"
    original_image_width_val = 1024  
    original_image_height_val = 1024 
    original_aspect_ratio_str_from_source = "1:1"
    original_job_sdxl_negative_prompt = ""
    source_job_id_for_tracking = "unknownSrc"
    original_guidance_flux = settings.get('default_guidance', 3.5) 
    original_guidance_sdxl = settings.get('default_guidance_sdxl', 7.0) 
    original_steps = settings.get('steps', 32) 

    if original_job_data:
        prompt_for_upscaler_text_node = original_job_data.get('enhanced_prompt') or \
                                        original_job_data.get('original_prompt') or \
                                        original_job_data.get('prompt', prompt_for_upscaler_text_node)
        original_unenhanced_prompt_from_source = original_job_data.get('original_prompt')
        original_style_from_source = original_job_data.get('style', original_style_from_source)
        original_guidance_flux_src = original_job_data.get('guidance', original_guidance_flux)
        original_guidance_sdxl_src = original_job_data.get('guidance_sdxl', original_guidance_sdxl)
        original_steps_src = original_job_data.get('steps', original_steps)

        width_from_job = original_job_data.get('width') or original_job_data.get('original_width')
        height_from_job = original_job_data.get('height') or original_job_data.get('original_height')
        try:
            original_image_width_val = int(width_from_job)
        except (ValueError, TypeError):
            original_image_width_val = None 
        try:
            original_image_height_val = int(height_from_job)
        except (ValueError, TypeError):
            original_image_height_val = None

        if original_image_width_val is None or original_image_height_val is None:
            dimensions = get_image_dimensions(target_image_url)
            if dimensions:
                original_image_width_val, original_image_height_val = dimensions
            else: 
                original_image_width_val = 1024
                original_image_height_val = 1024
                print(f"Upscaling: Failed to get dimensions from job data or URL. Defaulting to {original_image_width_val}x{original_image_height_val}.")

        original_job_sdxl_negative_prompt = original_job_data.get('negative_prompt', "") 
        source_job_id_for_tracking = original_job_data.get("job_id", source_job_id_for_tracking)
        
        ar_str_calc = original_job_data.get('aspect_ratio_str')
        if ar_str_calc and re.match(r'^\d+\s*:\s*\d+$', ar_str_calc): 
            original_aspect_ratio_str_from_source = ar_str_calc
        elif original_image_width_val and original_image_height_val and original_image_height_val > 0: 
            common_divisor = math.gcd(original_image_width_val, original_image_height_val)
            original_aspect_ratio_str_from_source = f"{original_image_width_val // common_divisor}:{original_image_height_val // common_divisor}"
    else: 
        dimensions = get_image_dimensions(target_image_url) 
        if dimensions:
            original_image_width_val, original_image_height_val = dimensions
            if original_image_height_val > 0: 
                common_divisor = math.gcd(original_image_width_val, original_image_height_val)
                original_aspect_ratio_str_from_source = f"{original_image_width_val // common_divisor}:{original_image_height_val // common_divisor}"
        else: 
            original_image_width_val = 1024
            original_image_height_val = 1024
            original_aspect_ratio_str_from_source = "1:1"
            print(f"Upscaling: No job data and failed to get dimensions from URL. Defaulting to {original_image_width_val}x{original_image_height_val}.")


    upscale_seed = generate_seed() 
    style_for_this_upscale = original_style_from_source
    if isinstance(message_content_or_obj, str):
        upscale_seed = parse_seed_from_message(message_content_or_obj, default_seed=upscale_seed)
        style_match = re.search(r'--style\s+([\w-]+)', message_content_or_obj, re.IGNORECASE)
        if style_match:
            requested_style = style_match.group(1) 
            if requested_style in styles_config: style_for_this_upscale = requested_style
    if style_for_this_upscale not in styles_config: style_for_this_upscale = "off"

    style_warning_message_ups = None
    if style_for_this_upscale != 'off':
        style_data_ups = styles_config.get(style_for_this_upscale, {})
        style_model_type_ups = style_data_ups.get('model_type', 'all')
        if style_model_type_ups != 'all' and style_model_type_ups != current_base_model_type:
            style_warning_message_ups = f"Style '{style_for_this_upscale}' is for {style_model_type_ups.upper()} models only. Upscaling with {current_base_model_type.upper()}. Style disabled."
            print(f"Style Warning for upscale job {upscale_job_id}: {style_warning_message_ups}")
            style_for_this_upscale = 'off'

    selected_upscaler_model_file = settings.get('selected_upscale_model')
    if not selected_upscaler_model_file or selected_upscaler_model_file.lower() == "none":
        selected_upscaler_model_file = "4x-UltraSharp.pth" 
    try:
        upscale_factor_setting = float(settings.get('upscale_factor', 1.85))
        if not (1.5 <= upscale_factor_setting <= 4.0): upscale_factor_setting = 1.85
    except (ValueError, TypeError): upscale_factor_setting = 1.85

    template_to_use = sdxl_upscale_prompt if current_base_model_type == "sdxl" else flux_upscale_template
    modified_upscale_prompt = json.loads(json.dumps(template_to_use))
    final_upscaler_denoise = 0.25
    upscale_job_steps = original_steps 
    upscale_job_guidance = original_guidance_flux if current_base_model_type == "flux" else original_guidance_sdxl

    if current_base_model_type == "flux":
        modified_upscale_prompt["1"]["inputs"]["text"] = prompt_for_upscaler_text_node
        modified_upscale_prompt["115"]["inputs"]["url_or_path"] = target_image_url
        flux_helper_node_id = str(FLUX_UPSCALE_HELPER_LATENT_NODE)
        modified_upscale_prompt[flux_helper_node_id]["inputs"].update({
            "aspect_ratio": original_aspect_ratio_str_from_source,
            "upscale_by": upscale_factor_setting, "model_type": "FLUX"
        })
        ultimate_upscale_node_id_flux = "104"
        modified_upscale_prompt[ultimate_upscale_node_id_flux]["inputs"]["seed"] = upscale_seed
        final_upscaler_denoise = modified_upscale_prompt[ultimate_upscale_node_id_flux]["inputs"].get("denoise", 0.25)
        upscale_job_steps = modified_upscale_prompt[ultimate_upscale_node_id_flux]["inputs"].get("steps", original_steps)
        flux_upscaler_model_loader_node_id = "103"
        if flux_upscaler_model_loader_node_id in modified_upscale_prompt and selected_upscaler_model_file:
            modified_upscale_prompt[flux_upscaler_model_loader_node_id]["inputs"]["model_name"] = selected_upscaler_model_file
    elif current_base_model_type == "sdxl":
        modified_upscale_prompt[str(SDXL_UPSCALE_POS_PROMPT_NODE)]["inputs"]["text"] = prompt_for_upscaler_text_node
        final_sdxl_upscale_neg_prompt = original_job_sdxl_negative_prompt if original_job_sdxl_negative_prompt else settings.get('default_sdxl_negative_prompt', "")
        modified_upscale_prompt[str(SDXL_UPSCALE_NEG_PROMPT_NODE)]["inputs"]["text"] = final_sdxl_upscale_neg_prompt
        modified_upscale_prompt[str(SDXL_UPSCALE_LOAD_IMAGE_NODE)]["inputs"]["url_or_path"] = target_image_url
        sdxl_helper_node_id = str(SDXL_UPSCALE_HELPER_LATENT_NODE)
        modified_upscale_prompt[sdxl_helper_node_id]["inputs"].update({
            "aspect_ratio": original_aspect_ratio_str_from_source,
            "upscale_by": upscale_factor_setting, "model_type": "SDXL"
        })
        sdxl_ultimate_node_id = str(SDXL_UPSCALE_ULTIMATE_NODE)
        modified_upscale_prompt[sdxl_ultimate_node_id]["inputs"]["seed"] = upscale_seed
        final_upscaler_denoise = modified_upscale_prompt[sdxl_ultimate_node_id]["inputs"].get("denoise", 0.25)
        upscale_job_steps = modified_upscale_prompt[sdxl_ultimate_node_id]["inputs"].get("steps", original_steps)
        upscale_job_guidance = modified_upscale_prompt[sdxl_ultimate_node_id]["inputs"].get("cfg", original_guidance_sdxl)

        sdxl_upscaler_model_loader_node_id = str(SDXL_UPSCALE_MODEL_LOADER_NODE)
        if sdxl_upscaler_model_loader_node_id in modified_upscale_prompt and selected_upscaler_model_file:
            modified_upscale_prompt[sdxl_upscaler_model_loader_node_id]["inputs"]["model_name"] = selected_upscaler_model_file

    os.makedirs(UPSCALES_DIR, exist_ok=True)
    filename_suffix_detail_ups = f"_from_img{image_index}_srcID{source_job_id_for_tracking}"
    
    file_prefix_base_ups = "GEN_UP_" 
    final_filename_prefix_ups = normalize_path_for_comfyui(
        os.path.join(UPSCALES_DIR, f"{file_prefix_base_ups}{upscale_job_id}{filename_suffix_detail_ups}")
    )
    save_node_id_final_ups = str(SDXL_UPSCALE_SAVE_IMAGE_NODE) if current_base_model_type == "sdxl" else "58"
    if save_node_id_final_ups in modified_upscale_prompt:
        modified_upscale_prompt[save_node_id_final_ups]["inputs"]["filename_prefix"] = final_filename_prefix_ups

    if actual_base_model_filename:
        base_model_loader_node_id_ups = str(SDXL_UPSCALE_BASE_MODEL_NODE) if current_base_model_type == "sdxl" else str(FLUX_UPSCALE_BASE_MODEL_NODE)
        if base_model_loader_node_id_ups in modified_upscale_prompt:
            try:
                prefixed_base_model_name_ups = f"{current_base_model_type.capitalize()}: {actual_base_model_filename}"
                model_node_update_dict_ups = get_model_node(prefixed_base_model_name_ups, base_model_loader_node_id_ups)
                if base_model_loader_node_id_ups in model_node_update_dict_ups:
                    modified_upscale_prompt[base_model_loader_node_id_ups] = model_node_update_dict_ups[base_model_loader_node_id_ups]
            except Exception as e_base_model_ups: print(f"Error setting upscale base model ('{actual_base_model_filename}'): {e_base_model_ups}")

    if current_base_model_type == "flux":
        sel_t5_clip_ups = settings.get('selected_t5_clip'); sel_clip_l_ups = settings.get('selected_clip_l')
        flux_clip_node_id_ups = str(FLUX_UPSCALE_CLIP_NODE)
        comfy_clips_data_ups = check_available_models_api(suppress_summary_print=True)
        comfy_clip_list_lower_ups = {m.lower() for m in comfy_clips_data_ups.get("clip", []) if isinstance(m, str)}
        if sel_t5_clip_ups and sel_clip_l_ups and \
           sel_t5_clip_ups.lower() in comfy_clip_list_lower_ups and \
           sel_clip_l_ups.lower() in comfy_clip_list_lower_ups and \
           flux_clip_node_id_ups in modified_upscale_prompt:
            if "inputs" in modified_upscale_prompt[flux_clip_node_id_ups]:
                 modified_upscale_prompt[flux_clip_node_id_ups]["inputs"].update({"clip_name1": sel_t5_clip_ups, "clip_name2": sel_clip_l_ups})

    lora_loader_node_id_for_ups_style = str(SDXL_UPSCALE_LORA_NODE) if current_base_model_type == "sdxl" else str(FLUX_UPSCALE_LORA_NODE)
    if lora_loader_node_id_for_ups_style in modified_upscale_prompt:
        if isinstance(modified_upscale_prompt[lora_loader_node_id_for_ups_style].get("inputs"), dict):
            lora_inputs_dict_ups = modified_upscale_prompt[lora_loader_node_id_for_ups_style]["inputs"]
            
            if current_base_model_type == "flux":
                 pass 
            elif current_base_model_type == "sdxl":
                lora_inputs_dict_ups["model"] = [str(SDXL_UPSCALE_BASE_MODEL_NODE), 0]
                lora_inputs_dict_ups["clip"] = [str(SDXL_UPSCALE_BASE_MODEL_NODE), 1]
            
            if style_for_this_upscale != 'off':
                style_data_loras_ups = styles_config.get(style_for_this_upscale, {})
                for i in range(1, 6):
                    lk_ups, lsc_ups = f"lora_{i}", style_data_loras_ups.get(f"lora_{i}")
                    if lk_ups in lora_inputs_dict_ups: 
                        on_ups = isinstance(lsc_ups,dict) and lsc_ups.get('on',False)
                        ln_ups = lsc_ups.get('lora', "None") if isinstance(lsc_ups,dict) else "None"
                        ls_ups = float(lsc_ups.get('strength',0.0)) if isinstance(lsc_ups,dict) else 0.0
                        if not isinstance(lora_inputs_dict_ups.get(lk_ups), dict): 
                            lora_inputs_dict_ups[lk_ups] = {}
                        lora_inputs_dict_ups[lk_ups].update({"on":on_ups, "lora":ln_ups, "strength":ls_ups})
            else: 
                for i in range(1, 6):
                    lk_ups = f"lora_{i}"
                    if lk_ups in lora_inputs_dict_ups:
                        if not isinstance(lora_inputs_dict_ups.get(lk_ups), dict):
                            lora_inputs_dict_ups[lk_ups] = {}
                        lora_inputs_dict_ups[lk_ups].update({"on": False, "lora": "None", "strength": 0.0})

    response_status_msg_ups = f"Upscaling image #{image_index} by {upscale_factor_setting:.2f}x (workflow: {current_base_model_type.upper()}). Seed: {upscale_seed}, Style: {style_for_this_upscale}."
    
    job_details_dict_ups = {
        "job_id": upscale_job_id, "prompt": prompt_for_upscaler_text_node,
        "original_prompt": original_unenhanced_prompt_from_source,
        "enhanced_prompt": original_job_data.get('enhanced_prompt') if original_job_data else None,
        "negative_prompt": final_sdxl_upscale_neg_prompt if current_base_model_type == "sdxl" else None,
        "seed": upscale_seed,
        "steps": upscale_job_steps, 
        "guidance": upscale_job_guidance if current_base_model_type == 'flux' else None, 
        "guidance_sdxl": upscale_job_guidance if current_base_model_type == 'sdxl' else None, 
        "image_url": target_image_url, 
        "original_width": original_image_width_val, 
        "original_height": original_image_height_val, 
        "aspect_ratio_str": original_aspect_ratio_str_from_source,
        "upscale_factor": upscale_factor_setting, "denoise": final_upscaler_denoise, 
        "style": style_for_this_upscale, "image_index": image_index, "type": "upscale",
        "model_type_for_enhancer": current_base_model_type, 
        "batch_size": 1,
        "style_warning_message": style_warning_message_ups,
        "parameters_used": {
            "seed": upscale_seed, "style": style_for_this_upscale, 
            "upscale_factor": upscale_factor_setting, 
            "selected_upscaler_model": selected_upscaler_model_file,
            "base_model_type_workflow": current_base_model_type, 
            "base_model_filename": actual_base_model_filename, 
            "source_job_id": source_job_id_for_tracking
        }
    }
    return upscale_job_id, modified_upscale_prompt, response_status_msg_ups, job_details_dict_ups
