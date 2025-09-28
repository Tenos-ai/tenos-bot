# --- START OF FILE bot_commands.py ---
import discord
from discord import app_commands # type: ignore
from bot_core_logic import (
    process_upscale_request as core_process_upscale,
    process_variation_request as core_process_variation,
    process_rerun_request as core_process_rerun,
    execute_generation_logic
)
from bot_ui_components import QueuedJobView
from utils.message_utils import safe_interaction_response
from utils.discord_helpers import (
    format_generation_status,
    format_rerun_status,
    format_upscale_status,
    format_variation_status,
    register_job_with_queue,
)

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
            content = format_generation_status(msg_details)

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

            registration_success = await register_job_with_queue(result, sent_message_object)
            if not sent_message_object:
                print(f"ERROR: Failed to send/get message for job {result['job_id']}. Not fully added to QM.")
                error_summary_for_followup.append(f"Job {result['run_number']}: Failed to send status message.")
            elif not registration_success:
                print(f"Warning: Job {result['job_id']} could not be registered with the queue manager.")
                error_summary_for_followup.append(f"Job {result['run_number']}: Failed to register queue metadata.")

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
            content = format_upscale_status(msg_details)
            view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
            sent_msg = await message.channel.send(content, view=view_to_send)
            registration_success = await register_job_with_queue(result, sent_msg)
            if not sent_msg:
                print(f"ERROR: Failed to send upscale status message for job {result['job_id']}.")
            elif not registration_success:
                print(f"Warning: Upscale job {result['job_id']} could not be registered with the queue manager.")
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
            content = format_variation_status(msg_details)
            view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
            sent_msg = await message.channel.send(content, view=view_to_send)
            registration_success = await register_job_with_queue(result, sent_msg)
            if not sent_msg:
                print(f"ERROR: Failed to send variation status message for job {result['job_id']}.")
            elif not registration_success:
                print(f"Warning: Variation job {result['job_id']} could not be registered with the queue manager.")
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
            content = format_rerun_status(msg_details, idx + 1, run_times)

            view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
            sent_msg = await message.channel.send(content, view=view_to_send)
            registration_success = await register_job_with_queue(result, sent_msg)
            if not sent_msg:
                print(f"ERROR: Failed to send rerun status message for job {result['job_id']}.")
                error_summary_rerun.append(f"Rerun job {idx+1}: Failed to send status message.")
            elif not registration_success:
                print(f"Warning: Rerun job {result['job_id']} could not be registered with the queue manager.")
                error_summary_rerun.append(f"Rerun job {idx+1}: Failed to register queue metadata.")
        elif result["status"] == "error":
            error_summary_rerun.append(f"Rerun job {idx+1}: {result.get('error_message_text', 'Unknown error.')}")

    if error_summary_rerun:
        await message.channel.send(f"{message.author.mention} Rerun request processed with error(s):\n- " + "\n".join(error_summary_rerun))
# --- END OF FILE bot_commands.py ---
