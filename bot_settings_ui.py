# --- START OF FILE bot_settings_ui.py ---
import discord
import json

from settings_manager import (
    load_settings, save_settings,
    get_model_choices, get_steps_choices, get_guidance_choices, get_sdxl_guidance_choices,
    get_t5_clip_choices, get_clip_l_choices, get_style_choices,
    get_variation_mode_choices, get_batch_size_choices,
    get_remix_mode_choices, get_upscale_factor_choices,
    get_llm_enhancer_choices, get_llm_provider_choices, get_llm_model_choices,
    get_mp_size_choices, get_display_prompt_preference_choices
)

# --- UI Select Components for /settings ---

class ModelSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_model_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Model (Flux or SDXL)")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['selected_model'] = self.values[0]
        save_settings(self.settings)
        view = ModelClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)

class StepsSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_steps_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Generation Steps")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        try:
            self.settings['steps'] = int(self.values[0])
            save_settings(self.settings)
            view = GenerationDefaultsView(self.settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
        except ValueError: await interaction.followup.send("Invalid step value selected.", ephemeral=True)

class GuidanceSelect(discord.ui.Select): # For Flux Guidance
    def __init__(self, settings):
        self.settings = settings
        choices = get_guidance_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Guidance (Flux)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        try:
            self.settings['default_guidance'] = float(self.values[0])
            save_settings(self.settings)
            view = GenerationDefaultsView(self.settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
        except ValueError: await interaction.followup.send("Invalid Flux guidance value selected.", ephemeral=True)

class SDXLGuidanceSelect(discord.ui.Select): # New for SDXL Guidance
    def __init__(self, settings):
        self.settings = settings
        choices = get_sdxl_guidance_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Guidance (SDXL)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        try:
            self.settings['default_guidance_sdxl'] = float(self.values[0])
            save_settings(self.settings)
            view = GenerationDefaultsView(self.settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
        except ValueError: await interaction.followup.send("Invalid SDXL guidance value selected.", ephemeral=True)

class BatchSizeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_batch_size_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Batch Size")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        try:
            self.settings['default_batch_size'] = int(self.values[0])
            save_settings(self.settings)
            view = GenerationDefaultsView(self.settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
        except ValueError: await interaction.followup.send("Invalid batch size value selected.", ephemeral=True)

class UpscaleFactorSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_upscale_factor_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Upscale Factor")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        try:
            self.settings['upscale_factor'] = float(self.values[0])
            save_settings(self.settings)
            view = StyleVariationSettingsView(self.settings)
            await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)
        except ValueError: await interaction.followup.send("Invalid upscale factor selected.", ephemeral=True)

class MPSizeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_mp_size_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default MP Target Size (Std Gen)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['default_mp_size'] = self.values[0]
        save_settings(self.settings)
        view = ModelClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)

class T5ClipSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_t5_clip_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default T5 CLIP Model")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['selected_t5_clip'] = self.values[0]
        save_settings(self.settings)
        view = ModelClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)

class ClipLSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_clip_l_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default CLIP-L Model")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['selected_clip_l'] = self.values[0]
        save_settings(self.settings)
        view = ModelClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)

class DefaultStyleSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_style_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Style (--style)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['default_style'] = self.values[0]
        save_settings(self.settings)
        view = StyleVariationSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)

class VariationModeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_variation_mode_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Variation Strength")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['default_variation_mode'] = self.values[0]
        save_settings(self.settings)
        view = StyleVariationSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)

class RemixModeToggle(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_remix_mode_choices(self.settings)
        super().__init__(options=choices, placeholder="Toggle Variation Remix Mode")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['remix_mode'] = (self.values[0] == 'True')
        save_settings(self.settings)
        view = StyleVariationSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)

