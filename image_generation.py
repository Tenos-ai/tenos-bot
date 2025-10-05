# --- START OF FILE image_generation.py ---
import json
import random
import uuid
import re
import math
import os
import requests 
import traceback
import asyncio 

from prompt_templates import (
    prompt as flux_prompt_template,
    img2img as flux_img2img_template,
    sdxl_prompt as sdxl_prompt_template,
    sdxl_img2img_prompt,
    GENERATION_MODEL_NODE,
    GENERATION_WORKFLOW_STEPS_NODE,
    GENERATION_CLIP_NODE,
    GENERATION_LATENT_NODE,
    PROMPT_LORA_NODE,
    IMG2IMG_LORA_NODE,
    SDXL_CHECKPOINT_LOADER_NODE, SDXL_LORA_NODE, SDXL_CLIP_SKIP_NODE,
    SDXL_POS_PROMPT_NODE, SDXL_NEG_PROMPT_NODE,
    SDXL_KSAMPLER_NODE, SDXL_VAE_DECODE_NODE,
    SDXL_SAVE_IMAGE_NODE, SDXL_LATENT_NODE,
    SDXL_IMG2IMG_LOAD_IMAGE_NODE, SDXL_IMG2IMG_RESIZE_NODE, SDXL_IMG2IMG_VAE_ENCODE_NODE
)
from utils.seed_utils import parse_seed_from_message, generate_seed
from settings_manager import load_settings, _get_default_settings, load_styles_config
from modelnodes import get_model_node
from comfyui_api import get_available_comfyui_models as check_available_models_api # suppress_summary_print will be passed as True
from utils.llm_enhancer import enhance_prompt, FLUX_ENHANCER_SYSTEM_PROMPT, SDXL_ENHANCER_SYSTEM_PROMPT


try:
    if not os.path.exists('config.json'):
        raise FileNotFoundError("config.json not found.")
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
         raise ValueError("config.json is not a valid dictionary.")
    GENERATIONS_DIR = config.get('OUTPUTS', {}).get('GENERATIONS', os.path.join('output','TENOSAI-BOT','GENERATIONS'))
    if not isinstance(GENERATIONS_DIR, str) or not GENERATIONS_DIR:
         print("Warning: Invalid 'GENERATIONS' path in config. Using default.")
         GENERATIONS_DIR = os.path.join('output','TENOSAI-BOT','GENERATIONS')
    if not os.path.isabs(GENERATIONS_DIR): 
        GENERATIONS_DIR = os.path.abspath(GENERATIONS_DIR)
except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError) as e:
    print(f"ERROR loading config.json in image_generation: {e}")
    config = {"OUTPUTS": {}, "LLM_ENHANCER": {}} 
    GENERATIONS_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','GENERATIONS')) 
except Exception as e:
    print(f"UNEXPECTED ERROR loading config.json in image_generation: {e}")
    traceback.print_exc()
    config = {"OUTPUTS": {}, "LLM_ENHANCER": {}} 
    GENERATIONS_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','GENERATIONS')) 


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

        else: 
            normalized = path.replace('\\', '/')
    else:
        normalized = path.replace('\\', '/')
    return normalized

