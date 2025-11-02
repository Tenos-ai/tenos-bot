# --- START OF FILE bot_commands.py ---
import discord
from discord import app_commands # type: ignore
import textwrap

from bot_core_logic import (
    process_upscale_request as core_process_upscale,
    process_variation_request as core_process_variation,
    process_rerun_request as core_process_rerun,
    execute_generation_logic
)
from bot_ui_components import QueuedJobView
from queue_manager import queue_manager
from utils.message_utils import safe_interaction_response
from websocket_client import WebsocketClient # Import the websocket client
from settings_manager import load_settings # For getting current model type

_bot_instance_commands = None
def register_bot_instance(bot_instance):
    global _bot_instance_commands
    _bot_instance_commands = bot_instance

def setup_bot_commands(bot):
    register_bot_instance(bot)
    return {
        'handle_reply_upscale': handle_reply_upscale,
        'handle_reply_vary': handle_reply_vary,
        'handle_reply_rerun': handle_reply_rerun,
        'handle_gen_command': handle_gen_command
    }

async def handle_gen_command(
    context: discord.Interaction | discord.Message,
    prompt: str,
    is_modal_submission: bool = False,
    model_type_override: str = None, # This will be the CURRENTLY selected model for derivative actions
    is_derivative_action: bool = False
):
    user_obj_ctx: discord.User | discord.Member
    channel_obj_ctx: discord.abc.MessageableChannel
    is_interaction_ctx: bool = isinstance(context, discord.Interaction)
    initial_interaction_ctx_obj: discord.Interaction | None = None
    initial_response_message_object = None 
    first_message_sent_this_command = False

    if is_interaction_ctx:
        interaction_context: discord.Interaction = context # type: ignore
        user_obj_ctx = interaction_context.user
        if interaction_context.channel is None:
            if interaction_context.type == discord.InteractionType.application_command and interaction_context.guild_id is None:
                 if user_obj_ctx.dm_channel is None: await user_obj_ctx.create_dm()
                 channel_obj_ctx = user_obj_ctx.dm_channel # type: ignore
                 if channel_obj_ctx is None:
                    print(f"Critical Error: Could not establish DM channel for interaction by {user_obj_ctx.id}.")
                    if not interaction_context.response.is_done(): await interaction_context.response.send_message("Error: Could not determine channel (DM creation failed).", ephemeral=True)
                    else: await interaction_context.followup.send("Error: Could not determine channel (DM creation failed).", ephemeral=True)
                    return
            else:
                 print(f"Critical Error: Could not determine channel for non-DM interaction by {user_obj_ctx.id}.")
                 if not interaction_context.response.is_done(): await interaction_context.response.send_message("Error: Could not determine channel.", ephemeral=True)
                 else: await interaction_context.followup.send("Error: Could not determine channel.", ephemeral=True)
                 return
        else: channel_obj_ctx = interaction_context.channel
        initial_interaction_ctx_obj = interaction_context

        if not initial_interaction_ctx_obj.response.is_done():
            try:
                await initial_interaction_ctx_obj.response.defer(ephemeral=False, thinking=True)
            except discord.errors.InteractionResponded:
                pass
            except Exception as e_defer:
                print(f"Error deferring in handle_gen_command: {e_defer}")
                try:
                    await initial_interaction_ctx_obj.followup.send("An error occurred while processing your request (defer failed).", ephemeral=True)
                except: pass 
                return
    else: 
        message_context: discord.Message = context # type: ignore
        user_obj_ctx = message_context.author
        channel_obj_ctx = message_context.channel
        initial_interaction_ctx_obj = None

    effective_is_derivative = is_derivative_action or is_modal_submission
    
    # If it's a derivative action OR a modal submission (which often implies a derivative like edit/remix),
    # model_type_override should already be set to the current model type by the caller.
    # If it's a brand new /gen command (not derivative, not modal), model_type_override will be None,
    # and execute_generation_logic will use the default from settings.
    
    # No change needed here for model_type_override itself, as it's passed in.
    # The CALLERS of handle_gen_command (e.g., for reruns, edits from modals)
    # need to ensure they pass the correct CURRENT model type.

    job_results_list = await execute_generation_logic(
        context_user=user_obj_ctx,
        context_channel=channel_obj_ctx, 
        prompt=prompt,
        is_interaction_context=is_interaction_ctx, 
        initial_interaction_object=initial_interaction_ctx_obj, 
        model_type_override=model_type_override, # Pass it through
        is_derivative_action=effective_is_derivative
    )

    error_summary_for_followup = []

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
            content += "\n> **Status:** Queued..."
            if msg_details.get("enhancer_applied_message_for_first_run"): 
                content += msg_details["enhancer_applied_message_for_first_run"]

            view_to_send = None
            if result["view_type"] == "QueuedJobView" and result["view_args"]:
                view_to_send = QueuedJobView(**result["view_args"])

            sent_message_object = None
            if is_interaction_ctx and initial_interaction_ctx_obj is not None:
                if not first_message_sent_this_command:
                    try:
                        await initial_interaction_ctx_obj.edit_original_response(content=content, view=view_to_send)
                        initial_response_message_object = await initial_interaction_ctx_obj.original_response()
                        sent_message_object = initial_response_message_object
                    except Exception as e_edit_orig:
                        print(f"Error editing original response for job {result['job_id']}, trying followup: {e_edit_orig}")
                        sent_message_object = await safe_interaction_response(initial_interaction_ctx_obj, content, view=view_to_send, ephemeral=False)
                    first_message_sent_this_command = True
                else: 
                    sent_message_object = await safe_interaction_response(initial_interaction_ctx_obj, content, view=view_to_send, ephemeral=False)
            else: 
                sent_message_object = await channel_obj_ctx.send(content, view=view_to_send)

            if sent_message_object and result["job_data_for_qm"]:
                job_data_to_add = result["job_data_for_qm"]
                job_data_to_add["message_id"] = sent_message_object.id
                queue_manager.add_job(result["job_id"], job_data_to_add)
                # Register with websocket client
                ws_client = WebsocketClient()
                if ws_client.is_connected and result.get("comfy_prompt_id"):
                    await ws_client.register_prompt(result["comfy_prompt_id"], sent_message_object.id, sent_message_object.channel.id)
            elif not sent_message_object:
                print(f"ERROR: Failed to send/get message for job {result['job_id']}. Not fully added to QM.")
                error_summary_for_followup.append(f"Job {result['run_number']}: Failed to send status message.")
                if result["job_data_for_qm"]: queue_manager.add_job(result["job_id"], result["job_data_for_qm"])

        elif result["status"] == "error":
            err_msg = result.get("error_message_text", "Unknown error.")
            print(f"Error processing job {result['run_number']}/{result['total_runs']}: {err_msg}")
            error_summary_for_followup.append(f"Job {result['run_number']}: {err_msg}")

    if error_summary_for_followup:
        summary_text = f"Generation request processed with {len(error_summary_for_followup)} error(s):\n- " + "\n- ".join(error_summary_for_followup)
        if is_interaction_ctx and initial_interaction_ctx_obj is not None:
            await safe_interaction_response(initial_interaction_ctx_obj, summary_text, ephemeral=True)
        else: 
            await channel_obj_ctx.send(f"{user_obj_ctx.mention} {summary_text}")

