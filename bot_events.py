# --- START OF FILE bot_events.py ---
import discord
import traceback
import re # For reply command parsing
import asyncio # For validate_models_against_comfyui
import textwrap # For message construction
import os
import json

from bot_config_loader import print_startup_info, ADMIN_ID, COMFYUI_HOST, COMFYUI_PORT, print_output_dirs
from bot_core_logic import check_output_folders, process_cancel_request, execute_generation_logic
from bot_commands import (
    handle_reply_upscale,
    handle_reply_vary,
    handle_reply_rerun
)
from file_management import extract_job_id, delete_job_files_and_message, remove_message
from queue_manager import queue_manager
from utils.show_prompt import reconstruct_full_prompt_string
from utils.message_utils import send_long_message
from model_scanner import (
    update_models_list,
    scan_clip_files,
    update_checkpoints_list,
    update_qwen_models_list,
    update_wan_models_list,
)
from comfyui_api import get_available_comfyui_models
from settings_manager import load_settings, load_styles_config
from upscaling import upscale_model_exists
from bot_ui_components import QueuedJobView


def _option_matches(selected_option: str, available_options):
    """Return True if *selected_option* matches any value in *available_options*.

    Comparison is case-insensitive and also tolerates situations where ComfyUI
    reports fully-qualified paths while our stored selection only contains a
    base filename (or vice versa).
    """

    if not selected_option or not available_options:
        return False

    selected_normalized = selected_option.strip().lower()
    selected_basename = os.path.basename(selected_normalized)

    for option in available_options:
        if not isinstance(option, str):
            continue
        option_normalized = option.strip().lower()
        if selected_normalized == option_normalized:
            return True
        if selected_basename and selected_basename == os.path.basename(option_normalized):
            return True

    return False

BLOCKED_USER_IDS = set()
BLOCKLIST_FILE = "blocklist.json"

def load_blocklist():
    global BLOCKED_USER_IDS
    if os.path.exists(BLOCKLIST_FILE):
        try:
            with open(BLOCKLIST_FILE, 'r') as f:
                loaded_list = json.load(f)
                if isinstance(loaded_list, list):
                    BLOCKED_USER_IDS = {int(uid) for uid in loaded_list if isinstance(uid, (int, str)) and str(uid).isdigit()}
                else:
                    BLOCKED_USER_IDS = set()
            print(f"Loaded {len(BLOCKED_USER_IDS)} user(s) from blocklist.")
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            BLOCKED_USER_IDS = set()
            print(f"Warning: Could not parse {BLOCKLIST_FILE}: {e}. Blocklist is empty.")
    else:
        BLOCKED_USER_IDS = set()

