import discord
import asyncio
import os
import json
import textwrap
from datetime import datetime, timedelta
import traceback
import re
import requests
from io import BytesIO
import math

from bot_config_loader import config, COMFYUI_HOST, COMFYUI_PORT, ADMIN_USERNAME
from queue_manager import queue_manager
from file_management import extract_job_id
from settings_manager import load_settings, load_styles_config
from comfyui_api import queue_prompt as comfy_queue_prompt, ConnectionRefusedError as ComfyConnectionRefusedError
from websocket_client import WebsocketClient

from image_generation import modify_prompt as ig_modify_prompt
from upscaling import modify_upscale_prompt as up_modify_upscale_prompt, get_image_dimensions
from variation import modify_variation_prompt
from kontext_editing import modify_kontext_prompt
from utils.seed_utils import generate_seed
from utils.show_prompt import reconstruct_full_prompt_string
from utils.message_utils import send_long_message, safe_interaction_response
from utils.llm_enhancer import enhance_prompt as util_enhance_prompt, FLUX_ENHANCER_SYSTEM_PROMPT, SDXL_ENHANCER_SYSTEM_PROMPT, KONTEXT_ENHANCER_SYSTEM_PROMPT

_bot_instance_core = None
def register_bot_instance_for_core(bot_instance):
    global _bot_instance_core
    _bot_instance_core = bot_instance

async def _ensure_ws_client_id():
    """Waits up to 5 seconds for the websocket client to get its session ID."""
    ws_client = WebsocketClient()
    if ws_client.client_id:
        return
    
    print("WebSocket client_id not yet available. Waiting up to 5 seconds...")
    for _ in range(10): # 10 * 0.5s = 5s
        if ws_client.client_id:
            print(f"WebSocket client_id acquired: {ws_client.client_id}")
            return
        await asyncio.sleep(0.5)
    
    print("Warning: WebSocket client_id still not available after waiting. Progress updates may fail for this job.")


async def _get_preview_image_from_comfyui(image_data):
    """Fetches a preview image from the ComfyUI server."""
    try:
        filename = image_data.get('filename')
        subfolder = image_data.get('subfolder')
        img_type = image_data.get('type')

        if not filename: return None

        params = {"filename": filename, "subfolder": subfolder, "type": img_type}
        url = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}/view"
        
        response = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
        response.raise_for_status()
        
        return BytesIO(response.content)
    except Exception as e:
        print(f"Error fetching preview image '{filename}': {e}")
        return None

async def update_job_progress(bot, prompt_id, current_step, max_steps, image_data):
    """Updates the Discord message with the current job progress."""
    ws_client = WebsocketClient()
    job_info = ws_client.active_prompts.get(prompt_id)
    if not job_info: return

    try:
        channel = bot.get_channel(job_info['channel_id']) or await bot.fetch_channel(job_info['channel_id'])
        message = await channel.fetch_message(job_info['message_id'])
    except discord.NotFound:
        ws_client.unregister_prompt(prompt_id)
        return
    except Exception as e:
        print(f"Error fetching message for progress update (Prompt ID: {prompt_id}): {e}")
        return
        
    job_data = queue_manager.get_job_by_comfy_id(prompt_id)
    if not job_data: return

    edit_kwargs = {}

    if current_step is not None and max_steps is not None and max_steps > 0:
        percentage = (current_step / max_steps) * 100
        filled_blocks = int(percentage / 10)
        empty_blocks = 10 - filled_blocks
        progress_bar = f"**Status:** Generating: [ {'● ' * filled_blocks}{'◌ ' * empty_blocks}] {int(percentage)}%"
        
        original_content = message.content
        new_content = re.sub(r'> \*\*Status:\*\*.*', f'> {progress_bar}', original_content, flags=re.MULTILINE)
        
        if new_content != original_content:
            edit_kwargs['content'] = new_content

    if image_data:
        now = asyncio.get_event_loop().time()
        if (now - job_info.get('last_preview_timestamp', 0)) > 2.0:
            job_info['last_preview_timestamp'] = now
            image_bytes = await _get_preview_image_from_comfyui(image_data)
            if image_bytes:
                edit_kwargs['attachments'] = [discord.File(image_bytes, filename=f"preview_{prompt_id}.jpeg")]

    if edit_kwargs:
        try:
            await message.edit(**edit_kwargs)
        except discord.HTTPException as e:
            if e.status != 429: 
                print(f"HTTPException updating progress for prompt {prompt_id}: {e}")
        except Exception as e:
            print(f"Error updating progress message for prompt {prompt_id}: {e}")

