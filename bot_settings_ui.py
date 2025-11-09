# --- START OF FILE bot_settings_ui.py ---
import discord
from typing import Callable, Optional

from settings_manager import (
    load_settings, save_settings,
    get_steps_choices, get_sdxl_steps_choices, get_qwen_steps_choices, get_qwen_edit_steps_choices, get_wan_steps_choices,
    get_guidance_choices, get_sdxl_guidance_choices, get_qwen_guidance_choices, get_qwen_edit_guidance_choices, get_wan_guidance_choices,
    get_t5_clip_choices, get_clip_l_choices, get_sdxl_clip_choices, get_qwen_clip_choices, get_qwen_edit_clip_choices, get_wan_clip_choices, get_wan_vision_clip_choices,
    get_style_choices_flux, get_style_choices_sdxl, get_style_choices_qwen, get_style_choices_wan,
    get_variation_mode_choices, get_batch_size_choices, get_variation_batch_size_choices,
    get_remix_mode_choices, get_upscale_factor_choices,
    get_llm_enhancer_choices, get_llm_provider_choices, get_llm_model_choices,
    get_mp_size_choices, get_display_prompt_preference_choices,
    get_editing_mode_choices, get_flux_vae_choices, get_qwen_vae_choices, get_qwen_edit_vae_choices, get_sdxl_vae_choices, get_wan_vae_choices,
    get_wan_t2v_high_unet_choices, get_wan_t2v_low_unet_choices, get_wan_i2v_high_unet_choices, get_wan_i2v_low_unet_choices,
    get_default_flux_model_choices, get_default_sdxl_model_choices,
    get_default_qwen_model_choices, get_default_qwen_edit_model_choices, get_default_wan_model_choices,
    get_active_model_family_choices, get_wan_animation_resolution_choices,
    get_wan_animation_duration_choices, get_wan_animation_motion_profile_choices,
    get_qwen_edit_shift_choices, get_qwen_edit_denoise_choices,
    sync_active_model_selection
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
        post_save_hook: Optional[Callable[[dict, object], None]] = None,
    ):
        self.settings = settings
        self._setting_key = setting_key
        self._view_factory = view_factory
        self._convert_func = convert_func
        self._error_message = error_message
        self._content_message = content_message
        self._post_save_hook = post_save_hook
        options = choices_func(self.settings)
        self._empty_choices = False
        if not options:
            options = [discord.SelectOption(label="No options available", value="__none__", default=True)]
            self._empty_choices = True
        super().__init__(options=options, placeholder=placeholder)
        if self._empty_choices:
            self.disabled = True

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
        if self._empty_choices or not self.values:
            return

        raw_value = self.values[0]
        try:
            converted_value = self._convert_func(raw_value)
        except (ValueError, TypeError):
            await self._handle_error(interaction)
            return

        self.settings[self._setting_key] = converted_value
        if self._post_save_hook:
            try:
                self._post_save_hook(self.settings, converted_value)
            except Exception as hook_error:
                print(f"Settings hook error for '{self._setting_key}': {hook_error}")
        save_settings(self.settings)

        view = self._view_factory(self.settings)
        await interaction.response.edit_message(content=self._content_message, view=view)


def _sync_if_active_family(target_family: str) -> Callable[[dict, object], None]:
    def _hook(settings: dict, _value: object) -> None:
        current_family = str(settings.get('active_model_family', 'flux') or 'flux').lower()
        if current_family == target_family:
            sync_active_model_selection(settings, active_family=target_family)

    return _hook


class ActiveModelFamilySelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Choose Active Model Type",
            setting_key='active_model_family',
            choices_func=get_active_model_family_choices,
            view_factory=lambda data: MainSettingsButtonView(data),
            convert_func=lambda value: str(value).lower(),
            content_message="Tenos.ai Bot Settings:",
            post_save_hook=lambda data, value: sync_active_model_selection(data, active_family=str(value)),
        )


class EditingModeSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Choose Default Editing Workflow",
            setting_key='default_editing_mode',
            choices_func=get_editing_mode_choices,
            view_factory=lambda data: GeneralSettingsView(data),
            convert_func=lambda value: str(value).lower(),
            content_message="Configure General Settings:",
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
            post_save_hook=_sync_if_active_family('flux'),
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
            post_save_hook=_sync_if_active_family('sdxl'),
        )


class DefaultQwenModelSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen Image Model",
            setting_key='default_qwen_checkpoint',
            choices_func=get_default_qwen_model_choices,
            view_factory=lambda data: QwenSettingsView(data),
            content_message="Configure Qwen Image Model Settings:",
            post_save_hook=_sync_if_active_family('qwen'),
        )


class DefaultQwenEditModelSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen Edit Model",
            setting_key='default_qwen_edit_checkpoint',
            choices_func=get_default_qwen_edit_model_choices,
            view_factory=lambda data: QwenEditSettingsView(data),
            content_message="Configure Qwen Edit Settings:",
            post_save_hook=_sync_if_active_family('qwen_edit'),
        )


class DefaultWANModelSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default WAN T2V High-Noise UNet",
            setting_key='default_wan_t2v_high_noise_unet',
            choices_func=get_default_wan_model_choices,
            view_factory=lambda data: WANSettingsView(data),
            content_message="Configure WAN Model Settings:",
            post_save_hook=_sync_if_active_family('wan'),
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
            content_message="Configure Qwen Image Model Settings:",
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


class SDXLClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default SDXL CLIP",
            setting_key='default_sdxl_clip',
            choices_func=get_sdxl_clip_choices,
            view_factory=lambda data: SDXLSettingsView(data),
            content_message="Configure SDXL Model Settings:",
        )


class SDXLVAESelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default SDXL VAE",
            setting_key='default_sdxl_vae',
            choices_func=get_sdxl_vae_choices,
            view_factory=lambda data: SDXLSettingsView(data),
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
            content_message="Configure Qwen Image Model Settings:",
        )


class QwenEditStepsSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Qwen Edit Steps",
            setting_key='qwen_edit_steps',
            choices_func=get_qwen_edit_steps_choices,
            view_factory=lambda data: QwenEditSettingsView(data),
            convert_func=int,
            error_message="Invalid Qwen Edit step value selected.",
            content_message="Configure Qwen Edit Settings:",
        )


class QwenEditGuidanceSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Qwen Edit Guidance",
            setting_key='default_guidance_qwen_edit',
            choices_func=get_qwen_edit_guidance_choices,
            view_factory=lambda data: QwenEditSettingsView(data),
            convert_func=float,
            error_message="Invalid Qwen Edit guidance selected.",
            content_message="Configure Qwen Edit Settings:",
        )


class QwenEditShiftSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Qwen Edit Shift",
            setting_key='qwen_edit_shift',
            choices_func=get_qwen_edit_shift_choices,
            view_factory=lambda data: QwenEditSettingsView(data),
            convert_func=float,
            error_message="Invalid Qwen Edit shift selected.",
            content_message="Configure Qwen Edit Settings:",
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


class WANT2VHighUnetSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select WAN T2V High-Noise UNet",
            setting_key='default_wan_t2v_high_noise_unet',
            choices_func=get_wan_t2v_high_unet_choices,
            view_factory=lambda data: WANLoaderSettingsView(data),
            content_message="Configure WAN Loader Settings:",
        )


class WANT2VLowUnetSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select WAN T2V Low-Noise UNet",
            setting_key='default_wan_t2v_low_noise_unet',
            choices_func=get_wan_t2v_low_unet_choices,
            view_factory=lambda data: WANLoaderSettingsView(data),
            content_message="Configure WAN Loader Settings:",
        )


class WANI2VHighUnetSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select WAN I2V High-Noise UNet",
            setting_key='default_wan_i2v_high_noise_unet',
            choices_func=get_wan_i2v_high_unet_choices,
            view_factory=lambda data: WANLoaderSettingsView(data),
            content_message="Configure WAN Loader Settings:",
        )


class WANI2VLowUnetSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select WAN I2V Low-Noise UNet",
            setting_key='default_wan_i2v_low_noise_unet',
            choices_func=get_wan_i2v_low_unet_choices,
            view_factory=lambda data: WANLoaderSettingsView(data),
            content_message="Configure WAN Loader Settings:",
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
        view = FluxClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Flux CLIP Settings:", view=view)

class ClipLSelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_clip_l_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default CLIP-L Model")

    async def callback(self, interaction: discord.Interaction):
        if not self.values: return
        self.settings['selected_clip_l'] = self.values[0]
        save_settings(self.settings)
        view = FluxClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Flux CLIP Settings:", view=view)


class FluxVAESelect(discord.ui.Select):
    def __init__(self, settings):
        self.settings = settings
        choices = get_flux_vae_choices(self.settings)
        super().__init__(options=choices, placeholder="Select Default Flux VAE")

    async def callback(self, interaction: discord.Interaction):
        if not self.values:
            return
        self.settings['default_flux_vae'] = self.values[0]
        save_settings(self.settings)
        view = FluxClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Flux CLIP Settings:", view=view)


class QwenClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen CLIP",
            setting_key='default_qwen_clip',
            choices_func=get_qwen_clip_choices,
            view_factory=lambda data: QwenAdvancedSettingsView(data),
            content_message="Configure Qwen Loader Settings:",
        )


class QwenEditClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen Edit CLIP",
            setting_key='default_qwen_edit_clip',
            choices_func=get_qwen_edit_clip_choices,
            view_factory=lambda data: QwenEditAdvancedSettingsView(data),
            content_message="Configure Qwen Edit Loader Settings:",
        )


class QwenVAESelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen VAE",
            setting_key='default_qwen_vae',
            choices_func=get_qwen_vae_choices,
            view_factory=lambda data: QwenAdvancedSettingsView(data),
            content_message="Configure Qwen Loader Settings:",
        )


class QwenEditVAESelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default Qwen Edit VAE",
            setting_key='default_qwen_edit_vae',
            choices_func=get_qwen_edit_vae_choices,
            view_factory=lambda data: QwenEditAdvancedSettingsView(data),
            content_message="Configure Qwen Edit Loader Settings:",
        )


class QwenEditDenoiseSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Qwen Edit Denoise",
            setting_key='qwen_edit_denoise',
            choices_func=get_qwen_edit_denoise_choices,
            view_factory=lambda data: QwenEditAdvancedSettingsView(data),
            convert_func=float,
            error_message="Invalid Qwen Edit denoise selected.",
            content_message="Configure Qwen Edit Loader Settings:",
        )


class WANClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default WAN CLIP",
            setting_key='default_wan_clip',
            choices_func=get_wan_clip_choices,
            view_factory=lambda data: WANLoaderSettingsView(data),
            content_message="Configure WAN Loader Settings:",
        )


class WANVisionClipSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select WAN Vision CLIP",
            setting_key='default_wan_vision_clip',
            choices_func=get_wan_vision_clip_choices,
            view_factory=lambda data: WANLoaderSettingsView(data),
            content_message="Configure WAN Loader Settings:",
        )


class WANVAESelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="Select Default WAN VAE",
            setting_key='default_wan_vae',
            choices_func=get_wan_vae_choices,
            view_factory=lambda data: WANLoaderSettingsView(data),
            content_message="Configure WAN Loader Settings:",
        )


class WANAnimationResolutionSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="WAN Animation Resolution",
            setting_key='wan_animation_resolution',
            choices_func=get_wan_animation_resolution_choices,
            view_factory=lambda data: WANAnimationSettingsView(data),
            content_message="Configure WAN Animation Settings:",
        )


class WANAnimationDurationSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="WAN Animation Frames",
            setting_key='wan_animation_duration',
            choices_func=get_wan_animation_duration_choices,
            view_factory=lambda data: WANAnimationSettingsView(data),
            convert_func=int,
            error_message="Invalid frame count selected.",
            content_message="Configure WAN Animation Settings:",
        )


