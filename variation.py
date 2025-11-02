# --- START OF FILE variation.py ---
import json
import random
import uuid
import re
import os
import requests
import traceback
import math

from queue_manager import queue_manager

from model_registry import (
    copy_variation_template,
    get_model_spec,
    resolve_model_type_from_prefix,
)
from utils.seed_utils import generate_seed, calculate_batch_seeds
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


def _update_model_loader_filename(modified_prompt: dict, node_id, *, file_name) -> None:
    """Override loader filenames for secondary UNet updates."""

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


def _apply_flux_variation_inputs(
    modified_prompt: dict,
    var_spec,
    *,
    prompt_text: str,
    image_url: str,
    seed: int,
    steps: int,
    guidance: float,
    denoise: float,
    batch_size: int,
):
    modified_prompt[var_spec.prompt_node]["inputs"]["text"] = prompt_text
    modified_prompt[var_spec.load_image_node]["inputs"]["url_or_path"] = image_url

    ksampler_inputs = modified_prompt[var_spec.ksampler_node]["inputs"]
    ksampler_inputs.update({"seed": seed, "steps": steps, "denoise": denoise})

    if var_spec.guidance_node and var_spec.guidance_node in modified_prompt:
        guidance_node_inputs = modified_prompt[var_spec.guidance_node].get("inputs", {})
        if "guidance" in guidance_node_inputs:
            guidance_node_inputs["guidance"] = guidance

    if var_spec.batch_node and var_spec.batch_node in modified_prompt:
        modified_prompt[var_spec.batch_node]["inputs"]["amount"] = batch_size