async def process_completed_job(bot, job_id, job_data, file_paths: list):
    ws_client = WebsocketClient()
    if job_data.get("comfy_prompt_id"):
        ws_client.unregister_prompt(job_data["comfy_prompt_id"])
        
    from bot_ui_components import BatchActionsView, GenerationActionsView

    if job_data.get("type") == "upscale":
        print(f"--- process_completed_job START (UPSCALE JOB) --- Job ID: {job_id}")
    print(f"Processing completed job: {job_id} with {len(file_paths)} files.")
    norm_file_paths = []
    for fp in file_paths:
        if fp and isinstance(fp, str):
            try: norm_file_paths.append(os.path.normpath(fp))
            except Exception as e_norm: print(f"Error normalizing path '{fp}': {e_norm}")
        else: print(f"Warning: Invalid file path found for job {job_id}: {fp}")
    if not norm_file_paths:
        print(f"Error: No valid normalized file paths found for job {job_id}.")
        channel_id_err = job_data.get('channel_id')
        if channel_id_err:
            try:
                channel_err = bot.get_channel(int(channel_id_err)) or await bot.fetch_channel(int(channel_id_err))
                user_mention_err = job_data.get('user_mention', f"<@{job_data.get('user_id', 'Unknown User')}>")
                await channel_err.send(f"{user_mention_err} Error processing job `{job_id}`: No output files found or files were invalid.")
            except Exception as e_notify_no_files_err: print(f"Failed to notify user about missing files for job {job_id}: {e_notify_no_files_err}")
        return
    try:
        channel_id = job_data.get('channel_id')
        message_id = job_data.get('message_id')
        user_mention = job_data.get('user_mention', f"<@{job_data.get('user_id', 'Unknown User')}>")
        batch_size = job_data.get('batch_size', 1)
        job_model_type = job_data.get('model_type_for_enhancer', job_data.get('parameters_used', {}).get('base_model_type_workflow', 'flux'))
        if not channel_id: print(f"CRITICAL Error: Missing channel_id for completed job {job_id}."); return
        message_to_edit = None; channel = None
        try:
            channel = bot.get_channel(int(channel_id)) or await bot.fetch_channel(int(channel_id))
            if message_id:
                try: message_to_edit = await channel.fetch_message(int(message_id)); print(f"Found status message {message_id} to edit for job {job_id}")
                except discord.NotFound: print(f"Warning: Original status message {message_id} not found for job {job_id}. Will send new message."); message_to_edit = None
                except discord.Forbidden: print(f"Warning: Bot lacks permission to fetch original status message {message_id} for job {job_id}."); message_to_edit = None
                except Exception as e_fetch_msg: print(f"Warning: Error fetching status message {message_id} for job {job_id}: {e_fetch_msg}"); message_to_edit = None
            else: print(f"Warning: No message_id stored for job {job_id}. Cannot edit status message.")
        except discord.NotFound: print(f"CRITICAL Error: Channel {channel_id} not found for job {job_id}."); return
        except discord.Forbidden: print(f"CRITICAL Error: Bot lacks permission for channel {channel_id} (job {job_id})."); return
        except Exception as e_fetch_chan: print(f"CRITICAL Error fetching channel {channel_id} for job {job_id}: {e_fetch_chan}"); return
        if not channel: print(f"CRITICAL Error: Failed get channel object for job {job_id}"); return
        valid_files_for_discord = []; discord_file_limit = 25 * 1024 * 1024; total_attachment_size = 0; max_total_size = 48 * 1024 * 1024
        norm_file_paths.sort()
        for fp_check in norm_file_paths:
            if os.path.exists(fp_check):
                try:
                    f_size = os.path.getsize(fp_check)
                    if f_size == 0: print(f"Warning: File '{os.path.basename(fp_check)}' is 0 bytes (job {job_id}). Skipping.")
                    elif f_size > discord_file_limit: print(f"Warning: File '{os.path.basename(fp_check)}' ({f_size} bytes) > Discord limit ({discord_file_limit} bytes). Skipping.")
                    elif total_attachment_size + f_size > max_total_size: print(f"Warning: Adding file '{os.path.basename(fp_check)}' would exceed total size limit. Skipping for job {job_id}."); break
                    else: valid_files_for_discord.append(fp_check); total_attachment_size += f_size
                except OSError as e_size_check: print(f"Error getting size/checking file {fp_check}: {e_size_check}")
            else: print(f"WARNING: File path not found during completion processing: {fp_check} (job {job_id})")
        if not valid_files_for_discord:
            error_content_no_files = f"{user_mention} Error: Output file(s) for job `{job_id}` were missing, empty, or too large to attach."
            try:
                if message_to_edit: await message_to_edit.edit(content=error_content_no_files, view=None, attachments=[])
                else: await channel.send(content=error_content_no_files)
            except Exception as e_send_err_nofiles: print(f"Error sending/editing message for missing files: {e_send_err_nofiles}")
            return
        attachment_warning_str = ""; discord_files_list = []
        files_to_attach_this_msg = valid_files_for_discord[:10]
        if len(valid_files_for_discord) > 10: attachment_warning_str = f"\n*(Showing first 10 of {len(valid_files_for_discord)} generated images)*"
        for fp_attach in files_to_attach_this_msg:
            try: discord_files_list.append(discord.File(fp_attach))
            except Exception as e_df_create: print(f"Error creating discord.File for {fp_attach}: {e_df_create}")
        if not discord_files_list:
            error_content_no_attach = f"{user_mention} Error: Failed to prepare attachments for job `{job_id}`."
            try:
                if message_to_edit: await message_to_edit.edit(content=error_content_no_attach, view=None, attachments=[])
                else: await channel.send(content=error_content_no_attach)
            except Exception as e_send_prep_err_attach: print(f"Error sending/editing msg for file prep fail: {e_send_prep_err_attach}")
            return
        current_settings = load_settings(); display_preference = current_settings.get('display_prompt_preference', 'enhanced')
        # FIX: Ensure prompt display logic correctly handles all cases and falls back gracefully
        prompt_to_use_for_display = job_data.get('prompt', '[No Prompt Provided]')
        if display_preference == 'enhanced' and job_data.get('enhanced_prompt'):
            prompt_to_use_for_display = job_data.get('enhanced_prompt')
        elif display_preference == 'original' and job_data.get('original_prompt'):
            prompt_to_use_for_display = job_data.get('original_prompt')

        enhancer_was_used = job_data.get('enhancer_used', False); enhancer_had_error = job_data.get('enhancer_error'); llm_provider_used = job_data.get('llm_provider')
        aspect_ratio_display = job_data.get("aspect_ratio_str", "?:?"); seed_display = job_data.get('seed', 'N/A'); style_display = job_data.get('style', 'off'); job_type_display_str = job_data.get('type', 'generate').capitalize()
        if job_type_display_str.lower() == 'upscale': steps_display = 'N/A (Upscale)'; guidance_display = 'N/A (Upscale)'; sdxl_guidance_display = 'N/A (Upscale)'; mp_size_display = 'N/A (Upscale)'
        else:
            steps_display = str(job_data.get('steps', '?')); guidance_val_flux = job_data.get('guidance'); guidance_val_sdxl = job_data.get('guidance_sdxl')
            try: guidance_display = f"{float(guidance_val_flux):.1f}" if guidance_val_flux is not None else 'N/A'
            except (ValueError, TypeError): guidance_display = '?'
            try: sdxl_guidance_display = f"{float(guidance_val_sdxl):.1f}" if guidance_val_sdxl is not None else 'N/A'
            except (ValueError, TypeError): sdxl_guidance_display = '?'
            mp_size_display = job_data.get("parameters_used", {}).get("mp", job_data.get("default_mp_size", "N/A"))
        final_content = f"{user_mention}: `{textwrap.shorten(prompt_to_use_for_display, 1000, placeholder='...')}`"
        if enhancer_was_used and display_preference == 'enhanced': final_content += " ✨"
        final_content += f"\n> **Seed:** `{seed_display}`"
        if job_type_display_str.lower() != 'upscale': final_content += f", **AR:** `{aspect_ratio_display}`, **MP:** `{mp_size_display}`"
        final_content += f", **Steps:** `{steps_display}`"
        if job_model_type == "sdxl": final_content += f", **Guidance:** `{sdxl_guidance_display}`"
        else: final_content += f", **Guidance:** `{guidance_display}`"
        final_content += f"\n> **Style:** `{style_display}`"
        job_type_info_str = f" ({job_model_type.upper()})"
        if job_type_display_str.lower() == 'upscale': job_type_info_str = f" (Upscaled {job_data.get('upscale_factor', '?x')}{job_type_info_str})"
        elif job_type_display_str.lower() == 'variation': job_type_info_str = f" ({job_data.get('variation_type', '?').capitalize()} Variation{job_type_info_str})"
        elif job_type_display_str.lower() == 'kontext_edit': job_type_info_str = f" (Kontext Edit)"
        elif batch_size > 1: job_type_info_str += f", **Batch:** `{batch_size}`"
        final_content += job_type_info_str
        if job_model_type == "sdxl" and job_data.get('negative_prompt'): final_content += f"\n> **No:** `{textwrap.shorten(job_data['negative_prompt'], 100, placeholder='...')}`"
        if enhancer_was_used and display_preference == 'original': final_content += f"\n> `(Prompt enhanced via {llm_provider_used.capitalize() if llm_provider_used else 'LLM'})`"
        elif enhancer_had_error: final_content += f"\n> `(Enhancer Error ({llm_provider_used.capitalize() if llm_provider_used else 'LLM'}): {enhancer_had_error})`"
        if job_data.get('style_warning_message'): final_content += f"\n> `(Style Warning: {job_data['style_warning_message']})`"
        final_content += attachment_warning_str
        
        action_msg_id = message_id if message_to_edit else 0
        view_to_use_final = BatchActionsView(action_msg_id, channel_id, job_id, batch_size, bot) if batch_size >= 2 else GenerationActionsView(action_msg_id, channel_id, job_id, bot)
        try:
            sent_msg_obj = None
            if message_to_edit: await message_to_edit.edit(content=final_content, attachments=discord_files_list, view=view_to_use_final); sent_msg_obj = message_to_edit; print(f"Successfully updated message {message_id} for job {job_id}")
            else:
                new_sent_msg = await channel.send(content=final_content, files=discord_files_list, view=view_to_use_final); sent_msg_obj = new_sent_msg
                print(f"Sent new message {new_sent_msg.id} for job {job_id} (original status msg missing/failed).")
                if new_sent_msg: queue_manager.update_job_message_id(job_id, new_sent_msg.id); view_to_use_final.original_message_id = new_sent_msg.id
        except discord.HTTPException as http_err_send:
            print(f"Discord HTTP Error sending results for job {job_id}: {http_err_send.status} - {http_err_send.text}")
            fb_content_err = final_content + ("\n\n**Error: Result files too large/many to attach.**" if http_err_send.status == 400 or ("Invalid Form Body" in str(http_err_send.text) and "attachments" in str(http_err_send.text).lower()) or http_err_send.status == 413 or "Request entity too large" in str(http_err_send.text).lower() or "payload too large" in str(http_err_send.text).lower() else "\n\n**Error attaching result images.**")
            try:
                if message_to_edit: await message_to_edit.edit(content=fb_content_err, view=None, attachments=[])
                else: await channel.send(content=fb_content_err, view=None)
            except Exception as e_send_fb_err_send: print(f"Error sending fallback error message: {e_send_fb_err_send}")
        except Exception as e_send_edit_final: print(f"Unexpected Error sending/editing final message for job {job_id}: {e_send_edit_final}"); traceback.print_exc()
    except Exception as e_main_proc: print(f"CRITICAL error in process_completed_job for {job_id}: {e_main_proc}"); traceback.print_exc()