class WANAnimationMotionProfileSelect(_ModelSettingSelect):
    def __init__(self, settings):
        super().__init__(
            settings,
            placeholder="WAN Motion Profile",
            setting_key='wan_animation_motion_profile',
            choices_func=get_wan_animation_motion_profile_choices,
            view_factory=lambda data: WANAnimationSettingsView(data),
            convert_func=lambda value: str(value).lower(),
            content_message="Configure WAN Animation Settings:",
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
            content_message="Configure Qwen Image Model Settings:",
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

        active_family_select = ActiveModelFamilySelect(self.settings)
        active_family_select.row = 0
        self.add_item(active_family_select)

        editing_select = EditingModeSelect(self.settings)
        editing_select._view_factory = lambda data: MainSettingsButtonView(data)
        editing_select._content_message = "Tenos.ai Bot Settings:"
        editing_select.row = 1
        self.add_item(editing_select)

    @discord.ui.button(label="General Settings", style=discord.ButtonStyle.primary, row=2)
    async def general_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = GeneralSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure General Settings:", view=view)

    @discord.ui.button(label="Flux Defaults", style=discord.ButtonStyle.secondary, row=2)
    async def flux_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FluxSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Flux Model Settings:", view=view)

    @discord.ui.button(label="SDXL Defaults", style=discord.ButtonStyle.secondary, row=2)
    async def sdxl_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SDXLSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure SDXL Model Settings:", view=view)

    @discord.ui.button(label="Qwen Image Defaults", style=discord.ButtonStyle.secondary, row=3)
    async def qwen_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = QwenSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Qwen Image Model Settings:", view=view)

    @discord.ui.button(label="Qwen Edit Defaults", style=discord.ButtonStyle.secondary, row=3)
    async def qwen_edit_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = QwenEditSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Qwen Edit Settings:", view=view)

    @discord.ui.button(label="WAN Defaults", style=discord.ButtonStyle.secondary, row=3)
    async def wan_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WANSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure WAN Model Settings:", view=view)

    @discord.ui.button(label="Variation & Remix", style=discord.ButtonStyle.primary, row=4)
    async def variation_remix_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = VariationRemixSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Variation & Remix Settings:", view=view)

    @discord.ui.button(label="LLM Enhancer", style=discord.ButtonStyle.primary, row=4)
    async def llm_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LLMSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure LLM Enhancer & Display Settings:", view=view)

    @discord.ui.button(label="Close Settings", style=discord.ButtonStyle.grey, row=4)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Settings panel closed.", view=None)


class GeneralSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(EditingModeSelect(self.settings))
        self.add_item(MPSizeSelect(self.settings))
        self.add_item(UpscaleFactorSelect(self.settings))
        self.add_item(BatchSizeSelect(self.settings))

class FluxSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultFluxModelSelect(self.settings)
        self.add_item(default_select)

        style_select = DefaultStyleSelectFlux(self.settings)
        self.add_item(style_select)

        steps_select = StepsSelect(self.settings)
        self.add_item(steps_select)

        guidance_select = GuidanceSelect(self.settings)
        self.add_item(guidance_select)

    @discord.ui.button(label="Flux CLIP Models", style=discord.ButtonStyle.secondary, row=4)
    async def flux_clip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FluxClipSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Flux CLIP Settings:", view=view)


class FluxClipSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(T5ClipSelect(self.settings))
        self.add_item(ClipLSelect(self.settings))
        self.add_item(FluxVAESelect(self.settings))

class SDXLSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultSDXLModelSelect(self.settings)
        self.add_item(default_select)

        style_select = DefaultStyleSelectSDXL(self.settings)
        self.add_item(style_select)

        steps_select = SDXLStepsSelect(self.settings)
        self.add_item(steps_select)

        guidance_select = SDXLGuidanceSelect(self.settings)
        self.add_item(guidance_select)

    @discord.ui.button(label="SDXL Loaders", style=discord.ButtonStyle.secondary, row=4)
    async def sdxl_loaders_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SDXLLoaderSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure SDXL Loader Settings:", view=view)


class SDXLLoaderSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(SDXLClipSelect(self.settings))
        self.add_item(SDXLVAESelect(self.settings))


class QwenSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultQwenModelSelect(self.settings)
        self.add_item(default_select)

        style_select = DefaultStyleSelectQwen(self.settings)
        self.add_item(style_select)

        steps_select = QwenStepsSelect(self.settings)
        self.add_item(steps_select)

        guidance_select = QwenGuidanceSelect(self.settings)
        self.add_item(guidance_select)

    @discord.ui.button(label="Qwen Loaders", style=discord.ButtonStyle.secondary, row=4)
    async def qwen_loaders_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = QwenAdvancedSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Qwen Image Loader Settings:", view=view)


class QwenAdvancedSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(QwenClipSelect(self.settings))
        self.add_item(QwenVAESelect(self.settings))


class QwenEditSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(DefaultQwenEditModelSelect(self.settings))
        self.add_item(QwenEditGuidanceSelect(self.settings))
        self.add_item(QwenEditStepsSelect(self.settings))
        self.add_item(QwenEditShiftSelect(self.settings))

    @discord.ui.button(label="Qwen Edit Loaders", style=discord.ButtonStyle.secondary, row=4)
    async def qwen_edit_loaders_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = QwenEditAdvancedSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure Qwen Edit Loader Settings:", view=view)


class QwenEditAdvancedSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(QwenEditClipSelect(self.settings))
        self.add_item(QwenEditVAESelect(self.settings))
        self.add_item(QwenEditDenoiseSelect(self.settings))


class WANSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        default_select = DefaultWANModelSelect(self.settings)
        self.add_item(default_select)

        style_select = DefaultStyleSelectWAN(self.settings)
        self.add_item(style_select)

        steps_select = WANStepsSelect(self.settings)
        self.add_item(steps_select)

        guidance_select = WANGuidanceSelect(self.settings)
        self.add_item(guidance_select)

    @discord.ui.button(label="WAN Loaders", style=discord.ButtonStyle.secondary, row=4)
    async def wan_loaders_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WANLoaderSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure WAN Loader Settings:", view=view)

    @discord.ui.button(label="WAN Animation", style=discord.ButtonStyle.secondary, row=4)
    async def wan_animation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WANAnimationSettingsView(self.settings)
        await interaction.response.edit_message(content="Configure WAN Animation Settings:", view=view)


class WANLoaderSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(WANT2VHighUnetSelect(self.settings))
        self.add_item(WANT2VLowUnetSelect(self.settings))
        self.add_item(WANI2VHighUnetSelect(self.settings))
        self.add_item(WANI2VLowUnetSelect(self.settings))
        self.add_item(WANClipSelect(self.settings))
        self.add_item(WANVisionClipSelect(self.settings))
        self.add_item(WANVAESelect(self.settings))


class WANAnimationSettingsView(BaseSettingsView):
    def __init__(self, settings_ref):
        super().__init__(settings_ref)
        self.add_item(WANAnimationResolutionSelect(self.settings))
        self.add_item(WANAnimationDurationSelect(self.settings))
        self.add_item(WANAnimationMotionProfileSelect(self.settings))

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
