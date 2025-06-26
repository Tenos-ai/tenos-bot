import discord
from discord.ui import Modal, TextInput, View, Button
import textwrap
import json
import traceback

from queue_manager import queue_manager
from file_management import extract_job_id, delete_job_files_and_message
from utils.show_prompt import reconstruct_full_prompt_string
from bot_config_loader import ADMIN_ID, ALLOWED_USERS
from settings_manager import load_settings
from utils.message_utils import safe_interaction_response
from websocket_client import WebsocketClient

from bot_core_logic import (
    process_upscale_request as core_process_upscale,
    process_variation_request as core_process_variation,
    process_rerun_request as core_process_rerun,
    execute_generation_logic,
    process_cancel_request
)

class EditPromptModal(Modal, title='Edit Prompt'):
    def __init__(self, original_prompt_full: str, job_id: str, view_ref: View, model_type: str = "flux"):
        super().__init__(timeout=600)
        self.original_prompt_full = original_prompt_full
        self.job_id_context = job_id
        self.view_ref = view_ref
        self.original_model_type_for_display = model_type 
        
        label_context = f"({self.original_model_type_for_display.upper()} context)"
        max_label_len = 45 - len("Edit Prompt ") - len(label_context)
        
        prompt_field_label = f"Edit Prompt {label_context}"
        if len(prompt_field_label) > 45:
            prompt_field_label = "Edit Prompt"

        self.prompt_input = TextInput(
            label=prompt_field_label[:45],
            style=discord.TextStyle.paragraph, 
            placeholder='Enter your new prompt here...', 
            default=original_prompt_full, 
            max_length=3000, 
            required=True
        )
        self.add_item(self.prompt_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False, thinking=True)
        except discord.errors.InteractionResponded:
            print("EditPromptModal: Interaction already responded to before defer.")
        except Exception as e_defer_modal:
            print(f"Error deferring EditPromptModal interaction: {e_defer_modal}")
            return
        
        edited_prompt = self.prompt_input.value
        initial_response_sent = False

        current_settings_edit = load_settings()
        selected_model_for_edit = current_settings_edit.get('selected_model')
        current_model_type_for_edit = "flux" 
        if selected_model_for_edit and ":" in selected_model_for_edit:
            current_model_type_for_edit = selected_model_for_edit.split(":", 1)[0].strip().lower()
        elif selected_model_for_edit: 
             if selected_model_for_edit.endswith((".gguf",".sft")): current_model_type_for_edit = "flux"
             else: current_model_type_for_edit = "sdxl"

        try:
            job_results_list = await execute_generation_logic(
                context_user=interaction.user,
                context_channel=interaction.channel, 
                prompt=edited_prompt,
                is_interaction_context=True,
                initial_interaction_object=interaction,
                model_type_override=current_model_type_for_edit, 
                is_derivative_action=True
            )
            for result in job_results_list:
                if result["status"] == "success":
                    msg_details = result["message_content_details"]
                    content = (f"{msg_details['user_mention']}: `{textwrap.shorten(msg_details['prompt_to_display'], 1500, placeholder='...')}`")
                    if msg_details['enhancer_used'] and msg_details['display_preference'] == 'enhanced': content += " ✨"
                    content += f" (Edited - {msg_details['model_type'].upper()})" 
                    content += f"\n> **Seed:** `{msg_details['seed']}`"
                    if msg_details['aspect_ratio']: content += f", **AR:** `{msg_details['aspect_ratio']}`"
                    if msg_details['steps']: content += f", **Steps:** `{msg_details['steps']}`"
                    if msg_details['model_type'] == "sdxl": content += f", **Guidance (SDXL):** `{msg_details['guidance_sdxl']}`"
                    else: content += f", **Guidance (Flux):** `{msg_details['guidance_flux']}`"
                    if msg_details['mp_size'] is not None: content += f", **MP:** `{msg_details['mp_size']}`"
                    content += f"\n> **Style:** `{msg_details['style']}`"
                    if msg_details['is_img2img']: content += f", **Strength:** `{msg_details['img_strength_percent']}%`"
                    if msg_details['negative_prompt']: content += f"\n> **No:** `{textwrap.shorten(msg_details['negative_prompt'], 100, placeholder='...')}`"
                    content += "\n> **Status:** Queued..."
                    if msg_details.get("enhancer_applied_message_for_first_run"): content += msg_details["enhancer_applied_message_for_first_run"]
                    view_to_send = QueuedJobView(**result["view_args"]) if result.get("view_type") == "QueuedJobView" and result.get("view_args") else None
                    sent_message = await interaction.followup.send(content, view=view_to_send, ephemeral=False, wait=True)
                    initial_response_sent = True
                    if sent_message and result["job_data_for_qm"]:
                        job_data_to_add = result["job_data_for_qm"]; job_data_to_add["message_id"] = sent_message.id
                        queue_manager.add_job(result["job_id"], job_data_to_add)
                        
                        ws_client = WebsocketClient()
                        if ws_client.is_connected and result.get("comfy_prompt_id"):
                            await ws_client.register_prompt(result["comfy_prompt_id"], sent_message.id, sent_message.channel.id)
                elif result["status"] == "error":
                    await interaction.followup.send(f"Error processing edited prompt: {result.get('error_message_text', 'Unknown error.')}", ephemeral=True)
                    initial_response_sent = True
            if not initial_response_sent and not job_results_list:
                 await interaction.followup.send("Failed to process the edited prompt (no job data returned).", ephemeral=True)
        except Exception as e:
            print(f"Error in EditPromptModal on_submit (orig job {self.job_id_context}): {e}"); traceback.print_exc()
            if not initial_response_sent:
                try: await interaction.followup.send("An error occurred while queuing the edited prompt (on_submit exception).", ephemeral=True)
                except Exception: pass

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Error in EditPromptModal on_error: {error}"); traceback.print_exc()
        try: 
            if interaction.response.is_done():
                await interaction.followup.send("An error occurred with the editing form itself.", ephemeral=True)
            else:
                await interaction.response.send_message("An error occurred with the editing form itself.", ephemeral=True)
        except Exception as e_on_err: print(f"Error sending modal on_error followup for EditPromptModal: {e_on_err}")