async def check_output_folders(bot):
    await bot.wait_until_ready()
    
    ws_client = WebsocketClient(bot)
    
    print("Background task: Starting output folder check loop.")
    output_paths_cfg = config.get('OUTPUTS', {}); checked_paths_startup = set()
    for key_cfg, path_val_cfg in output_paths_cfg.items():
        if path_val_cfg and isinstance(path_val_cfg, str) and path_val_cfg not in checked_paths_startup:
            checked_paths_startup.add(path_val_cfg)
            try:
                abs_path_cfg = os.path.abspath(os.path.normpath(path_val_cfg))
                if not os.path.exists(abs_path_cfg): print(f"Output directory '{abs_path_cfg}' for '{key_cfg}' not found. Creating..."); os.makedirs(abs_path_cfg, exist_ok=True); print(f"Created output directory: {abs_path_cfg}")
                elif not os.path.isdir(abs_path_cfg): print(f"ERROR: Configured output path '{abs_path_cfg}' for '{key_cfg}' exists but is not a directory.")
            except OSError as e_create_cfg: print(f"ERROR verifying/creating output directory {key_cfg} ('{path_val_cfg}'): {e_create_cfg}")
            except Exception as e_verify_cfg: print(f"Unexpected ERROR verifying output directory {key_cfg} ('{path_val_cfg}'): {e_verify_cfg}"); traceback.print_exc()
    startup_scan_done_flag = False
    while not bot.is_closed():
        try:
            if not ws_client.is_connected and not ws_client.is_connecting:
                bot.loop.create_task(ws_client.ensure_connected())

            current_pending_jobs = queue_manager.get_pending_jobs()
            if not current_pending_jobs and startup_scan_done_flag: await asyncio.sleep(15); continue
            normalized_pending_lookup = {str(k_job).lower().strip(): v_job for k_job, v_job in current_pending_jobs.items()}
            output_folders_to_scan_now = []; current_checked_this_iter = set()
            for key_iter_cfg, path_iter_cfg in config.get('OUTPUTS', {}).items():
                if path_iter_cfg and isinstance(path_iter_cfg, str) and path_iter_cfg not in current_checked_this_iter:
                    current_checked_this_iter.add(path_iter_cfg)
                    try:
                        abs_path_iter_cfg = os.path.abspath(os.path.normpath(path_iter_cfg))
                        if os.path.isdir(abs_path_iter_cfg): output_folders_to_scan_now.append(abs_path_iter_cfg)
                    except Exception as e_path_iter: print(f"Error checking path '{path_iter_cfg}': {e_path_iter}")
            if not output_folders_to_scan_now:
                if not startup_scan_done_flag: print("Warning: No valid output folders configured to scan during startup.")
                await asyncio.sleep(60); continue
            found_files_by_job_id = {}
            for folder_scan in output_folders_to_scan_now:
                try:
                    for entry_scan in os.scandir(folder_scan):
                        if entry_scan.is_file():
                            filepath_scan = entry_scan.path; filename_scan = entry_scan.name
                            job_id_extracted = extract_job_id(filename_scan)
                            if job_id_extracted:
                                job_id_norm = str(job_id_extracted).lower().strip()
                                if job_id_norm in normalized_pending_lookup:
                                    try:
                                        size1_scan = entry_scan.stat().st_size
                                        if size1_scan == 0: continue
                                        await asyncio.sleep(1.0)
                                        if not os.path.exists(filepath_scan): continue
                                        size2_scan = os.path.getsize(filepath_scan)
                                        if size1_scan != size2_scan: continue
                                        norm_filepath_scan = os.path.normpath(filepath_scan)
                                        found_files_by_job_id.setdefault(job_id_norm, []).append(norm_filepath_scan)
                                        if len(found_files_by_job_id[job_id_norm]) == 1 : queue_manager.record_first_file_seen(job_id_norm)
                                    except FileNotFoundError: continue
                                    except OSError as e_stat_scan:
                                        if not isinstance(e_stat_scan, FileNotFoundError): print(f"OSError during stat for {filename_scan}: {e_stat_scan}")
                                        continue
                                    except Exception as e_size_check_scan: print(f"Unexpected error during size check for {filename_scan}: {e_size_check_scan}"); traceback.print_exc(); continue
                except FileNotFoundError: print(f"Warning: Folder not found during scan loop: {folder_scan}")
                except OSError as e_os_scan: print(f"Error scanning folder {folder_scan}: {e_os_scan}")
                except Exception as e_unexp_scan: print(f"Unexpected error scanning folder {folder_scan}: {e_unexp_scan}"); traceback.print_exc()
            jobs_to_process_now = {}
            for original_job_id_iter, job_data_iter in current_pending_jobs.items():
                normalized_job_id_lookup_iter = str(original_job_id_iter).lower().strip()
                found_files_list_iter = list(set(found_files_by_job_id.get(normalized_job_id_lookup_iter, [])))
                expected_files_iter = job_data_iter.get('batch_size', 1)
                if len(found_files_list_iter) >= expected_files_iter:
                    if original_job_id_iter not in jobs_to_process_now: jobs_to_process_now[original_job_id_iter] = {"data": job_data_iter, "files": sorted(found_files_list_iter)}
                elif found_files_list_iter:
                    time_since_first_file = queue_manager.get_time_since_first_file(normalized_job_id_lookup_iter)
                    timeout_val_minutes = 5 * expected_files_iter
                    timeout_delta = timedelta(minutes=timeout_val_minutes)
                    if time_since_first_file and time_since_first_file > timeout_delta:
                        if original_job_id_iter not in jobs_to_process_now:
                            print(f"TIMEOUT job {original_job_id_iter}: Found {len(found_files_list_iter)}/{expected_files_iter} after {time_since_first_file}. Processing.")
                            jobs_to_process_now[original_job_id_iter] = {"data": job_data_iter, "files": sorted(found_files_list_iter)}
            if jobs_to_process_now: print(f"Processing {len(jobs_to_process_now)} completed/timed-out jobs: {list(jobs_to_process_now.keys())}")
            for job_id_proc, proc_info in jobs_to_process_now.items():
                if job_id_proc in queue_manager.get_pending_jobs():
                    try:
                        await process_completed_job(bot, job_id_proc, proc_info["data"], proc_info["files"])
                        queue_manager.mark_job_complete(job_id_proc, proc_info["data"], proc_info["files"])
                    except Exception as e_proc_job: print(f"Error during process_completed_job for {job_id_proc}: {e_proc_job}"); traceback.print_exc()
            if not startup_scan_done_flag: startup_scan_done_flag = True; print("Initial startup scan of output folders complete.")
        except Exception as e_main_loop: print(f"CRITICAL error in check_output_folders loop: {e_main_loop}"); traceback.print_exc(); await asyncio.sleep(60)
        await asyncio.sleep(2 if queue_manager.get_pending_jobs() else 10)

