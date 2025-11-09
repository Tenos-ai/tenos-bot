import json
import math
import os
import re
import traceback
import uuid

from typing import Iterable, Optional

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


def _sanitize_override(value: Optional[str]) -> Optional[str]:
    """Normalize optional model overrides, stripping whitespace and sentinel values."""

    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    lowered = normalized.lower()
    if lowered in {"none", "auto", "automatic", "default"}:
        return None

    return normalized


_UPSCALE_MODEL_EXTENSIONS = {'.pth', '.pt', '.onnx', '.safetensors', '.ckpt', '.bin'}


def _looks_like_upscale_model(name: Optional[str]) -> bool:
    if not name or not isinstance(name, str):
        return False

    cleaned = name.strip()
    if not cleaned:
        return False

    base = os.path.basename(cleaned)
    stem, ext = os.path.splitext(base)
    if not stem or not ext:
        return False
    return ext.lower() in _UPSCALE_MODEL_EXTENSIONS


def _upscale_model_exists(name: Optional[str]) -> bool:
    if not name or not isinstance(name, str):
        return False

    cleaned = name.strip()
    if not cleaned:
        return False

    candidate_names: set[str] = {cleaned}
    basename = os.path.basename(cleaned)
    if basename:
        candidate_names.add(basename)

    lowercase_candidates = {candidate.lower() for candidate in candidate_names}
    stem_candidates = {
        os.path.splitext(candidate)[0]
        for candidate in lowercase_candidates
    }

    if not UPSCALE_MODELS_ROOT or not os.path.isdir(UPSCALE_MODELS_ROOT):
        # If we cannot inspect the configured directory, assume the caller
        # knows what they are doing to avoid false warnings.
        return any(_looks_like_upscale_model(candidate) for candidate in candidate_names)

    candidate_path = os.path.join(UPSCALE_MODELS_ROOT, basename or cleaned)
    if os.path.exists(candidate_path):
        return True

    for local_entry in get_local_upscale_models():
        normalized_local = local_entry.strip().lower()
        if not normalized_local:
            continue

        if normalized_local in lowercase_candidates:
            return True

        local_stem, _ = os.path.splitext(normalized_local)
        if local_stem and local_stem in stem_candidates:
            return True

    return False


def get_local_upscale_models() -> list[str]:
    """Return discovered upscale models from the configured directory."""

    if not UPSCALE_MODELS_ROOT or not os.path.isdir(UPSCALE_MODELS_ROOT):
        return []

    discovered: list[str] = []
    try:
        for entry in os.listdir(UPSCALE_MODELS_ROOT):
            if not _looks_like_upscale_model(entry):
                continue
            discovered.append(entry)
    except OSError as os_error:
        print(
            "Upscaling: Unable to scan local upscale model directory "
            f"'{UPSCALE_MODELS_ROOT}': {os_error}"
        )
        return []

    normalized = {item.strip() for item in discovered if isinstance(item, str) and item.strip()}
    return sorted(normalized, key=str.lower)


def upscale_model_exists(name: Optional[str]) -> bool:
    """Public helper to confirm whether an upscale model is available locally."""

    if not name:
        return False

    if _upscale_model_exists(name):
        return True

    # Some ComfyUI installations report relative paths instead of just the
    # filename. Check the basename as a final attempt before giving up.
    basename = os.path.basename(name)
    if basename and basename != name:
        return _upscale_model_exists(basename)

    return False


