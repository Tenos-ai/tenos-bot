import json
import random
import uuid
import re
import os
import requests
import traceback
import math

from queue_manager import queue_manager

from prompt_templates import (
    weakvary_prompt as flux_weakvary_template,
    strongvary_prompt as flux_strongvary_template,
    sdxl_variation_prompt,
    VARIATION_MODEL_NODE as FLUX_VAR_BASE_MODEL_NODE,
    VARIATION_WORKFLOW_STEPS_NODE as FLUX_VAR_KSAMPLER_NODE,
    VARIATION_CLIP_NODE as FLUX_VAR_CLIP_NODE,
    VARY_LORA_NODE as FLUX_VAR_LORA_NODE,
    SDXL_CHECKPOINT_LOADER_NODE as SDXL_VAR_BASE_MODEL_NODE,
    SDXL_VAR_LORA_NODE,
    SDXL_VAR_LOAD_IMAGE_NODE,
    SDXL_VAR_RESIZE_NODE,
    SDXL_VAR_VAE_ENCODE_NODE,
    SDXL_VAR_CLIP_SKIP_NODE,
    SDXL_VAR_POS_PROMPT_NODE,
    SDXL_VAR_NEG_PROMPT_NODE,
    SDXL_VAR_KSAMPLER_NODE,
    SDXL_VAR_VAE_DECODE_NODE,
    SDXL_VAR_SAVE_IMAGE_NODE
)
from utils.seed_utils import generate_seed
from settings_manager import load_settings, load_styles_config, _get_default_settings
from modelnodes import get_model_node
from upscaling import get_image_dimensions 
from comfyui_api import get_available_comfyui_models as check_available_models_api

try:
    if not os.path.exists('config.json'):
        raise FileNotFoundError("config.json not found in variation.py.")
    with open('config.json', 'r') as config_file:
        config_data_var = json.load(config_file)
    if not isinstance(config_data_var, dict):
         raise ValueError("config.json is not a valid dictionary in variation.py.")
    VARIATIONS_DIR = config_data_var.get('OUTPUTS', {}).get('VARIATIONS', os.path.join('output','TENOSAI-BOT','VARIATIONS'))
    if not isinstance(VARIATIONS_DIR, str) or not VARIATIONS_DIR:
        print("Warning: Invalid 'VARIATIONS' path in config (variation.py). Using default.")
        VARIATIONS_DIR = os.path.join('output','TENOSAI-BOT','VARIATIONS')
    if not os.path.isabs(VARIATIONS_DIR):
        VARIATIONS_DIR = os.path.abspath(VARIATIONS_DIR)
except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError) as e:
    print(f"Error loading config.json in variation.py: {e}")
    config_data_var = {"OUTPUTS": {}}
    VARIATIONS_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','VARIATIONS'))
except Exception as e:
    print(f"Unexpected error loading config.json in variation.py: {e}")
    traceback.print_exc()
    config_data_var = {"OUTPUTS": {}}
    VARIATIONS_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','VARIATIONS'))

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