async def process_cancel_request(comfy_prompt_id: str) -> tuple[bool, str]:
    ws_client = WebsocketClient()
    ws_client.unregister_prompt(comfy_prompt_id)

    bot_job_data = queue_manager.get_job_by_comfy_id(comfy_prompt_id)
    bot_job_id = bot_job_data.get('job_id') if bot_job_data else None
    print(f"Attempting to cancel Comfy Prompt ID: {comfy_prompt_id} (Bot Job ID: {bot_job_id or 'Unknown'})")
    
    if bot_job_id:
         if queue_manager.is_job_completed_or_cancelled(bot_job_id): 
             print(f"Local job {bot_job_id} already completed/cancelled. No API call needed.")
             return False, "Job already completed or cancelled."
         else: 
             print(f"Marking local job {bot_job_id} as cancelled.")
             queue_manager.mark_job_cancelled(bot_job_id)
    else: 
        print(f"Warning: No local bot job found for ComfyID {comfy_prompt_id} during cancel request.")

    try:
        api_url_base = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
        delete_payload = {"delete": [comfy_prompt_id]}
        
        print(f"Sending DELETE to ComfyUI queue for prompt {comfy_prompt_id}...")
        delete_response = await asyncio.to_thread(requests.post, f"{api_url_base}/queue", json=delete_payload, timeout=10)
        
        if delete_response.status_code == 200:
            final_status_msg = "Job successfully deleted from queue."
            print(f"ComfyUI API Success for {comfy_prompt_id}: {final_status_msg}")
            return True, final_status_msg
        else:
            error_msg = f"Failed to delete from queue (Status: {delete_response.status_code}). Job may have already started or completed."
            print(f"ComfyUI API Info for {comfy_prompt_id}: {error_msg}")
            return True, "Job cancelled locally (not found in ComfyUI pending queue)."

    except requests.Timeout: 
        print(f"Timeout connecting to ComfyUI for API cancel/interrupt {comfy_prompt_id}.")
        return True, "Job cancelled locally (Timeout contacting ComfyUI API)."
    except requests.RequestException as e_req_cancel:
        error_details_cancel = f"Error connecting to ComfyUI API: {e_req_cancel}"
        print(f"API Error cancelling/interrupting {comfy_prompt_id}: {e_req_cancel}")
        if e_req_cancel.response is not None:
            try: error_details_cancel += f"\nResponse: {e_req_cancel.response.text}"
            except Exception: pass
        return True, f"Job cancelled locally ({error_details_cancel})."
    except Exception as e_unexp_cancel: 
        print(f"Unexpected error during API cancel/interrupt for {comfy_prompt_id}: {e_unexp_cancel}")
        traceback.print_exc()
        return True, "Job cancelled locally (Unexpected error during API cancel/interrupt)."