async def handle_reply_upscale(message: discord.Message, referenced_message: discord.Message):
    # core_process_upscale now uses the CURRENTLY selected model from settings.
    results = await core_process_upscale( 
        context_user=message.author,
        context_channel=message.channel,
        referenced_message_obj=referenced_message,
        image_idx=1, 
        is_interaction=False,
        initial_interaction_obj=None
    )
    for result in results:
        if result["status"] == "success":
            msg_details = result["message_content_details"]
            model_display = msg_details.get('model_type_display') or msg_details.get('model_type')
            content = (f"{msg_details['user_mention']}: Upscaling image #{msg_details['image_index']} from job `{msg_details['original_job_id']}` (Workflow: {model_display})\n" # model_type IS the current model
                       f"> **Using Prompt:** `{textwrap.shorten(msg_details['prompt_to_display'], 70, placeholder='...')}`\n"
                       f"> **Seed:** `{msg_details['seed']}`, **Style:** `{msg_details['style']}`, **Orig AR:** `{msg_details['aspect_ratio']}`\n"
                       f"> **Factor:** `{msg_details['upscale_factor']}`, **Denoise:** `{msg_details['denoise']}`\n"
                       f"> **Status:** Queued...")
            view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
            sent_msg = await message.channel.send(content, view=view_to_send)
            if sent_msg and result["job_data_for_qm"]:
                job_data_to_add = result["job_data_for_qm"]; job_data_to_add["message_id"] = sent_msg.id
                queue_manager.add_job(result["job_id"], job_data_to_add)
                ws_client = WebsocketClient()
                if ws_client.is_connected and result.get("comfy_prompt_id"):
                    await ws_client.register_prompt(result["comfy_prompt_id"], sent_msg.id, sent_msg.channel.id)
        elif result["status"] == "error":
            await message.channel.send(f"{message.author.mention} Error upscaling: {result.get('error_message_text', 'Unknown error.')}")

