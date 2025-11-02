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

from model_registry import (
    copy_generation_template,
    get_model_spec,
    resolve_model_type_from_prefix,
)
from utils.seed_utils import parse_seed_from_message, generate_seed
from settings_manager import load_settings, _get_default_settings, load_styles_config
from modelnodes import get_model_node
from comfyui_api import get_available_comfyui_models as check_available_models_api # suppress_summary_print will be passed as True
from utils.llm_enhancer import enhance_prompt


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
    """Update a loader node's filename inputs/widgets when overriding selections."""

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


def _apply_flux_generation_inputs(
    modified_prompt: dict,
    gen_spec,
    *,
    text: str,
    seed: int,
    steps: float,
    guidance: float,
    is_img2img: bool,
    denoise: float,
    image_source: str | None,
    aspect_ratio: str,
    mp_size: str,
    batch_size: int,
):
    prompt_node = gen_spec.prompt_node
    guidance_node = gen_spec.guidance_node
    ksampler_node = gen_spec.ksampler_node
    latent_node = gen_spec.latent_node
    lora_node = gen_spec.lora_node_img2img if is_img2img else gen_spec.lora_node

    modified_prompt[prompt_node]["inputs"]["text"] = text
    modified_prompt[prompt_node]["inputs"]["clip"] = [lora_node, 1]

    ksampler_inputs = modified_prompt[ksampler_node]["inputs"]
    ksampler_inputs.update({
        "seed": seed,
        "steps": steps,
        "model": [lora_node, 0],
        "positive": [prompt_node, 0],
        "negative": [prompt_node, 0],
    })

    modified_prompt[guidance_node]["inputs"]["guidance"] = guidance

    if is_img2img:
        if gen_spec.img2img_load_node:
            modified_prompt[gen_spec.img2img_load_node]["inputs"]["url_or_path"] = image_source
        if gen_spec.img2img_encode_node:
            ksampler_inputs["latent_image"] = [gen_spec.img2img_encode_node, 0]
        ksampler_inputs["denoise"] = denoise
    else:
        latent_inputs = modified_prompt[latent_node]["inputs"]
        latent_inputs.update(
            {
                "aspect_ratio": aspect_ratio,
                "mp_size_float": mp_size,
                "model_type": gen_spec.latent_model_type,
                "batch_size": batch_size,
            }
        )
        ksampler_inputs["denoise"] = 1.0
        ksampler_inputs["latent_image"] = [latent_node, 0]