async def execute_generation_logic(
    context_user: discord.User,
    context_channel: discord.abc.Messageable,
    prompt: str,
    is_interaction_context: bool,
    initial_interaction_object: discord.Interaction | None = None,
    model_type_override: str | None = None, 
    is_derivative_action: bool = False
) -> list:
    await _ensure_ws_client_id()
    current_styles_config = load_styles_config()
    settings_gen = load_settings()
    param_pattern_gen = r'\s--(\w+)(?:\s+("([^"]*)"|((?:(?!--|\s--).)+)|([^\s]+)))?'
    params_dict_gen = {}; prompt_base_gen = prompt; param_string_for_neg_prompt_gen = prompt
    first_param_match_gen = re.search(r'\s--\w+', prompt)
    if first_param_match_gen:
        prompt_base_gen = prompt[:first_param_match_gen.start()].strip()
        param_string_for_params_dict_gen = prompt[first_param_match_gen.start():]
        param_matches_gen = re.findall(param_pattern_gen, param_string_for_params_dict_gen)
        for key_gen, _, quoted_val_gen, unquoted_compound_gen, unquoted_single_gen in param_matches_gen:
             value_gen = quoted_val_gen if quoted_val_gen else (unquoted_compound_gen if unquoted_compound_gen else unquoted_single_gen)
             params_dict_gen[key_gen.lower()] = value_gen.strip() if value_gen else True
    else: prompt_base_gen = prompt.strip()
    
    selected_model_prefix_gen = settings_gen.get('selected_model')
    current_model_type_for_job = "flux" 
    
    if model_type_override: 
        current_model_type_for_job = model_type_override.lower()
    elif selected_model_prefix_gen and ":" in selected_model_prefix_gen:
        prefix_from_settings, name_from_settings = selected_model_prefix_gen.split(":", 1)
        current_model_type_for_job = prefix_from_settings.strip().lower()
    elif selected_model_prefix_gen: 
        if selected_model_prefix_gen.endswith((".gguf",".sft")): current_model_type_for_job = "flux"
        else: current_model_type_for_job = "sdxl"
    
    user_provided_neg_prompt_gen = None
    no_param_match_gen = re.search(r'--no\s+(?:"([^"]*)"|((?:(?!\s--).)+))', param_string_for_neg_prompt_gen, re.I | re.S)
    if no_param_match_gen:
        user_provided_neg_prompt_gen = (no_param_match_gen.group(1) or no_param_match_gen.group(2)).strip()
        prompt_base_gen = re.sub(r'\s*--no\s+(?:"([^"]*)"|((?:(?!\s--).)+))\s*', ' ', prompt_base_gen, flags=re.I | re.S).strip()
        if 'no' in params_dict_gen: del params_dict_gen['no']
    elif params_dict_gen.get('no') is True: user_provided_neg_prompt_gen = "";  del params_dict_gen['no']
    
    negative_prompt_text_gen = None
    if current_model_type_for_job == "sdxl":
        if is_derivative_action: 
            negative_prompt_text_gen = user_provided_neg_prompt_gen
        else: 
            default_sdxl_neg_gen = settings_gen.get('default_sdxl_negative_prompt', "").strip()
            if user_provided_neg_prompt_gen is not None: 
                negative_prompt_text_gen = user_provided_neg_prompt_gen if user_provided_neg_prompt_gen else default_sdxl_neg_gen
            else: 
                negative_prompt_text_gen = default_sdxl_neg_gen
    
    is_img2img_gen = 'img' in params_dict_gen and params_dict_gen['img'] is not True
    run_times_gen = 1
    if 'r' in params_dict_gen:
        try: run_times_gen = min(max(1, int(params_dict_gen['r'])), 10); del params_dict_gen['r']
        except (ValueError, TypeError):
            if 'r' in params_dict_gen: del params_dict_gen['r']
    
    enhancer_enabled_gen = settings_gen.get('llm_enhancer_enabled', False)
    llm_provider_gen = settings_gen.get('llm_provider', 'gemini')
    enhancer_info_gen = {'used': False, 'provider': None, 'enhanced_text': None, 'error': None, 'model_type_for_enhancer': current_model_type_for_job}
    additional_info_msg_gen = ""
    is_admin_text_cmd_gen = (not is_interaction_context) and isinstance(context_user, discord.Member) and context_user.name == ADMIN_USERNAME
    api_key_present_enh_gen = False
    try:
        config_file_path = config.get("CONFIG_FILE_NAME", "config.json")
        with open(config_file_path, 'r') as cf_enh: temp_cfg_enh = json.load(cf_enh).get('LLM_ENHANCER',{})
        if llm_provider_gen == 'gemini' and temp_cfg_enh.get('GEMINI_API_KEY',''): api_key_present_enh_gen = True
        elif llm_provider_gen == 'groq' and temp_cfg_enh.get('GROQ_API_KEY',''): api_key_present_enh_gen = True
        elif llm_provider_gen == 'openai' and temp_cfg_enh.get('OPENAI_API_KEY',''): api_key_present_enh_gen = True
    except Exception as e_apikey_read: print(f"Warning: Could not read API keys for LLM enhancer: {e_apikey_read}")

    if enhancer_enabled_gen and api_key_present_enh_gen and not is_derivative_action and not is_admin_text_cmd_gen and not is_img2img_gen:
        enhancer_info_gen['provider'] = llm_provider_gen
        system_prompt_llm_gen = SDXL_ENHANCER_SYSTEM_PROMPT if current_model_type_for_job == "sdxl" else FLUX_ENHANCER_SYSTEM_PROMPT
        enhanced_res_gen, err_msg_llm_gen = await util_enhance_prompt(prompt_base_gen, system_prompt_text_override=system_prompt_llm_gen, target_model_type=current_model_type_for_job)
        if enhanced_res_gen:
            if enhanced_res_gen.strip().lower() != prompt_base_gen.strip().lower():
                enhancer_info_gen.update({'used': True, 'enhanced_text': enhanced_res_gen})
                additional_info_msg_gen = f"\n> ✨ *LLM enhancer ({llm_provider_gen} for {current_model_type_for_job.upper()}) applied.*"
            else: additional_info_msg_gen = f"\n> ✨ *LLM enhancer ({llm_provider_gen} for {current_model_type_for_job.upper()}): Prompt unchanged.*"
        elif err_msg_llm_gen:
            enhancer_info_gen['error'] = err_msg_llm_gen
            additional_info_msg_gen = f"\n> ⚠️ *LLM enhancer ({llm_provider_gen} for {current_model_type_for_job.upper()}) failed: {err_msg_llm_gen}*"
    elif enhancer_enabled_gen and not api_key_present_enh_gen and not is_derivative_action and not is_admin_text_cmd_gen and not is_img2img_gen :
        additional_info_msg_gen = f"\n> ⚠️ *LLM enhancer ON ({llm_provider_gen} for {current_model_type_for_job.upper()}), but API key missing.*"; enhancer_info_gen['error'] = f"API Key missing for {llm_provider_gen}"
    elif is_derivative_action: pass 
    elif is_admin_text_cmd_gen: print("Skipping LLM Enhancer for admin text command.")
    elif is_img2img_gen: print("Skipping LLM Enhancer for img2img command.")

    results_list = []
    for run_idx_gen in range(run_times_gen):
        job_result = {
            "status": "error", "run_number": run_idx_gen + 1, "total_runs": run_times_gen,
            "message_content_details": {}, "view_type": None, "view_args": None,
            "job_data_for_qm": None, "error_message_text": "Unknown error during job preparation."
        }
        try:
            job_id_current_gen, mod_prompt_payload_gen, response_status_text_modify, job_details_current_gen = await ig_modify_prompt(
                original_prompt_text=prompt_base_gen, params_dict=params_dict_gen.copy(), enhancer_info=enhancer_info_gen,
                is_img2img=is_img2img_gen, explicit_seed=None,
                selected_model_name_with_prefix=selected_model_prefix_gen, 
                negative_prompt_text=negative_prompt_text_gen
            )
            
            if not job_id_current_gen:
                job_result["error_message_text"] = response_status_text_modify or "Failed to prepare prompt payload."
                results_list.append(job_result); continue
            job_details_current_gen['run_times'] = run_times_gen
            job_details_current_gen['model_type_for_enhancer'] = current_model_type_for_job 

            comfy_id_current_gen = None; queue_err_msg_gen = None
            try: comfy_id_current_gen = comfy_queue_prompt(mod_prompt_payload_gen, COMFYUI_HOST, COMFYUI_PORT)
            except ComfyConnectionRefusedError as e_conn_gen: queue_err_msg_gen = f"Error: Could not connect to ComfyUI ({e_conn_gen})."
            except Exception as e_q_inner_gen: queue_err_msg_gen = "Error: Failed to queue job with ComfyUI."; print(f"{queue_err_msg_gen}: {e_q_inner_gen}")
            if not comfy_id_current_gen:
                job_result["error_message_text"] = queue_err_msg_gen or "Failed to queue job with ComfyUI (unknown error)."
                results_list.append(job_result)
                if "Could not connect" in (queue_err_msg_gen or "") and run_idx_gen == 0 : break
                continue
            job_result["status"] = "success"; job_result["job_id"] = job_id_current_gen; job_result["comfy_prompt_id"] = comfy_id_current_gen
            job_result["view_type"] = "QueuedJobView"; job_result["view_args"] = {"comfy_prompt_id": comfy_id_current_gen}
            display_pref_gen = settings_gen.get('display_prompt_preference', 'enhanced')
            prompt_text_status_gen = job_details_current_gen.get("prompt", "[No Prompt Provided]")
            if display_pref_gen == 'original' and job_details_current_gen.get('original_prompt'): prompt_text_status_gen = job_details_current_gen.get('original_prompt')
            
            final_additional_info_msg = additional_info_msg_gen
            style_warning = job_details_current_gen.get('style_warning_message')
            if style_warning:
                final_additional_info_msg += f"\n> ⚠️ *Style Warning: {style_warning}*"
                
            job_result["message_content_details"] = {
                "user_mention": context_user.mention, "prompt_to_display": prompt_text_status_gen,
                "enhancer_used": enhancer_info_gen.get('used', False), "display_preference": display_pref_gen,
                "original_prompt_available": bool(job_details_current_gen.get('original_prompt')),
                "llm_provider": enhancer_info_gen.get('provider'), "enhancer_error": enhancer_info_gen.get('error'),
                "enhancer_applied_message_for_first_run": final_additional_info_msg if run_idx_gen == 0 else "",
                "run_number": run_idx_gen + 1, "total_runs": run_times_gen, 
                "model_type": current_model_type_for_job, 
                "seed": job_details_current_gen.get('seed', 'N/A'), "aspect_ratio": job_details_current_gen.get("aspect_ratio_str", "?:?"),
                "steps": str(job_details_current_gen.get('steps', '?')),
                "guidance_flux": f"{float(job_details_current_gen.get('guidance')):.1f}" if job_details_current_gen.get('guidance') is not None else 'N/A',
                "guidance_sdxl": f"{float(job_details_current_gen.get('guidance_sdxl')):.1f}" if job_details_current_gen.get('guidance_sdxl') is not None else 'N/A',
                "mp_size": job_details_current_gen.get("default_mp_size", "N/A") if not is_img2img_gen else None, 
                "style": job_details_current_gen.get('style', 'off'), "is_img2img": is_img2img_gen,
                "img_strength_percent": job_details_current_gen.get('img_strength_percent') if is_img2img_gen else None,
                "negative_prompt": job_details_current_gen.get('negative_prompt') if current_model_type_for_job == "sdxl" else None,
            }
            job_result["job_data_for_qm"] = {"comfy_prompt_id": comfy_id_current_gen, "channel_id": context_channel.id, "user_id": context_user.id, "user_name": context_user.name, "user_mention": context_user.mention, **job_details_current_gen}
            results_list.append(job_result)
        except Exception as e_gen_loop_outer:
            job_result["error_message_text"] = f"Unexpected error: {e_gen_loop_outer}"
            results_list.append(job_result); traceback.print_exc()
    return results_list

