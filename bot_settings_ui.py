# --- START OF FILE bot_settings_ui.py ---
import discord
import json
from typing import Callable, Optional

from settings_manager import (
    load_settings, save_settings,
    get_model_choices,
    get_steps_choices, get_sdxl_steps_choices, get_qwen_steps_choices, get_wan_steps_choices,
    get_guidance_choices, get_sdxl_guidance_choices, get_qwen_guidance_choices, get_wan_guidance_choices,
    get_t5_clip_choices, get_clip_l_choices, get_qwen_clip_choices, get_wan_clip_choices, get_wan_vision_clip_choices,
    get_style_choices_flux, get_style_choices_sdxl, get_style_choices_qwen, get_style_choices_wan,
    get_variation_mode_choices, get_batch_size_choices, get_variation_batch_size_choices,
    get_remix_mode_choices, get_upscale_factor_choices,
    get_llm_enhancer_choices, get_llm_provider_choices, get_llm_model_choices,
    get_mp_size_choices, get_display_prompt_preference_choices,
    get_qwen_vae_choices, get_wan_vae_choices, get_wan_low_noise_unet_choices,
    get_default_flux_model_choices, get_default_sdxl_model_choices,
    get_default_qwen_model_choices, get_default_wan_model_choices,
    get_active_model_family_choices, get_wan_animation_resolution_choices,
    get_wan_animation_duration_choices, get_wan_animation_motion_profile_choices
)

# --- UI Select Components for /settings ---


class _ModelSettingSelect(discord.ui.Select):
    def __init__(
        self,
        settings,
        *,
        placeholder: str,
        setting_key: str,
        choices_func,
        view_factory: Callable[[dict], discord.ui.View],
        convert_func=lambda value: value,
        error_message: Optional[str] = None,
        content_message: str = "Settings updated.",
    ):
        self.settings = settings
        self._setting_key = setting_key
        self._view_factory = view_factory
        self._convert_func = convert_func
        self._error_message = error_message
        self._content_message = content_message
        options = choices_func(self.settings)
        super().__init__(options=options, placeholder=placeholder)

    async def _handle_error(self, interaction: discord.Interaction):
        if self._error_message:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(self._error_message, ephemeral=True)
                else:
                    await interaction.followup.send(self._error_message, ephemeral=True)
            except discord.HTTPException:
                pass

    async def callback(self, interaction: discord.Interaction):
        if not self.values:
            return

        raw_value = self.values[0]
        try:
            converted_value = self._convert_func(raw_value)
        except (ValueError, TypeError):
            await self._handle_error(interaction)
            return

        self.settings[self._setting_key] = converted_value
        save_settings(self.settings)

        view = self._view_factory(self.settings)
        await interaction.response.edit_message(content=self._content_message, view=view)


class ModelSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_model_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Model")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['selected_model'] = self.values[0]
        save_settings(self.settings)
        view = ModelClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)


class ActiveModelFamilySelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Set Active Model Family",
            setting_key='active_model_family',
            choices_func=get_active_model_family_choices,
            view_factory=lambda data: ModelClipSettingsView(data),
            convert_func=lambda value: str(value).lower(),
            content_message="Configure Model & CLIP Settings:",
        )


class DefaultFluxModelSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Flux Model",
            setting_key='default_flux_model',
            choices_func=get_default_flux_model_choices,
            view_factory=lambda data: FluxSettingsView(data),
            content_message="Configure Flux Model Settings:",
        )


class DefaultSDXLModelSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default SDXL Checkpoint",
            setting_key='default_sdxl_checkpoint',
            choices_func=get_default_sdxl_model_choices,
            view_factory=lambda data: SDXLSettingsView(data),
            content_message="Configure SDXL Model Settings:",
        )


class DefaultQwenModelSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen Model",
            setting_key='default_qwen_checkpoint',
            choices_func=get_default_qwen_model_choices,
            view_factory=lambda data: QwenSettingsView(data),
            content_message="Configure Qwen Model Settings:",
        )


class DefaultWANModelSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default WAN Model",
            setting_key='default_wan_checkpoint',
            choices_func=get_default_wan_model_choices,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
        )

class StepsSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Steps (Flux)",
            setting_key='steps',
            choices_func=get_steps_choices,
            view_factory=lambda data: FluxSettingsView(data),
            convert_func=int,
            error_message="Invalid step value selected.",
            content_message="Configure Flux Model Settings:",
        )


class SDXLStepsSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Steps (SDXL)",
            setting_key='sdxl_steps',
            choices_func=get_sdxl_steps_choices,
            view_factory=lambda data: SDXLSettingsView(data),
            convert_func=int,
            error_message="Invalid SDXL step value selected.",
            content_message="Configure SDXL Model Settings:",
        )


class QwenStepsSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Steps (Qwen)",
            setting_key='qwen_steps',
            choices_func=get_qwen_steps_choices,
            view_factory=lambda data: QwenSettingsView(data),
            convert_func=int,
            error_message="Invalid Qwen step value selected.",
            content_message="Configure Qwen Model Settings:",
        )


class WANStepsSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Steps (WAN)",
            setting_key='wan_steps',
            choices_func=get_wan_steps_choices,
            view_factory=lambda data: WANSettingsView(data),
            convert_func=int,
            error_message="Invalid WAN step value selected.",
            content_message="Configure WAN Model Settings:",
        )


class GuidanceSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Guidance (Flux)",
            setting_key='default_guidance',
            choices_func=get_guidance_choices,
            view_factory=lambda data: FluxSettingsView(data),
            convert_func=float,
            error_message="Invalid Flux guidance value selected.",
            content_message="Configure Flux Model Settings:",
        )


class SDXLGuidanceSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Guidance (SDXL)",
            setting_key='default_guidance_sdxl',
            choices_func=get_sdxl_guidance_choices,
            view_factory=lambda data: SDXLSettingsView(data),
            convert_func=float,
            error_message="Invalid SDXL guidance value selected.",
            content_message="Configure SDXL Model Settings:",
        )


class QwenGuidanceSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Guidance (Qwen)",
            setting_key='default_guidance_qwen',
            choices_func=get_qwen_guidance_choices,
            view_factory=lambda data: QwenSettingsView(data),
            convert_func=float,
            error_message="Invalid Qwen guidance value selected.",
            content_message="Configure Qwen Model Settings:",
        )


class WANGuidanceSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Guidance (WAN)",
            setting_key='default_guidance_wan',
            choices_func=get_wan_guidance_choices,
            view_factory=lambda data: WANSettingsView(data),
            convert_func=float,
            error_message="Invalid WAN guidance value selected.",
            content_message="Configure WAN Model Settings:",
        )


class WANLowNoiseUnetSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select WAN Low-Noise UNet",
            setting_key='default_wan_low_noise_unet',
            choices_func=get_wan_low_noise_unet_choices,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
        )


class BatchSizeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_batch_size_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Batch Size (/gen)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        try:
            self.settings['default_batch_size'] = int(self.values[0])
            save_settings(self.settings)
            view = GeneralSettingsView(self.settings)
            await interaction.response.edit_message(content="Configure General Settings:", view=view)
        except ValueError: await interaction.followup.send("Invalid batch size value selected.", ephemeral=True)

class VariationBatchSizeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_variation_batch_size_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Batch Size (Vary)")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        try:
            self.settings['variation_batch_size'] = int(self.values[0])
            save_settings(self.settings)
            view = VariationRemixSettingsView(self.settings)
            await interaction.response.edit_message(content="Configure Variation & Remix Settings:", view=view)
        except ValueError: await interaction.followup.send("Invalid variation batch size selected.", ephemeral=True)

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
            view = GeneralSettingsView(self.settings)
            await interaction.response.edit_message(content="Configure General Settings:", view=view)
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
        view = GeneralSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure General Settings:", view=view)

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


class QwenClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen CLIP",
            setting_key='default_qwen_clip',
            choices_func=get_qwen_clip_choices,
            view_factory=lambda data: QwenSettingsView(data),
            content_message="Configure Qwen Model Settings:",
        )


class QwenVAESelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen VAE",
            setting_key='default_qwen_vae',
            choices_func=get_qwen_vae_choices,
            view_factory=lambda data: QwenSettingsView(data),
            content_message="Configure Qwen Model Settings:",
        )


class WANClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default WAN CLIP",
            setting_key='default_wan_clip',
            choices_func=get_wan_clip_choices,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
        )


class WANVisionClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select WAN Vision CLIP",
            setting_key='default_wan_vision_clip',
            choices_func=get_wan_vision_clip_choices,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
        )


class WANVAESelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default WAN VAE",
            setting_key='default_wan_vae',
            choices_func=get_wan_vae_choices,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
        )


class WANAnimationResolutionSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="WAN Animation Resolution",
            setting_key='wan_animation_resolution',
            choices_func=get_wan_animation_resolution_choices,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
        )


class WANAnimationDurationSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="WAN Animation Frames",
            setting_key='wan_animation_duration',
            choices_func=get_wan_animation_duration_choices,
            view_factory=lambda data: WANSettingsView(data),
            convert_func=int,
            error_message="Invalid frame count selected.",
            content_message="Configure WAN Model Settings:",
        )


class WANAnimationMotionProfileSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="WAN Motion Profile",
            setting_key='wan_animation_motion_profile',
            choices_func=get_wan_animation_motion_profile_choices,
            view_factory=lambda data: WANSettingsView(data),
            convert_func=lambda value: str(value).lower(),
            content_message="Configure WAN Model Settings:",
        )


class DefaultStyleSelectFlux(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Style (Flux)",
            setting_key='default_style_flux',
            choices_func=get_style_choices_flux,
            view_factory=lambda data: FluxSettingsView(data),
            content_message="Configure Flux Model Settings:",
        )


class DefaultStyleSelectSDXL(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Style (SDXL)",
            setting_key='default_style_sdxl',
            choices_func=get_style_choices_sdxl,
            view_factory=lambda data: SDXLSettingsView(data),
            content_message="Configure SDXL Model Settings:",
        )


class DefaultStyleSelectQwen(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Style (Qwen)",
            setting_key='default_style_qwen',
            choices_func=get_style_choices_qwen,
            view_factory=lambda data: QwenSettingsView(data),
            content_message="Configure Qwen Model Settings:",
        )


class DefaultStyleSelectWAN(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Style (WAN)",
            setting_key='default_style_wan',
            choices_func=get_style_choices_wan,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
        )

class VariationModeSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_variation_mode_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Variation Strength")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['default_variation_mode'] = self.values[0]
        save_settings(self.settings)
        view = VariationRemixSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Variation & Remix Settings:", view=view)