async def modify_prompt(
    original_prompt_text: str,
    params_dict: dict,
    enhancer_info: dict,
    is_img2img: bool,
    explicit_seed: int | None = None,
    selected_model_name_with_prefix: str | None = None, # This is the CURRENTLY selected model from settings
    negative_prompt_text: str | None = None 
):
    job_id = str(uuid.uuid4())[:8]
    model_type = "flux" 
    actual_model_name = None 
    styles_config = load_styles_config() 

    # Determine model_type and actual_model_name based on selected_model_name_with_prefix (current setting)
    if selected_model_name_with_prefix:
        if selected_model_name_with_prefix.startswith("Flux: "):
            model_type = "flux"
            actual_model_name = selected_model_name_with_prefix.split("Flux: ", 1)[1].strip()
        elif selected_model_name_with_prefix.startswith("SDXL: "):
            model_type = "sdxl"
            actual_model_name = selected_model_name_with_prefix.split("SDXL: ", 1)[1].strip()
        else: 
            print(f"Warning: selected_model_name_with_prefix '{selected_model_name_with_prefix}' missing type prefix. Inferring.")
            if selected_model_name_with_prefix.endswith((".gguf", ".sft")): 
                model_type = "flux"
            else: 
                model_type = "sdxl"
            actual_model_name = selected_model_name_with_prefix.strip()
    else: # Fallback if no model selected in settings (should be rare)
        print("image_generation: No model selected in settings. Defaulting to Flux.")
        model_type = "flux"
        # actual_model_name will be None, ComfyUI might use its default or error.

    text_for_generation = enhancer_info.get('enhanced_text') if enhancer_info.get('used') else original_prompt_text
    
    print("-" * 30)
    print(f"Preparing Job: {job_id} ({model_type.upper()}{' Img2Img' if is_img2img else ''})")
    print(f"  User Prompt: {original_prompt_text}")
    if enhancer_info.get('used'): print(f"  LLM Enhanced: {text_for_generation}")
    if enhancer_info.get('error'): print(f"  LLM Error: {enhancer_info['error']}")

    try:
        settings = load_settings()
    except Exception as e:
        print(f"ERROR loading settings in modify_prompt: {e}"); settings = _get_default_settings()

    seed = explicit_seed
    if seed is None: 
        seed_param_val = params_dict.get('seed')
        if seed_param_val and seed_param_val is not True: 
            try: seed = int(seed_param_val)
            except (ValueError, TypeError): seed = generate_seed()
        else: seed = generate_seed() 

    # Use guidance from current settings, overridden by params if provided
    default_flux_guidance = settings.get('default_guidance', 3.5)
    default_sdxl_guidance = settings.get('default_guidance_sdxl', 7.0)
    guidance_to_use = default_sdxl_guidance if model_type == "sdxl" else default_flux_guidance

    g_param_flux = params_dict.get('g')
    g_param_sdxl = params_dict.get('g_sdxl')

    if model_type == "sdxl" and g_param_sdxl and g_param_sdxl is not True:
        try: guidance_to_use = float(g_param_sdxl)
        except (ValueError, TypeError): print(f"  Warn: Invalid --g_sdxl value. Using SDXL default: {default_sdxl_guidance:.1f}")
    elif model_type == "flux" and g_param_flux and g_param_flux is not True:
        try: guidance_to_use = float(g_param_flux)
        except (ValueError, TypeError): print(f"  Warn: Invalid --g value. Using Flux default: {default_flux_guidance:.1f}")

    final_negative_prompt_for_sdxl = negative_prompt_text if model_type == "sdxl" and negative_prompt_text is not None else ""
    if model_type == "sdxl": print(f"  Negative Prompt: {final_negative_prompt_for_sdxl}")

    aspect_ratio_str = "1:1" 
    mp_size_str = settings.get('default_mp_size', "1") 
    original_ar_param_val = params_dict.get('ar')
    mp_param_val = params_dict.get('mp')
    allowed_mp_sizes = ["0.25", "0.5", "1", "1.25", "1.5", "1.75", "2", "2.5", "3", "4"]

    if not is_img2img: 
        if original_ar_param_val and original_ar_param_val is not True:
            if re.match(r'^\d+\s*:\s*\d+$', original_ar_param_val):
                aspect_ratio_str = original_ar_param_val
            else:
                return None, None, f"Invalid AR format '{original_ar_param_val}'. Use W:H (e.g., 16:9).", None
        if mp_param_val and mp_param_val is not True:
             if str(mp_param_val) in allowed_mp_sizes:
                 mp_size_str = str(mp_param_val)
        else: 
            current_settings_mp_size = settings.get('default_mp_size', "1")
            mp_size_str = current_settings_mp_size if current_settings_mp_size in allowed_mp_sizes else "1"
    else: 
        aspect_ratio_str = "From Image" 
        mp_size_str = "N/A"

    image_source_for_node = None 
    img_strength_percent_for_job = None
    denoise_for_ksampler = 1.0 

    if is_img2img:
        img_param_str_raw = params_dict.get('img')
        if img_param_str_raw and img_param_str_raw is not True:
            img_param_match = re.match(r'(\d+)\s+(?:"([^"]+)"|(.+))', str(img_param_str_raw).strip())

            if img_param_match:
                try:
                    img_strength_percent_for_job = int(img_param_match.group(1))
                    path_or_url_candidate = img_param_match.group(2) if img_param_match.group(2) else img_param_match.group(3)
                    path_or_url_candidate = path_or_url_candidate.strip().strip('"\'') 

                    if not (0 <= img_strength_percent_for_job <= 100):
                        raise ValueError("Strength must be between 0-100.")

                    if path_or_url_candidate.lower().startswith("http://") or path_or_url_candidate.lower().startswith("https://"):
                        image_source_for_node = path_or_url_candidate 
                        try:
                            head_response = await asyncio.to_thread(requests.head, image_source_for_node, timeout=10, allow_redirects=True)
                            head_response.raise_for_status()
                            content_type = head_response.headers.get('Content-Type', '').lower()
                            if not content_type.startswith('image/'):
                                return None, None, f"Invalid Img2Img URL: The URL does not point to a valid image (Content-Type: {content_type}). Please provide a direct link to an image file.", None
                        except requests.exceptions.Timeout:
                            print(f"Img2Img URL validation failed: Timeout connecting to {image_source_for_node}")
                            return None, None, "Img2Img URL validation failed: Timeout trying to reach the image URL.", None
                        except requests.exceptions.RequestException as e_req:
                            print(f"Img2Img URL validation failed: RequestException {e_req} for {image_source_for_node}")
                            return None, None, f"Img2Img URL validation failed: Could not access the image URL ({str(e_req)}).", None
                        except Exception as e_val:
                            print(f"Img2Img URL validation failed: Unexpected error {e_val} for {image_source_for_node}")
                            traceback.print_exc()
                            return None, None, "Img2Img URL validation failed: An unexpected error occurred while checking the image URL.", None
                    else: 
                        image_source_for_node = os.path.normpath(path_or_url_candidate)
                        if not os.path.exists(image_source_for_node):
                            print(f"Img2Img local path validation failed: Path does not exist: {image_source_for_node}")
                            return None, None, f"Invalid Img2Img path: The local file path '{image_source_for_node}' does not exist.", None
                        if not os.path.isfile(image_source_for_node):
                            print(f"Img2Img local path validation failed: Path is not a file: {image_source_for_node}")
                            return None, None, f"Invalid Img2Img path: '{image_source_for_node}' is not a file.", None
                        
                        allowed_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff') 
                        if not image_source_for_node.lower().endswith(allowed_extensions):
                             print(f"Img2Img local path validation failed: File extension not recognized as image: {image_source_for_node}")
                             return None, None, f"Invalid Img2Img path: File '{os.path.basename(image_source_for_node)}' does not have a common image extension.", None

                    denoise_for_ksampler = round(max(0.0, min(1.0, 1.0 - (img_strength_percent_for_job / 100.0))), 2)
                except Exception as e_img_param:
                    return None, None, f"Invalid --img parameter. Usage: '--img [strength 0-100] [URL_or_FilePath]'. Error: {e_img_param}", None
            else:
                return None, None, "Invalid --img format. Usage: '--img [strength 0-100] [URL_or_FilePath]'. Example: `--img 70 https://example.com/image.png` or `--img 70 \"C:\\path\\to\\image.jpg\"`", None
        else:
            return None, None, "Missing or invalid value for --img parameter. Usage: '--img [strength 0-100] [URL_or_FilePath]'.", None

    default_style_key = f"default_style_{model_type}"
    default_style_from_settings = settings.get(default_style_key, 'off')
    style_to_apply = default_style_from_settings
    style_param_val = params_dict.get('style')
    style_warning_message = None

    if style_param_val and style_param_val is not True: 
        if style_param_val in styles_config: style_to_apply = style_param_val
    elif style_to_apply not in styles_config: 
        style_to_apply = 'off'

    if style_to_apply != 'off':
        style_data = styles_config.get(style_to_apply, {})
        style_model_type = style_data.get('model_type', 'all')
        if style_model_type != 'all' and style_model_type != model_type: # model_type is the CURRENTLY selected model type
            style_warning_message = f"Style '{style_to_apply}' is for {style_model_type.upper()} models only. Your current model is {model_type.upper()}. The style was disabled for this generation."
            print(f"Style Warning for job {job_id}: {style_warning_message}")
            style_to_apply = 'off'

    if model_type == "sdxl":
        steps_for_ksampler = settings.get('sdxl_steps', 26)
    else:
        steps_for_ksampler = settings.get('steps', 32)
        
    default_batch_size_from_settings = settings.get('default_batch_size', 1)

    print(f"  Seed: {seed}, Steps: {steps_for_ksampler}, Guidance: {guidance_to_use:.1f}, Style: {style_to_apply}")
    if not is_img2img: print(f"  AR: {aspect_ratio_str}, MP: {mp_size_str}, Batch: {default_batch_size_from_settings}")
    else: print(f"  Img2Img: Strength {img_strength_percent_for_job}%, Denoise {denoise_for_ksampler:.2f}")

    template_to_use = None
    if model_type == "sdxl":
        template_to_use = sdxl_img2img_prompt if is_img2img else sdxl_prompt_template
    elif model_type == "flux":
        template_to_use = flux_img2img_template if is_img2img else flux_prompt_template
    else: 
        return None, None, f"Internal error: Unknown model_type '{model_type}' for template selection.", None

    modified_prompt = json.loads(json.dumps(template_to_use)) 

    try:
        flux_ksampler_node_id = str(GENERATION_WORKFLOW_STEPS_NODE) 
        flux_clip_text_encode_node_id = "4"
        flux_guidance_node_id = "5"
        flux_latent_node_id = str(GENERATION_LATENT_NODE) 
        flux_lora_node_id_gen = str(PROMPT_LORA_NODE) 
        flux_lora_node_id_img2img = str(IMG2IMG_LORA_NODE) 
        flux_img2img_load_image_node_id = "15" 
        flux_img2img_vae_encode_node_id = "14"

        sdxl_pos_prompt_node_id = str(SDXL_POS_PROMPT_NODE)
        sdxl_neg_prompt_node_id = str(SDXL_NEG_PROMPT_NODE)
        sdxl_ksampler_node_id = str(SDXL_KSAMPLER_NODE)
        sdxl_lora_node_id = str(SDXL_LORA_NODE)
        sdxl_clip_skip_node_id = str(SDXL_CLIP_SKIP_NODE)
        sdxl_latent_node_id = str(SDXL_LATENT_NODE) 
        sdxl_img2img_load_image_node_id = str(SDXL_IMG2IMG_LOAD_IMAGE_NODE) 
        sdxl_img2img_vae_encode_node_id = str(SDXL_IMG2IMG_VAE_ENCODE_NODE)

        if model_type == "flux":
            current_flux_lora_node_id = flux_lora_node_id_img2img if is_img2img else flux_lora_node_id_gen
            modified_prompt[flux_clip_text_encode_node_id]["inputs"]["text"] = text_for_generation
            modified_prompt[flux_clip_text_encode_node_id]["inputs"]["clip"] = [current_flux_lora_node_id, 1]
            modified_prompt[flux_ksampler_node_id]["inputs"]["seed"] = seed
            modified_prompt[flux_ksampler_node_id]["inputs"]["steps"] = steps_for_ksampler
            modified_prompt[flux_ksampler_node_id]["inputs"]["model"] = [current_flux_lora_node_id, 0]
            modified_prompt[flux_guidance_node_id]["inputs"]["guidance"] = guidance_to_use

            if is_img2img:
                modified_prompt[flux_ksampler_node_id]["inputs"]["denoise"] = denoise_for_ksampler
                modified_prompt[flux_img2img_load_image_node_id]["inputs"]["url_or_path"] = image_source_for_node 
                modified_prompt[flux_ksampler_node_id]["inputs"]["latent_image"] = [flux_img2img_vae_encode_node_id, 0]
            else: 
                modified_prompt[flux_ksampler_node_id]["inputs"]["denoise"] = 1.0
                if flux_latent_node_id in modified_prompt and "inputs" in modified_prompt[flux_latent_node_id]:
                    modified_prompt[flux_latent_node_id]["inputs"].update({
                        "aspect_ratio": aspect_ratio_str,
                        "mp_size_float": mp_size_str,
                        "model_type": "FLUX", 
                        "batch_size": default_batch_size_from_settings 
                    })
                    modified_prompt[flux_ksampler_node_id]["inputs"]["latent_image"] = [flux_latent_node_id, 0]
                else: raise KeyError(f"Flux latent node {flux_latent_node_id} or its inputs not found for Text2Img.")

        elif model_type == "sdxl":
            modified_prompt[sdxl_clip_skip_node_id]["inputs"]["clip"] = [sdxl_lora_node_id, 1]
            modified_prompt[sdxl_pos_prompt_node_id]["inputs"]["text"] = text_for_generation
            modified_prompt[sdxl_pos_prompt_node_id]["inputs"]["clip"] = [sdxl_clip_skip_node_id, 0]
            modified_prompt[sdxl_neg_prompt_node_id]["inputs"]["text"] = final_negative_prompt_for_sdxl
            modified_prompt[sdxl_neg_prompt_node_id]["inputs"]["clip"] = [sdxl_clip_skip_node_id, 0]
            modified_prompt[sdxl_ksampler_node_id]["inputs"].update({
                "seed": seed, "steps": steps_for_ksampler, "cfg": guidance_to_use,
                "model": [sdxl_lora_node_id, 0]
            })

            if is_img2img: 
                modified_prompt[sdxl_img2img_load_image_node_id]["inputs"]["url_or_path"] = image_source_for_node 
                modified_prompt[sdxl_ksampler_node_id]["inputs"]["denoise"] = denoise_for_ksampler
                modified_prompt[sdxl_ksampler_node_id]["inputs"]["latent_image"] = [sdxl_img2img_vae_encode_node_id, 0]
            else: 
                modified_prompt[sdxl_ksampler_node_id]["inputs"]["denoise"] = 1.0
                if sdxl_latent_node_id in modified_prompt and "inputs" in modified_prompt[sdxl_latent_node_id]:
                    modified_prompt[sdxl_latent_node_id]["inputs"].update({
                        "aspect_ratio": aspect_ratio_str,
                        "mp_size_float": mp_size_str,
                        "model_type": "SDXL", 
                        "batch_size": default_batch_size_from_settings 
                    })
                    modified_prompt[sdxl_ksampler_node_id]["inputs"]["latent_image"] = [sdxl_latent_node_id, 0]
                else: raise KeyError(f"SDXL latent node {sdxl_latent_node_id} or its inputs not found for Text2Img.")
    except KeyError as e_key:
        print(f"ERROR (KeyError) during core input application: {e_key}"); traceback.print_exc()
        return None, None, f"Internal Error: Template invalid (KeyError: {e_key}).", None
    except Exception as e_core:
        print(f"ERROR (General) during core input application: {e_core}"); traceback.print_exc()
        return None, None, "Internal Error: Failed to apply prompt inputs (core section).", None

    try:
        os.makedirs(GENERATIONS_DIR, exist_ok=True)
        # Standardized prefix based on operation type, not model type
        filename_prefix_base = "GEN_I2I_" if is_img2img else "GEN_"
        
        filename_prefix_full = normalize_path_for_comfyui(os.path.join(GENERATIONS_DIR, f"{filename_prefix_base}{job_id}"))
        
        save_node_id_final = str(SDXL_SAVE_IMAGE_NODE) if model_type == "sdxl" else "7" 
            
        if save_node_id_final in modified_prompt and "inputs" in modified_prompt[save_node_id_final]:
             modified_prompt[save_node_id_final]["inputs"]["filename_prefix"] = filename_prefix_full
        else: print(f"Warning: SaveImage node ({save_node_id_final}) or its inputs missing/invalid in template.")
    except OSError as e_os:
        print(f"ERROR (OSError) during filename prefix application: {e_os}"); traceback.print_exc()
        return None, None, "Error setting output directory.", None
    except Exception as e_fn:
        print(f"ERROR (General) during filename prefix application: {e_fn}"); traceback.print_exc()
        return None, None, "Error processing output filename.", None

    try:
        comfy_models_data = check_available_models_api(suppress_summary_print=True)
        comfy_unet_list_lower = {m.lower() for m in comfy_models_data.get("unet", []) if isinstance(m, str)}
        comfy_checkpoint_list_lower = {m.lower() for m in comfy_models_data.get("checkpoint", []) if isinstance(m, str)}
        
        is_actual_model_valid_in_comfy = False
        if model_type == "flux" and actual_model_name: is_actual_model_valid_in_comfy = actual_model_name.lower() in comfy_unet_list_lower
        elif model_type == "sdxl" and actual_model_name: is_actual_model_valid_in_comfy = actual_model_name.lower() in comfy_checkpoint_list_lower

        model_applied_successfully = False
        if is_actual_model_valid_in_comfy and actual_model_name:
            model_loader_node_id_target = str(SDXL_CHECKPOINT_LOADER_NODE) if model_type == "sdxl" else str(GENERATION_MODEL_NODE) 
            if model_loader_node_id_target in modified_prompt:
                # selected_model_name_with_prefix IS the current setting (e.g. "Flux: model.gguf")
                model_node_update_dict = get_model_node(selected_model_name_with_prefix, model_loader_node_id_target)
                if model_loader_node_id_target in model_node_update_dict:
                     modified_prompt[model_loader_node_id_target] = model_node_update_dict[model_loader_node_id_target]
                     model_applied_successfully = True

        if model_type == "flux": 
            sel_t5_clip = settings.get('selected_t5_clip'); sel_clip_l = settings.get('selected_clip_l')
            comfy_clip_list_lower = {m.lower() for m in comfy_models_data.get("clip", []) if isinstance(m, str)}
            valid_t5 = sel_t5_clip and sel_t5_clip.lower() in comfy_clip_list_lower
            valid_cl = sel_clip_l and sel_clip_l.lower() in comfy_clip_list_lower
            if valid_t5 and valid_cl:
                flux_clip_loader_node_id = str(GENERATION_CLIP_NODE) 
                if flux_clip_loader_node_id in modified_prompt and "inputs" in modified_prompt[flux_clip_loader_node_id]:
                    modified_prompt[flux_clip_loader_node_id]["inputs"].update({"clip_name1": sel_t5_clip, "clip_name2": sel_clip_l})
    except Exception as e_model_clip:
        print(f"ERROR during model/CLIP application: {e_model_clip}"); traceback.print_exc()
        return None, None, "Internal Error: Failed during model/CLIP setup.", None
    
    try:
        lora_node_key_final = None
        if model_type == "flux":
            lora_node_key_final = flux_lora_node_id_img2img if is_img2img else flux_lora_node_id_gen
        elif model_type == "sdxl":
            lora_node_key_final = sdxl_lora_node_id 

        if lora_node_key_final and lora_node_key_final in modified_prompt:
            if "inputs" not in modified_prompt[lora_node_key_final] or not isinstance(modified_prompt[lora_node_key_final]["inputs"], dict):
                print(f"  ERROR: LoRA node '{lora_node_key_final}' is missing 'inputs' dictionary or it's not a dict.")
            else:
                lora_inputs_dict = modified_prompt[lora_node_key_final]["inputs"]
                
                if style_to_apply != 'off':
                    current_style_config = styles_config.get(style_to_apply, {})
                    if not isinstance(current_style_config, dict): current_style_config = {}
                    
                    for i in range(1, 6):
                        lora_slot_key = f"lora_{i}"
                        if lora_slot_key in lora_inputs_dict:
                            slot_data_from_style = current_style_config.get(lora_slot_key, {})
                            
                            on_val = slot_data_from_style.get("on", False)
                            lora_name_val = slot_data_from_style.get("lora", "None")
                            lora_strength_val = float(slot_data_from_style.get("strength", 0.0))
                            
                            if not isinstance(lora_inputs_dict.get(lora_slot_key), dict):
                                lora_inputs_dict[lora_slot_key] = {}
                            
                            lora_inputs_dict[lora_slot_key].update({
                                "on": on_val,
                                "lora": lora_name_val,
                                "strength": lora_strength_val
                            })
                else: 
                    for i in range(1, 6):
                        lora_slot_key = f"lora_{i}"
                        if lora_slot_key in lora_inputs_dict:
                            if not isinstance(lora_inputs_dict.get(lora_slot_key), dict):
                                lora_inputs_dict[lora_slot_key] = {}
                            lora_inputs_dict[lora_slot_key].update({
                                "on": False,
                                "lora": "None",
                                "strength": 0.0
                            })
    except Exception as e_lora:
        print(f"ERROR applying style LoRAs: {e_lora}"); traceback.print_exc()
        return None, None, "Internal Error: Failed during LoRA application.", None
    
    final_batch_size_for_job_details = 1 
    if not is_img2img: 
        latent_node_id_for_batch_check = sdxl_latent_node_id if model_type == "sdxl" else flux_latent_node_id
        if latent_node_id_for_batch_check in modified_prompt and \
           isinstance(modified_prompt.get(latent_node_id_for_batch_check), dict) and \
           isinstance(modified_prompt[latent_node_id_for_batch_check].get("inputs"), dict):
            try:
                final_batch_size_for_job_details = int(modified_prompt[latent_node_id_for_batch_check]["inputs"].get("batch_size", default_batch_size_from_settings))
            except (ValueError, TypeError):
                final_batch_size_for_job_details = default_batch_size_from_settings
        else: 
            final_batch_size_for_job_details = default_batch_size_from_settings

    job_details_dict = {
        "job_id": job_id,
        "prompt": text_for_generation, 
        "negative_prompt": final_negative_prompt_for_sdxl if model_type == "sdxl" else None,
        "seed": seed,
        "guidance": guidance_to_use if model_type == "flux" else None,
        "guidance_sdxl": guidance_to_use if model_type == "sdxl" else None,
        "steps": steps_for_ksampler,
        "width": "N/A", "height": "N/A", 
        "aspect_ratio_str": aspect_ratio_str, 
        "mp_size": mp_size_str if not is_img2img else "N/A", 
        "original_ar_param": original_ar_param_val, 
        "image_url": image_source_for_node, 
        "img_strength_percent": img_strength_percent_for_job, 
        "denoise": denoise_for_ksampler, 
        "style": style_to_apply,
        "batch_size": final_batch_size_for_job_details, 
        "selected_model": selected_model_name_with_prefix, # This is the CURRENTLY selected model from settings
        "sel_t5": settings.get('selected_t5_clip'), 
        "sel_cl": settings.get('selected_clip_l'),   
        "parameters_used": params_dict, 
        "model_used": actual_model_name or "Unknown/Template Default", # actual_model_name is from CURRENT setting
        "t5_clip_used": settings.get('selected_t5_clip') if model_type == "flux" else "N/A",
        "clip_l_used": settings.get('selected_clip_l') if model_type == "flux" else "N/A",
        "type": "img2img" if is_img2img else "generate",
        "model_type_for_enhancer": model_type, # This is the model_type used for THIS job
        "enhancer_used": enhancer_info.get('used', False),
        "llm_provider": enhancer_info.get('provider'),
        "original_prompt": original_prompt_text, 
        "enhanced_prompt": enhancer_info.get('enhanced_text'), 
        "enhancer_error": enhancer_info.get('error'),
        "style_warning_message": style_warning_message
    }
    status_message_for_user = f"Prompt prepared for job {job_id} ({model_type.upper()}{' Img2Img' if is_img2img else ' Text2Img'})."
    return job_id, modified_prompt, status_message_for_user, job_details_dict
# --- END OF FILE image_generation.py ---