async def process_upscale_request(context_user, context_channel, referenced_message_obj, image_idx, is_interaction, initial_interaction_obj=None):
    await _ensure_ws_client_id()
    if not referenced_message_obj.attachments or len(referenced_message_obj.attachments) < image_idx:
        return [{"status": "error", "error_message_text": f"Error: Cannot find image #{image_idx} in referenced message."}]
    target_attachment_obj = referenced_message_obj.attachments[image_idx-1]
    if not target_attachment_obj.content_type or not target_attachment_obj.content_type.startswith('image/'):
        return [{"status": "error", "error_message_text": f"Error: Attachment #{image_idx} is not a valid image."}]

    original_job_id_str = extract_job_id(target_attachment_obj.filename)
    message_content_str = initial_interaction_obj.message.content if is_interaction and initial_interaction_obj and initial_interaction_obj.message else "" 

    job_id_ups, modified_prompt_ups, response_status_ups, job_details_ups = up_modify_upscale_prompt(message_content_str, referenced_message_obj, target_attachment_obj.url, image_idx)
    if not job_id_ups:
        return [{"status": "error", "error_message_text": response_status_ups or "Failed to prepare upscale request."}]
    comfy_id_ups = None; queue_err_ups = None
    try: comfy_id_ups = comfy_queue_prompt(modified_prompt_ups, COMFYUI_HOST, COMFYUI_PORT)
    except ComfyConnectionRefusedError as e_conn_ref: queue_err_ups = f"Error: Could not connect to ComfyUI ({e_conn_ref})."
    except Exception as e_q_ups: queue_err_ups = "Error: Failed to queue upscale job with ComfyUI."; print(f"{queue_err_ups}: {e_q_ups}")
    if not comfy_id_ups:
        return [{"status": "error", "error_message_text": queue_err_ups or "Failed to queue upscale with ComfyUI (unknown error)."}]

    job_data_for_qm_ups = {"job_id":job_id_ups, "comfy_prompt_id":comfy_id_ups, "type":"upscale", "original_prompt_id":original_job_id_str, "channel_id":context_channel.id,"user_id":context_user.id, "user_name":context_user.name, "user_mention":context_user.mention, **job_details_ups}
    prompt_disp_ups = job_details_ups.get("prompt", "[Original Prompt]"); seed_disp_ups = job_details_ups.get('seed','N/A'); style_disp_ups = job_details_ups.get('style','N/A'); ar_disp_ups = job_details_ups.get("aspect_ratio_str", "?:?"); factor_disp_ups = f"{job_details_ups.get('upscale_factor', '?'):.2f}x"; denoise_disp_ups = job_details_ups.get('denoise', '?')
    model_type_disp_ups = job_details_ups.get('model_type_for_enhancer', 'Unknown').upper() 
    
    msg_details = {
        "user_mention": context_user.mention, "image_index": image_idx, "original_job_id": original_job_id_str or 'N/A',
        "model_type": model_type_disp_ups, "prompt_to_display": prompt_disp_ups, "seed": seed_disp_ups,
        "style": style_disp_ups, "aspect_ratio": ar_disp_ups, "upscale_factor": factor_disp_ups, "denoise": denoise_disp_ups,
        "job_type": "upscale", "style_warning_message": job_details_ups.get("style_warning_message")
    }
    return [{
        "status": "success", "job_id": job_id_ups, "comfy_prompt_id": comfy_id_ups,
        "message_content_details": msg_details, "view_type": "QueuedJobView",
        "view_args": {"comfy_prompt_id": comfy_id_ups}, "job_data_for_qm": job_data_for_qm_ups
    }]