async def validate_models_against_comfyui(bot):
    try:
        print("Validating selected models against ComfyUI API...")
        available_models = await asyncio.to_thread(get_available_comfyui_models, COMFYUI_HOST, COMFYUI_PORT)
        unet_count = len(available_models.get('unet', [])); checkpoint_count = len(available_models.get('checkpoint', [])); clip_count = len(available_models.get('clip', [])); vae_count = len(available_models.get('vae', [])); upscaler_count = len(available_models.get('upscaler', []))
        print(f"\n=== Available Models (API Summary) ===\nUNET (Flux): {unet_count}, CHECKPOINT (SDXL): {checkpoint_count}, CLIP: {clip_count}, VAE: {vae_count}, UPSCALER: {upscaler_count}\n" + "="*36)
        if unet_count == 0 and checkpoint_count == 0 and clip_count == 0 : print("WARNING: ComfyUI API returned no Flux UNETs, SDXL Checkpoints, or CLIPs. Validation cannot proceed effectively."); return False
        settings = load_settings(); selected_model_prefix = settings.get('selected_model'); sel_t5 = settings.get('selected_t5_clip'); sel_l = settings.get('selected_clip_l'); sel_upscaler = settings.get('selected_upscale_model'); issues = False
        if selected_model_prefix:
            m_type, m_name = (selected_model_prefix.split(":",1)[0].strip().lower(), selected_model_prefix.split(":",1)[1].strip()) if ":" in selected_model_prefix else (None, selected_model_prefix.strip())
            if m_type == "flux" and not _option_matches(m_name, available_models.get("unet", [])):
                print(f"⚠️ WARNING: Selected Flux Model '{m_name}' not found in ComfyUI UNET list!"); issues=True
            elif m_type == "sdxl" and not _option_matches(m_name, available_models.get("checkpoint", [])):
                print(f"⚠️ WARNING: Selected SDXL Checkpoint '{m_name}' not found in ComfyUI CHECKPOINT list!"); issues=True
            elif not m_type : print(f"❓ Info: Selected model '{selected_model_prefix}' has missing type prefix.")
        else: print("❓ Info: No default model selected.")
        available_clips = available_models.get("clip", [])
        if sel_t5 and not _option_matches(sel_t5, available_clips): print(f"⚠️ WARNING: Selected T5 CLIP '{sel_t5}' not found!"); issues=True
        elif not sel_t5: print("❓ Info: No T5 CLIP selected.")
        if sel_l and not _option_matches(sel_l, available_clips): print(f"⚠️ WARNING: Selected CLIP-L '{sel_l}' not found!"); issues=True
        elif not sel_l: print("❓ Info: No CLIP-L selected.")
        if sel_upscaler and sel_upscaler != "None":
            api_upscalers = available_models.get("upscaler", [])
            if not _option_matches(sel_upscaler, api_upscalers):
                if upscale_model_exists(sel_upscaler):
                    print(
                        f"ℹ️ Info: Selected Upscaler '{sel_upscaler}' available locally "
                        "but not reported by ComfyUI API."
                    )
                else:
                    print(f"⚠️ WARNING: Selected Upscaler '{sel_upscaler}' not found!"); issues=True
        elif not sel_upscaler or sel_upscaler == "None": print("❓ Info: No Upscaler selected.")
        if issues: print("‼️-> Please update settings or check ComfyUI models.")
        else: print("✅ Configured models appear valid according to ComfyUI API.")
        return not issues
    except Exception as e: print(f"Error during model validation: {e}"); traceback.print_exc(); return False

def update_models_on_startup():
    print("Scanning models/CLIPs/checkpoints on startup...")
    try: update_models_list('config.json', 'modelslist.json'); print("Flux models list updated.")
    except Exception as e: print(f"ERROR updating Flux models list: {e}"); traceback.print_exc()
    try: update_checkpoints_list('config.json', 'checkpointslist.json'); print("SDXL checkpoints list updated.")
    except Exception as e: print(f"ERROR updating SDXL checkpoints list: {e}"); traceback.print_exc()
    try: update_qwen_models_list('config.json', 'qwenmodels.json'); print("Qwen models list updated.")
    except Exception as e: print(f"ERROR updating Qwen models list: {e}"); traceback.print_exc()
    try: update_wan_models_list('config.json', 'wanmodels.json'); print("WAN models list updated.")
    except Exception as e: print(f"ERROR updating WAN models list: {e}"); traceback.print_exc()
    try: scan_clip_files('config.json', 'cliplist.json'); print("CLIP list updated.")
    except Exception as e: print(f"ERROR updating CLIP list: {e}"); traceback.print_exc()

async def on_bot_ready(bot):
    print(f'\n{bot.user.name}#{bot.user.discriminator} connected to Discord!')
    print(f"User ID: {bot.user.id}"); print("-" * 20)
    print_startup_info(); styles_config_on_ready_unused = load_styles_config(); print(f"Styles Loaded: {len(styles_config_on_ready_unused)}")
    print_output_dirs(); update_models_on_startup(); await validate_models_against_comfyui(bot)
    try:
        print("Registering/syncing slash commands..."); synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash commands globally.")
    except discord.errors.Forbidden as e_sync_forbidden: print(f"ERROR syncing commands: Bot lacks 'applications.commands' scope. {e_sync_forbidden}")
    except Exception as e_sync: print(f"Error during command sync: {e_sync}"); traceback.print_exc()
    print("-" * 20); load_blocklist(); print("Bot is ready and listening!")
    bot.loop.create_task(check_output_folders(bot))