def _apply_checkpoint_variation_inputs(
    modified_prompt: dict,
    var_spec,
    *,
    prompt_text: str,
    negative_prompt: str,
    image_url: str,
    seed: int,
    steps: int,
    guidance: float,
    denoise: float,
    batch_size: int,
):
    clip_skip_node = var_spec.clip_skip_node
    lora_node = var_spec.lora_node
    pos_prompt_node = var_spec.pos_prompt_node
    neg_prompt_node = var_spec.neg_prompt_node

    clip_reference = None
    if clip_skip_node and clip_skip_node in modified_prompt:
        if lora_node and lora_node in modified_prompt:
            modified_prompt[clip_skip_node]["inputs"]["clip"] = [lora_node, 1]
        clip_reference = [clip_skip_node, 0]
    elif lora_node and lora_node in modified_prompt:
        clip_reference = [lora_node, 1]
    elif var_spec.clip_loader_node and var_spec.clip_loader_node in modified_prompt:
        clip_reference = [var_spec.clip_loader_node, 0]
    elif var_spec.model_loader_node and var_spec.model_loader_node in modified_prompt:
        clip_reference = [var_spec.model_loader_node, 1]

    if clip_reference and pos_prompt_node and pos_prompt_node in modified_prompt:
        modified_prompt[pos_prompt_node]["inputs"].update({"text": prompt_text, "clip": clip_reference})
    if clip_reference and neg_prompt_node and neg_prompt_node in modified_prompt:
        modified_prompt[neg_prompt_node]["inputs"].update({"text": negative_prompt, "clip": clip_reference})

    modified_prompt[var_spec.load_image_node]["inputs"]["url_or_path"] = image_url

    ksampler_inputs = modified_prompt[var_spec.ksampler_node]["inputs"]
    ksampler_inputs.update({
        "seed": seed,
        "steps": steps,
        "denoise": denoise,
        "cfg": guidance,
    })

    if var_spec.batch_node and var_spec.batch_node in modified_prompt:
        modified_prompt[var_spec.batch_node]["inputs"]["amount"] = batch_size
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
    
    selected_base_model_setting = settings.get('selected_model')
    base_model_type_for_variation_workflow, actual_base_model_filename_for_variation = resolve_model_type_from_prefix(
        selected_base_model_setting if isinstance(selected_base_model_setting, str) else None
    )

    if not selected_base_model_setting:
        print("Variation: No model selected in settings. Defaulting to Flux (this might cause issues).")
        default_settings = _get_default_settings()
        fallback_model_setting = default_settings.get('selected_model')
        if fallback_model_setting and isinstance(fallback_model_setting, str):
            base_model_type_for_variation_workflow, actual_base_model_filename_for_variation = resolve_model_type_from_prefix(
                fallback_model_setting
            )
    
    model_name_to_print_in_log = actual_base_model_filename_for_variation if actual_base_model_filename_for_variation else "Settings Default (or ComfyUI Default)"
    print(f"Variation Request: Using CURRENTLY SELECTED model type '{base_model_type_for_variation_workflow.upper()}' and model '{model_name_to_print_in_log}'.")

    spec = get_model_spec(base_model_type_for_variation_workflow)
    var_spec = spec.variation

    original_job_data = queue_manager.get_job_data(referenced_message.id, referenced_message.channel.id)
    if not original_job_data and referenced_message.attachments:
        from file_management import extract_job_id
        job_id_from_filename = extract_job_id(referenced_message.attachments[0].filename)
        if job_id_from_filename:
            original_job_data = queue_manager.get_job_data_by_id(job_id_from_filename)

    prompt_for_variation_node = " "
    original_prompt_for_log = ""
    enhanced_prompt_from_source = None
    original_style_from_source = "off"
    original_image_width_val = 1024 
    original_image_height_val = 1024 
    original_aspect_ratio_str_from_source = "1:1"
    source_job_id_for_tracking_var = "unknownSrc"
    
    variation_job_steps = settings.get(spec.defaults.steps_key, spec.defaults.steps_fallback)
    variation_job_guidance = settings.get(spec.defaults.guidance_key, spec.defaults.guidance_fallback)
    
    if original_job_data:
        original_prompt_for_log = original_job_data.get('original_prompt', original_job_data.get('prompt', ''))
        enhanced_prompt_from_source = original_job_data.get('enhanced_prompt')
        prompt_for_variation_node = enhanced_prompt_from_source or original_prompt_for_log or " "
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
    
    param_pattern = r'\s--(\w+)(?:\s+("([^"]*)"|((?:(?!--|\s--).)+)|([^\s]+)))?'
    base_seed = generate_seed()
    style_for_this_variation = original_style_from_source
    
    if edited_prompt is not None:
        params_remix = {}
        prompt_base_remix = edited_prompt
        first_param_match_remix = re.search(r'\s--\w+', edited_prompt)
        if first_param_match_remix:
            prompt_base_remix = edited_prompt[:first_param_match_remix.start()].strip()
            param_string_remix = edited_prompt[first_param_match_remix.start():]
            param_matches_remix = re.findall(param_pattern, param_string_remix)
            for key, _, quoted_val, unquoted_compound, unquoted_single in param_matches_remix:
                value = quoted_val if quoted_val else (unquoted_compound if unquoted_compound else unquoted_single)
                params_remix[key.lower()] = value.strip() if value else True

        prompt_for_variation_node = prompt_base_remix.strip() if prompt_base_remix.strip() else " "
        original_prompt_for_log = prompt_for_variation_node # For remixed jobs, the original prompt is what the user typed.

        if 'style' in params_remix and params_remix['style'] in styles_config:
            style_for_this_variation = params_remix['style']
 
        if 'seed' in params_remix:
            try: base_seed = int(params_remix['seed'])
            except (ValueError, TypeError): pass

        if 'steps' in params_remix:
            try: variation_job_steps = int(params_remix['steps'])
            except (ValueError, TypeError): pass

        guidance_value = None
        for guidance_key in ['g','guidance','g_flux','g_sdxl','cfg']:
            if guidance_key in params_remix:
                try: guidance_value = float(params_remix[guidance_key])
                except (ValueError, TypeError): guidance_value = None
                break
        if guidance_value is not None:
            variation_job_guidance = guidance_value
    else: 
        if isinstance(message_content_or_obj, str):
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
            print(f"Style Warning: {style_warning_message_var}")
            style_for_this_variation = 'off'

    final_negative_prompt = ""
    if spec.generation.supports_negative_prompt:
        if edited_negative_prompt is not None:
            final_negative_prompt = edited_negative_prompt.strip()
        elif original_job_data and original_job_data.get('negative_prompt') is not None:
            final_negative_prompt = original_job_data.get('negative_prompt', "")
        else:
            default_neg_key = f"default_{base_model_type_for_variation_workflow}_negative_prompt"
            final_negative_prompt = settings.get(default_neg_key, "")
    
    denoise_for_ksampler_variation = 0.48 if variation_type == 'weak' else 0.75

    batch_size = settings.get('variation_batch_size', 1)
    if not isinstance(batch_size, int) or not (1 <= batch_size <= 4):
        batch_size = 1

    variation_job_id = str(uuid.uuid4())[:8]
    try:
        template_strength = variation_type if variation_type in var_spec.templates else "default"
        modified_variation_prompt = copy_variation_template(var_spec, strength=template_strength)
    except Exception as template_error:
        print(f"ERROR copying variation template for model '{base_model_type_for_variation_workflow}': {template_error}")
        return None, "Internal error preparing variation template.", None

    if var_spec.family == "flux":
        _apply_flux_variation_inputs(
            modified_variation_prompt,
            var_spec,
            prompt_text=prompt_for_variation_node,
            image_url=target_image_url,
            seed=base_seed,
            steps=variation_job_steps,
            guidance=variation_job_guidance,
            denoise=denoise_for_ksampler_variation,
            batch_size=batch_size,
        )
    else:
        _apply_checkpoint_variation_inputs(
            modified_variation_prompt,
            var_spec,
            prompt_text=prompt_for_variation_node,
            negative_prompt=final_negative_prompt,
            image_url=target_image_url,
            seed=base_seed,
            steps=variation_job_steps,
            guidance=variation_job_guidance,
            denoise=denoise_for_ksampler_variation,
            batch_size=batch_size,
        )

    os.makedirs(VARIATIONS_DIR, exist_ok=True)
    variation_char = variation_type[0].upper()
    filename_suffix_detail_var = f"_{variation_char}_from_img{image_index}_srcID{source_job_id_for_tracking_var}"
    file_prefix_base_var = "GEN_VAR_"
    final_filename_prefix_var = normalize_path_for_comfyui(
        os.path.join(VARIATIONS_DIR, f"{file_prefix_base_var}{variation_job_id}{filename_suffix_detail_var}")
    )
    save_node_id_var = var_spec.save_node
    if save_node_id_var in modified_variation_prompt:
        modified_variation_prompt[save_node_id_var]["inputs"]["filename_prefix"] = final_filename_prefix_var

    if actual_base_model_filename_for_variation:
        base_model_loader_node_id_var = var_spec.model_loader_node
        if base_model_loader_node_id_var in modified_variation_prompt:
            try:
                prefixed_model_name = selected_base_model_setting if isinstance(selected_base_model_setting, str) else None
                if not prefixed_model_name:
                    prefixed_model_name = f"{base_model_type_for_variation_workflow.upper()}: {actual_base_model_filename_for_variation}"
                model_node_update_dict_var = get_model_node(prefixed_model_name, base_model_loader_node_id_var)
                if base_model_loader_node_id_var in model_node_update_dict_var:
                    modified_variation_prompt[base_model_loader_node_id_var] = model_node_update_dict_var[base_model_loader_node_id_var]
            except Exception as e_base_model_var:
                print(f"Error setting variation base model (from current setting '{actual_base_model_filename_for_variation}'): {e_base_model_var}")
                traceback.print_exc()

    if var_spec.family == "flux":
        sel_t5_clip_var = settings.get('selected_t5_clip')
        sel_clip_l_var = settings.get('selected_clip_l')
        flux_clip_node_id_var = var_spec.clip_node
        if sel_t5_clip_var and sel_clip_l_var and flux_clip_node_id_var in modified_variation_prompt:
            if "inputs" in modified_variation_prompt[flux_clip_node_id_var]:
                modified_variation_prompt[flux_clip_node_id_var]["inputs"].update({"clip_name1": sel_t5_clip_var, "clip_name2": sel_clip_l_var})
    else:
        clip_setting_key_var = f"default_{base_model_type_for_variation_workflow}_clip"
        clip_override_var = settings.get(clip_setting_key_var)
        clip_loader_node_id_var = var_spec.clip_loader_node
        if clip_override_var and clip_loader_node_id_var and clip_loader_node_id_var in modified_variation_prompt:
            clip_inputs_var = modified_variation_prompt[clip_loader_node_id_var].setdefault("inputs", {})
            clip_inputs_var["clip_name"] = clip_override_var

    vae_setting_key_var = f"default_{base_model_type_for_variation_workflow}_vae"
    vae_override_var = settings.get(vae_setting_key_var)
    vae_loader_node_id_var = var_spec.vae_loader_node
    if vae_override_var and vae_loader_node_id_var and vae_loader_node_id_var in modified_variation_prompt:
        vae_inputs_var = modified_variation_prompt[vae_loader_node_id_var].setdefault("inputs", {})
        vae_inputs_var["vae_name"] = vae_override_var

    secondary_node_id_var = getattr(var_spec, "secondary_model_loader_node", None)
    secondary_setting_key_var = getattr(var_spec, "secondary_model_setting_key", None)
    if secondary_setting_key_var:
        secondary_override_var = settings.get(secondary_setting_key_var)
    else:
        secondary_override_var = None
    if secondary_override_var:
        _update_model_loader_filename(
            modified_variation_prompt,
            secondary_node_id_var,
            file_name=secondary_override_var,
        )

    lora_loader_node_id_for_var_style = var_spec.lora_node
    if lora_loader_node_id_for_var_style in modified_variation_prompt:
        if isinstance(modified_variation_prompt[lora_loader_node_id_for_var_style].get("inputs"), dict):
            lora_inputs_dict_var = modified_variation_prompt[lora_loader_node_id_for_var_style]["inputs"]
            if var_spec.family == "flux":
                lora_inputs_dict_var["model"] = [var_spec.model_loader_node, 0]
                if var_spec.clip_node:
                    lora_inputs_dict_var["clip"] = [var_spec.clip_node, 0]
            else:
                lora_inputs_dict_var["model"] = [var_spec.model_loader_node, 0]
                if var_spec.clip_loader_node and var_spec.clip_loader_node in modified_variation_prompt:
                    lora_inputs_dict_var["clip"] = [var_spec.clip_loader_node, 0]
                else:
                    lora_inputs_dict_var["clip"] = [var_spec.model_loader_node, 1]
            
            if style_for_this_variation != 'off':
                style_data_loras_var = styles_config.get(style_for_this_variation, {})
                for i_lora in range(1, 6):
                    lk_var, lsc_var = f"lora_{i_lora}", style_data_loras_var.get(f"lora_{i_lora}")
                    if lk_var in lora_inputs_dict_var: 
                        on_var = isinstance(lsc_var,dict) and lsc_var.get('on',False)
                        ln_var = lsc_var.get('lora', "None") if isinstance(lsc_var,dict) else "None"
                        ls_var = float(lsc_var.get('strength',0.0)) if isinstance(lsc_var,dict) else 0.0
                        if not isinstance(lora_inputs_dict_var.get(lk_var), dict):
                             lora_inputs_dict_var[lk_var] = {} 
                        lora_inputs_dict_var[lk_var].update({"on": on_var, "lora": ln_var, "strength": ls_var})
            else: 
                for i_lora in range(1, 6):
                    lk_var = f"lora_{i_lora}"
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
        "job_id": variation_job_id,
        "prompt": prompt_for_variation_node,
        "original_prompt": original_prompt_for_log,
        "enhanced_prompt": enhanced_prompt_from_source if edited_prompt is None else None,
        "negative_prompt": final_negative_prompt if spec.generation.supports_negative_prompt else None,
        "seed": base_seed,
        "steps": variation_job_steps,
        "guidance": variation_job_guidance,
        "guidance_sdxl": variation_job_guidance if base_model_type_for_variation_workflow == 'sdxl' else None,
        "guidance_qwen": variation_job_guidance if base_model_type_for_variation_workflow == 'qwen' else None,
        "guidance_wan": variation_job_guidance if base_model_type_for_variation_workflow == 'wan' else None,
        "image_url": target_image_url,
        "original_width": original_image_width_val,
        "original_height": original_image_height_val,
        "aspect_ratio_str": original_aspect_ratio_str_from_source,
        "variation_type": variation_type,
        "style": style_for_this_variation,
        "image_index": image_index,
        "type": "variation",
        "model_type_for_enhancer": base_model_type_for_variation_workflow,
        "batch_size": batch_size,
        "model_used": actual_base_model_filename_for_variation or "Unknown/Template Default",
        "selected_model": selected_base_model_setting if isinstance(selected_base_model_setting, str) else None,
        "enhancer_reference_text": enhancer_ref_text,
        "style_warning_message": style_warning_message_var,
        "supports_animation": spec.supports_animation,
        "followup_animation_workflow": "wan_image_to_video" if spec.supports_animation else None,
        "parameters_used": {
            "seed": base_seed,
            "style": style_for_this_variation,
            "denoise": denoise_for_ksampler_variation,
            "variation_strength": variation_type,
            "negative_prompt": final_negative_prompt if spec.generation.supports_negative_prompt else None,
            "base_model_type_workflow": base_model_type_for_variation_workflow,
            "base_model_filename": actual_base_model_filename_for_variation,
            "source_job_id": source_job_id_for_tracking_var,
            "is_remix": edited_prompt is not None
        }
    }
    return [(variation_job_id, modified_variation_prompt, response_status_msg_var, job_details_dict_var)]


def modify_weak_variation_prompt(message_content_or_obj, referenced_message, target_image_url: str, image_index: int = 1, edited_prompt: str | None = None, edited_negative_prompt: str | None = None):
    return modify_variation_prompt(message_content_or_obj, referenced_message, "weak", target_image_url, image_index, edited_prompt, edited_negative_prompt)

def modify_strong_variation_prompt(message_content_or_obj, referenced_message, target_image_url: str, image_index: int = 1, edited_prompt: str | None = None, edited_negative_prompt: str | None = None):
    return modify_variation_prompt(message_content_or_obj, referenced_message, "strong", target_image_url, image_index, edited_prompt, edited_negative_prompt)
# --- END OF FILE variation.py ---