class LLMEnhancerToggle(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_llm_enhancer_choices(self.settings)
        super().__init__(options=choices, placeholder="Toggle LLM Prompt Enhancer")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['llm_enhancer_enabled'] = (self.values[0] == 'True')
        save_settings(self.settings)
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer Settings:", view=view)

class LLMProviderSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_llm_provider_choices(self.settings)
        super().__init__(options=choices, placeholder="Select LLM Provider")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['llm_provider'] = self.values[0]
        save_settings(self.settings)
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer Settings:", view=view)

class LLMModelSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        current_provider = settings.get('llm_provider', 'gemini')
        choices = get_llm_model_choices(self.settings, provider=current_provider)
        placeholder_text = "Select Model (No provider/models?)"
        if choices and not (len(choices) == 1 and choices[0].value == "none"):
             provider_display_name = current_provider.capitalize()
             for choice_opt in get_llm_provider_choices(self.settings):
                 if choice_opt.value == current_provider:
                     provider_display_name = choice_opt.label; break
             placeholder_text = f"Select Model for {provider_display_name}"

        super().__init__(options=choices, placeholder=placeholder_text)
        if not choices or (len(choices) == 1 and choices[0].value == "none"):
            self.disabled = True

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_model = self.values[0]
        current_provider = self.settings.get('llm_provider', 'gemini')
        if current_provider == 'gemini': self.settings['llm_model_gemini'] = selected_model
        elif current_provider == 'groq': self.settings['llm_model_groq'] = selected_model
        elif current_provider == 'openai': self.settings['llm_model_openai'] = selected_model
        else:
            await interaction.followup.send("Error: Unknown provider selected.", ephemeral=True)
            return
        save_settings(self.settings)
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer Settings:", view=view)

class DisplayPromptPreferenceSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_display_prompt_preference_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Prompt to Display on Discord")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['display_prompt_preference'] = self.values[0]
        save_settings(self.settings)
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer & Display Settings:", view=view)


# --- UI View Definitions for /settings ---

class BaseSettingsView(discord.ui.View):
    def __init__(self, settings_ref, timeout=300):
        super().__init__(timeout=timeout)
        self.settings = settings_ref
        back_button = discord.ui.Button(label="Back to Main Settings", style=discord.ButtonStyle.grey, custom_id="back_to_main_settings", row=4)
        back_button.callback = self.back_callback
        self.add_item(back_button)

    async def back_callback(self, interaction: discord.Interaction):
        view = MainSettingsButtonView(self.settings)
        try:
            await interaction.response.edit_message(content="Tenos.ai Bot Settings:", view=view)
        except discord.NotFound:
            print("Original message for settings view not found during back callback.")
            await interaction.followup.send("Returning to main settings selection.", view=MainSettingsButtonView(load_settings()), ephemeral=True)
        except Exception as e:
            print(f"Error during settings back callback edit: {e}")

class MainSettingsButtonView(discord.ui.View):
    def __init__(self, settings_ref):
        super().__init__(timeout=180) 
        self.settings = settings_ref

    @discord.ui.button(label="Model & Clips", style=discord.ButtonStyle.primary, row=0)
    async def model_clips_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ModelClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)

    @discord.ui.button(label="Generation Defaults", style=discord.ButtonStyle.primary, row=0)
    async def generation_defaults_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GenerationDefaultsView(self.settings)
        await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)

    @discord.ui.button(label="Style & Variation", style=discord.ButtonStyle.primary, row=1)
    async def style_variation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = StyleVariationSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)

    @discord.ui.button(label="LLM Enhancer & Display", style=discord.ButtonStyle.primary, row=1)
    async def llm_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer & Display Settings:", view=view)

    @discord.ui.button(label="Close Settings", style=discord.ButtonStyle.grey, row=2)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Settings panel closed.", view=None)


class ModelClipSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref) 
        self.add_item(ModelSelect(self.settings))
        self.add_item(T5ClipSelect(self.settings))
        self.add_item(ClipLSelect(self.settings))
        self.add_item(MPSizeSelect(self.settings))

class GenerationDefaultsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(StepsSelect(self.settings))
        self.add_item(GuidanceSelect(self.settings))
        self.add_item(SDXLGuidanceSelect(self.settings))
        self.add_item(BatchSizeSelect(self.settings))

class StyleVariationSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(DefaultStyleSelect(self.settings))
        self.add_item(VariationModeSelect(self.settings))
        self.add_item(RemixModeToggle(self.settings))
        self.add_item(UpscaleFactorSelect(self.settings))

class LLMSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(LLMEnhancerToggle(self.settings))
        self.add_item(LLMProviderSelect(self.settings))
        if settings_ref.get('llm_enhancer_enabled', False):
            model_select = LLMModelSelect(self.settings)
            if not model_select.disabled:
                 self.add_item(model_select)
        self.add_item(DisplayPromptPreferenceSelect(self.settings))