def _resolve_upscale_model_choice(
    preferred: Optional[str],
    template_default: Optional[str],
    available_options: Iterable[str] | None = None,
) -> Optional[str]:
    """Pick the best usable upscale model, falling back to available options."""

    ordered_candidates: list[str] = []

    def _add_candidate(candidate: Optional[str]) -> None:
        if not candidate or not isinstance(candidate, str):
            return
        cleaned = candidate.strip()
        if not cleaned:
            return
        if cleaned not in ordered_candidates:
            ordered_candidates.append(cleaned)

    _add_candidate(preferred)
    _add_candidate(template_default)

    if available_options:
        for option in available_options:
            if not isinstance(option, str):
                continue
            cleaned_option = option.strip()
            if not cleaned_option:
                continue
            if cleaned_option in ordered_candidates:
                continue
            ordered_candidates.append(cleaned_option)

    if UPSCALE_MODELS_ROOT and os.path.isdir(UPSCALE_MODELS_ROOT):
        try:
            for entry in os.listdir(UPSCALE_MODELS_ROOT):
                entry_path = os.path.join(UPSCALE_MODELS_ROOT, entry)
                if not os.path.isfile(entry_path):
                    continue
                if not _looks_like_upscale_model(entry):
                    continue
                if entry not in ordered_candidates:
                    ordered_candidates.append(entry)
        except OSError as os_error:
            print(
                "Upscaling: Unable to read local upscale model directory "
                f"'{UPSCALE_MODELS_ROOT}': {os_error}"
            )

    for candidate in ordered_candidates:
        if _upscale_model_exists(candidate):
            return candidate

    for candidate in ordered_candidates:
        if _looks_like_upscale_model(candidate):
            return candidate

    return None


def _normalize_comfy_option(value: str) -> str:
    """Return a normalized representation for comparing ComfyUI model entries."""

    return os.path.normpath(value).replace("\\", "/").lower()


def _find_matching_model_option(requested: str, options: Iterable[str]) -> Optional[str]:
    """Find an option that matches the requested name, ignoring case and path differences."""

    requested_norm = _normalize_comfy_option(requested)
    requested_basename = os.path.basename(requested_norm)

    normalized_options = []
    for option in options:
        if not isinstance(option, str):
            continue
        option_clean = option.strip()
        if not option_clean:
            continue
        option_norm = _normalize_comfy_option(option_clean)
        normalized_options.append((option_clean, option_norm))

    for option_clean, option_norm in normalized_options:
        if option_norm == requested_norm:
            return option_clean

    if requested_basename:
        for option_clean, option_norm in normalized_options:
            if os.path.basename(option_norm) == requested_basename:
                return option_clean

    return None


def _match_available_option(requested: Optional[str], options: Iterable[str]) -> tuple[Optional[str], bool]:
    """Return the closest available option and whether it was an exact match."""

    if not requested:
        return None, False

    valid_options = [opt for opt in options if isinstance(opt, str) and opt.strip()]
    match = _find_matching_model_option(requested, valid_options)
    if match is not None:
        return match, True

    if not valid_options:
        return requested, False

    return valid_options[0], False


def _select_preferred_option(
    candidates: Iterable[Optional[str]],
    options: Iterable[str],
    *,
    description: str,
    message_prefix: str = "Upscaling",
) -> Optional[str]:
    """Pick the best available option for a loader based on ordered preferences.

    The helper iterates through the provided ``candidates`` (already sanitized) in
    order. It returns the first candidate that resolves to a valid ComfyUI option,
    logging when a requested name is unavailable and a fallback is chosen. If no
    candidates resolve but ComfyUI exposes alternatives, the first available
    option is returned; otherwise the first non-empty candidate is returned.
    """

    valid_options = [opt for opt in options if isinstance(opt, str) and opt.strip()]
    if not valid_options:
        for candidate in candidates:
            if candidate:
                return candidate
        return None

    missing_requests: list[str] = []
    seen_candidates: set[str] = set()

    for candidate in candidates:
        if not candidate:
            continue
        normalized = _normalize_comfy_option(candidate)
        if normalized in seen_candidates:
            continue
        seen_candidates.add(normalized)

        resolved, exact = _match_available_option(candidate, valid_options)
        if resolved:
            if missing_requests:
                print(
                    f"{message_prefix}: Requested {description} '{missing_requests[0]}' "
                    f"not available; using '{resolved}' instead."
                )
            elif not exact:
                print(
                    f"{message_prefix}: Requested {description} '{candidate}' "
                    f"not available; using '{resolved}' instead."
                )
            return resolved

        missing_requests.append(candidate)

    fallback_choice = valid_options[0]
    if missing_requests:
        print(
            f"{message_prefix}: Requested {description} '{missing_requests[0]}' "
            f"not available; defaulting to '{fallback_choice}'."
        )
    return fallback_choice


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
    UPSCALE_MODELS_ROOT = config_data.get('MODELS', {}).get('UPSCALE_MODELS')
    if isinstance(UPSCALE_MODELS_ROOT, str) and UPSCALE_MODELS_ROOT.strip():
        UPSCALE_MODELS_ROOT = os.path.abspath(UPSCALE_MODELS_ROOT.strip())
    else:
        UPSCALE_MODELS_ROOT = None
