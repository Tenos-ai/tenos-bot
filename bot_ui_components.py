# --- START OF FILE bot_ui_components.py ---
import discord
from discord.ui import Modal, TextInput, View, Button
import textwrap
import json
import traceback
import re

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
    process_cancel_request,
    process_kontext_edit_request,
    execute_generation_logic
)

class EditKontextModal(Modal, title='Edit with Kontext'):
    def __init__(self, primary_image_url: str, interaction: discord.Interaction):
        super().__init__(timeout=600)
        self.primary_image_url = primary_image_url
        self.original_interaction = interaction

        # Field for the user's instruction, with updated placeholder
        self.instruction_input = TextInput(
            label="Edit Command & Optional Parameters",
            style=discord.TextStyle.paragraph,
            placeholder="add a hat on the man --steps 40 --ar 1:1\nmake the sky night time --g 4.5",
            required=True
        )

        # Field for the primary image URL - pre-filled
        self.image1_input = TextInput(
            label="Image to Edit (Primary)",
            default=self.primary_image_url,
            style=discord.TextStyle.short,
            required=True,
        )
        
        # Optional fields for additional images
        self.image2_input = TextInput(label="Image 2 (Optional URL)", required=False, placeholder="Paste another image URL to stitch...")
        self.image3_input = TextInput(label="Image 3 (Optional URL)", required=False, placeholder="Paste another image URL to stitch...")
        self.image4_input = TextInput(label="Image 4 (Optional URL)", required=False, placeholder="Paste another image URL to stitch...")

        self.add_item(self.instruction_input)
        self.add_item(self.image1_input)
        self.add_item(self.image2_input)
        self.add_item(self.image3_input)
        self.add_item(self.image4_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False, thinking=True)

        instruction = self.instruction_input.value
        
        image_urls = [self.image1_input.value] 
        if self.image2_input.value: image_urls.append(self.image2_input.value)
        if self.image3_input.value: image_urls.append(self.image3_input.value)
        if self.image4_input.value: image_urls.append(self.image4_input.value)
        
        await process_kontext_edit_request(
            context_user=interaction.user,
            context_channel=interaction.channel,
            instruction=instruction,
            image_urls=image_urls,
            initial_interaction_obj=interaction
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Error in EditKontextModal: {error}")
        traceback.print_exc()
        await safe_interaction_response(interaction, "An error occurred with the editing form.", ephemeral=True)


class RemixModal(Modal, title='Remix Variation'):
    def __init__(self, job_data: dict, variation_type: str, image_index: int, ref_message: discord.Message):
        super().__init__(timeout=600)
        self.job_data = job_data
        self.variation_type = variation_type
        self.image_index = image_index
        self.referenced_message = ref_message
        
        original_prompt = reconstruct_full_prompt_string(job_data)
        # Truncate the prompt to a safe length for the modal text input
        truncated_prompt = textwrap.shorten(original_prompt, 1400, placeholder="... (prompt too long)")

        self.prompt_input = TextInput(
            label="Prompt",
            style=discord.TextStyle.paragraph,
            default=truncated_prompt, # Use the truncated prompt
            required=True,
            max_length=1500
        )
        self.add_item(self.prompt_input)

        original_model_type = job_data.get('model_type_for_enhancer', 'flux')
        if original_model_type == 'sdxl':
            self.negative_prompt_input = TextInput(
                label="Negative Prompt (SDXL Only)",
                style=discord.TextStyle.paragraph,
                default=job_data.get('negative_prompt', ''),
                required=False
            )
            self.add_item(self.negative_prompt_input)
        else:
            self.negative_prompt_input = None

    async def on_submit(self, interaction: discord.Interaction):
        
        edited_prompt_text = self.prompt_input.value
        edited_neg_prompt_text = self.negative_prompt_input.value if self.negative_prompt_input else None
        
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False, thinking=False)
        except discord.errors.InteractionResponded: pass
        except Exception as e: print(f"Error deferring in RemixModal on_submit: {e}")

        results = await core_process_variation(
            context_user=interaction.user,
            context_channel=interaction.channel,
            referenced_message_obj=self.referenced_message,
            variation_type_str=self.variation_type,
            image_idx=self.image_index,
            edited_prompt_str=edited_prompt_text,
            edited_neg_prompt_str=edited_neg_prompt_text,
            is_interaction=True,
            initial_interaction_obj=interaction
        )

        for result_item in results:
            if result_item["status"] == "success":
                msg_details_item = result_item["message_content_details"]
                content_str = (f"{msg_details_item['user_mention']}: `{textwrap.shorten(msg_details_item['prompt_to_display'], 50, placeholder='...')}` ({msg_details_item['description']} on img #{msg_details_item['image_index']} from `{msg_details_item['original_job_id']}` - {msg_details_item['model_type']})\n" 
                               f"> **Seed:** `{msg_details_item['seed']}`, **AR:** `{msg_details_item['aspect_ratio']}`, **Steps:** `{msg_details_item['steps']}`, **Style:** `{msg_details_item['style']}`")
                if msg_details_item.get('is_remixed'): content_str += "\n> `(Remixed Prompt)`"
                enhancer_text_val = msg_details_item.get('enhancer_reference_text')
                if enhancer_text_val: content_str += f"\n{enhancer_text_val.strip()}"
                content_str += "\n> **Status:** Queued... "

                view_to_send_item = QueuedJobView(**result_item["view_args"]) if result_item.get("view_type") == "QueuedJobView" and result_item.get("view_args") else None
                sent_message_item = await safe_interaction_response(interaction, content=content_str, view=view_to_send_item)

                if sent_message_item and result_item["job_data_for_qm"]:
                    job_data_to_add_item = result_item["job_data_for_qm"]
                    job_data_to_add_item["message_id"] = sent_message_item.id
                    queue_manager.add_job(result_item["job_id"], job_data_to_add_item)
                    ws_client = WebsocketClient()
                    if ws_client.is_connected and result_item.get("comfy_prompt_id"):
                        await ws_client.register_prompt(result_item["comfy_prompt_id"], sent_message_item.id, sent_message_item.channel.id)

            elif result_item["status"] == "error":
                error_text_item = result_item.get('error_message_text', 'Unknown error during variation.')
                await safe_interaction_response(interaction, f"Error (Variation): {error_text_item}", ephemeral=True)


    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Error in RemixModal: {error}")
        traceback.print_exc()
        await safe_interaction_response(interaction, "An error occurred with the remix form.", ephemeral=True)