async def process_variation_request(context_user, context_channel, referenced_message_obj, variation_type_str, image_idx, edited_prompt_str=None, edited_neg_prompt_str=None, is_interaction=None, initial_interaction_obj=None):
    await _ensure_ws_client_id()
    if not referenced_message_obj.attachments or len(referenced_message_obj.attachments) < image_idx:
        return [{"status": "error", "error_message_text": f"Error: Cannot find image #{image_idx}."}]
    target_attachment_var = referenced_message_obj.attachments[image_idx-1]
    if not target_attachment_var.content_type or not target_attachment_var.content_type.startswith('image/'):
        return [{"status": "error", "error_message_text": f"Error: Attachment #{image_idx} is not an image."}]

    original_job_id_var = extract_job_id(target_attachment_var.filename)
    message_content_var = initial_interaction_obj.message.content if is_interaction and initial_interaction_obj and initial_interaction_obj.message else ""

    job_id_var, mod_prompt_var, resp_status_var, job_details_var = modify_variation_prompt(
        message_content_var, referenced_message_obj, variation_type_str, target_attachment_var.url, image_idx, edited_prompt_str, edited_neg_prompt_str
    )
    if not job_id_var: return [{"status": "error", "error_message_text": resp_status_var or "Failed to prepare variation."}]
    
    comfy_id_var = None; queue_err_var = None
    try: comfy_id_var = comfy_queue_prompt(mod_prompt_var, COMFYUI_HOST, COMFYUI_PORT)
    except ComfyConnectionRefusedError as e_conn_ref_var: queue_err_var = f"Error: Could not connect to ComfyUI ({e_conn_ref_var})."
    except Exception as e_q_var: queue_err_var = "Error: Failed to queue variation job."; print(f"{queue_err_var}: {e_q_var}")
    if not comfy_id_var: return [{"status": "error", "error_message_text": queue_err_var or "Failed to queue variation."}]

    job_data_for_qm_var = {"job_id":job_id_var, "comfy_prompt_id":comfy_id_var, "type":"variation", "variation_type":variation_type_str, "original_prompt_id":original_job_id_var, "channel_id":context_channel.id,"user_id":context_user.id, "user_name":context_user.name, "user_mention":context_user.mention, **job_details_var}
    prompt_disp_var = job_details_var.get("prompt", "[Original Prompt]"); seed_disp_var = job_details_var.get('seed','N/A'); style_disp_var = job_details_var.get('style','N/A'); ar_disp_var = job_details_var.get("aspect_ratio_str", "?:?"); steps_disp_var = str(job_details_var.get('steps','?'))
    desc_var = "Weak Variation 🤏" if variation_type_str == 'weak' else "Strong Variation 💪"
    model_type_disp_var = job_details_var.get('model_type_for_enhancer', 'Unknown').upper() 
    
    source_job_id_enh_check = job_details_var.get('parameters_used',{}).get('source_job_id')
    enhancer_ref_text = ""
    if source_job_id_enh_check and source_job_id_enh_check != 'unknownSrc':
        source_job_data_enh = queue_manager.get_job_data_by_id(source_job_id_enh_check)
        if source_job_data_enh and source_job_data_enh.get('enhancer_used'):
            provider_enh = source_job_data_enh.get('llm_provider', "LLM").capitalize()
            enhancer_ref_text = f"\n> `(Based on Enhanced Prompt via {provider_enh})`"

    msg_details_var = {
        "user_mention": context_user.mention, "prompt_to_display": prompt_disp_var,
        "description": desc_var, "image_index": image_idx, "original_job_id": original_job_id_var or 'N/A',
        "model_type": model_type_disp_var, "seed": seed_disp_var, "aspect_ratio": ar_disp_var,
        "steps": steps_disp_var, "style": style_disp_var, "is_remixed": edited_prompt_str is not None,
        "enhancer_reference_text": enhancer_ref_text, "job_type": "variation",
        "style_warning_message": job_details_var.get("style_warning_message")
    }
    return [{
        "status": "success", "job_id": job_id_var, "comfy_prompt_id": comfy_id_var,
        "message_content_details": msg_details_var, "view_type": "QueuedJobView",
        "view_args": {"comfy_prompt_id": comfy_id_var}, "job_data_for_qm": job_data_for_qm_var
    }]