except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError) as e:
    print(f"Error loading config.json in upscaling.py: {e}")
    config_data = {"OUTPUTS": {}}
    UPSCALES_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','UPSCALES'))
    UPSCALE_MODELS_ROOT = None
except Exception as e:
    print(f"Unexpected error loading config.json in upscaling.py: {e}")
    traceback.print_exc()
    config_data = {"OUTPUTS": {}}
    UPSCALES_DIR = os.path.abspath(os.path.join('output','TENOSAI-BOT','UPSCALES'))
    UPSCALE_MODELS_ROOT = None

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
        elif "ckpt_name" in inputs:
            inputs["ckpt_name"] = file_name

    widgets = node_entry.get("widgets_values")
    if isinstance(widgets, list) and widgets:
        widgets[0] = file_name


def _get_loader_default_name(
    prompt: dict,
    node_id: Optional[str],
    *,
    keys: Iterable[str] = ("model_name", "unet_name", "vae_name", "clip_name"),
) -> Optional[str]:
    """Return the default model name configured on a loader node."""

    if not node_id:
        return None

    node_entry = prompt.get(node_id)
    if not isinstance(node_entry, dict):
        return None

    inputs = node_entry.get("inputs")
    if isinstance(inputs, dict):
        for key in keys:
            value = inputs.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned

    widgets = node_entry.get("widgets_values")
    if isinstance(widgets, list) and widgets:
        first = widgets[0]
        if isinstance(first, str):
            cleaned = first.strip()
            if cleaned:
                return cleaned

    return None


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