def modify_variation_prompt(
    message_content_or_obj,
    referenced_message,
    variation_type: str,
    target_image_url: str,
    image_index: int = 1,
    edited_prompt: str | None = None,
    edited_negative_prompt: str | None = None
):
    settings = load_settings()
    styles_config = load_styles_config() 
    variation_job_id = str(uuid.uuid4())[:8]

    base_model_type_for_variation_workflow = "flux"
    actual_base_model_filename_for_variation = None
    selected_base_model_setting = settings.get('selected_model')

    if selected_base_model_setting and isinstance(selected_base_model_setting, str):
        selected_base_model_stripped = selected_base_model_setting.strip()
        if ":" in selected_base_model_stripped:
            prefix, name = selected_base_model_stripped.split(":", 1)
            base_model_type_for_variation_workflow = prefix.strip().lower()
            actual_base_model_filename_for_variation = name.strip()
        else:
            actual_base_model_filename_for_variation = selected_base_model_stripped
            if actual_base_model_filename_for_variation.endswith((".gguf", ".sft")):
                base_model_type_for_variation_workflow = "flux"
            else:
                base_model_type_for_variation_workflow = "sdxl"
    else:
        print("Variation: No model selected in settings. Defaulting to Flux (this might cause issues).")
        default_settings = _get_default_settings()
        fallback_model_setting = default_settings.get('selected_model')
        if fallback_model_setting and isinstance(fallback_model_setting, str):
             selected_base_model_stripped = fallback_model_setting.strip()
             if ":" in selected_base_model_stripped:
                prefix, name = selected_base_model_stripped.split(":", 1)
                base_model_type_for_variation_workflow = prefix.strip().lower()
                actual_base_model_filename_for_variation = name.strip()
    
    model_name_to_print_in_log = actual_base_model_filename_for_variation if actual_base_model_filename_for_variation else "Settings Default (or ComfyUI Default)"
    print(f"Variation job {variation_job_id}: Using CURRENTLY SELECTED model type '{base_model_type_for_variation_workflow.upper()}' and model '{model_name_to_print_in_log}'.")

    original_job_data = queue_manager.get_job_data(referenced_message.id, referenced_message.channel.id)
    if not original_job_data and referenced_message.attachments:
        from file_management import extract_job_id
        job_id_from_filename = extract_job_id(referenced_message.attachments[0].filename)
        if job_id_from_filename:
            original_job_data = queue_manager.get_job_data_by_id(job_id_from_filename)

    original_prompt_text_unenhanced = None
    prompt_for_variation_node = " " 
    original_style_from_source = "off"
    original_image_width_val = 1024 
    original_image_height_val = 1024 
    original_aspect_ratio_str_from_source = "1:1"
    source_job_id_for_tracking_var = "unknownSrc"
    variation_job_steps = settings.get('steps', 32)
    variation_job_guidance_flux = settings.get('default_guidance', 3.5)
    variation_job_guidance_sdxl = settings.get('default_guidance_sdxl', 7.0)
    original_unenhanced_prompt_from_source = None

    if original_job_data:
        original_unenhanced_prompt_from_source = original_job_data.get('original_prompt')
        prompt_for_variation_node = original_job_data.get('enhanced_prompt') or \
                                    original_unenhanced_prompt_from_source or \
                                    original_job_data.get('prompt', " ") 
        original_style_from_source = original_job_data.get('style', original_style_from_source)
        
        width_from_job = original_job_data.get('width') or original_job_data.get('original_width')
        height_from_job = original_job_data.get('height') or original_job_data.get('original_height')
        try: original_image_width_val = int(width_from_job)
        except (ValueError, TypeError): original_image_width_val = None
        try: original_image_height_val = int(height_from_job)
        except (ValueError, TypeError): original_image_height_val = None

        if original_image_width_val is None or original_image_height_val is None:
            dimensions = get_image_dimensions(target_image_url)
            if dimensions: original_image_width_val, original_image_height_val = dimensions
            else:
                original_image_width_val = 1024; original_image_height_val = 1024
                print(f"Variation: Failed to get dimensions from job data or URL. Defaulting to {original_image_width_val}x{original_image_height_val}.")

        source_job_id_for_tracking_var = original_job_data.get("job_id", source_job_id_for_tracking_var)
        
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
            original_image_width_val = 1024; original_image_height_val = 1024
            original_aspect_ratio_str_from_source = "1:1"
            print(f"Variation: No job data and failed to get dimensions from URL. Defaulting to {original_image_width_val}x{original_image_height_val}.")
    
    if edited_prompt is not None:
        prompt_for_variation_node = edited_prompt.strip() if edited_prompt.strip() else " "

    variation_seed = generate_seed()
    style_for_this_variation = original_style_from_source
    
    if edited_prompt is None and isinstance(message_content_or_obj, str):
        style_match_reply = re.search(r'--style\s+([\w-]+)', message_content_or_obj, re.IGNORECASE)
        if style_match_reply:
            requested_style_reply = style_match_reply.group(1) 
            if requested_style_reply in styles_config: style_for_this_variation = requested_style_reply
    if style_for_this_variation not in styles_config: style_for_this_variation = "off"

    style_warning_message_var = None
    if style_for_this_variation != 'off':
        style_data_var = styles_config.get(style_for_this_variation, {})
        style_model_type_var = style_data_var.get('model_type', 'all')
        if style_model_type_var != 'all' and style_model_type_var != base_model_type_for_variation_workflow:
            style_warning_message_var = f"Style '{style_for_this_variation}' is for {style_model_type_var.upper()} models. Variation uses {base_model_type_for_variation_workflow.upper()}. Style disabled."
            print(f"Style Warning for variation job {variation_job_id}: {style_warning_message_var}")
            style_for_this_variation = 'off'

    final_negative_prompt_for_sdxl_variation = ""
    if base_model_type_for_variation_workflow == "sdxl":
        if edited_negative_prompt is not None:
            final_negative_prompt_for_sdxl_variation = edited_negative_prompt.strip()
        elif original_job_data and original_job_data.get('negative_prompt') is not None: 
            final_negative_prompt_for_sdxl_variation = original_job_data.get('negative_prompt', "")
        else: 
            final_negative_prompt_for_sdxl_variation = settings.get('default_sdxl_negative_prompt', "")
    
    denoise_for_ksampler_variation = 0.48 if variation_type == 'weak' else 0.75

    template_to_use = None
    if base_model_type_for_variation_workflow == "sdxl": template_to_use = sdxl_variation_prompt
    else: template_to_use = flux_weakvary_template if variation_type == 'weak' else flux_strongvary_template
    modified_variation_prompt = json.loads(json.dumps(template_to_use))

    if base_model_type_for_variation_workflow == "flux":
        modified_variation_prompt["8"]["inputs"]["text"] = prompt_for_variation_node 
        modified_variation_prompt["33"]["inputs"]["url_or_path"] = target_image_url
        modified_variation_prompt[str(FLUX_VAR_KSAMPLER_NODE)]["inputs"]["seed"] = variation_seed
        modified_variation_prompt[str(FLUX_VAR_KSAMPLER_NODE)]["inputs"]["denoise"] = denoise_for_ksampler_variation
        modified_variation_prompt[str(FLUX_VAR_KSAMPLER_NODE)]["inputs"]["steps"] = variation_job_steps 
        if "5" in modified_variation_prompt and "inputs" in modified_variation_prompt["5"] and "guidance" in modified_variation_prompt["5"]["inputs"]:
            modified_variation_prompt["5"]["inputs"]["guidance"] = variation_job_guidance_flux
    elif base_model_type_for_variation_workflow == "sdxl":
        modified_variation_prompt[str(SDXL_VAR_POS_PROMPT_NODE)]["inputs"]["text"] = prompt_for_variation_node
        modified_variation_prompt[str(SDXL_VAR_NEG_PROMPT_NODE)]["inputs"]["text"] = final_negative_prompt_for_sdxl_variation
        modified_variation_prompt[str(SDXL_VAR_LOAD_IMAGE_NODE)]["inputs"]["url_or_path"] = target_image_url
        modified_variation_prompt[str(SDXL_VAR_KSAMPLER_NODE)]["inputs"]["seed"] = variation_seed
        modified_variation_prompt[str(SDXL_VAR_KSAMPLER_NODE)]["inputs"]["denoise"] = denoise_for_ksampler_variation
        modified_variation_prompt[str(SDXL_VAR_KSAMPLER_NODE)]["inputs"]["steps"] = variation_job_steps 
        modified_variation_prompt[str(SDXL_VAR_KSAMPLER_NODE)]["inputs"]["cfg"] = variation_job_guidance_sdxl 

    os.makedirs(VARIATIONS_DIR, exist_ok=True)
    variation_char = variation_type[0].upper()
    filename_suffix_detail_var = f"_{variation_char}_from_img{image_index}_srcID{source_job_id_for_tracking_var}"
    # Standardized prefix for variations
    file_prefix_base_var = "GEN_VAR_"
    final_filename_prefix_var = normalize_path_for_comfyui(
        os.path.join(VARIATIONS_DIR, f"{file_prefix_base_var}{variation_job_id}{filename_suffix_detail_var}")
    )
    save_node_id_var = str(SDXL_VAR_SAVE_IMAGE_NODE) if base_model_type_for_variation_workflow == "sdxl" else "34"
    if save_node_id_var in modified_variation_prompt:
        modified_variation_prompt[save_node_id_var]["inputs"]["filename_prefix"] = final_filename_prefix_var

    if actual_base_model_filename_for_variation:
        base_model_loader_node_id_var = str(SDXL_VAR_BASE_MODEL_NODE) if base_model_type_for_variation_workflow == "sdxl" else str(FLUX_VAR_BASE_MODEL_NODE)
        if base_model_loader_node_id_var in modified_variation_prompt:
            try:
                prefixed_base_model_name_for_get_node = f"{base_model_type_for_variation_workflow.capitalize()}: {actual_base_model_filename_for_variation}"
                model_node_update_dict_var = get_model_node(prefixed_base_model_name_for_get_node, base_model_loader_node_id_var)
                if base_model_loader_node_id_var in model_node_update_dict_var:
                    modified_variation_prompt[base_model_loader_node_id_var] = model_node_update_dict_var[base_model_loader_node_id_var]
            except Exception as e_base_model_var:
                print(f"Error setting variation base model (from current setting '{actual_base_model_filename_for_variation}'): {e_base_model_var}")
                traceback.print_exc()

    if base_model_type_for_variation_workflow == "flux":
        sel_t5_clip_var = settings.get('selected_t5_clip'); sel_clip_l_var = settings.get('selected_clip_l')
        flux_clip_node_id_var = str(FLUX_VAR_CLIP_NODE)
        if sel_t5_clip_var and sel_clip_l_var and flux_clip_node_id_var in modified_variation_prompt:
            if "inputs" in modified_variation_prompt[flux_clip_node_id_var]:
                 modified_variation_prompt[flux_clip_node_id_var]["inputs"].update({"clip_name1": sel_t5_clip_var, "clip_name2": sel_clip_l_var})

    lora_loader_node_id_for_var_style = str(SDXL_VAR_LORA_NODE) if base_model_type_for_variation_workflow == "sdxl" else str(FLUX_VAR_LORA_NODE)
    if lora_loader_node_id_for_var_style in modified_variation_prompt:
        if isinstance(modified_variation_prompt[lora_loader_node_id_for_var_style].get("inputs"), dict):
            lora_inputs_dict_var = modified_variation_prompt[lora_loader_node_id_for_var_style]["inputs"]
            if base_model_type_for_variation_workflow == "flux":
                lora_inputs_dict_var["model"] = [str(FLUX_VAR_BASE_MODEL_NODE), 0]
                lora_inputs_dict_var["clip"] = [str(FLUX_VAR_CLIP_NODE), 0]
            elif base_model_type_for_variation_workflow == "sdxl":
                lora_inputs_dict_var["model"] = [str(SDXL_VAR_BASE_MODEL_NODE), 0]
                lora_inputs_dict_var["clip"] = [str(SDXL_VAR_BASE_MODEL_NODE), 1]
            
            if style_for_this_variation != 'off':
                style_data_loras_var = styles_config.get(style_for_this_variation, {})
                for i in range(1, 6):
                    lk_var, lsc_var = f"lora_{i}", style_data_loras_var.get(f"lora_{i}")
                    if lk_var in lora_inputs_dict_var: 
                        on_var = isinstance(lsc_var,dict) and lsc_var.get('on',False)
                        ln_var = lsc_var.get('lora', "None") if isinstance(lsc_var,dict) else "None"
                        ls_var = float(lsc_var.get('strength',0.0)) if isinstance(lsc_var,dict) else 0.0
                        if not isinstance(lora_inputs_dict_var.get(lk_var), dict):
                             lora_inputs_dict_var[lk_var] = {} 
                        lora_inputs_dict_var[lk_var].update({"on": on_var, "lora": ln_var, "strength": ls_var})
            else: 
                for i in range(1, 6):
                    lk_var = f"lora_{i}"
                    if lk_var in lora_inputs_dict_var:
                        if not isinstance(lora_inputs_dict_var.get(lk_var), dict):
                            lora_inputs_dict_var[lk_var] = {}
                        lora_inputs_dict_var[lk_var].update({"on": False, "lora": "None", "strength": 0.0})
    
    variation_desc_full_str_var = "Weak" if variation_type == 'weak' else "Strong"
    response_status_msg_var = f"{variation_desc_full_str_var} variation ({base_model_type_for_variation_workflow.upper()}) queued for image #{image_index}."
    
    enhancer_ref_text = ""
    if source_job_id_for_tracking_var and source_job_id_for_tracking_var != 'unknownSrc':
        source_job_data_enh = queue_manager.get_job_data_by_id(source_job_id_for_tracking_var)
        if source_job_data_enh and source_job_data_enh.get('enhancer_used'):
            provider_enh = source_job_data_enh.get('llm_provider', "LLM").capitalize()
            enhancer_ref_text = f"\n> `(Based on Enhanced Prompt via {provider_enh})`"

    job_details_dict_var = {
        "job_id": variation_job_id, "prompt": prompt_for_variation_node,
        "original_prompt": original_unenhanced_prompt_from_source,
        "enhanced_prompt": original_job_data.get('enhanced_prompt') if original_job_data else None,
        "negative_prompt": final_negative_prompt_for_sdxl_variation if base_model_type_for_variation_workflow == "sdxl" else None,
        "seed": variation_seed, "steps": variation_job_steps, 
        "guidance": variation_job_guidance_flux if base_model_type_for_variation_workflow == 'flux' else None, 
        "guidance_sdxl": variation_job_guidance_sdxl if base_model_type_for_variation_workflow == 'sdxl' else None, 
        "image_url": target_image_url, 
        "original_width": original_image_width_val, "original_height": original_image_height_val,
        "aspect_ratio_str": original_aspect_ratio_str_from_source,
        "variation_type": variation_type, "style": style_for_this_variation, "image_index": image_index,
        "type": "variation", 
        "model_type_for_enhancer": base_model_type_for_variation_workflow, 
        "batch_size": 1,
        "enhancer_reference_text": enhancer_ref_text,
        "style_warning_message": style_warning_message_var,
        "parameters_used": { 
            "seed": variation_seed, "style": style_for_this_variation, 
            "denoise": denoise_for_ksampler_variation, "variation_strength": variation_type,
            "base_model_type_workflow": base_model_type_for_variation_workflow, 
            "base_model_filename": actual_base_model_filename_for_variation,
            "source_job_id": source_job_id_for_tracking_var
        }
    }
    return variation_job_id, modified_variation_prompt, response_status_msg_var, job_details_dict_var

def modify_weak_variation_prompt(message_content_or_obj, referenced_message, target_image_url: str, image_index: int = 1, edited_prompt: str | None = None, edited_negative_prompt: str | None = None):
    return modify_variation_prompt(message_content_or_obj, referenced_message, "weak", target_image_url, image_index, edited_prompt, edited_negative_prompt)

def modify_strong_variation_prompt(message_content_or_obj, referenced_message, target_image_url: str, image_index: int = 1, edited_prompt: str | None = None, edited_negative_prompt: str | None = None):
    return modify_variation_prompt(message_content_or_obj, referenced_message, "strong", target_image_url, image_index, edited_prompt, edited_negative_prompt)