async def handle_reply_vary(message: discord.Message, referenced_message: discord.Message, variation_type: str):
    # core_process_variation now uses the CURRENTLY selected model from settings.
    results = await core_process_variation(
        context_user=message.author,
        context_channel=message.channel,
        referenced_message_obj=referenced_message,
        variation_type_str=variation_type,
        image_idx=1, 
        is_interaction=False,
        initial_interaction_obj=None
    )
    for result in results: 
        if result["status"] == "success":
            msg_details = result["message_content_details"]
            model_display = msg_details.get('model_type_display') or msg_details.get('model_type')
            content = (f"{msg_details['user_mention']}: `{textwrap.shorten(msg_details['prompt_to_display'], 50, placeholder='...')}` ({msg_details['description']} on img #{msg_details['image_index']} from `{msg_details['original_job_id']}` - {model_display})\n" # model_type IS the current model
                       f"> **Seed:** `{msg_details['seed']}`, **AR:** `{msg_details['aspect_ratio']}`, **Steps:** `{msg_details['steps']}`, **Style:** `{msg_details['style']}`")
            if msg_details.get('is_remixed'): 
                content += "\n> `(Remixed Prompt)`"
            
            enhancer_text_val_reply_vary = msg_details.get('enhancer_reference_text')
            if enhancer_text_val_reply_vary:
                content += f"\n{enhancer_text_val_reply_vary.strip()}"

            content += "\n> **Status:** Queued..."
            view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
            sent_msg = await message.channel.send(content, view=view_to_send)
            if sent_msg and result["job_data_for_qm"]:
                job_data_to_add = result["job_data_for_qm"]; job_data_to_add["message_id"] = sent_msg.id
                queue_manager.add_job(result["job_id"], job_data_to_add)
                ws_client = WebsocketClient()
                if ws_client.is_connected and result.get("comfy_prompt_id"):
                    await ws_client.register_prompt(result["comfy_prompt_id"], sent_msg.id, sent_msg.channel.id)
        elif result["status"] == "error":
            await message.channel.send(f"{message.author.mention} Error varying: {result.get('error_message_text', 'Unknown error.')}")

async def handle_reply_rerun(message: discord.Message, referenced_message: discord.Message, run_times: int):
    # core_process_rerun now calls execute_generation_logic with model_type_override set to CURRENT model
    job_results_list = await core_process_rerun(
        context_user=message.author,
        context_channel=message.channel,
        referenced_message_obj=referenced_message,
        run_times_count=run_times,
        is_interaction=False, 
        initial_interaction_obj=None
    )
    error_summary_rerun = []
    for idx, result in enumerate(job_results_list):
        if result["status"] == "success":
            msg_details = result["message_content_details"]
            content = (f"{msg_details['user_mention']}: `{textwrap.shorten(msg_details['prompt_to_display'], 1000, placeholder='...')}`")
            if msg_details['enhancer_used'] and msg_details['display_preference'] == 'enhanced': content += " ✨"
            model_display = msg_details.get('model_type_display') or msg_details.get('model_type', 'UNKNOWN').upper()
            content += f" (Rerun {idx+1}/{run_times} - {model_display})" # model_type IS the current model
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
            content += "\n> **Status:** Queued..."
            
            view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
            sent_msg = await message.channel.send(content, view=view_to_send)
            if sent_msg and result["job_data_for_qm"]:
                job_data_to_add = result["job_data_for_qm"]; job_data_to_add["message_id"] = sent_msg.id
                queue_manager.add_job(result["job_id"], job_data_to_add)
                ws_client = WebsocketClient()
                if ws_client.is_connected and result.get("comfy_prompt_id"):
                    await ws_client.register_prompt(result["comfy_prompt_id"], sent_msg.id, sent_msg.channel.id)
        elif result["status"] == "error":
            error_summary_rerun.append(f"Rerun job {idx+1}: {result.get('error_message_text', 'Unknown error.')}")

    if error_summary_rerun:
        await message.channel.send(f"{message.author.mention} Rerun request processed with error(s):\n- " + "\n".join(error_summary_rerun))
# --- END OF FILE bot_commands.py ---