def _apply_sampling_shift_overrides(prompt: dict, shift_value: float | None) -> None:
    if shift_value is None:
        return

    for node_data in prompt.values():
        if not isinstance(node_data, dict):
            continue
        if node_data.get("class_type") not in {"ModelSamplingAuraFlow", "ModelSamplingSD3"}:
            continue
        inputs = node_data.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            continue
        inputs.pop("clip", None)
        inputs.pop("model_b", None)
        inputs.pop("cfg_rescale", None)
        try:
            inputs["shift"] = float(shift_value)
        except (TypeError, ValueError):
            inputs["shift"] = 0.0


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

    models_data_fetch_error = False
    try:
        available_models_data = check_available_models_api(suppress_summary_print=True)
    except Exception as comfy_error:
        print(f"Upscaling: Unable to fetch model availability from ComfyUI: {comfy_error}")
        available_models_data = {}
        models_data_fetch_error = True

    def _extract_available_list(key: str) -> list[str]:
        if isinstance(available_models_data, dict):
            return [item for item in available_models_data.get(key, []) if isinstance(item, str)]
        return []

    available_unet_options = _extract_available_list("unet")
    available_checkpoint_options = _extract_available_list("checkpoint")
    available_clip_options = _extract_available_list("clip")
    available_vae_options = _extract_available_list("vae")
    available_upscaler_options = _extract_available_list("upscaler")

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

    available_models_for_type = (
        available_checkpoint_options if current_base_model_type == 'sdxl' else available_unet_options
    )

    sanitized_base_model = _sanitize_override(actual_base_model_filename)
    resolved_base_model = None
    base_match_exact = False
    if sanitized_base_model:
        resolved_base_model, base_match_exact = _match_available_option(sanitized_base_model, available_models_for_type)
        if (
            resolved_base_model
            and available_models_for_type
            and not base_match_exact
        ):
            print(
                f"Upscaling: Requested base model '{sanitized_base_model}' not available; using '{resolved_base_model}' instead."
            )
    elif available_models_for_type:
        resolved_base_model = available_models_for_type[0]

    if resolved_base_model:
        actual_base_model_filename = resolved_base_model

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

    effective_selected_model_entry = None
    if isinstance(selected_base_model_setting, str) and selected_base_model_setting.strip():
        effective_selected_model_entry = selected_base_model_setting.strip()

    if actual_base_model_filename:
        prefixed_default_entry = f"{current_base_model_type.upper()}: {actual_base_model_filename}"
        if not effective_selected_model_entry or _find_matching_model_option(
            actual_base_model_filename, [effective_selected_model_entry]
        ) is None:
            effective_selected_model_entry = prefixed_default_entry
    try:
        upscale_factor_setting = float(settings.get('upscale_factor', 1.85))
        if not (1.5 <= upscale_factor_setting <= 4.0): upscale_factor_setting = 1.85
    except (ValueError, TypeError): upscale_factor_setting = 1.85

    try:
        modified_upscale_prompt = copy_upscale_template(upscale_spec)
    except Exception as template_error:
        print(f"ERROR copying upscale template for model '{current_base_model_type}': {template_error}")
        return None, "Internal error preparing upscale template.", None

    template_upscaler_default = _get_loader_default_name(
        modified_upscale_prompt,
        upscale_spec.upscale_model_loader_node,
    )

    requested_upscaler = _sanitize_override(settings.get('selected_upscale_model'))
    selected_upscaler_model_file = _select_preferred_option(
        [requested_upscaler, template_upscaler_default],
        available_upscaler_options,
        description="upscaler",
    )

    resolved_upscaler_choice = _resolve_upscale_model_choice(
        selected_upscaler_model_file,
        template_upscaler_default,
        available_upscaler_options,
    )
    if resolved_upscaler_choice != selected_upscaler_model_file:
        if selected_upscaler_model_file:
            fallback_notice = resolved_upscaler_choice or template_upscaler_default or "template default"
            print(
                f"Upscaling: Requested upscaler '{selected_upscaler_model_file}' "
                f"not available; using '{fallback_notice}'."
            )
    selected_upscaler_model_file = resolved_upscaler_choice


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
                prefixed_base_model_name_ups = effective_selected_model_entry or f"{current_base_model_type.upper()}: {actual_base_model_filename}"
                model_node_update_dict_ups = get_model_node(prefixed_base_model_name_ups, base_model_loader_node_id_ups)
                if base_model_loader_node_id_ups in model_node_update_dict_ups:
                    modified_upscale_prompt[base_model_loader_node_id_ups] = model_node_update_dict_ups[base_model_loader_node_id_ups]
            except Exception as e_base_model_ups:
                print(f"Error setting upscale base model ('{actual_base_model_filename}'): {e_base_model_ups}")

    if (
        upscale_spec.upscale_model_loader_node
        and upscale_spec.upscale_model_loader_node in modified_upscale_prompt
        and selected_upscaler_model_file
    ):
        modified_upscale_prompt[upscale_spec.upscale_model_loader_node]["inputs"]["model_name"] = selected_upscaler_model_file

    if upscale_spec.family == "flux":
        flux_clip_node_id_ups = upscale_spec.clip_loader_node
        if flux_clip_node_id_ups and flux_clip_node_id_ups in modified_upscale_prompt:
            clip_inputs = modified_upscale_prompt[flux_clip_node_id_ups].setdefault("inputs", {})

            template_t5_clip = clip_inputs.get("clip_name1") if isinstance(clip_inputs, dict) else None
            template_clip_l = clip_inputs.get("clip_name2") if isinstance(clip_inputs, dict) else None

            resolved_t5_clip = _select_preferred_option(
                [
                    _sanitize_override(settings.get('selected_t5_clip')),
                    template_t5_clip,
                ],
                available_clip_options,
                description="Flux T5 clip",
            )

            resolved_clip_l = _select_preferred_option(
                [
                    _sanitize_override(settings.get('selected_clip_l')),
                    template_clip_l,
                ],
                available_clip_options,
                description="Flux CLIP-L",
            )

            if resolved_t5_clip:
                clip_inputs["clip_name1"] = resolved_t5_clip
            if resolved_clip_l:
                clip_inputs["clip_name2"] = resolved_clip_l
    else:
        clip_setting_key_ups = f"default_{current_base_model_type}_clip"
        clip_loader_node_id_ups = upscale_spec.clip_loader_node
        template_clip_default = _get_loader_default_name(
            modified_upscale_prompt,
            clip_loader_node_id_ups,
            keys=("clip_name",),
        )
        clip_override_ups = _sanitize_override(settings.get(clip_setting_key_ups))
        if clip_loader_node_id_ups and clip_loader_node_id_ups in modified_upscale_prompt:
            resolved_clip_override = _select_preferred_option(
                [clip_override_ups, template_clip_default],
                available_clip_options,
                description=f"{current_base_model_type.upper()} clip",
            )
            if resolved_clip_override:
                clip_inputs_ups = modified_upscale_prompt[clip_loader_node_id_ups].setdefault("inputs", {})
                clip_inputs_ups["clip_name"] = resolved_clip_override

    vae_setting_key_ups = f"default_{current_base_model_type}_vae"
    vae_loader_node_id_ups = upscale_spec.vae_loader_node
    template_vae_default = _get_loader_default_name(
        modified_upscale_prompt,
        vae_loader_node_id_ups,
        keys=("vae_name",),
    )
    vae_override_ups = _sanitize_override(settings.get(vae_setting_key_ups))
    if vae_loader_node_id_ups and vae_loader_node_id_ups in modified_upscale_prompt:
        resolved_vae_override = _select_preferred_option(
            [vae_override_ups, template_vae_default],
            available_vae_options,
            description=f"{current_base_model_type.upper()} VAE",
        )
        if resolved_vae_override:
            vae_inputs_ups = modified_upscale_prompt[vae_loader_node_id_ups].setdefault("inputs", {})
            vae_inputs_ups["vae_name"] = resolved_vae_override

    secondary_node_id_ups = getattr(upscale_spec, "secondary_model_loader_node", None)
    secondary_setting_key_ups = getattr(upscale_spec, "secondary_model_setting_key", None)
    if secondary_setting_key_ups:
        secondary_override_ups = _sanitize_override(settings.get(secondary_setting_key_ups))
    else:
        secondary_override_ups = None
    template_secondary_default = _get_loader_default_name(
        modified_upscale_prompt,
        secondary_node_id_ups,
    )
    resolved_secondary_override = _select_preferred_option(
        [secondary_override_ups, template_secondary_default],
        available_unet_options,
        description="secondary model",
    )
    if resolved_secondary_override:
        _update_model_loader_filename(
            modified_upscale_prompt,
            secondary_node_id_ups,
            file_name=resolved_secondary_override,
        )

    shift_value_ups = None
    if current_base_model_type in {'qwen', 'wan'}:
        shift_candidate_ups = settings.get(f"default_{current_base_model_type}_shift", 0.0)
        try:
            shift_value_ups = float(shift_candidate_ups)
        except (TypeError, ValueError):
            shift_value_ups = 0.0
    _apply_sampling_shift_overrides(modified_upscale_prompt, shift_value_ups)

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
    
    runtime_animation_supported = True

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
        "selected_model": effective_selected_model_entry,
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
