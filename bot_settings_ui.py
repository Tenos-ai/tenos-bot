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

class ModelSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_model_choices()
        super().__init__(options=choices, placeholder="Select Default Model (Flux or SDXL)")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_model_with_prefix = self.values[0]
        self.settings['selected_model'] = selected_model_with_prefix
        save_settings(self.settings)
        updated_settings = load_settings() # Reload to ensure view reflects saved changes
        view = ModelClipSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)
        await interaction.followup.send(f"Default model set to: `{selected_model_with_prefix or 'None'}`", ephemeral=True)

class StepsSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_steps_choices()
        super().__init__(options=choices, placeholder="Select Default Generation Steps")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_steps = self.values[0]
        try:
            self.settings['steps'] = int(selected_steps)
            save_settings(self.settings)
            updated_settings = load_settings()
            view = GenerationDefaultsView(updated_settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
            await interaction.followup.send(f"Default steps set to: {selected_steps}", ephemeral=True)
        except ValueError: await interaction.followup.send("Invalid step value selected.", ephemeral=True)

class GuidanceSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_guidance_choices()
        super().__init__(options=choices, placeholder="Select Default Guidance (Flux)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_guidance = self.values[0]
        try:
            self.settings['default_guidance'] = float(selected_guidance)
            save_settings(self.settings)
            updated_settings = load_settings()
            view = GenerationDefaultsView(updated_settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
            await interaction.followup.send(f"Default Flux guidance set to: {selected_guidance}", ephemeral=True)
        except ValueError: await interaction.followup.send("Invalid Flux guidance value selected.", ephemeral=True)

class SDXLGuidanceSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_sdxl_guidance_choices()
        super().__init__(options=choices, placeholder="Select Default Guidance (SDXL)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_guidance_sdxl = self.values[0]
        try:
            self.settings['default_guidance_sdxl'] = float(selected_guidance_sdxl)
            save_settings(self.settings)
            updated_settings = load_settings()
            view = GenerationDefaultsView(updated_settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
            await interaction.followup.send(f"Default SDXL guidance set to: {selected_guidance_sdxl}", ephemeral=True)
        except ValueError: await interaction.followup.send("Invalid SDXL guidance value selected.", ephemeral=True)

class BatchSizeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_batch_size_choices()
        super().__init__(options=choices, placeholder="Select Default Batch Size")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_size = self.values[0]
        try:
            self.settings['default_batch_size'] = int(selected_size)
            save_settings(self.settings)
            updated_settings = load_settings()
            view = GenerationDefaultsView(updated_settings)
            await interaction.response.edit_message(content="Configure Generation Default Settings:", view=view)
            await interaction.followup.send(f"Default Batch Size set to: {selected_size}", ephemeral=True)
        except ValueError: await interaction.followup.send("Invalid batch size value selected.", ephemeral=True)

class UpscaleFactorSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_upscale_factor_choices()
        super().__init__(options=choices, placeholder="Select Default Upscale Factor")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_factor = self.values[0]
        try:
            self.settings['upscale_factor'] = float(selected_factor)
            save_settings(self.settings)
            updated_settings = load_settings()
            
            view = StyleVariationSettingsView(updated_settings)
            await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)
            await interaction.followup.send(f"Default Upscale Factor set to: {selected_factor}x", ephemeral=True)
        except ValueError: await interaction.followup.send("Invalid upscale factor selected.", ephemeral=True)

class MPSizeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_mp_size_choices()
        super().__init__(options=choices, placeholder="Select Default MP Target Size (Std Gen)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_size = self.values[0]
        self.settings['default_mp_size'] = selected_size
        save_settings(self.settings)
        updated_settings = load_settings()
        view = ModelClipSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)
        await interaction.followup.send(f"Default MP Target Size set to: {selected_size} MP", ephemeral=True)

class T5ClipSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_t5_clip_choices()
        super().__init__(options=choices, placeholder="Select Default T5 CLIP Model")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_t5_clip = self.values[0]
        self.settings['selected_t5_clip'] = selected_t5_clip
        save_settings(self.settings)
        updated_settings = load_settings()
        view = ModelClipSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)
        await interaction.followup.send(f"Default T5 CLIP set to: `{selected_t5_clip or 'None'}`", ephemeral=True)

class ClipLSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_clip_l_choices()
        super().__init__(options=choices, placeholder="Select Default CLIP-L Model")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_clip_l = self.values[0]
        self.settings['selected_clip_l'] = selected_clip_l
        save_settings(self.settings)
        updated_settings = load_settings()
        view = ModelClipSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)
        await interaction.followup.send(f"Default CLIP-L set to: `{selected_clip_l or 'None'}`", ephemeral=True)

class DefaultStyleSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_style_choices()
        super().__init__(options=choices, placeholder="Select Default Style (--style)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_style = self.values[0]
        self.settings['default_style'] = selected_style
        save_settings(self.settings)
        updated_settings = load_settings()
        view = StyleVariationSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)
        await interaction.followup.send(f"Default Style set to: {selected_style}", ephemeral=True)

class VariationModeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_variation_mode_choices()
        super().__init__(options=choices, placeholder="Select Default Variation Strength")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_mode = self.values[0]
        self.settings['default_variation_mode'] = selected_mode
        save_settings(self.settings)
        updated_settings = load_settings()
        view = StyleVariationSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)
        await interaction.followup.send(f"Default Variation Mode set to: {selected_mode.capitalize()}", ephemeral=True)

class RemixModeToggle(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_remix_mode_choices()
        super().__init__(options=choices, placeholder="Toggle Variation Remix Mode")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_value = self.values[0]
        self.settings['remix_mode'] = (selected_value == 'True')
        save_settings(self.settings)
        updated_settings = load_settings()
        view = StyleVariationSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure Style & Variation Settings:", view=view)
        await interaction.followup.send(f"Variation Remix Mode set to: {'ON' if self.settings['remix_mode'] else 'OFF'}", ephemeral=True)

class LLMEnhancerToggle(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_llm_enhancer_choices()
        super().__init__(options=choices, placeholder="Toggle LLM Prompt Enhancer")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_value = self.values[0]
        self.settings['llm_enhancer_enabled'] = (selected_value == 'True')
        save_settings(self.settings)
        updated_settings = load_settings()
        view = LLMSettingsView(updated_settings) # Recreate LLMSettingsView
        await interaction.response.edit_message(content="Configure LLM Enhancer Settings:", view=view)
        feedback = f"LLM Prompt Enhancer set to: {'ON' if self.settings['llm_enhancer_enabled'] else 'OFF'}"

        
        key_missing = False
        if self.settings['llm_enhancer_enabled']:
            provider = self.settings.get('llm_provider', 'gemini')
            
            try:
                with open('config.json', 'r') as cf: temp_config = json.load(cf)
                temp_gemini_key = temp_config.get('LLM_ENHANCER', {}).get('GEMINI_API_KEY', '')
                temp_groq_key = temp_config.get('LLM_ENHANCER', {}).get('GROQ_API_KEY', '')
                temp_openai_key = temp_config.get('LLM_ENHANCER', {}).get('OPENAI_API_KEY', '')
            except Exception: temp_gemini_key, temp_groq_key, temp_openai_key = '', '', ''

            if provider == 'gemini' and not temp_gemini_key: key_missing = True
            elif provider == 'groq' and not temp_groq_key: key_missing = True
            elif provider == 'openai' and not temp_openai_key: key_missing = True
            if key_missing: feedback += f" (⚠️ Warning: API key for {provider} not set in config.json)"
        await interaction.followup.send(feedback, ephemeral=True)

class LLMProviderSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_llm_provider_choices()
        super().__init__(options=choices, placeholder="Select LLM Provider")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_provider = self.values[0]
        self.settings['llm_provider'] = selected_provider
        save_settings(self.settings)
        updated_settings = load_settings()
        view = LLMSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer Settings:", view=view)
        provider_display_name = selected_provider.capitalize()
        
        for choice in get_llm_provider_choices():
            if choice.value == selected_provider:
                provider_display_name = choice.label
                break
        await interaction.followup.send(f"LLM Provider set to: {provider_display_name}", ephemeral=True)

class LLMModelSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        current_provider = settings.get('llm_provider', 'gemini')
        choices = get_llm_model_choices(provider=current_provider)
        placeholder_text = "Select Model (No provider/models?)"
        if choices and not (len(choices) == 1 and choices[0].value == "none"):
             provider_display_name = current_provider.capitalize()
             for choice_opt in get_llm_provider_choices():
                 if choice_opt.value == current_provider:
                     provider_display_name = choice_opt.label; break
             placeholder_text = f"Select Model for {provider_display_name}"

        super().__init__(options=choices, placeholder=placeholder_text)
        if not choices or (len(choices) == 1 and choices[0].value == "none"):
            self.disabled = True

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_model = self.values[0]
        current_provider = self.settings.get('llm_provider', 'gemini') # Get current provider again
        if current_provider == 'gemini': self.settings['llm_model_gemini'] = selected_model
        elif current_provider == 'groq': self.settings['llm_model_groq'] = selected_model
        elif current_provider == 'openai': self.settings['llm_model_openai'] = selected_model
        else:
            await interaction.followup.send("Error: Unknown provider selected when setting model.", ephemeral=True)
            return
        save_settings(self.settings)
        updated_settings = load_settings()
        view = LLMSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer Settings:", view=view)
        provider_display_name = current_provider.capitalize()
        for choice_opt in get_llm_provider_choices():
            if choice_opt.value == current_provider:
                provider_display_name = choice_opt.label; break
        await interaction.followup.send(f"Default {provider_display_name} model set to: `{selected_model}`", ephemeral=True)

class DisplayPromptPreferenceSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_display_prompt_preference_choices()
        super().__init__(options=choices, placeholder="Select Prompt to Display on Discord")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        selected_preference = self.values[0]
        self.settings['display_prompt_preference'] = selected_preference
        save_settings(self.settings)
        updated_settings = load_settings()
        view = LLMSettingsView(updated_settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer Settings:", view=view)
        display_text = "Enhanced Prompt ✨" if selected_preference == "enhanced" else "Original Prompt ✍️"
        await interaction.followup.send(f"Display preference set to: {display_text}", ephemeral=True)




class BaseSettingsView(discord.ui.View):
    def __init__(self, settings_ref, timeout=300):
        super().__init__(timeout=timeout)
        self.settings = settings_ref
        back_button = discord.ui.Button(label="Back to Main Settings", style=discord.ButtonStyle.grey, custom_id="back_to_main_settings", row=4)
        back_button.callback = self.back_callback
        self.add_item(back_button)

    async def back_callback(self, interaction: discord.Interaction):
        updated_settings = load_settings() # Reload settings
        view = MainSettingsButtonView(updated_settings)
        try:
            
            
            if not interaction.response.is_done():
                await interaction.response.edit_message(content="Tenos.ai Bot Settings:", view=view)
            else: 
                 await interaction.edit_original_response(content="Tenos.ai Bot Settings:", view=view)
        except discord.NotFound:
            print("Original message for settings view not found during back callback.")
            
            await interaction.followup.send("Returning to main settings selection.", view=MainSettingsButtonView(load_settings()), ephemeral=True)
        except Exception as e:
            print(f"Error during settings back callback edit: {e}")
            try:
                
                await interaction.followup.send("Error returning to main settings. Please use `/settings` again.", ephemeral=True)
            except Exception as e_fb:
                print(f"Error sending settings back error followup: {e_fb}")

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

    @discord.ui.button(label="LLM Enhancer & Display", style=discord.ButtonStyle.primary, row=1) # Updated label
    async def llm_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer & Display Settings:", view=view) # Updated content

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