class RemixEditPromptModal(Modal, title='Remix Prompt'):
    def __init__( self, job_data: dict, job_id_original_context: str, variation_type: str, image_index: int, original_interaction_context: discord.Interaction, referenced_message_target: discord.Message, target_image_url_actual: str ):
        super().__init__(timeout=600)
        enhanced_prompt_orig = (job_data or {}).get('enhanced_prompt'); original_prompt_text = (job_data or {}).get('original_prompt') or (job_data or {}).get('prompt', '')
        prompt_for_modal_display = enhanced_prompt_orig if enhanced_prompt_orig else original_prompt_text
        self.model_type_original_for_display = (job_data or {}).get('model_type_for_enhancer', 'flux')
        self.job_id_for_context = job_id_original_context
        self.variation_type_for_action = variation_type; self.image_index_for_action = image_index
        self.original_interaction_context_opener = original_interaction_context; self.referenced_message_for_variation = referenced_message_target
        self.target_image_url_for_variation = target_image_url_actual

        
        base_label = f"Remix Prompt ({variation_type.capitalize()} #{image_index})"
        
        self.prompt_input_remix_field = TextInput(
            label=base_label[:45], 
            style=discord.TextStyle.paragraph, 
            placeholder='Enter your remixed prompt here...', 
            default=prompt_for_modal_display, 
            max_length=3000, 
            required=True
        )
        self.add_item(self.prompt_input_remix_field)

        if self.model_type_original_for_display == "sdxl": 
            original_neg_prompt_text = (job_data or {}).get('negative_prompt', '')
            self.negative_prompt_input_remix_field = TextInput(
                label="Negative Prompt (SDXL)"[:45], 
                style=discord.TextStyle.paragraph, 
                placeholder='Enter negative prompt (optional)...', 
                default=original_neg_prompt_text, 
                max_length=1000, 
                required=False
            )
            self.add_item(self.negative_prompt_input_remix_field)
        else: self.negative_prompt_input_remix_field = None

    async def on_submit(self, interaction_from_modal: discord.Interaction):
        try:
            if not interaction_from_modal.response.is_done():
                await interaction_from_modal.response.defer(ephemeral=False, thinking=True)
        except discord.errors.InteractionResponded: pass
        except Exception as e_defer_modal_remix:
            print(f"Error deferring RemixEditPromptModal interaction: {e_defer_modal_remix}"); return

        edited_prompt_text_remix = self.prompt_input_remix_field.value; edited_negative_prompt_text_remix = None
        if self.negative_prompt_input_remix_field: 
            edited_negative_prompt_text_remix = self.negative_prompt_input_remix_field.value
            if edited_negative_prompt_text_remix is not None: edited_negative_prompt_text_remix = edited_negative_prompt_text_remix.strip();
            if not edited_negative_prompt_text_remix: edited_negative_prompt_text_remix = None
        
        initial_response_sent_remix = False
        try:
            results_list_remix = await core_process_variation(
                context_user=interaction_from_modal.user, 
                context_channel=interaction_from_modal.channel, 
                referenced_message_obj=self.referenced_message_for_variation, 
                variation_type_str=self.variation_type_for_action, 
                image_idx=self.image_index_for_action, 
                edited_prompt_str=edited_prompt_text_remix, 
                edited_neg_prompt_str=edited_negative_prompt_text_remix, 
                is_interaction=True, 
                initial_interaction_obj=interaction_from_modal
            )
            for result_remix in results_list_remix:
                if result_remix["status"] == "success":
                    msg_details_remix = result_remix["message_content_details"]
                    content_remix = (f"{msg_details_remix['user_mention']}: `{textwrap.shorten(msg_details_remix['prompt_to_display'], 50, placeholder='...')}` ({msg_details_remix['description']} on img #{msg_details_remix['image_index']} from `{msg_details_remix['original_job_id']}` - {msg_details_remix['model_type']})\n"
                                   f"> **Seed:** `{msg_details_remix['seed']}`, **AR:** `{msg_details_remix['aspect_ratio']}`, **Steps:** `{msg_details_remix['steps']}`, **Style:** `{msg_details_remix['style']}`")
                    if msg_details_remix.get('is_remixed'): content_remix += "\n> `(Remixed Prompt)`"
                    enhancer_text_val_remix = msg_details_remix.get('enhancer_reference_text')
                    if enhancer_text_val_remix: content_remix += f"\n{enhancer_text_val_remix.strip()}"
                    content_remix += "\n> **Status:** Queued... "
                    view_remix = QueuedJobView(**result_remix["view_args"]) if result_remix.get("view_type") == "QueuedJobView" and result_remix.get("view_args") else None
                    sent_msg_remix = await interaction_from_modal.followup.send(content_remix, view=view_remix, ephemeral=False, wait=True)
                    initial_response_sent_remix = True
                    if sent_msg_remix and result_remix["job_data_for_qm"]:
                        job_data_add_remix = result_remix["job_data_for_qm"]; job_data_add_remix["message_id"] = sent_msg_remix.id
                        queue_manager.add_job(result_remix["job_id"], job_data_add_remix)
                        
                        ws_client = WebsocketClient()
                        if ws_client.is_connected and result_remix.get("comfy_prompt_id"):
                            await ws_client.register_prompt(result_remix["comfy_prompt_id"], sent_msg_remix.id, sent_msg_remix.channel.id)
                elif result_remix["status"] == "error":
                    await interaction_from_modal.followup.send(f"Error processing remixed variation: {result_remix.get('error_message_text', 'Unknown error.')}", ephemeral=True)
                    initial_response_sent_remix = True
            if not initial_response_sent_remix and not results_list_remix: 
                await interaction_from_modal.followup.send("Failed to process remixed variation (no results).", ephemeral=True)
        except Exception as e_submit_remix_modal:
            print(f"Error in RemixEditPromptModal on_submit (orig job {self.job_id_for_context}): {e_submit_remix_modal}"); traceback.print_exc()
            if not initial_response_sent_remix:
                try: await interaction_from_modal.followup.send("An error occurred while queuing remixed variation (on_submit exception).", ephemeral=True)
                except Exception: pass

    async def on_error(self, interaction_modal_error: discord.Interaction, error: Exception):
        print(f"Error in RemixEditPromptModal on_error: {error}"); traceback.print_exc()
        try: 
            if interaction_modal_error.response.is_done():
                await interaction_modal_error.followup.send("An error occurred with the remix editing form itself.", ephemeral=True)
            else:
                await interaction_modal_error.response.send_message("An error occurred with the remix editing form itself.", ephemeral=True)
        except Exception as e_on_err_remix_modal: print(f"Error sending remix modal on_error followup: {e_on_err_remix_modal}")