def _apply_checkpoint_generation_inputs(
    modified_prompt: dict,
    gen_spec,
    *,
    text: str,
    negative_prompt: str,
    seed: int,
    steps: float,
    guidance: float,
    is_img2img: bool,
    denoise: float,
    image_source: str | None,
    aspect_ratio: str,
    mp_size: str,
    batch_size: int,
):
    clip_skip_node = gen_spec.clip_skip_node
    lora_node = gen_spec.lora_node
    pos_prompt_node = gen_spec.pos_prompt_node
    neg_prompt_node = gen_spec.neg_prompt_node
    ksampler_node = gen_spec.ksampler_node
    latent_node = gen_spec.latent_node

    clip_reference = None
    has_lora_node = lora_node and lora_node in modified_prompt

    if clip_skip_node and clip_skip_node in modified_prompt:
        if has_lora_node:
            modified_prompt[clip_skip_node]["inputs"]["clip"] = [lora_node, 1]
        clip_reference = [clip_skip_node, 0]
    elif has_lora_node:
        clip_reference = [lora_node, 1]

    if clip_reference is None and gen_spec.clip_loader_node and gen_spec.clip_loader_node in modified_prompt:
        clip_reference = [gen_spec.clip_loader_node, 0]
    elif clip_reference is None and gen_spec.model_loader_node and gen_spec.model_loader_node in modified_prompt:
        clip_reference = [gen_spec.model_loader_node, 1]

    positive_ref = None
    negative_ref = None

    if pos_prompt_node and pos_prompt_node in modified_prompt and clip_reference:
        modified_prompt[pos_prompt_node]["inputs"].update({"text": text, "clip": clip_reference})
        positive_ref = [pos_prompt_node, 0]

    if neg_prompt_node and neg_prompt_node in modified_prompt and clip_reference:
        modified_prompt[neg_prompt_node]["inputs"].update({"text": negative_prompt, "clip": clip_reference})
        negative_ref = [neg_prompt_node, 0]

    ksampler_inputs = modified_prompt[ksampler_node]["inputs"]
    model_ref = None
    if gen_spec.ksampler_model_ref:
        model_ref = list(gen_spec.ksampler_model_ref)
    elif has_lora_node:
        model_ref = [lora_node, 0]
    elif gen_spec.model_loader_node and gen_spec.model_loader_node in modified_prompt:
        model_ref = [gen_spec.model_loader_node, 0]

    ksampler_inputs.update(
        {
            "seed": seed,
            "steps": steps,
            "cfg": guidance,
        }
    )
    if model_ref:
        ksampler_inputs["model"] = model_ref
    if positive_ref:
        ksampler_inputs["positive"] = positive_ref
    if negative_ref is not None:
        ksampler_inputs["negative"] = negative_ref

    sampling_node_id = None
    if gen_spec.ksampler_model_ref:
        sampling_node_id = str(gen_spec.ksampler_model_ref[0])

    clip_for_sampling = None
    if has_lora_node:
        clip_for_sampling = [lora_node, 1]
    elif gen_spec.clip_loader_node and gen_spec.clip_loader_node in modified_prompt:
        clip_for_sampling = [gen_spec.clip_loader_node, 0]
    elif clip_reference:
        clip_for_sampling = clip_reference

    if sampling_node_id and sampling_node_id in modified_prompt:
        sampling_inputs = modified_prompt[sampling_node_id].setdefault("inputs", {})
        if has_lora_node:
            sampling_inputs["model"] = [lora_node, 0]
        elif gen_spec.model_loader_node and gen_spec.model_loader_node in modified_prompt:
            sampling_inputs["model"] = [gen_spec.model_loader_node, 0]
        if clip_for_sampling:
            sampling_inputs["clip"] = clip_for_sampling

    if is_img2img:
        if gen_spec.img2img_load_node:
            modified_prompt[gen_spec.img2img_load_node]["inputs"]["url_or_path"] = image_source
        if gen_spec.img2img_encode_node:
            ksampler_inputs["latent_image"] = [gen_spec.img2img_encode_node, 0]
        ksampler_inputs["denoise"] = denoise
    else:
        latent_inputs = modified_prompt[latent_node]["inputs"]
        latent_inputs.update(
            {
                "aspect_ratio": aspect_ratio,
                "mp_size_float": mp_size,
                "model_type": gen_spec.latent_model_type,
                "batch_size": batch_size,
            }
        )
        ksampler_inputs["denoise"] = 1.0
        ksampler_inputs["latent_image"] = [latent_node, 0]
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
    styles_config = load_styles_config()

    model_type, actual_model_name = resolve_model_type_from_prefix(selected_model_name_with_prefix)
    if selected_model_name_with_prefix and model_type not in ("flux", "sdxl", "qwen", "wan"):
        print(f"Warning: Selected model prefix '{selected_model_name_with_prefix}' not recognized. Defaulting to {model_type.upper()}.")
    if not selected_model_name_with_prefix:
        print("image_generation: No model selected in settings. Defaulting to Flux.")

    spec = get_model_spec(model_type)
    defaults = spec.defaults

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
    guidance_to_use = settings.get(defaults.guidance_key, defaults.guidance_fallback)
    param_candidates = [f"g_{model_type}"]
    if model_type == "sdxl":
        param_candidates.insert(0, "g_sdxl")
    elif model_type == "flux":
        param_candidates.insert(0, "g")
    else:
        param_candidates.extend(["g_sdxl", "g"])

    for param_key in param_candidates:
        param_val = params_dict.get(param_key)
        if param_val and param_val is not True:
            try:
                guidance_to_use = float(param_val)
                break
            except (ValueError, TypeError):
                print(f"  Warn: Invalid --{param_key} value. Using default: {guidance_to_use:.2f}")

    final_negative_prompt = ""
    if spec.generation.supports_negative_prompt:
        final_negative_prompt = negative_prompt_text or ""
        if final_negative_prompt:
            print(f"  Negative Prompt: {final_negative_prompt}")

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

    default_style_key = defaults.style_key
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
        if style_model_type != 'all' and style_model_type != model_type:
            style_warning_message = (
                f"Style '{style_to_apply}' is for {style_model_type.upper()} models only. "
                f"Your current model is {model_type.upper()}. The style was disabled for this generation."
            )
            print(f"Style Warning for job {job_id}: {style_warning_message}")
            style_to_apply = 'off'

    steps_for_ksampler = settings.get(defaults.steps_key, defaults.steps_fallback)
        
    default_batch_size_from_settings = settings.get('default_batch_size', 1)

    print(f"  Seed: {seed}, Steps: {steps_for_ksampler}, Guidance: {guidance_to_use:.1f}, Style: {style_to_apply}")
    if not is_img2img: print(f"  AR: {aspect_ratio_str}, MP: {mp_size_str}, Batch: {default_batch_size_from_settings}")
    else: print(f"  Img2Img: Strength {img_strength_percent_for_job}%, Denoise {denoise_for_ksampler:.2f}")

    try:
        modified_prompt = copy_generation_template(spec.generation, is_img2img=is_img2img)
    except Exception as template_error:
        print(f"ERROR copying template for model '{model_type}': {template_error}")
        return None, None, "Internal Error: Failed to prepare workflow template.", None

    try:
        gen_spec = spec.generation
        if gen_spec.family == "flux":
            _apply_flux_generation_inputs(
                modified_prompt,
                gen_spec,
                text=text_for_generation,
                seed=seed,
                steps=steps_for_ksampler,
                guidance=guidance_to_use,
                is_img2img=is_img2img,
                denoise=denoise_for_ksampler,
                image_source=image_source_for_node,
                aspect_ratio=aspect_ratio_str,
                mp_size=mp_size_str,
                batch_size=default_batch_size_from_settings,
            )
        else:
            _apply_checkpoint_generation_inputs(
                modified_prompt,
                gen_spec,
                text=text_for_generation,
                negative_prompt=final_negative_prompt,
                seed=seed,
                steps=steps_for_ksampler,
                guidance=guidance_to_use,
                is_img2img=is_img2img,
                denoise=denoise_for_ksampler,
                image_source=image_source_for_node,
                aspect_ratio=aspect_ratio_str,
                mp_size=mp_size_str,
                batch_size=default_batch_size_from_settings,
            )
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
        
        save_node_id_final = spec.generation.save_node
            
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
        comfy_category_list = {
            key: {m.lower() for m in comfy_models_data.get(key, []) if isinstance(m, str)}
            for key in ("unet", "checkpoint", "clip")
        }

        model_applied_successfully = False
        if actual_model_name and selected_model_name_with_prefix:
            category_key = spec.generation.comfy_category
            available_models = comfy_category_list.get(category_key, set())
            if actual_model_name.lower() in available_models:
                model_loader_node_id_target = spec.generation.model_loader_node
                if model_loader_node_id_target in modified_prompt:
                    model_node_update_dict = get_model_node(selected_model_name_with_prefix, model_loader_node_id_target)
                    if model_loader_node_id_target in model_node_update_dict:
                        modified_prompt[model_loader_node_id_target] = model_node_update_dict[model_loader_node_id_target]
                        model_applied_successfully = True

        if spec.generation.family == "flux":
            sel_t5_clip = settings.get('selected_t5_clip')
            sel_clip_l = settings.get('selected_clip_l')
            comfy_clip_list_lower = comfy_category_list.get("clip", set())
            valid_t5 = sel_t5_clip and sel_t5_clip.lower() in comfy_clip_list_lower
            valid_cl = sel_clip_l and sel_clip_l.lower() in comfy_clip_list_lower
            clip_loader_node_id = spec.generation.clip_loader_node
            if valid_t5 and valid_cl and clip_loader_node_id in modified_prompt and "inputs" in modified_prompt[clip_loader_node_id]:
                modified_prompt[clip_loader_node_id]["inputs"].update({"clip_name1": sel_t5_clip, "clip_name2": sel_clip_l})
        else:
            clip_setting_key = f"default_{model_type}_clip"
            clip_name_override = settings.get(clip_setting_key)
            clip_loader_node_id = spec.generation.clip_loader_node
            if clip_name_override and clip_loader_node_id in modified_prompt:
                clip_inputs = modified_prompt[clip_loader_node_id].setdefault("inputs", {})
                clip_inputs["clip_name"] = clip_name_override

        vae_setting_key = f"default_{model_type}_vae"
        vae_name_override = settings.get(vae_setting_key)
        vae_loader_node_id = getattr(spec.generation, "vae_loader_node", None)
        if vae_name_override and vae_loader_node_id and vae_loader_node_id in modified_prompt:
            vae_inputs = modified_prompt[vae_loader_node_id].setdefault("inputs", {})
            vae_inputs["vae_name"] = vae_name_override

        secondary_node_id = getattr(spec.generation, "secondary_model_loader_node", None)
        secondary_setting_key = getattr(spec.generation, "secondary_model_setting_key", None)
        if secondary_setting_key:
            secondary_override = settings.get(secondary_setting_key)
        else:
            secondary_override = None
        if secondary_override:
            _update_model_loader_filename(
                modified_prompt,
                secondary_node_id,
                file_name=secondary_override,
            )
    except Exception as e_model_clip:
        print(f"ERROR during model/CLIP application: {e_model_clip}"); traceback.print_exc()
        return None, None, "Internal Error: Failed during model/CLIP setup.", None
    
    try:
        lora_node_key_final = None
        gen_spec = spec.generation
        if gen_spec.family == "flux":
            lora_node_key_final = gen_spec.lora_node_img2img if is_img2img else gen_spec.lora_node
        else:
            lora_node_key_final = gen_spec.lora_node

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
        latent_node_id_for_batch_check = spec.generation.latent_node
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
        "negative_prompt": final_negative_prompt if spec.generation.supports_negative_prompt else None,
        "seed": seed,
        "guidance": guidance_to_use,
        "guidance_sdxl": guidance_to_use if model_type == "sdxl" else None,
        "guidance_qwen": guidance_to_use if model_type == "qwen" else None,
        "guidance_wan": guidance_to_use if model_type == "wan" else None,
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
        "model_used": actual_model_name or "Unknown/Template Default",
        "t5_clip_used": settings.get('selected_t5_clip') if spec.generation.family == "flux" else "N/A",
        "clip_l_used": settings.get('selected_clip_l') if spec.generation.family == "flux" else "N/A",
        "type": "img2img" if is_img2img else "generate",
        "model_type_for_enhancer": model_type, # This is the model_type used for THIS job
        "enhancer_used": enhancer_info.get('used', False),
        "llm_provider": enhancer_info.get('provider'),
        "original_prompt": original_prompt_text,
        "enhanced_prompt": enhancer_info.get('enhanced_text'),
        "enhancer_error": enhancer_info.get('error'),
        "style_warning_message": style_warning_message,
        "supports_animation": spec.supports_animation,
        "followup_animation_workflow": "wan_image_to_video" if spec.supports_animation else None,
    }
    status_message_for_user = f"Prompt prepared for job {job_id} ({model_type.upper()}{' Img2Img' if is_img2img else ' Text2Img'})."
    return job_id, modified_prompt, status_message_for_user, job_details_dict
# --- END OF FILE image_generation.py ---
