# --- START OF FILE utils/show_prompt.py ---
import json
from datetime import datetime, timedelta
import os
import re

def reconstruct_full_prompt_string(job_data):
    if not job_data or not isinstance(job_data, dict):
        return ""

    base_prompt = job_data.get('enhanced_prompt') or job_data.get('prompt') or job_data.get('original_prompt', '')
    full_prompt = base_prompt

    # Handle SDXL negative prompt if present
    negative_prompt = job_data.get('negative_prompt') # This key needs to be added to job_details
    if negative_prompt:
        full_prompt += f" --no \"{negative_prompt}\"" # Add --no "negative text"

    params = job_data.get('parameters_used')

    if params and isinstance(params, dict):
        if 'seed' in params and params['seed'] is not None:
            full_prompt += f" --seed {params['seed']}"

        # Guidance - check for both flux and sdxl guidance
        flux_guidance_used = False
        if 'guidance' in job_data and job_data['guidance'] is not None: # Flux guidance from top level
            try:
                full_prompt += f" --g {float(job_data['guidance']):.1f}"
                flux_guidance_used = True
            except (ValueError, TypeError): pass
        elif 'g' in params and params['g']: # Fallback to original 'g' param for Flux
            full_prompt += f" --g {params['g']}"
            flux_guidance_used = True
        
        # Add SDXL guidance if it was used and different from Flux guidance (or Flux wasn't used)
        sdxl_guidance_param = params.get('g_sdxl') # Check for explicit --g_sdxl
        if sdxl_guidance_param:
            full_prompt += f" --g_sdxl {sdxl_guidance_param}"
        elif 'guidance_sdxl' in job_data and job_data['guidance_sdxl'] is not None: # SDXL guidance from top level
            try:
                sdxl_g_val = float(job_data['guidance_sdxl'])
                # Only add if it's different from flux guidance or flux guidance wasn't added
                if not flux_guidance_used or (flux_guidance_used and abs(sdxl_g_val - float(job_data.get('guidance', sdxl_g_val + 1))) > 0.01):
                     full_prompt += f" --g_sdxl {sdxl_g_val:.1f}"
            except (ValueError, TypeError): pass


        ar_to_add = job_data.get('original_ar_param')
        if not ar_to_add:
            ar_str = job_data.get('aspect_ratio_str')
            if ar_str and ar_str != "1:1":
                ar_to_add = ar_str
        if ar_to_add:
            full_prompt += f" --ar {ar_to_add}"

        if job_data.get('type') == 'img2img':
             strength = job_data.get('img_strength_percent')
             url = job_data.get('image_url')
             if strength is not None and url:
                 full_prompt += f" --img {strength} {url}"

        style = job_data.get('style')
        if style and style != 'off':
            full_prompt += f" --style {style}"

        if 'run_times' in job_data and job_data['run_times'] > 1:
            full_prompt += f" --r {job_data['run_times']}"
    else:
        # Fallback for older job data without 'parameters_used'
        if 'seed' in job_data and job_data['seed'] is not None:
            full_prompt += f" --seed {job_data['seed']}"
        if 'guidance' in job_data and job_data['guidance'] is not None:
            try: full_prompt += f" --g {float(job_data['guidance']):.1f}"
            except (ValueError, TypeError): pass
        # Add SDXL guidance fallback if applicable
        if 'guidance_sdxl' in job_data and job_data['guidance_sdxl'] is not None:
             try: full_prompt += f" --g_sdxl {float(job_data['guidance_sdxl']):.1f}"
             except (ValueError, TypeError): pass

        ar_to_add = job_data.get('original_ar_param')
        if not ar_to_add:
            ar_str = job_data.get('aspect_ratio_str')
            if ar_str and ar_str != "1:1": ar_to_add = ar_str
        if ar_to_add: full_prompt += f" --ar {ar_to_add}"
        if job_data.get('type') == 'img2img' and job_data.get('image_url') and job_data.get('img_strength_percent') is not None:
            full_prompt += f" --img {job_data['img_strength_percent']} {job_data['image_url']}"
        style = job_data.get('style')
        if style and style != 'off':
            full_prompt += f" --style {style}"
        if 'run_times' in job_data and job_data['run_times'] > 1:
            full_prompt += f" --r {job_data['run_times']}"


    return full_prompt.strip()


def show_prompt(message_id, channel_id, queue_manager):
    job_data = queue_manager.get_job_data(message_id, channel_id)
    if job_data:
        return reconstruct_full_prompt_string(job_data)
    else:
        print(f"show_prompt: Job data not found for message {message_id} / channel {channel_id}")
        return "Prompt data not found"

# --- END OF FILE utils/show_prompt.py ---