class QueuedJobView(View):
    def __init__(self, comfy_prompt_id: str, timeout=86400*2):
        super().__init__(timeout=timeout)
        self.comfy_prompt_id = comfy_prompt_id
        cancel_button = Button(label="Cancel ⏸️", style=discord.ButtonStyle.danger, custom_id=f"cancel_{self.comfy_prompt_id}")
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) == str(ADMIN_ID): return True
        job_data = queue_manager.get_job_by_comfy_id(self.comfy_prompt_id)
        if not job_data and interaction.message:
            job_data = queue_manager.get_job_data(interaction.message.id, interaction.message.channel.id)
        if job_data and job_data.get('user_id') == interaction.user.id: return True
        allowed_user_perms = ALLOWED_USERS.get(str(interaction.user.id), {})
        if allowed_user_perms.get("can_delete_jobs", False): return True 
        await interaction.response.send_message("You don't have permission to cancel this job.", ephemeral=True); return False

    async def cancel_callback(self, interaction: discord.Interaction):
        if not interaction.data or 'custom_id' not in interaction.data: return
        custom_id = interaction.data['custom_id']
        if not custom_id.startswith("cancel_"): return
        comfy_id_to_cancel = custom_id.split('_', 1)[1]; bot_job_id = queue_manager.get_job_id_by_comfy_id(comfy_id_to_cancel)
        try:
            if not interaction.response.is_done(): await interaction.response.defer(ephemeral=True)
        except discord.NotFound: print("Warning: Interaction expired before deferral in cancel_callback.")
        except Exception as e_defer: print(f"Error deferring in cancel_callback: {e_defer}")
        if bot_job_id and queue_manager.is_job_completed_or_cancelled(bot_job_id):
            for item in self.children:
                if isinstance(item, Button) and item.custom_id == custom_id: item.disabled = True; item.label = "Cancelled"; break
            feedback = "Job was already completed or cancelled."
            try: await interaction.edit_original_response(view=self)
            except Exception: feedback = "Job was already completed or cancelled (failed to update button)."
            try: await interaction.followup.send(feedback, ephemeral=True)
            except discord.NotFound:
                 if interaction.message and interaction.message.channel: await interaction.message.channel.send(f"{interaction.user.mention} {feedback}", delete_after=10) 
            except Exception as e_followup: print(f"Error sending 'already cancelled' followup: {e_followup}")
            return
        for item in self.children:
            if isinstance(item, Button) and item.custom_id == custom_id: item.disabled = True; item.label = "Cancelling..."; break
        try:
            if interaction.message: await interaction.edit_original_response(view=self)
        except discord.NotFound: pass
        except Exception as e_edit_disabling: print(f"Minor error disabling cancel button view: {e_edit_disabling}")
        success, message_text_from_cancel = await process_cancel_request(comfy_id_to_cancel)
        final_feedback = "";
        if success:
            try:
                if interaction.message: await interaction.message.delete()
                final_feedback = "Job successfully cancelled."
            except Exception: final_feedback = "Job cancelled (Error deleting original status message)."
        else:
            for item_fail in self.children:
                if isinstance(item_fail, Button) and item_fail.custom_id == custom_id: item_fail.disabled = True; item_fail.label = "Cancelled (State Uncertain)"; break
            try:
                 if interaction.message: await interaction.edit_original_response(view=self)
            except Exception: pass
            final_feedback = f"Job cancelled locally. ComfyUI status: {message_text_from_cancel}"
        try: await interaction.followup.send(final_feedback, ephemeral=True)
        except Exception as e_final_follow: print(f"Error sending final cancel followup: {e_final_follow}")