async def process_rerun_request(context_user, context_channel, referenced_message_obj, run_times_count, is_interaction, initial_interaction_obj=None):
    original_job_data_rerun = queue_manager.get_job_data(referenced_message_obj.id, referenced_message_obj.channel.id)
    if not original_job_data_rerun and referenced_message_obj.attachments:
        job_id_from_file_rerun = extract_job_id(referenced_message_obj.attachments[0].filename)
        if job_id_from_file_rerun: original_job_data_rerun = queue_manager.get_job_data_by_id(job_id_from_file_rerun)
    if not original_job_data_rerun:
        return [{"status": "error", "error_message_text": "Error: Cannot find original job data for rerun."}]
    
    prompt_for_rerun_str = reconstruct_full_prompt_string(original_job_data_rerun)
    if not prompt_for_rerun_str:
        return [{"status": "error", "error_message_text": "Error: Cannot reconstruct original prompt for rerun."}]
    
    prompt_for_rerun_str = re.sub(r'\s--seed\s+\d+\b', '', prompt_for_rerun_str, flags=re.I).strip()
    prompt_for_rerun_str = re.sub(r'\s--r\s+\d+\b', '', prompt_for_rerun_str, flags=re.I).strip()
    if run_times_count > 1: prompt_for_rerun_str += f" --r {run_times_count}"
    
    current_settings_rerun = load_settings()
    selected_model_rerun = current_settings_rerun.get('selected_model')
    model_type_for_rerun = "flux" 
    if selected_model_rerun and ":" in selected_model_rerun:
        model_type_for_rerun = selected_model_rerun.split(":",1)[0].strip().lower()
    elif selected_model_rerun: 
        if selected_model_rerun.endswith((".gguf",".sft")): model_type_for_rerun = "flux"
        else: model_type_for_rerun = "sdxl"
    
    return await execute_generation_logic(
        context_user, context_channel, prompt_for_rerun_str,
        is_interaction_context=is_interaction,
        initial_interaction_object=initial_interaction_obj,
        model_type_override=model_type_for_rerun, 
        is_derivative_action=True 
    )

async def process_kontext_edit_request(
    context_user: discord.User,
    context_channel: discord.abc.Messageable,
    instruction: str,
    image_urls: list,
    initial_interaction_obj: discord.Interaction | None = None
):
    """Handles a Kontext edit request from start to finish."""
    await _ensure_ws_client_id()
    settings = load_settings()
    
    param_pattern = r'\s--(\w+)(?:\s+("([^"]*)"|((?:(?!--|\s--).)+)|([^\s]+)))?'
    params_dict = {}
    clean_instruction = instruction
    first_param_match = re.search(r'\s--\w+', instruction)
    
    if first_param_match:
        clean_instruction = instruction[:first_param_match.start()].strip()
        param_string = instruction[first_param_match.start():]
        param_matches = re.findall(param_pattern, param_string)
        for key, _, quoted_val, unquoted_compound, unquoted_single in param_matches:
            value = quoted_val if quoted_val else (unquoted_compound if unquoted_compound else unquoted_single)
            params_dict[key.lower()] = value.strip() if value else True

    enhancer_info = {'used': False, 'provider': None, 'enhanced_text': None, 'error': None}
    enhanced_instruction = clean_instruction
    
    if settings.get('llm_enhancer_enabled', False):
        enhancer_info['provider'] = settings.get('llm_provider', 'gemini')
        enhanced_res, err_msg = await util_enhance_prompt(
            clean_instruction, 
            system_prompt_text_override=KONTEXT_ENHANCER_SYSTEM_PROMPT, 
            target_model_type="kontext",
            image_urls=image_urls
        )
        if enhanced_res:
            enhanced_instruction = enhanced_res
            enhancer_info.update({'used': True, 'enhanced_text': enhanced_res})
        elif err_msg:
            enhancer_info['error'] = err_msg

    primary_image_url = image_urls[0]
    dimensions = await asyncio.to_thread(get_image_dimensions, primary_image_url)
    final_aspect_ratio = "1:1"
    if dimensions:
        w, h = dimensions
        if h > 0:
            common_divisor = math.gcd(w, h)
            final_aspect_ratio = f"{w//common_divisor}:{h//common_divisor}"
    
    if params_dict.get('ar') and re.match(r'^\d+:\d+$', str(params_dict['ar'])):
        final_aspect_ratio = str(params_dict['ar'])

    final_steps = settings.get('steps', 32)
    if params_dict.get('steps') and str(params_dict.get('steps')).isdigit():
        final_steps = int(params_dict['steps'])

    final_guidance = 3.0
    if params_dict.get('g'):
        try:
            final_guidance = float(params_dict['g'])
        except (ValueError, TypeError): pass

    seed = generate_seed()
    source_job_id = "slash_command"
    if initial_interaction_obj and initial_interaction_obj.message and initial_interaction_obj.message.attachments:
        source_job_id = extract_job_id(initial_interaction_obj.message.attachments[0].filename) or "unknown"

    job_id, workflow_payload, status_msg, job_details = modify_kontext_prompt(
        image_urls=image_urls,
        instruction=enhanced_instruction,
        user_settings=settings,
        base_seed=seed,
        aspect_ratio=final_aspect_ratio,
        steps_override=final_steps,
        guidance_override=final_guidance,
        source_job_id=source_job_id
    )
    
    if not workflow_payload:
        await safe_interaction_response(initial_interaction_obj, f"Error: {status_msg}", ephemeral=True)
        return

    comfy_id = None
    try:
        comfy_id = comfy_queue_prompt(workflow_payload, COMFYUI_HOST, COMFYUI_PORT)
    except Exception as e:
        await safe_interaction_response(initial_interaction_obj, f"Error queueing job with ComfyUI: {e}", ephemeral=True)
        return
        
    if not comfy_id:
        await safe_interaction_response(initial_interaction_obj, "Failed to queue job with ComfyUI (unknown error).", ephemeral=True)
        return

    from bot_ui_components import QueuedJobView
    
    content = (f"{context_user.mention}: Editing with Kontext...\n"
               f"> **Instruction:** `{textwrap.shorten(instruction, 100, placeholder='...')}`\n"
               f"> **Images:** {len(image_urls)}, **AR:** `{final_aspect_ratio}`, **Seed:** `{seed}`\n"
               f"> **Status:** Queued...")
    
    if enhancer_info['used']:
        content += " ✨"
    
    view = QueuedJobView(comfy_prompt_id=comfy_id)
    sent_message = await safe_interaction_response(initial_interaction_obj, content=content, view=view)
    
    if sent_message:
        job_data_for_qm = {
            "comfy_prompt_id": comfy_id, "channel_id": context_channel.id,
            "user_id": context_user.id, "user_name": context_user.name,
            "user_mention": context_user.mention, "message_id": sent_message.id,
            "enhancer_used": enhancer_info['used'], "llm_provider": enhancer_info['provider'],
            "original_prompt": instruction, 
            "enhanced_prompt": enhanced_instruction,
            "prompt": enhanced_instruction,
            "enhancer_error": enhancer_info['error'], **job_details
        }
        queue_manager.add_job(job_id, job_data_for_qm)
        ws_client = WebsocketClient()
        if ws_client.is_connected:
            await ws_client.register_prompt(comfy_id, sent_message.id, sent_message.channel.id)