class RemixModeToggle(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_remix_mode_choices(self.settings)
        super().__init__(options=choices, placeholder="Toggle Variation Remix Mode")
    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['remix_mode'] = (self.values[0] == 'True')
        save_settings(self.settings)
        view = VariationRemixSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Variation & Remix Settings:", view=view)

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

    @discord.ui.button(label="Models & Clips", style=discord.ButtonStyle.primary, row=0)
    async def model_clips_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ModelClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Model & CLIP Settings:", view=view)

    @discord.ui.button(label="General Settings", style=discord.ButtonStyle.primary, row=0)
    async def general_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GeneralSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure General Settings:", view=view)

    @discord.ui.button(label="Flux Specifics", style=discord.ButtonStyle.secondary, row=1)
    async def flux_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FluxSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Flux Model Settings:", view=view)

    @discord.ui.button(label="SDXL Specifics", style=discord.ButtonStyle.secondary, row=1)
    async def sdxl_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SDXLSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure SDXL Model Settings:", view=view)

    @discord.ui.button(label="Qwen Specifics", style=discord.ButtonStyle.secondary, row=1)
    async def qwen_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = QwenSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Qwen Model Settings:", view=view)

    @discord.ui.button(label="WAN Specifics", style=discord.ButtonStyle.secondary, row=1)
    async def wan_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WANSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure WAN Model Settings:", view=view)
        
    @discord.ui.button(label="Variation & Remix", style=discord.ButtonStyle.primary, row=2)
    async def variation_remix_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = VariationRemixSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Variation & Remix Settings:", view=view)

    @discord.ui.button(label="LLM Enhancer", style=discord.ButtonStyle.primary, row=2)
    async def llm_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer & Display Settings:", view=view)

    @discord.ui.button(label="Close Settings", style=discord.ButtonStyle.grey, row=3)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Settings panel closed.", view=None)


class ModelClipSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(ActiveModelFamilySelect(self.settings))
        self.add_item(ModelSelect(self.settings))
        self.add_item(T5ClipSelect(self.settings))
        self.add_item(ClipLSelect(self.settings))

class GeneralSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(MPSizeSelect(self.settings))
        self.add_item(UpscaleFactorSelect(self.settings))
        self.add_item(BatchSizeSelect(self.settings))

class FluxSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultFluxModelSelect(self.settings)
        default_select.row = 0
        self.add_item(default_select)

        style_select = DefaultStyleSelectFlux(self.settings)
        style_select.row = 0
        self.add_item(style_select)

        steps_select = StepsSelect(self.settings)
        steps_select.row = 1
        self.add_item(steps_select)

        guidance_select = GuidanceSelect(self.settings)
        guidance_select.row = 1
        self.add_item(guidance_select)

class SDXLSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultSDXLModelSelect(self.settings)
        default_select.row = 0
        self.add_item(default_select)

        style_select = DefaultStyleSelectSDXL(self.settings)
        style_select.row = 0
        self.add_item(style_select)

        steps_select = SDXLStepsSelect(self.settings)
        steps_select.row = 1
        self.add_item(steps_select)

        guidance_select = SDXLGuidanceSelect(self.settings)
        guidance_select.row = 1
        self.add_item(guidance_select)


class QwenSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultQwenModelSelect(self.settings)
        default_select.row = 0
        self.add_item(default_select)

        style_select = DefaultStyleSelectQwen(self.settings)
        style_select.row = 0
        self.add_item(style_select)

        steps_select = QwenStepsSelect(self.settings)
        steps_select.row = 1
        self.add_item(steps_select)

        guidance_select = QwenGuidanceSelect(self.settings)
        guidance_select.row = 1
        self.add_item(guidance_select)

        clip_select = QwenClipSelect(self.settings)
        clip_select.row = 2
        self.add_item(clip_select)

        vae_select = QwenVAESelect(self.settings)
        vae_select.row = 2
        self.add_item(vae_select)


class WANSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultWANModelSelect(self.settings)
        default_select.row = 0
        self.add_item(default_select)

        style_select = DefaultStyleSelectWAN(self.settings)
        style_select.row = 0
        self.add_item(style_select)

        steps_select = WANStepsSelect(self.settings)
        steps_select.row = 1
        self.add_item(steps_select)

        guidance_select = WANGuidanceSelect(self.settings)
        guidance_select.row = 1
        self.add_item(guidance_select)

        low_noise_select = WANLowNoiseUnetSelect(self.settings)
        low_noise_select.row = 2
        self.add_item(low_noise_select)

        clip_select = WANClipSelect(self.settings)
        clip_select.row = 2
        self.add_item(clip_select)

        vision_clip_select = WANVisionClipSelect(self.settings)
        vision_clip_select.row = 3
        self.add_item(vision_clip_select)

        wan_vae_select = WANVAESelect(self.settings)
        wan_vae_select.row = 3
        self.add_item(wan_vae_select)

        anim_res_select = WANAnimationResolutionSelect(self.settings)
        anim_res_select.row = 4
        self.add_item(anim_res_select)

        anim_duration_select = WANAnimationDurationSelect(self.settings)
        anim_duration_select.row = 4
        self.add_item(anim_duration_select)

        motion_profile_select = WANAnimationMotionProfileSelect(self.settings)
        motion_profile_select.row = 4
        self.add_item(motion_profile_select)

class VariationRemixSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(VariationModeSelect(self.settings))
        self.add_item(VariationBatchSizeSelect(self.settings))
        self.add_item(RemixModeToggle(self.settings))

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
# --- END OF FILE bot_settings_ui.py ---