class GenerationActionsView(View):
    def __init__(self, original_message_id: int, original_channel_id: int, job_id: str, bot_ref, timeout=86400*3):
        super().__init__(timeout=timeout)
        self.original_message_id = original_message_id; self.original_channel_id = original_channel_id
        self.job_id = job_id; self.bot = bot_ref
        buttons_def = [ Button(label="Upscale ⬆️", style=discord.ButtonStyle.primary, custom_id=f"upscale_1_{job_id}", row=0), Button(label="Vary W 🤏", style=discord.ButtonStyle.secondary, custom_id=f"vary_w_1_{job_id}", row=0), Button(label="Vary S 💪", style=discord.ButtonStyle.secondary, custom_id=f"vary_s_1_{job_id}", row=0), Button(label="Rerun 🔄", style=discord.ButtonStyle.secondary, custom_id=f"rerun_{job_id}", row=1), Button(label="Edit ✏️", style=discord.ButtonStyle.secondary, custom_id=f"edit_{job_id}", row=1), Button(label="Delete 🗑️", style=discord.ButtonStyle.danger, custom_id=f"delete_{job_id}", row=1)]
        for btn_item in buttons_def:
            action_type_btn = btn_item.custom_id.split('_')[0]
            if action_type_btn == "upscale": btn_item.callback = self.upscale_callback
            elif action_type_btn == "vary": btn_item.callback = self.vary_callback
            elif action_type_btn == "rerun": btn_item.callback = self.rerun_callback
            elif action_type_btn == "edit": btn_item.callback = self.edit_callback
            elif action_type_btn == "delete": btn_item.callback = self.delete_callback
            self.add_item(btn_item)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) == str(ADMIN_ID): return True
        job_data = queue_manager.get_job_data_by_id(self.job_id)
        if not job_data and interaction.message:
            job_data = queue_manager.get_job_data(interaction.message.id, interaction.message.channel.id)
        is_owner = job_data and job_data.get('user_id') == interaction.user.id
        custom_id = interaction.data.get('custom_id', '')
        permission_key = "can_delete_jobs" if 'delete' in custom_id else "can_use_actions"
        allowed_user_perms = ALLOWED_USERS.get(str(interaction.user.id), {})
        has_general_permission = allowed_user_perms.get(permission_key, False)
        if is_owner or has_general_permission: return True
        await interaction.response.send_message("You don't have permission to use this button.", ephemeral=True)
        return False

    async def get_referenced_message(self, interaction: discord.Interaction):
        if interaction.message: return interaction.message
        try:
            channel = self.bot.get_channel(self.original_channel_id) or await self.bot.fetch_channel(self.original_channel_id)
            return await channel.fetch_message(self.original_message_id) if channel else None
        except Exception as e: print(f"Error refetching message {self.original_message_id} for view: {e}"); return None

    async def handle_action_error(self, interaction: discord.Interaction, action_name: str, error: Exception):
        print(f"Error during '{action_name}' (Job ID: {self.job_id}): {error}"); traceback.print_exc()
        try:
            if interaction.response.is_done(): await interaction.followup.send(f"Action '{action_name}' failed due to an error.", ephemeral=True)
            else: await interaction.response.send_message(f"Action '{action_name}' failed due to an error.", ephemeral=True)
        except Exception as fe: print(f"Error sending followup/response during {action_name} failure: {fe}")

    async def _process_and_send_action_results(self, interaction: discord.Interaction, results: list, action_description: str):
        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=False, thinking=False) 
            except discord.errors.InteractionResponded: pass
            except Exception as e_defer_process: print(f"Error deferring in _process_and_send_action_results for {action_description}: {e_defer_process}")
        for result_item in results:
            if result_item["status"] == "success":
                msg_details_item = result_item["message_content_details"]
                job_type_item = result_item.get("job_data_for_qm", {}).get("type", action_description.lower())
                content_str = ""
                if job_type_item == "upscale":
                    content_str = (f"{msg_details_item['user_mention']}: Upscaling image #{msg_details_item['image_index']} from job `{msg_details_item['original_job_id']}` (Workflow: {msg_details_item['model_type']})\n" 
                               f"> **Using Prompt:** `{textwrap.shorten(msg_details_item['prompt_to_display'], 70, placeholder='...')}`\n"
                               f"> **Seed:** `{msg_details_item['seed']}`, **Style:** `{msg_details_item['style']}`, **Orig AR:** `{msg_details_item['aspect_ratio']}`\n"
                               f"> **Factor:** `{msg_details_item['upscale_factor']}`, **Denoise:** `{msg_details_item['denoise']}`\n"
                               f"> **Status:** Queued... ")
                elif job_type_item == "variation":
                    content_str = (f"{msg_details_item['user_mention']}: `{textwrap.shorten(msg_details_item['prompt_to_display'], 50, placeholder='...')}` ({msg_details_item['description']} on img #{msg_details_item['image_index']} from `{msg_details_item['original_job_id']}` - {msg_details_item['model_type']})\n" 
                               f"> **Seed:** `{msg_details_item['seed']}`, **AR:** `{msg_details_item['aspect_ratio']}`, **Steps:** `{msg_details_item['steps']}`, **Style:** `{msg_details_item['style']}`")
                    if msg_details_item.get('is_remixed'): content_str += "\n> `(Remixed Prompt)`"
                    enhancer_text_val = msg_details_item.get('enhancer_reference_text')
                    if enhancer_text_val: content_str += f"\n{enhancer_text_val.strip()}"
                    content_str += "\n> **Status:** Queued... "
                elif job_type_item == "generate": 
                    content_str = (f"{msg_details_item['user_mention']}: `{textwrap.shorten(msg_details_item['prompt_to_display'], 1500, placeholder='...')}`")
                    if msg_details_item.get('enhancer_used') and msg_details_item.get('display_preference') == 'enhanced': content_str += " ✨"
                    run_times = msg_details_item.get('total_runs', 1); run_num = msg_details_item.get('run_number', 1)
                    if run_times > 1: content_str += f" (Rerun {run_num}/{run_times} - {msg_details_item['model_type'].upper()})" 
                    else: content_str += f" (Rerun/Edited - {msg_details_item['model_type'].upper()})" 
                    content_str += f"\n> **Seed:** `{msg_details_item['seed']}`"
                    if msg_details_item.get('aspect_ratio'): content_str += f", **AR:** `{msg_details_item['aspect_ratio']}`"
                    if msg_details_item.get('steps'): content_str += f", **Steps:** `{msg_details_item['steps']}`"
                    if msg_details_item.get('model_type') == "sdxl": content_str += f", **Guidance (SDXL):** `{msg_details_item['guidance_sdxl']}`"
                    else: content_str += f", **Guidance (Flux):** `{msg_details_item['guidance_flux']}`"
                    if msg_details_item.get('mp_size') is not None: content_str += f", **MP:** `{msg_details_item['mp_size']}`"
                    content_str += f"\n> **Style:** `{msg_details_item['style']}`"
                    if msg_details_item.get('is_img2img'): content_str += f", **Strength:** `{msg_details_item['img_strength_percent']}%`"
                    if msg_details_item.get('negative_prompt'): content_str += f"\n> **No:** `{textwrap.shorten(msg_details_item['negative_prompt'], 100, placeholder='...')}`"
                    content_str += "\n> **Status:** Queued... "
                    if msg_details_item.get("enhancer_applied_message_for_first_run"): content_str += msg_details_item["enhancer_applied_message_for_first_run"]
                view_to_send_item = QueuedJobView(**result_item["view_args"]) if result_item.get("view_type") == "QueuedJobView" and result_item.get("view_args") else None
                sent_message_item = await interaction.followup.send(content_str, view=view_to_send_item, ephemeral=False, wait=True)
                if sent_message_item and result_item["job_data_for_qm"]:
                    job_data_to_add_item = result_item["job_data_for_qm"]; job_data_to_add_item["message_id"] = sent_message_item.id
                    queue_manager.add_job(result_item["job_id"], job_data_to_add_item)
                    # Register with websocket client for progress updates
                    ws_client = WebsocketClient()
                    if ws_client.is_connected and result_item.get("comfy_prompt_id"):
                        await ws_client.register_prompt(result_item["comfy_prompt_id"], sent_message_item.id, sent_message_item.channel.id)
            elif result_item["status"] == "error":
                error_text_item = result_item.get('error_message_text', f'Unknown error during {action_description}.')
                await interaction.followup.send(f"Error ({action_description}): {error_text_item}", ephemeral=True)
        if not results:
            await interaction.followup.send(f"Failed to process {action_description.lower()} request (no results returned from logic).", ephemeral=True)

    async def upscale_callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            try: await interaction.response.defer(ephemeral=False, thinking=False)
            except discord.errors.InteractionResponded: pass
        ref_msg = await self.get_referenced_message(interaction)
        if not ref_msg: await interaction.followup.send("Error: Original message not found.", ephemeral=True); return
        image_idx = 1
        try: image_idx = int(interaction.data['custom_id'].split('_')[1]) 
        except (IndexError, ValueError): pass
        results = await core_process_upscale(context_user=interaction.user, context_channel=interaction.channel, referenced_message_obj=ref_msg, image_idx=image_idx, is_interaction=True, initial_interaction_obj=interaction) 
        await self._process_and_send_action_results(interaction, results, "Upscale")

    async def vary_callback(self, interaction: discord.Interaction):
        settings = load_settings(); remix_enabled = settings.get('remix_mode', False)
        variation_type = 'weak' if '_w_' in interaction.data['custom_id'] else 'strong' 
        image_idx = 1
        try: parts = interaction.data['custom_id'].split('_'); image_idx = int(parts[2] if len(parts) > 2 and parts[1] in ['w','s'] else parts[1]) 
        except (IndexError, ValueError): pass
        if remix_enabled:
            if interaction.response.is_done(): await interaction.followup.send("Remix mode: Cannot open edit modal as interaction was already acknowledged. Please try action again.", ephemeral=True); return
            ref_msg = await self.get_referenced_message(interaction)
            if not ref_msg: await interaction.response.send_message("Error: Original message not found for remix.",ephemeral=True); return 
            job_data = queue_manager.get_job_data_by_id(self.job_id) or queue_manager.get_job_data(ref_msg.id, ref_msg.channel.id if ref_msg.channel else interaction.channel_id) 
            target_attachment = ref_msg.attachments[image_idx-1] if len(ref_msg.attachments) >= image_idx else None
            if not target_attachment: await interaction.response.send_message("Error: Target image for remix not found.",ephemeral=True); return
            modal = RemixEditPromptModal(job_data or {}, self.job_id, variation_type, image_idx, interaction, ref_msg, target_attachment.url)
            await interaction.response.send_modal(modal) 
        else:
            if not interaction.response.is_done(): await interaction.response.defer(ephemeral=False, thinking=False)
            ref_msg = await self.get_referenced_message(interaction)
            if not ref_msg: await interaction.followup.send("Error: Original message not found.", ephemeral=True); return
            results = await core_process_variation(context_user=interaction.user, context_channel=interaction.channel, referenced_message_obj=ref_msg, variation_type_str=variation_type, image_idx=image_idx, is_interaction=True, initial_interaction_obj=interaction) 
            await self._process_and_send_action_results(interaction, results, f"{variation_type.capitalize()} Variation")

    async def rerun_callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done(): await interaction.response.defer(ephemeral=False, thinking=True) 
        ref_msg = await self.get_referenced_message(interaction)
        if not ref_msg: await interaction.followup.send("Error: Original message not found.", ephemeral=True); return
        results = await core_process_rerun(context_user=interaction.user, context_channel=interaction.channel, referenced_message_obj=ref_msg, run_times_count=1, is_interaction=True, initial_interaction_obj=interaction) 
        await self._process_and_send_action_results(interaction, results, "Rerun")

    async def edit_callback(self, interaction: discord.Interaction):
        if interaction.response.is_done(): await interaction.followup.send("Cannot open edit modal (interaction already acknowledged). Try again or use `/gen`.", ephemeral=True); return
        job_data = queue_manager.get_job_data_by_id(self.job_id)
        if not job_data: ref_msg_for_edit = await self.get_referenced_message(interaction); job_id_file_edit = extract_job_id(ref_msg_for_edit.attachments[0].filename) if ref_msg_for_edit and ref_msg_for_edit.attachments else None; job_data = queue_manager.get_job_data_by_id(job_id_file_edit) if job_id_file_edit else None
        if not job_data: await interaction.response.send_message("Error: Cannot find job data to edit.", ephemeral=True); return
        full_prompt_str = reconstruct_full_prompt_string(job_data); 
        original_model_type_for_modal_display = job_data.get('model_type_for_enhancer', 'flux') 
        modal_to_send = EditPromptModal(full_prompt_str, self.job_id, self, model_type=original_model_type_for_modal_display)
        await interaction.response.send_modal(modal_to_send)

    async def delete_callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done(): await interaction.response.defer(ephemeral=True)
        for item_btn_del in self.children:
            if isinstance(item_btn_del,Button) and item_btn_del.custom_id == interaction.data['custom_id']: item_btn_del.disabled=True; item_btn_del.label="Deleting..."; break 
        try:
            if interaction.message: await interaction.message.edit(view=self)
        except discord.NotFound: print(f"Original message for delete (job {self.job_id}) not found.")
        except Exception as e_edit_del: print(f"Error editing message for delete button (job {self.job_id}): {e_edit_del}")
        ref_msg_del = await self.get_referenced_message(interaction)
        await delete_job_files_and_message(self.job_id, ref_msg_del, interaction)