async def on_bot_message(bot, message: discord.Message):
    if message.author == bot.user or message.author.bot: return
    if message.author.id in BLOCKED_USER_IDS: return

    # Admin check by ID
    is_admin = str(message.author.id) == str(ADMIN_ID)

    if message.content.startswith('/gen '):
        if not is_admin:
            if message.guild:
                try: await message.channel.send(f"> {message.author.mention} Please use the slash command `/gen` or `/please`.", delete_after=5); await message.delete(delay=1)
                except (discord.NotFound, discord.Forbidden): pass
            return
        prompt_text_gen = message.content[5:].strip()
        if not prompt_text_gen:
            try: await message.reply("Please provide a prompt.", delete_after=10)
            except Exception: pass
            return
        settings_admin_gen = load_settings(); model_type_override_admin = "flux"
        selected_model_cfg_admin = settings_admin_gen.get('selected_model')
        if selected_model_cfg_admin and ":" in selected_model_cfg_admin: model_type_override_admin = selected_model_cfg_admin.split(":",1)[0].strip().lower()
        job_results_list = await execute_generation_logic(context_user=message.author, context_channel=message.channel, prompt=prompt_text_gen, is_interaction_context=False, initial_interaction_object=None, model_type_override=model_type_override_admin)
        error_summary_admin_gen = []
        for idx, result in enumerate(job_results_list):
            if result["status"] == "success":
                msg_details = result["message_content_details"]
                content = (f"{msg_details['user_mention']}: `{textwrap.shorten(msg_details['prompt_to_display'], 1000, placeholder='...')}`")
                if msg_details['enhancer_used'] and msg_details['display_preference'] == 'enhanced': content += " ✨"
                model_display = msg_details.get('model_type_display') or msg_details.get('model_type', 'UNKNOWN').upper()
                if msg_details['total_runs'] > 1: content += f" (Job {msg_details['run_number']}/{msg_details['total_runs']} - {model_display})"
                else: content += f" ({model_display})"
                content += f"\n> **Seed:** `{msg_details['seed']}`"
                if msg_details['aspect_ratio']: content += f", **AR:** `{msg_details['aspect_ratio']}`"
                if msg_details['steps']: content += f", **Steps:** `{msg_details['steps']}`"
                guidance_label = msg_details.get('guidance_display_label')
                guidance_value = msg_details.get('guidance_display_value')
                if guidance_label and guidance_value is not None:
                    content += f", **{guidance_label}:** `{guidance_value}`"
                if msg_details['mp_size'] is not None: content += f", **MP:** `{msg_details['mp_size']}`"
                content += f"\n> **Style:** `{msg_details['style']}`"
                if msg_details['is_img2img']: content += f", **Strength:** `{msg_details['img_strength_percent']}%`"
                if msg_details['negative_prompt']: content += f"\n> **No:** `{textwrap.shorten(msg_details['negative_prompt'], 100, placeholder='...')}`"
                content += "\n> Prompt queued. Generating... Please wait."
                if msg_details.get("enhancer_applied_message_for_first_run"): content += msg_details["enhancer_applied_message_for_first_run"]
                view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
                sent_msg = await message.channel.send(content, view=view_to_send)
                if sent_msg and result["job_data_for_qm"]:
                    job_data_to_add = result["job_data_for_qm"]; job_data_to_add["message_id"] = sent_msg.id
                    queue_manager.add_job(result["job_id"], job_data_to_add)
            elif result["status"] == "error":
                error_summary_admin_gen.append(f"Job {result['run_number']}: {result.get('error_message_text', 'Unknown error.')}")
        if error_summary_admin_gen:
            await message.channel.send(f"{message.author.mention} Admin /gen request processed with error(s):\n- " + "\n- ".join(error_summary_admin_gen))
        return

    if message.reference and message.reference.resolved and message.reference.resolved.author == bot.user:
        ref_msg_reply = message.reference.resolved; content_lower_reply = message.content.lower().strip()
        is_admin_reply = str(message.author.id) == str(ADMIN_ID)
        job_data_reply = queue_manager.get_job_data(ref_msg_reply.id, ref_msg_reply.channel.id)
        job_id_reply = job_data_reply.get('job_id') if job_data_reply else (extract_job_id(ref_msg_reply.attachments[0].filename) if ref_msg_reply.attachments else None)
        if not job_data_reply and job_id_reply: job_data_reply = queue_manager.get_job_data_by_id(job_id_reply)
        is_owner_reply = job_data_reply and job_data_reply.get('user_id') == message.author.id
        can_action_reply = is_admin_reply or is_owner_reply; should_delete_trigger_msg = False
        try:
            if content_lower_reply == '--remove':
                if can_action_reply: await remove_message(ref_msg_reply, message); should_delete_trigger_msg = True
                else: await message.reply("Permission denied.", delete_after=10)
            elif content_lower_reply == '--delete':
                if job_id_reply and can_action_reply: await delete_job_files_and_message(job_id_reply, ref_msg_reply, None); should_delete_trigger_msg = True
                else: await message.reply("Permission denied or Job ID not found.", delete_after=10)
            elif content_lower_reply == '--show':
                if is_admin_reply:
                    prompt_text_show = reconstruct_full_prompt_string(job_data_reply) if job_data_reply else "Prompt data not found."
                    if await send_long_message(message.author, f"Prompt for msg {ref_msg_reply.id}:\n```\n{prompt_text_show}\n```"): await message.add_reaction("✉️")
                    else: await message.reply("Could not send DM.", delete_after=10)
                    should_delete_trigger_msg = True
                else: await message.reply("Admin only.", delete_after=10)
            elif content_lower_reply.startswith('--up'):
                if can_action_reply:
                    await bot.commands_module['handle_reply_upscale'](message, ref_msg_reply); should_delete_trigger_msg = True
                else: await message.reply("Permission denied.", delete_after=10)
            elif content_lower_reply.startswith('--vary'):
                if can_action_reply:
                    v_type_reply = 'weak' if ' w' in content_lower_reply else ('strong' if ' s' in content_lower_reply else None)
                    if v_type_reply:
                        await bot.commands_module['handle_reply_vary'](message, ref_msg_reply, v_type_reply); should_delete_trigger_msg = True
                    else: await message.reply("Usage: `--vary w` or `--vary s`", delete_after=10)
                else: await message.reply("Permission denied.", delete_after=10)
            elif content_lower_reply.startswith('--r'):
                if can_action_reply:
                    parts_reply_r = content_lower_reply.split(); times_reply_r = int(parts_reply_r[1]) if len(parts_reply_r)>1 and parts_reply_r[1].isdigit() else 1
                    await bot.commands_module['handle_reply_rerun'](message, ref_msg_reply, min(max(1, times_reply_r), 10)); should_delete_trigger_msg = True
                else: await message.reply("Permission denied.", delete_after=10)

            if should_delete_trigger_msg:
                try: await message.delete()
                except (discord.NotFound, discord.Forbidden): pass
        except Exception as e_reply_cmd: print(f"Error processing reply command '{content_lower_reply}': {e_reply_cmd}"); traceback.print_exc()

async def on_bot_reaction_add(bot, reaction: discord.Reaction, user: discord.User | discord.Member):
    if user.bot or reaction.message.author != bot.user or str(reaction.emoji) != '🗑️': return
    is_admin_react = str(user.id) == str(ADMIN_ID)
    job_data_react = queue_manager.get_job_data(reaction.message.id, reaction.message.channel.id)
    job_id_react = job_data_react.get('job_id') if job_data_react else (extract_job_id(reaction.message.attachments[0].filename) if reaction.message.attachments else None)
    if not job_data_react and job_id_react: job_data_react = queue_manager.get_job_data_by_id(job_id_react)
    is_owner_react = job_data_react and job_data_react.get('user_id') == user.id
    if is_admin_react or is_owner_react:
        print(f"User ID {user.id} react-deleted message {reaction.message.id} (Job ID: {job_id_react or 'N/A'}).")
        await delete_job_files_and_message(job_id_react, reaction.message, None)
    else:
        try: await reaction.remove(user)
        except discord.Forbidden: print(f"No permission to remove reaction for {user.name} on msg {reaction.message.id}")
        except Exception as e_rem_react_user: print(f"Error removing reaction: {e_rem_react_user}")