class ImageSelectionView(View):
    def __init__(self, attachments: list[discord.Attachment], original_interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.original_interaction = original_interaction
        
        for i, attachment in enumerate(attachments):
            if i >= 4: break 
            button = Button(label=f"Edit Image {i+1}", style=discord.ButtonStyle.primary, custom_id=f"select_edit_img_{i}")
            
            async def callback(interaction: discord.Interaction, image_url=attachment.url):
                modal = EditKontextModal(primary_image_url=image_url, interaction=interaction)
                await interaction.response.send_modal(modal)
            
            button.callback = callback
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("You cannot select an image for another user's edit request.", ephemeral=True)
            return False
        return True


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
                    content_str = (f"{msg_details_item['user_mention']}: `{textwrap.shorten(msg_details_item['prompt_to_display'], 1000, placeholder='...')}`")
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
                sent_message_item = await safe_interaction_response(interaction, content=content_str, view=view_to_send_item)
                if sent_message_item and result_item["job_data_for_qm"]:
                    job_data_to_add_item = result_item["job_data_for_qm"]; job_data_to_add_item["message_id"] = sent_message_item.id
                    queue_manager.add_job(result_item["job_id"], job_data_to_add_item)
                    ws_client = WebsocketClient()
                    if ws_client.is_connected and result_item.get("comfy_prompt_id"):
                        await ws_client.register_prompt(result_item["comfy_prompt_id"], sent_message_item.id, sent_message_item.channel.id)
            elif result_item["status"] == "error":
                error_text_item = result_item.get('error_message_text', f'Unknown error during {action_description}.')
                await safe_interaction_response(interaction, f"Error ({action_description}): {error_text_item}", ephemeral=True)
        if not results:
            await safe_interaction_response(interaction, f"Failed to process {action_description.lower()} request (no results returned).", ephemeral=True)

    async def upscale_callback(self, interaction: discord.Interaction):
        ref_msg = await self.get_referenced_message(interaction)
        if not ref_msg: await safe_interaction_response(interaction, "Error: Original message not found.", ephemeral=True); return
        image_idx = 1
        try: image_idx = int(interaction.data['custom_id'].split('_')[1]) 
        except (IndexError, ValueError): pass
        results = await core_process_upscale(context_user=interaction.user, context_channel=interaction.channel, referenced_message_obj=ref_msg, image_idx=image_idx, is_interaction=True, initial_interaction_obj=interaction) 
        await self._process_and_send_action_results(interaction, results, "Upscale")

    async def vary_callback(self, interaction: discord.Interaction):
        try:
            settings = load_settings()
            remix_enabled = settings.get('remix_mode', False)
            
            custom_id = interaction.data['custom_id']
            
            variation_type = 'strong' if '_s_' in custom_id else 'weak'

            image_idx = 1
            try:
                parts = custom_id.split('_')
                image_idx = int(parts[-2])
            except (IndexError, ValueError): pass

            ref_msg = await self.get_referenced_message(interaction)
            if not ref_msg:
                await safe_interaction_response(interaction, "Error: Original message not found.", ephemeral=True)
                return
            
            if remix_enabled:
                job_data = queue_manager.get_job_data_by_id(self.job_id) or queue_manager.get_job_data(ref_msg.id, ref_msg.channel.id if ref_msg.channel else interaction.channel_id) 
                if not job_data:
                    await safe_interaction_response(interaction, "Error: Original job data for remix not found.", ephemeral=True)
                    return
                
                modal = RemixModal(job_data, variation_type, image_idx, ref_msg)
                await interaction.response.send_modal(modal)

            else:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=False, thinking=False)
                results = await core_process_variation(context_user=interaction.user, context_channel=interaction.channel, referenced_message_obj=ref_msg, variation_type_str=variation_type, image_idx=image_idx, is_interaction=True, initial_interaction_obj=interaction) 
                await self._process_and_send_action_results(interaction, results, f"{variation_type.capitalize()} Variation")
        except Exception as e:
            print(f"Error in single vary_callback: {e}")
            traceback.print_exc()
            await safe_interaction_response(interaction, "An unexpected error occurred during the variation process.", ephemeral=True)

    async def rerun_callback(self, interaction: discord.Interaction):
        ref_msg = await self.get_referenced_message(interaction)
        if not ref_msg: await safe_interaction_response(interaction, "Error: Original message not found.", ephemeral=True); return
        results = await core_process_rerun(context_user=interaction.user, context_channel=interaction.channel, referenced_message_obj=ref_msg, run_times_count=1, is_interaction=True, initial_interaction_obj=interaction) 
        await self._process_and_send_action_results(interaction, results, "Rerun")

    async def edit_callback(self, interaction: discord.Interaction):
        ref_msg = await self.get_referenced_message(interaction)
        if not ref_msg or not ref_msg.attachments:
            await safe_interaction_response(interaction, "Original message or its images not found.", ephemeral=True)
            return

        attachments = ref_msg.attachments
        if len(attachments) == 1:
            modal = EditKontextModal(primary_image_url=attachments[0].url, interaction=interaction)
            await interaction.response.send_modal(modal)
        else:
            view = ImageSelectionView(attachments=attachments, original_interaction=interaction)
            await interaction.response.send_message("This job has multiple images. Please select which one you'd like to edit:", view=view, ephemeral=True)

    async def delete_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
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
        
        # Clear all buttons added by the parent __init__
        self.clear_items()
        
        for i_batch_up in range(1, self.batch_size + 1):
            if i_batch_up > 5 : break 
            btn_up = Button(label=f"U{i_batch_up}", style=discord.ButtonStyle.primary, custom_id=f"upscale_{i_batch_up}_{job_id}", row=0)
            btn_up.callback = self.upscale_callback
            self.add_item(btn_up)
            
        for i_batch_vary in range(1, self.batch_size + 1):
            if i_batch_vary > 5: break
            btn_vary = Button(label=f"V{i_batch_vary}", style=discord.ButtonStyle.secondary, custom_id=f"vary_dynamic_{i_batch_vary}_{job_id}", row=1)
            btn_vary.callback = self.batch_vary_callback # Use the new dedicated callback
            self.add_item(btn_vary)
            
        # Re-add the general action buttons on the last row
        btn_rerun = Button(label="Rerun 🔄", style=discord.ButtonStyle.secondary, custom_id=f"rerun_{job_id}", row=2)
        btn_rerun.callback = self.rerun_callback
        self.add_item(btn_rerun)

        btn_edit = Button(label="Edit ✏️", style=discord.ButtonStyle.secondary, custom_id=f"edit_{job_id}", row=2)
        btn_edit.callback = self.edit_callback
        self.add_item(btn_edit)

        btn_delete = Button(label="Delete 🗑️", style=discord.ButtonStyle.danger, custom_id=f"delete_{job_id}", row=2)
        btn_delete.callback = self.delete_callback
        self.add_item(btn_delete)

    async def batch_vary_callback(self, interaction: discord.Interaction):
        """Dedicated callback for batch variation buttons (V1, V2, etc.)."""
        try:
            settings = load_settings()
            remix_enabled = settings.get('remix_mode', False)
            variation_type = settings.get('default_variation_mode', 'weak')
            
            custom_id = interaction.data['custom_id']
            
            image_idx = 1
            try:
                parts = custom_id.split('_')
                image_idx = int(parts[-2])
            except (IndexError, ValueError):
                print(f"Could not parse image index from custom_id: {custom_id}. Defaulting to 1.")

            ref_msg = await self.get_referenced_message(interaction)
            if not ref_msg:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Error: Original message not found.", ephemeral=True)
                else:
                    await interaction.followup.send("Error: Original message not found.", ephemeral=True)
                return

            if remix_enabled:
                job_data = queue_manager.get_job_data_by_id(self.job_id) or queue_manager.get_job_data(ref_msg.id, ref_msg.channel.id if ref_msg.channel else interaction.channel_id) 
                if not job_data:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("Error: Original job data for remix not found.", ephemeral=True)
                    else:
                        await interaction.followup.send("Error: Original job data for remix not found.", ephemeral=True)
                    return
                
                modal = RemixModal(job_data, variation_type, image_idx, ref_msg)
                await interaction.response.send_modal(modal)
            else:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=False, thinking=False)
                
                results = await core_process_variation(
                    context_user=interaction.user,
                    context_channel=interaction.channel,
                    referenced_message_obj=ref_msg,
                    variation_type_str=variation_type,
                    image_idx=image_idx,
                    is_interaction=True,
                    initial_interaction_obj=interaction
                )
                await self._process_and_send_action_results(interaction, results, f"{variation_type.capitalize()} Variation")

        except Exception as e:
            print(f"Error in batch_vary_callback: {e}")
            traceback.print_exc()
            await safe_interaction_response(interaction, "An unexpected error occurred during the batch variation process.", ephemeral=True)
# --- END OF FILE bot_ui_components.py ---