class BatchActionsView(GenerationActionsView):
    def __init__(self, original_message_id: int, original_channel_id: int, job_id: str, batch_size: int, bot_ref, timeout=86400*3):
        super().__init__(original_message_id, original_channel_id, job_id, bot_ref, timeout)
        self.batch_size = batch_size
        action_buttons_to_readd = []
        ids_to_remove_or_reposition = [f"upscale_1_{job_id}", f"vary_w_1_{job_id}", f"vary_s_1_{job_id}", f"rerun_{job_id}", f"edit_{job_id}", f"delete_{job_id}"]
        current_children_copy = self.children[:] 
        for item in current_children_copy:
            if isinstance(item, Button) and item.custom_id in ids_to_remove_or_reposition:
                if item.custom_id in [f"rerun_{job_id}", f"edit_{job_id}", f"delete_{job_id}"]: action_buttons_to_readd.append({'label': item.label, 'style': item.style, 'custom_id': item.custom_id, 'callback': item.callback })
                self.remove_item(item)
        settings_batch = load_settings()
        self.default_variation_char = settings_batch.get('default_variation_mode', 'weak')[0]
        v_label_char = "🤏" if self.default_variation_char == 'w' else ("💪" if self.default_variation_char == 's' else "V")
        for i_batch_up in range(1, self.batch_size + 1):
            if i_batch_up > 5 : break 
            btn_up = Button(label=f"U{i_batch_up}", style=discord.ButtonStyle.primary, custom_id=f"upscale_{i_batch_up}_{job_id}", row=0)
            btn_up.callback = self.upscale_callback; self.add_item(btn_up)
        for i_batch_vary in range(1, self.batch_size + 1):
            if i_batch_vary > 5: break
            btn_vary = Button(label=f"{v_label_char}{i_batch_vary}", style=discord.ButtonStyle.secondary, custom_id=f"vary_{self.default_variation_char}_{i_batch_vary}_{job_id}", row=1)
            btn_vary.callback = self.vary_callback; self.add_item(btn_vary)
        action_button_row = 2
        for btn_data in action_buttons_to_readd:
            re_added_button = Button(label=btn_data['label'], style=btn_data['style'], custom_id=btn_data['custom_id'], row=action_button_row)
            re_added_button.callback = btn_data['callback']; self.add_item(re_added_button)
        if not any(b['custom_id'] == f"rerun_{job_id}" for b in action_buttons_to_readd):
            btn_rerun_fallback = Button(label="Rerun 🔄", style=discord.ButtonStyle.secondary, custom_id=f"rerun_{job_id}", row=action_button_row)
            btn_rerun_fallback.callback = self.rerun_callback; self.add_item(btn_rerun_fallback)
        if not any(b['custom_id'] == f"edit_{job_id}" for b in action_buttons_to_readd):
            btn_edit_fallback = Button(label="Edit ✏️", style=discord.ButtonStyle.secondary, custom_id=f"edit_{job_id}", row=action_button_row)
            btn_edit_fallback.callback = self.edit_callback; self.add_item(btn_edit_fallback)
        if not any(b['custom_id'] == f"delete_{job_id}" for b in action_buttons_to_readd):
            btn_delete_fallback = Button(label="Delete 🗑️", style=discord.ButtonStyle.danger, custom_id=f"delete_{job_id}", row=action_button_row)
            btn_delete_fallback.callback = self.delete_callback; self.add_item(btn_delete_fallback)
