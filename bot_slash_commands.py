# --- START OF FILE bot_slash_commands.py ---
import discord
from discord import app_commands
import textwrap
import traceback
import json 
import re 
from io import StringIO 
import asyncio 
import requests 

from bot_config_loader import ADMIN_ID, ALLOWED_USERS, COMFYUI_HOST, COMFYUI_PORT
from bot_commands import handle_gen_command
from bot_settings_ui import MainSettingsButtonView
from utils.message_utils import send_long_message, safe_interaction_response
from settings_manager import load_settings, load_styles_config
from comfyui_api import get_available_comfyui_models
from bot_core_logic import process_kontext_edit_request

_bot_instance_slash = None
def register_bot_instance_for_slash(bot_instance):
    global _bot_instance_slash
    _bot_instance_slash = bot_instance

def setup_slash_commands(tree: app_commands.CommandTree, bot_ref):
    register_bot_instance_for_slash(bot_ref)

    def has_permission(user: discord.User, permission_key: str) -> bool:
        if str(user.id) == ADMIN_ID:
            return True
        user_config = ALLOWED_USERS.get(str(user.id), {})
        return user_config.get(permission_key, False)

    @tree.command(name="ping", description="Test bot response time.")
    async def ping(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=False)
        latency_ms = round(bot_ref.latency * 1000)
        await interaction.followup.send(f"Pong! Bot latency: {latency_ms}ms", ephemeral=True)


    @tree.command(name="gen", description="Generate image(s). Use --no for SDXL negative. See /help for all options.")
    @app_commands.describe(prompt="Prompt text + optional parameters (--seed, --g, --g_sdxl, --ar, --mp, --style, --r, --no)")
    async def gen(interaction: discord.Interaction, prompt: str):
        if not has_permission(interaction.user, "can_gen"):
            await interaction.response.send_message(
                "You do not have permission to use the `/gen` command. You might be able to use `/please` to request a generation.",
                ephemeral=True
            )
            return
        await handle_gen_command(interaction, prompt)


    @tree.command(name="edit", description="Edit image(s) with an instruction using FLUX Kontext. Add --ar, --steps, --g, --mp.")
    @app_commands.describe(
        instruction="The command for editing the image (e.g., 'make the sky blue').",
        image1="The primary image to edit.",
        image2="(Optional) A second image for stitching/editing.",
        image3="(Optional) A third image for stitching/editing.",
        image4="(Optional) A fourth image for stitching/editing."
    )
    async def edit(
        interaction: discord.Interaction,
        instruction: str,
        image1: discord.Attachment,
        image2: discord.Attachment = None,
        image3: discord.Attachment = None,
        image4: discord.Attachment = None
    ):
        if not has_permission(interaction.user, "can_gen"):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False, thinking=True)
        
        image_urls = [att.url for att in [image1, image2, image3, image4] if att is not None]

        for att in [image1, image2, image3, image4]:
            if att and not att.content_type.startswith('image/'):
                await interaction.followup.send(f"Error: File '{att.filename}' is not a valid image. Please only upload images.", ephemeral=True)
                return

        await process_kontext_edit_request(
            context_user=interaction.user,
            context_channel=interaction.channel,
            instruction=instruction,
            image_urls=image_urls,
            initial_interaction_obj=interaction
        )


    @tree.command(name="styles", description="View available style names for use with --style.")
    async def styles(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        styles_data = load_styles_config()
        
        styles_with_types = []
        for name, data in styles_data.items():
            if name == "off" or not isinstance(data, dict):
                continue
            model_type = data.get('model_type', 'all').upper()
            is_favorite = data.get('favorite', False)
            styles_with_types.append({'name': name, 'type': model_type, 'favorite': is_favorite})
            
        if not styles_with_types:
            await interaction.followup.send("No custom styles are currently configured.", ephemeral=True)
            return
            
        styles_with_types.sort(key=lambda s: (not s['favorite'], s['type'], s['name'].lower()))

        msg = "**Available styles (`--style name`):**\n"
        
        max_len = 0
        for s in styles_with_types:
            item_len = len(s['name']) + len(s['type']) + 4 
            if s['favorite']:
                item_len += 2 
            if item_len > max_len:
                max_len = item_len
        
        cols = max(1, 80 // (max_len + 4)) 
        col_items = (len(styles_with_types) + cols - 1) // cols
        
        lines = []
        for i in range(col_items):
            line_parts = []
            for j in range(cols):
                idx = i + j * col_items
                if idx < len(styles_with_types):
                    style = styles_with_types[idx]
                    prefix = "⭐ " if style['favorite'] else ""
                    formatted_name = f"`{prefix}[{style['type']}] {style['name']}`"
                    line_parts.append(formatted_name.ljust(max_len + 4 + len(prefix)))
            lines.append(" ".join(line_parts).strip())
            
        msg += "\n".join(lines)
        
        dm_sent = await send_long_message(interaction.user, msg)
        if dm_sent: 
            await interaction.followup.send("Available styles list sent via DM.", ephemeral=True)
        else:
            try:
                if len(msg) > 2000:
                    msg = msg[:1990] + "\n... (list truncated)"
                if interaction.channel:
                    await interaction.channel.send(msg)
                    await interaction.followup.send("(Could not send via DM, styles list shown in channel instead)", ephemeral=True)
                else: 
                    await interaction.followup.send("Could not send styles list (channel unavailable).", ephemeral=True)
            except discord.HTTPException:
                await interaction.followup.send("Could not send styles list (message too long for DM/channel).", ephemeral=True)

    @tree.command(name="please", description="Request image generation (admin approval). See /help for options.")
    @app_commands.describe(prompt="Prompt text + optional parameters (--seed, --g, --g_sdxl, --ar, --mp, --img, --style, --r, --no)")
    async def please(interaction: discord.Interaction, prompt: str):
        admin_id_str = ADMIN_ID
        if not admin_id_str:
            await interaction.response.send_message("Bot admin not configured. This command is unavailable.", ephemeral=True)
            return
        if str(interaction.user.id) == admin_id_str:
            await interaction.response.send_message("You are the admin. Please use the `/gen` command directly.", ephemeral=True)
            return
        if has_permission(interaction.user, "can_gen"):
            await interaction.response.send_message(f"You already have permission to use `/gen` directly.", ephemeral=True)
            return

        admin_user_obj = None
        try:
            admin_user_obj = await bot_ref.fetch_user(int(admin_id_str))
        except (ValueError, TypeError, discord.NotFound):
             await interaction.response.send_message(f"Could not find the admin user with ID {admin_id_str}. Please notify them to check the config.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=True, thinking=True)

        class AcceptDeclineViewPlease(discord.ui.View):
            def __init__(self, requester_user, admin_discord_user, original_prompt_str, original_interaction_please):
                super().__init__(timeout=600)
                self.approval_status = None
                self.requester = requester_user
                self.admin_user = admin_discord_user
                self.prompt_text = original_prompt_str
                self.original_interaction_ref = original_interaction_please

            async def interaction_check(self, inter_admin: discord.Interaction) -> bool:
                if inter_admin.user.id != self.admin_user.id:
                    await inter_admin.response.send_message("Only the admin can respond to this request.", ephemeral=True)
                    return False
                return True
            async def _disable_all_buttons(self):
                for item_child in self.children:
                    if isinstance(item_child, discord.ui.Button): item_child.disabled = True
            @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
            async def accept_req_button(self, inter_admin_resp: discord.Interaction, button: discord.ui.Button):
                self.approval_status = True; await self._disable_all_buttons()
                await inter_admin_resp.response.edit_message(content=f"✅ Request accepted from {self.requester.mention} for prompt:\n```\n{textwrap.shorten(self.prompt_text, 300, placeholder='...')}\n```", view=self)
                self.stop()
            @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
            async def decline_req_button(self, inter_admin_resp: discord.Interaction, button: discord.ui.Button):
                self.approval_status = False; await self._disable_all_buttons()
                await inter_admin_resp.response.edit_message(content=f"❌ Request declined from {self.requester.mention}.", view=self)
                self.stop()
            @discord.ui.button(label="View Full Prompt", style=discord.ButtonStyle.grey)
            async def view_prompt_detail_button(self, inter_admin_resp: discord.Interaction, button: discord.ui.Button):
                await inter_admin_resp.response.defer(ephemeral=True)
                header_txt = f"Full prompt text requested by {self.requester.mention}:\n"; content_full = header_txt + f"```\n{self.prompt_text}\n```"
                dm_sent_admin = await send_long_message(inter_admin_resp.user, content_full)
                await inter_admin_resp.followup.send("Full prompt sent to your DMs." if dm_sent_admin else "Could not send prompt via DM.", ephemeral=True)

        please_view = AcceptDeclineViewPlease(interaction.user, admin_user_obj, prompt, interaction)
        truncated_prompt_admin = textwrap.shorten(prompt, 1500, placeholder="...")
        dm_request_text = f"{interaction.user.mention} requests a generation:\n```\n{truncated_prompt_admin}\n```\nPlease approve or decline."
        admin_dm_message = None
        try:
            admin_dm_message = await admin_user_obj.send(dm_request_text, view=please_view)
            await interaction.followup.send(f"Your request has been sent to {admin_user_obj.mention} for approval.", ephemeral=True)
        except discord.Forbidden: await interaction.followup.send(f"Failed to DM admin {admin_user_obj.mention}. They might have DMs disabled or blocked the bot.", ephemeral=True); return
        except Exception as e_dm_admin_please: print(f"Error DMing admin for /please: {e_dm_admin_please}"); await interaction.followup.send("Error sending request to admin.", ephemeral=True); return

        await please_view.wait()
        admin_dm_final_content = ""; requester_final_feedback = ""
        if please_view.approval_status is True:
            admin_dm_final_content = f"✅ Request from {interaction.user.mention} was **approved** by you."; requester_final_feedback = "Your generation request was approved and is being processed!"
            print(f"Request from {interaction.user.name} approved by {admin_user_obj.name}.")
            current_settings_please = load_settings(); selected_model_please = current_settings_please.get('selected_model'); model_type_please_val = "flux"
            if selected_model_please and ":" in selected_model_please: model_type_please_val = selected_model_please.split(":",1)[0].strip().lower()
            await handle_gen_command(please_view.original_interaction_ref, please_view.prompt_text, is_modal_submission=False, model_type_override=model_type_please_val, is_derivative_action=False)
        elif please_view.approval_status is False:
            admin_dm_final_content = f"❌ Request from {interaction.user.mention} was **declined** by you."; requester_final_feedback = "Your generation request was declined by the admin."
            print(f"Request from {interaction.user.name} declined by {admin_user_obj.name}.")
        else:
            admin_dm_final_content = f"⌛ Request from {interaction.user.mention} timed out (no response from you)."; requester_final_feedback = "Your request timed out as admin did not respond."
            print(f"Request from {interaction.user.name} timed out for admin {admin_user_obj.name}.")
            if admin_dm_message: await please_view._disable_all_buttons(); await admin_dm_message.edit(view=please_view)
        if admin_dm_message and please_view.approval_status is not None:
            try: await admin_dm_message.edit(content=admin_dm_final_content, view=None)
            except discord.NotFound: pass
        if requester_final_feedback:
            try: await please_view.original_interaction_ref.followup.send(requester_final_feedback, ephemeral=True)
            except Exception as e_fup_req: print(f"Error sending final feedback to /please requester: {e_fup_req}")

    @tree.command(name="settings", description="Configure default bot settings (Admin & managers only).")
    async def settings_cmd(interaction: discord.Interaction):
        if not has_permission(interaction.user, "can_manage_bot"):
            await interaction.response.send_message("Permission denied. This command is for administrators only.", ephemeral=True); return
        current_settings = load_settings(); view = MainSettingsButtonView(current_settings)
        await interaction.response.send_message("Tenos.ai Bot Settings:", view=view, ephemeral=True)

    @tree.command(name="sheet", description="Queue prompts from a TSV file (Admin & managers only).")
    @app_commands.describe(tsv_source="URL or Discord message link/ID containing a TSV file.")
    async def fetch_tsv_cmd(interaction: discord.Interaction, tsv_source: str):
        if not has_permission(interaction.user, "can_manage_bot"):
            await interaction.response.send_message("Permission denied.", ephemeral=True); return
        try: import pandas as pd
        except ImportError: await interaction.response.send_message("Error: `pandas` library required.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True); tsv_data_content = None; source_desc_log = tsv_source
        msg_match_tsv = re.match(r'(?:https?://discord\.com/channels/\d+/(\d+)/)?(\d+)', tsv_source)
        if msg_match_tsv:
            chan_id_link = msg_match_tsv.group(1); msg_id_tsv = int(msg_match_tsv.group(2)); source_desc_log = f"Discord msg ID {msg_id_tsv}"
            try:
                target_chan_tsv = await (_bot_instance_slash.fetch_channel(int(chan_id_link)) if chan_id_link else interaction.channel) # type: ignore
                if not target_chan_tsv : await interaction.followup.send("Error: Could not determine channel.",ephemeral=True); return
                msg_attach = await target_chan_tsv.fetch_message(msg_id_tsv) # type: ignore
                if msg_attach.attachments and msg_attach.attachments[0].filename.lower().endswith('.tsv'):
                    attach_tsv = msg_attach.attachments[0]
                    if attach_tsv.size > 10*1024*1024: await interaction.followup.send("Error: TSV file too large (max 10MB).",ephemeral=True); return
                    tsv_data_content = (await attach_tsv.read()).decode('utf-8')
                else: await interaction.followup.send("Error: Message has no `.tsv` attachment.",ephemeral=True); return
            except Exception as e_fetch_disc_tsv: await interaction.followup.send(f"Error accessing Discord message for TSV: {e_fetch_disc_tsv}",ephemeral=True); return
        elif tsv_source.lower().startswith("http"):
            source_desc_log = "URL"
            try:
                resp_url_tsv = await asyncio.to_thread(requests.get, tsv_source, timeout=20, stream=True); resp_url_tsv.raise_for_status()
                if int(resp_url_tsv.headers.get('content-length',0)) > 10*1024*1024: await interaction.followup.send("Error: TSV from URL too large (max 10MB).",ephemeral=True); return
                tsv_data_content = resp_url_tsv.text
            except Exception as e_fetch_url_tsv: await interaction.followup.send(f"Error fetching TSV from URL: {e_fetch_url_tsv}",ephemeral=True); return
        else: await interaction.followup.send("Invalid source. Use Discord message link/ID or URL.",ephemeral=True); return

        if tsv_data_content:
            try:
                df_tsv = pd.read_csv(StringIO(tsv_data_content), sep='\t'); prompt_col_name_tsv = next((c for c in df_tsv.columns if c.lower()=='prompt'), None)
                if not prompt_col_name_tsv: await interaction.followup.send("Error: TSV needs 'prompt' column.",ephemeral=True); return
                prompts_list_tsv = [str(p).strip() for p in df_tsv[prompt_col_name_tsv].dropna().tolist() if str(p).strip()]
                if not prompts_list_tsv: await interaction.followup.send("No valid prompts in 'prompt' column.",ephemeral=True); return
                num_prompts_tsv = len(prompts_list_tsv)
                await interaction.followup.send(f"Found {num_prompts_tsv} prompt(s) from {source_desc_log}. Starting queue in this channel...", ephemeral=True)
                
                settings_sheet = load_settings(); model_type_sheet = "flux"
                if settings_sheet.get('selected_model') and ":" in settings_sheet.get('selected_model'): model_type_sheet = settings_sheet.get('selected_model').split(":",1)[0].strip().lower() # type: ignore

                for idx_tsv, p_txt_tsv in enumerate(prompts_list_tsv):
                    print(f"Sheet Queuing {idx_tsv+1}/{num_prompts_tsv} ({model_type_sheet.upper()}): '{textwrap.shorten(p_txt_tsv,50)}'")
                    await handle_gen_command(interaction, p_txt_tsv, is_modal_submission=False, model_type_override=model_type_sheet, is_derivative_action=False)
                    await asyncio.sleep(1.5)
                await interaction.channel.send(f"{interaction.user.mention}: Finished TSV from {source_desc_log}. Queued {num_prompts_tsv} prompts.") # type: ignore
            except Exception as e_proc_tsv: await interaction.followup.send(f"Error processing TSV: {e_proc_tsv}",ephemeral=True); traceback.print_exc()
        else: await interaction.followup.send("Failed to retrieve TSV data.",ephemeral=True)

    @tree.command(name="help", description="Show information about bot commands and features.")
    async def help_cmd(interaction: discord.Interaction):
        help_text_content = (
            "**🤖 Tenos.ai Bot Help! 🤖**\n\n"
            "**Core Commands:**\n"
            "`/gen [prompt] [opts]` - Generate image(s).\n"
            "`/edit [instruction] [images] [opts]` - Edit image(s) with a command. Supports `--ar`, `--steps`, `--g`, `--mp`.\n"
            "`/please [prompt] [opts]` - Request an image generation from the admin.\n"
            "`/styles` - View available style presets.\n"
            "`/help` - Show this help message.\n\n"
            "**Action Buttons (on generated images):**\n"
            "`Upscale ⬆️` - Upscale an image for more detail.\n"
            "`Vary W 🤏` / `Vary S 💪` - Create a weak or strong variation of an image.\n"
            "`Rerun 🔄` - Rerun the original prompt with a new random seed.\n"
            "`Edit ✏️` - Open a modal to perform a Kontext edit on the image(s).\n"
            "`Delete 🗑️` - Delete the image and its source file.\n\n"
            "**Optional Parameters (for /gen and /please):**\n"
            "`--seed [number]` - Use a specific seed.\n"
            "`--g [number]` - Set guidance strength for Flux models (e.g., 3.5).\n"
            "`--g_sdxl [number]` - Set guidance for SDXL models (e.g., 7.0).\n"
            "`--ar [W:H]` - Set aspect ratio (e.g., 16:9, 1:1, 2:3).\n"
            "`--mp [megapixels]` - Set target megapixels (e.g., 1, 1.5, 4).\n"
            "`--r [number]` - Run the same prompt multiple times (1-10).\n"
            "`--style [name]` - Apply a style from `/styles`.\n"
            "`--img [strength] [url]` - Img2Img. Strength is 0-100.\n"
            "`--no \"[negative text]\"` - (SDXL only) Provide a negative prompt.\n\n"
            "**Reply Commands (reply to a bot message):**\n"
            "`--remove` - Admin/owner can remove a bot message.\n"
            "`--delete` - Admin/owner can delete job files and message.\n"
            "`--show` - Admin can see the full prompt details via DM."
        )
        try:
            dm_sent_status = await send_long_message(interaction.user, help_text_content)
            if not interaction.response.is_done():
                await interaction.response.send_message("Help information sent via DM." if dm_sent_status else help_text_content, ephemeral=True)
            elif dm_sent_status :
                await interaction.followup.send("Help information sent via DM.", ephemeral=True)
            else:
                 await interaction.followup.send(help_text_content, ephemeral=True)
        except Exception as e_help_send:
            print(f"Failed to send help message: {e_help_send}")
            if not interaction.response.is_done(): await interaction.response.send_message("Could not send help info.", ephemeral=True)
            else: await interaction.followup.send("Could not send help info.", ephemeral=True)

    @tree.command(name="clear", description="Clear the ComfyUI processing queue (Admin & managers only).")
    async def clear_queue_cmd(interaction: discord.Interaction):
        if not has_permission(interaction.user, "can_manage_bot"):
            await interaction.response.send_message("Permission denied.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True); cancelled_count = 0; interrupted_count = 0; failed_cancel_ids = []; failed_interrupt_id = None
        try:
            from bot_core_logic import process_cancel_request
            api_url = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"; q_resp = await asyncio.to_thread(requests.get, f"{api_url}/queue", timeout=10); q_resp.raise_for_status(); q_data = q_resp.json()
            pending_jobs = q_data.get('queue_pending', []); pending_ids = [job[1] for job in pending_jobs if isinstance(job, list) and len(job) > 1 and job[1] is not None]
            if pending_ids:
                cancel_payload = {"delete": [str(pid) for pid in pending_ids]};
                c_resp = await asyncio.to_thread(requests.post, f"{api_url}/queue", json=cancel_payload, timeout=15)
                if c_resp.status_code == 200: cancelled_count = len(pending_ids)
                else: failed_cancel_ids.extend(pending_ids)
                for pid_str in pending_ids: bot_job_id_c = queue_manager.get_job_id_by_comfy_id(str(pid_str)); queue_manager.mark_job_cancelled(bot_job_id_c) if bot_job_id_c else None
            running_job_info = q_data.get('queue_running', []); run_id_str = None
            if running_job_info and isinstance(running_job_info[0], list) and running_job_info[0]: run_id_str = str(running_job_info[0][0])
            if run_id_str:
                i_resp = await asyncio.to_thread(requests.post, f"{api_url}/interrupt", timeout=10)
                if i_resp.status_code == 200: interrupted_count = 1
                else: failed_interrupt_id = run_id_str
                bot_job_id_r = queue_manager.get_job_id_by_comfy_id(run_id_str); queue_manager.mark_job_cancelled(bot_job_id_r) if bot_job_id_r else None
            fb_parts = ["**ComfyUI Queue Clear Results:**", f"- Interrupted Running (API): {interrupted_count}"]
            if failed_interrupt_id: fb_parts.append(f"  *(Failed API interrupt for: `{failed_interrupt_id}`, marked cancelled locally)*")
            fb_parts.append(f"- Cancelled Pending (API): {cancelled_count}")
            if failed_cancel_ids: fb_parts.append(f"  *(Failed API cancel for `{len(failed_cancel_ids)}` IDs, marked cancelled locally)*")
            await interaction.followup.send("\n".join(fb_parts), ephemeral=True)
        except Exception as e_clear: await interaction.followup.send(f"Error clearing queue: {e_clear}", ephemeral=True); traceback.print_exc()

    @tree.command(name="models", description="List models available to ComfyUI via DM (Admin & managers only).")
    async def list_models_cmd(interaction: discord.Interaction):
        if not has_permission(interaction.user, "can_manage_bot"):
            await interaction.response.send_message("Permission denied.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            available = await asyncio.to_thread(get_available_comfyui_models, COMFYUI_HOST, COMFYUI_PORT)
            model_info = "**Available Models (from ComfyUI API)**\n"
            def format_section(title, models_list):
                section = f"\n**{title} ({len(models_list)}):**\n"; section += "\n".join([f"- `{m}`" for m in sorted(models_list,key=str.lower)]) if models_list else "- None Found"; return section + "\n"
            model_info += format_section("Flux UNET Models", available.get("unet", []))
            model_info += format_section("SDXL Checkpoint Models", available.get("checkpoint", []))
            model_info += format_section("CLIP Models", available.get("clip", []))
            model_info += format_section("VAE Models", available.get("vae", []))
            model_info += format_section("Upscaler Models", available.get("upscaler", []))
            dm_sent = await send_long_message(interaction.user, model_info)
            await interaction.followup.send("Model list sent via DM." if dm_sent else f"Found models but could not send DM (message too long or DMs disabled).", ephemeral=True)
        except Exception as e: await interaction.followup.send(f"Error getting models: {e}", ephemeral=True); traceback.print_exc()
