import json
import math
import os
import re
import traceback
import uuid

import requests
from io import BytesIO
from PIL import Image

from queue_manager import queue_manager

from model_registry import (
    copy_upscale_template,
    get_model_spec,
    resolve_model_type_from_prefix,
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
        if len(parts) > 2:
            server_share = '\\\\' + parts[2]
            rest_of_path = parts[3] if len(parts) > 3 else ""
            normalized = server_share.replace('\\', '/') + ('/' + rest_of_path.replace('\\', '/') if rest_of_path else "")
            if not rest_of_path and path.count('\\') == 3 and path.endswith('\\'):
                normalized = server_share.replace('\\', '/') + '/'
            elif not rest_of_path and path.count('\\') == 3 and not path.endswith('\\'):
                normalized = server_share.replace('\\', '/')
        else:
            normalized = path.replace('\\', '/')
    else:
        normalized = path.replace('\\', '/')
    return normalized


def _update_model_loader_filename(modified_prompt: dict, node_id, *, file_name) -> None:
    """Update loader nodes with override filenames for upscale flows."""

    if not node_id or not file_name:
        return

    node_entry = modified_prompt.get(node_id)
    if not isinstance(node_entry, dict):
        return

    inputs = node_entry.setdefault("inputs", {})
    if isinstance(inputs, dict):
        if "unet_name" in inputs:
            inputs["unet_name"] = file_name
        elif "model_name" in inputs:
            inputs["model_name"] = file_name

    widgets = node_entry.get("widgets_values")
    if isinstance(widgets, list) and widgets:
        widgets[0] = file_name


def _apply_flux_upscale_inputs(
    modified_prompt: dict,
    upscale_spec,
    *,
    prompt_text: str,
    image_url: str,
    aspect_ratio: str,
    upscale_by: float,
    seed: int,
    guidance: float,
    default_steps: int,
    default_denoise: float,
):
    if upscale_spec.pos_prompt_node and upscale_spec.pos_prompt_node in modified_prompt:
        modified_prompt[upscale_spec.pos_prompt_node]["inputs"]["text"] = prompt_text
    modified_prompt[upscale_spec.load_image_node]["inputs"]["url_or_path"] = image_url

    helper_inputs = modified_prompt[upscale_spec.helper_latent_node]["inputs"]
    helper_inputs.update({
        "aspect_ratio": aspect_ratio,
        "upscale_by": upscale_by,
        "model_type": upscale_spec.latent_model_type,
    })

    ultimate_inputs = modified_prompt[upscale_spec.upscale_node]["inputs"]
    ultimate_inputs["seed"] = seed
    if "cfg" in ultimate_inputs:
        ultimate_inputs["cfg"] = guidance

    final_steps = ultimate_inputs.get("steps", default_steps)
    final_denoise = ultimate_inputs.get("denoise", default_denoise)
    return final_denoise, final_steps, ultimate_inputs.get("cfg", guidance)


def _apply_checkpoint_upscale_inputs(
    modified_prompt: dict,
    upscale_spec,
    *,
    prompt_text: str,
    negative_prompt: str,
    image_url: str,
    aspect_ratio: str,
    upscale_by: float,
    seed: int,
    guidance: float,
    default_steps: int,
    default_denoise: float,
):
    clip_reference = [upscale_spec.model_loader_node, 1]
    if upscale_spec.clip_skip_node and upscale_spec.clip_skip_node in modified_prompt:
        modified_prompt[upscale_spec.clip_skip_node]["inputs"]["clip"] = [upscale_spec.lora_node, 1]
        clip_reference = [upscale_spec.clip_skip_node, 0]
    elif upscale_spec.lora_node in modified_prompt:
        clip_reference = [upscale_spec.lora_node, 1]
    elif upscale_spec.clip_loader_node and upscale_spec.clip_loader_node in modified_prompt:
        clip_reference = [upscale_spec.clip_loader_node, 0]

    if upscale_spec.pos_prompt_node and upscale_spec.pos_prompt_node in modified_prompt:
        modified_prompt[upscale_spec.pos_prompt_node]["inputs"].update({"text": prompt_text, "clip": clip_reference})
    if upscale_spec.neg_prompt_node and upscale_spec.neg_prompt_node in modified_prompt:
        modified_prompt[upscale_spec.neg_prompt_node]["inputs"].update({"text": negative_prompt, "clip": clip_reference})

    modified_prompt[upscale_spec.load_image_node]["inputs"]["url_or_path"] = image_url

    helper_inputs = modified_prompt[upscale_spec.helper_latent_node]["inputs"]
    helper_inputs.update({
        "aspect_ratio": aspect_ratio,
        "upscale_by": upscale_by,
        "model_type": upscale_spec.latent_model_type,
    })

    ultimate_inputs = modified_prompt[upscale_spec.upscale_node]["inputs"]
    ultimate_inputs["seed"] = seed
    ultimate_inputs["cfg"] = guidance

    final_steps = ultimate_inputs.get("steps", default_steps)
    final_denoise = ultimate_inputs.get("denoise", default_denoise)
    final_guidance = ultimate_inputs.get("cfg", guidance)
    return final_denoise, final_steps, final_guidance
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

    selected_base_model_setting = settings.get('selected_model')
    current_base_model_type, actual_base_model_filename = resolve_model_type_from_prefix(
        selected_base_model_setting if isinstance(selected_base_model_setting, str) else None
    )

    if not selected_base_model_setting:
        print("Upscaling: No model selected in settings. Defaulting to Flux (this might cause issues).")
        default_settings = _get_default_settings()
        fallback_model_setting = default_settings.get('selected_model')
        if fallback_model_setting and isinstance(fallback_model_setting, str):
            current_base_model_type, actual_base_model_filename = resolve_model_type_from_prefix(fallback_model_setting)

    spec = get_model_spec(current_base_model_type)
    upscale_spec = spec.upscale

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
    original_job_negative_prompt = ""
    source_job_id_for_tracking = "unknownSrc"
    original_guidance_default = settings.get(spec.defaults.guidance_key, spec.defaults.guidance_fallback)
    original_steps_default = settings.get(spec.defaults.steps_key, spec.defaults.steps_fallback)
    original_guidance_from_source = original_guidance_default
    original_steps_src = original_steps_default

    if original_job_data:
        prompt_for_upscaler_text_node = original_job_data.get('enhanced_prompt') or \
                                        original_job_data.get('original_prompt') or \
                                        original_job_data.get('prompt', prompt_for_upscaler_text_node)
        original_unenhanced_prompt_from_source = original_job_data.get('original_prompt')
        original_style_from_source = original_job_data.get('style', original_style_from_source)
        original_guidance_from_source = original_job_data.get('guidance', original_guidance_default)
        if current_base_model_type == 'sdxl':
            original_guidance_from_source = original_job_data.get('guidance_sdxl', original_guidance_from_source)
        elif current_base_model_type == 'qwen':
            original_guidance_from_source = original_job_data.get('guidance_qwen', original_guidance_from_source)
        elif current_base_model_type == 'wan':
            original_guidance_from_source = original_job_data.get('guidance_wan', original_guidance_from_source)
        original_steps_src = original_job_data.get('steps', original_steps_default)

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

        original_job_negative_prompt = original_job_data.get('negative_prompt', "")
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

    try:
        modified_upscale_prompt = copy_upscale_template(upscale_spec)
    except Exception as template_error:
        print(f"ERROR copying upscale template for model '{current_base_model_type}': {template_error}")
        return None, "Internal error preparing upscale template.", None

    default_negative_prompt = ""
    if spec.generation.supports_negative_prompt:
        default_neg_key = f"default_{current_base_model_type}_negative_prompt"
        default_negative_prompt = settings.get(default_neg_key, "")
    final_negative_prompt = original_job_negative_prompt if original_job_negative_prompt else default_negative_prompt

    final_upscaler_denoise = 0.25
    upscale_job_steps = original_steps_src
    upscale_job_guidance = original_guidance_from_source

    if upscale_spec.family == "flux":
        final_upscaler_denoise, upscale_job_steps, upscale_job_guidance = _apply_flux_upscale_inputs(
            modified_upscale_prompt,
            upscale_spec,
            prompt_text=prompt_for_upscaler_text_node,
            image_url=target_image_url,
            aspect_ratio=original_aspect_ratio_str_from_source,
            upscale_by=upscale_factor_setting,
            seed=upscale_seed,
            guidance=original_guidance_from_source,
            default_steps=original_steps_src,
            default_denoise=0.25,
        )
    else:
        final_upscaler_denoise, upscale_job_steps, upscale_job_guidance = _apply_checkpoint_upscale_inputs(
            modified_upscale_prompt,
            upscale_spec,
            prompt_text=prompt_for_upscaler_text_node,
            negative_prompt=final_negative_prompt,
            image_url=target_image_url,
            aspect_ratio=original_aspect_ratio_str_from_source,
            upscale_by=upscale_factor_setting,
            seed=upscale_seed,
            guidance=original_guidance_from_source,
            default_steps=original_steps_src,
            default_denoise=0.25,
        )

    os.makedirs(UPSCALES_DIR, exist_ok=True)
    filename_suffix_detail_ups = f"_from_img{image_index}_srcID{source_job_id_for_tracking}"
    
    file_prefix_base_ups = "GEN_UP_" 
    final_filename_prefix_ups = normalize_path_for_comfyui(
        os.path.join(UPSCALES_DIR, f"{file_prefix_base_ups}{upscale_job_id}{filename_suffix_detail_ups}")
    )
    save_node_id_final_ups = upscale_spec.save_node
    if save_node_id_final_ups in modified_upscale_prompt:
        modified_upscale_prompt[save_node_id_final_ups]["inputs"]["filename_prefix"] = final_filename_prefix_ups

    if actual_base_model_filename:
        base_model_loader_node_id_ups = upscale_spec.model_loader_node
        if base_model_loader_node_id_ups in modified_upscale_prompt:
            try:
                prefixed_base_model_name_ups = selected_base_model_setting if isinstance(selected_base_model_setting, str) else None
                if not prefixed_base_model_name_ups:
                    prefixed_base_model_name_ups = f"{current_base_model_type.upper()}: {actual_base_model_filename}"
                model_node_update_dict_ups = get_model_node(prefixed_base_model_name_ups, base_model_loader_node_id_ups)
                if base_model_loader_node_id_ups in model_node_update_dict_ups:
                    modified_upscale_prompt[base_model_loader_node_id_ups] = model_node_update_dict_ups[base_model_loader_node_id_ups]
            except Exception as e_base_model_ups:
                print(f"Error setting upscale base model ('{actual_base_model_filename}'): {e_base_model_ups}")

    if upscale_spec.upscale_model_loader_node and upscale_spec.upscale_model_loader_node in modified_upscale_prompt and selected_upscaler_model_file:
        modified_upscale_prompt[upscale_spec.upscale_model_loader_node]["inputs"]["model_name"] = selected_upscaler_model_file

    if upscale_spec.family == "flux":
        sel_t5_clip_ups = settings.get('selected_t5_clip')
        sel_clip_l_ups = settings.get('selected_clip_l')
        comfy_clips_data_ups = check_available_models_api(suppress_summary_print=True)
        comfy_clip_list_lower_ups = {m.lower() for m in comfy_clips_data_ups.get("clip", []) if isinstance(m, str)}
        flux_clip_node_id_ups = upscale_spec.clip_loader_node
        if sel_t5_clip_ups and sel_clip_l_ups and flux_clip_node_id_ups in modified_upscale_prompt:
            if sel_t5_clip_ups.lower() in comfy_clip_list_lower_ups and sel_clip_l_ups.lower() in comfy_clip_list_lower_ups:
                if "inputs" in modified_upscale_prompt[flux_clip_node_id_ups]:
                    modified_upscale_prompt[flux_clip_node_id_ups]["inputs"].update({"clip_name1": sel_t5_clip_ups, "clip_name2": sel_clip_l_ups})
    else:
        clip_setting_key_ups = f"default_{current_base_model_type}_clip"
        clip_override_ups = settings.get(clip_setting_key_ups)
        clip_loader_node_id_ups = upscale_spec.clip_loader_node
        if clip_override_ups and clip_loader_node_id_ups and clip_loader_node_id_ups in modified_upscale_prompt:
            clip_inputs_ups = modified_upscale_prompt[clip_loader_node_id_ups].setdefault("inputs", {})
            clip_inputs_ups["clip_name"] = clip_override_ups

    vae_setting_key_ups = f"default_{current_base_model_type}_vae"
    vae_override_ups = settings.get(vae_setting_key_ups)
    vae_loader_node_id_ups = upscale_spec.vae_loader_node
    if vae_override_ups and vae_loader_node_id_ups and vae_loader_node_id_ups in modified_upscale_prompt:
        vae_inputs_ups = modified_upscale_prompt[vae_loader_node_id_ups].setdefault("inputs", {})
        vae_inputs_ups["vae_name"] = vae_override_ups

    secondary_node_id_ups = getattr(upscale_spec, "secondary_model_loader_node", None)
    secondary_setting_key_ups = getattr(upscale_spec, "secondary_model_setting_key", None)
    if secondary_setting_key_ups:
        secondary_override_ups = settings.get(secondary_setting_key_ups)
    else:
        secondary_override_ups = None
    if secondary_override_ups:
        _update_model_loader_filename(
            modified_upscale_prompt,
            secondary_node_id_ups,
            file_name=secondary_override_ups,
        )

    lora_loader_node_id_for_ups_style = upscale_spec.lora_node
    if lora_loader_node_id_for_ups_style in modified_upscale_prompt:
        if isinstance(modified_upscale_prompt[lora_loader_node_id_for_ups_style].get("inputs"), dict):
            lora_inputs_dict_ups = modified_upscale_prompt[lora_loader_node_id_for_ups_style]["inputs"]
            if upscale_spec.family == "flux":
                lora_inputs_dict_ups["model"] = [upscale_spec.model_loader_node, 0]
                if upscale_spec.clip_loader_node:
                    lora_inputs_dict_ups["clip"] = [upscale_spec.clip_loader_node, 0]
            else:
                lora_inputs_dict_ups["model"] = [upscale_spec.model_loader_node, 0]
                if upscale_spec.clip_loader_node and upscale_spec.clip_loader_node in modified_upscale_prompt:
                    lora_inputs_dict_ups["clip"] = [upscale_spec.clip_loader_node, 0]
                else:
                    lora_inputs_dict_ups["clip"] = [upscale_spec.model_loader_node, 1]

            if style_for_this_upscale != 'off':
                style_data_loras_ups = styles_config.get(style_for_this_upscale, {})
                for i in range(1, 6):
                    lk_ups, lsc_ups = f"lora_{i}", style_data_loras_ups.get(f"lora_{i}")
                    if lk_ups in lora_inputs_dict_ups:
                        on_ups = isinstance(lsc_ups, dict) and lsc_ups.get('on', False)
                        ln_ups = lsc_ups.get('lora', "None") if isinstance(lsc_ups, dict) else "None"
                        ls_ups = float(lsc_ups.get('strength', 0.0)) if isinstance(lsc_ups, dict) else 0.0
                        if not isinstance(lora_inputs_dict_ups.get(lk_ups), dict):
                            lora_inputs_dict_ups[lk_ups] = {}
                        lora_inputs_dict_ups[lk_ups].update({"on": on_ups, "lora": ln_ups, "strength": ls_ups})
            else:
                for i in range(1, 6):
                    lk_ups = f"lora_{i}"
                    if lk_ups in lora_inputs_dict_ups:
                        if not isinstance(lora_inputs_dict_ups.get(lk_ups), dict):
                            lora_inputs_dict_ups[lk_ups] = {}
                        lora_inputs_dict_ups[lk_ups].update({"on": False, "lora": "None", "strength": 0.0})

    response_status_msg_ups = f"Upscaling image #{image_index} by {upscale_factor_setting:.2f}x (workflow: {current_base_model_type.upper()}). Seed: {upscale_seed}, Style: {style_for_this_upscale}."
    
    runtime_animation_supported = bool(spec.supports_animation)

    job_details_dict_ups = {
        "job_id": upscale_job_id,
        "prompt": prompt_for_upscaler_text_node,
        "original_prompt": original_unenhanced_prompt_from_source,
        "enhanced_prompt": original_job_data.get('enhanced_prompt') if original_job_data else None,
        "negative_prompt": final_negative_prompt if spec.generation.supports_negative_prompt else None,
        "seed": upscale_seed,
        "steps": upscale_job_steps,
        "guidance": upscale_job_guidance,
        "guidance_sdxl": upscale_job_guidance if current_base_model_type == 'sdxl' else None,
        "guidance_qwen": upscale_job_guidance if current_base_model_type == 'qwen' else None,
        "guidance_wan": upscale_job_guidance if current_base_model_type == 'wan' else None,
        "image_url": target_image_url,
        "original_width": original_image_width_val,
        "original_height": original_image_height_val,
        "aspect_ratio_str": original_aspect_ratio_str_from_source,
        "upscale_factor": upscale_factor_setting,
        "denoise": final_upscaler_denoise,
        "style": style_for_this_upscale,
        "image_index": image_index,
        "type": "upscale",
        "model_type_for_enhancer": current_base_model_type,
        "model_used": actual_base_model_filename or "Unknown/Template Default",
        "selected_model": selected_base_model_setting if isinstance(selected_base_model_setting, str) else None,
        "batch_size": 1,
        "style_warning_message": style_warning_message_ups,
        "supports_animation": runtime_animation_supported,
        "followup_animation_workflow": "wan_image_to_video" if runtime_animation_supported else None,
        "wan_animation_resolution": settings.get('wan_animation_resolution') if runtime_animation_supported else None,
        "wan_animation_duration": settings.get('wan_animation_duration') if runtime_animation_supported else None,
        "wan_animation_motion_profile": settings.get('wan_animation_motion_profile') if runtime_animation_supported else None,
        "parameters_used": {
            "seed": upscale_seed,
            "style": style_for_this_upscale,
            "upscale_factor": upscale_factor_setting,
            "selected_upscaler_model": selected_upscaler_model_file,
            "negative_prompt": final_negative_prompt if spec.generation.supports_negative_prompt else None,
            "base_model_type_workflow": current_base_model_type,
            "base_model_filename": actual_base_model_filename,
            "source_job_id": source_job_id_for_tracking
        }
    }
    return upscale_job_id, modified_upscale_prompt, response_status_msg_ups, job_details_dict_ups
