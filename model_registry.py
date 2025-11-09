from __future__ import annotations

"""Central registry describing Tenos model workflows."""

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple

from prompt_templates import (
    # Flux templates
    prompt as flux_prompt_template,
    img2img as flux_img2img_template,
    weakvary_prompt as flux_weakvary_template,
    strongvary_prompt as flux_strongvary_template,
    upscale_prompt as flux_upscale_template,
    GENERATION_MODEL_NODE,
    GENERATION_WORKFLOW_STEPS_NODE,
    GENERATION_CLIP_NODE,
    GENERATION_LATENT_NODE,
    PROMPT_LORA_NODE,
    IMG2IMG_LORA_NODE,
    VARIATION_MODEL_NODE,
    VARIATION_WORKFLOW_STEPS_NODE,
    VARIATION_CLIP_NODE,
    VARY_LORA_NODE,
    FLUX_VAR_BATCH_NODE,
    UPSCALE_MODEL_NODE,
    UPSCALE_CLIP_NODE,
    UPSCALE_LORA_NODE,
    UPSCALE_HELPER_LATENT_NODE,
    # SDXL templates
    sdxl_prompt as sdxl_prompt_template,
    sdxl_img2img_prompt,
    sdxl_variation_prompt,
    sdxl_upscale_prompt,
    SDXL_CHECKPOINT_LOADER_NODE,
    SDXL_LORA_NODE,
    SDXL_CLIP_SKIP_NODE,
    SDXL_POS_PROMPT_NODE,
    SDXL_NEG_PROMPT_NODE,
    SDXL_KSAMPLER_NODE,
    SDXL_SAVE_IMAGE_NODE,
    SDXL_LATENT_NODE,
    SDXL_IMG2IMG_LOAD_IMAGE_NODE,
    SDXL_IMG2IMG_VAE_ENCODE_NODE,
    SDXL_VAR_LORA_NODE,
    SDXL_VAR_LOAD_IMAGE_NODE,
    SDXL_VAR_RESIZE_NODE,
    SDXL_VAR_VAE_ENCODE_NODE,
    SDXL_VAR_CLIP_SKIP_NODE,
    SDXL_VAR_POS_PROMPT_NODE,
    SDXL_VAR_NEG_PROMPT_NODE,
    SDXL_VAR_KSAMPLER_NODE,
    SDXL_VAR_VAE_DECODE_NODE,
    SDXL_VAR_SAVE_IMAGE_NODE,
    SDXL_VAR_BATCH_NODE,
    SDXL_UPSCALE_LORA_NODE,
    SDXL_UPSCALE_LOAD_IMAGE_NODE,
    SDXL_UPSCALE_MODEL_LOADER_NODE,
    SDXL_UPSCALE_ULTIMATE_NODE,
    SDXL_UPSCALE_HELPER_LATENT_NODE,
    SDXL_UPSCALE_SAVE_IMAGE_NODE,
    SDXL_UPSCALE_CLIP_SKIP_NODE,
    SDXL_UPSCALE_POS_PROMPT_NODE,
    SDXL_UPSCALE_NEG_PROMPT_NODE,
    # Qwen templates
    qwen_prompt,
    qwen_img2img_prompt,
    qwen_variation_prompt,
    qwen_upscale_prompt,
    QWEN_UNET_LOADER_NODE,
    QWEN_CLIP_LOADER_NODE,
    QWEN_VAE_LOADER_NODE,
    QWEN_LORA_NODE,
    QWEN_SAMPLING_NODE,
    QWEN_POS_PROMPT_NODE,
    QWEN_NEG_PROMPT_NODE,
    QWEN_KSAMPLER_NODE,
    QWEN_SAVE_IMAGE_NODE,
    QWEN_LATENT_NODE,
    QWEN_IMG2IMG_LOAD_IMAGE_NODE,
    QWEN_IMG2IMG_VAE_ENCODE_NODE,
    QWEN_VAR_LOAD_IMAGE_NODE,
    QWEN_VAR_RESIZE_NODE,
    QWEN_VAR_VAE_ENCODE_NODE,
    QWEN_VAR_SAMPLING_NODE,
    QWEN_VAR_POS_PROMPT_NODE,
    QWEN_VAR_NEG_PROMPT_NODE,
    QWEN_VAR_KSAMPLER_NODE,
    QWEN_VAR_VAE_DECODE_NODE,
    QWEN_VAR_SAVE_IMAGE_NODE,
    QWEN_VAR_BATCH_NODE,
    QWEN_UPSCALE_LOAD_IMAGE_NODE,
    QWEN_UPSCALE_MODEL_LOADER_NODE,
    QWEN_UPSCALE_ULTIMATE_NODE,
    QWEN_UPSCALE_HELPER_LATENT_NODE,
    QWEN_UPSCALE_SAVE_IMAGE_NODE,
    QWEN_UPSCALE_POS_PROMPT_NODE,
    QWEN_UPSCALE_NEG_PROMPT_NODE,
    QWEN_UPSCALE_SAMPLING_NODE,
    # WAN templates
    wan_prompt,
    wan_img2img_prompt,
    wan_variation_prompt,
    wan_image_to_video_prompt,
    WAN_MODEL_LOADER_NODE,
    WAN_T5_LOADER_NODE,
    WAN_TEXT_ENCODER_NODE,
    WAN_VAE_LOADER_NODE,
    WAN_IMAGE_EMBEDS_NODE,
    WAN_CACHE_ARGS_NODE,
    WAN_SLG_ARGS_NODE,
    WAN_EXPERIMENTAL_ARGS_NODE,
    WAN_SAMPLER_NODE,
    WAN_DECODE_NODE,
    WAN_VIDEO_SAVE_NODE,
    WAN_IMAGE_LOADER_NODE,
    WAN_IMAGE_RESIZE_NODE,
    WAN_IMAGE_ENCODE_NODE,
)
from utils.llm_enhancer import get_model_type_enhancer_prompt


@dataclass(frozen=True)
class DefaultKeys:
    guidance_key: str
    guidance_fallback: float
    steps_key: str
    steps_fallback: int
    style_key: str


@dataclass(frozen=True)
class GenerationSpec:
    family: str
    text2img_template: Mapping[str, dict]
    img2img_template: Mapping[str, dict]
    ksampler_node: str
    initial_ksampler_node: Optional[str]
    latent_node: str
    latent_model_type: str
    save_node: str
    model_loader_node: str
    comfy_category: str
    supports_negative_prompt: bool
    prompt_node: Optional[str] = None
    guidance_node: Optional[str] = None
    clip_loader_node: Optional[str] = None
    vae_loader_node: Optional[str] = None
    clip_skip_node: Optional[str] = None
    pos_prompt_node: Optional[str] = None
    neg_prompt_node: Optional[str] = None
    lora_node: Optional[str] = None
    lora_node_img2img: Optional[str] = None
    img2img_load_node: Optional[str] = None
    img2img_encode_node: Optional[str] = None
    ksampler_model_ref: Optional[Tuple[str, int]] = None
    secondary_model_loader_node: Optional[str] = None
    secondary_model_setting_key: Optional[str] = None
    secondary_lora_node: Optional[str] = None
    t5_loader_node: Optional[str] = None
    text_encoder_node: Optional[str] = None
    cache_args_node: Optional[str] = None
    slg_args_node: Optional[str] = None
    experimental_args_node: Optional[str] = None
    video_decode_node: Optional[str] = None
    image_loader_node: Optional[str] = None
    image_resize_node: Optional[str] = None
    image_encode_node: Optional[str] = None


@dataclass(frozen=True)
class VariationSpec:
    family: str
    templates: Mapping[str, Mapping[str, dict]]
    ksampler_node: str
    save_node: str
    model_loader_node: str
    load_image_node: str
    resize_node: str
    vae_encode_node: str
    vae_decode_node: str
    lora_node: Optional[str] = None
    clip_node: Optional[str] = None
    clip_loader_node: Optional[str] = None
    clip_skip_node: Optional[str] = None
    latent_node: Optional[str] = None
    cache_args_node: Optional[str] = None
    slg_args_node: Optional[str] = None
    experimental_args_node: Optional[str] = None
    text_encoder_node: Optional[str] = None
    t5_loader_node: Optional[str] = None
    video_decode_node: Optional[str] = None
    pos_prompt_node: Optional[str] = None
    neg_prompt_node: Optional[str] = None
    prompt_node: Optional[str] = None
    batch_node: Optional[str] = None
    guidance_node: Optional[str] = None
    vae_loader_node: Optional[str] = None
    secondary_model_loader_node: Optional[str] = None
    secondary_model_setting_key: Optional[str] = None


@dataclass(frozen=True)
class UpscaleSpec:
    family: str
    template: Mapping[str, dict]
    upscale_node: str
    save_node: str
    model_loader_node: str
    load_image_node: str
    lora_node: str
    helper_latent_node: str
    latent_model_type: str
    pos_prompt_node: Optional[str] = None
    neg_prompt_node: Optional[str] = None
    clip_skip_node: Optional[str] = None
    upscale_model_loader_node: Optional[str] = None
    clip_loader_node: Optional[str] = None
    vae_loader_node: Optional[str] = None
    secondary_model_loader_node: Optional[str] = None
    secondary_model_setting_key: Optional[str] = None


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    defaults: DefaultKeys
    generation: GenerationSpec
    variation: VariationSpec
    upscale: Optional[UpscaleSpec]
    enhancer_prompt_key: str
    supports_animation: bool = False
    animation_template: Optional[Mapping[str, dict]] = None


def _deepcopy_template(template: Mapping[str, dict]) -> dict:
    """Create a JSON-safe copy of a template mapping."""
    import json

    return json.loads(json.dumps(template))


def copy_generation_template(spec: GenerationSpec, *, is_img2img: bool) -> dict:
    source = spec.img2img_template if is_img2img else spec.text2img_template
    return _deepcopy_template(source)


def copy_variation_template(spec: VariationSpec, *, strength: str = "default") -> dict:
    template_map = spec.templates
    if strength in template_map:
        template = template_map[strength]
    elif "default" in template_map:
        template = template_map["default"]
    else:
        template = next(iter(template_map.values()))
    return _deepcopy_template(template)


def copy_upscale_template(spec: Optional[UpscaleSpec]) -> dict:
    if spec is None:
        raise ValueError("Requested model does not define an upscale template")
    return _deepcopy_template(spec.template)


def copy_animation_template(spec: ModelSpec) -> dict:
    if not spec.animation_template:
        raise ValueError(f"Model '{spec.key}' does not define an animation template")
    return _deepcopy_template(spec.animation_template)


MODEL_REGISTRY: Dict[str, ModelSpec] = {
    "flux": ModelSpec(
        key="flux",
        label="Flux",
        defaults=DefaultKeys(
            guidance_key="default_guidance",
            guidance_fallback=3.5,
            steps_key="steps",
            steps_fallback=32,
            style_key="default_style_flux",
        ),
        generation=GenerationSpec(
            family="flux",
            text2img_template=flux_prompt_template,
            img2img_template=flux_img2img_template,
            ksampler_node=str(GENERATION_WORKFLOW_STEPS_NODE),
            initial_ksampler_node=None,
            latent_node=str(GENERATION_LATENT_NODE),
            latent_model_type="FLUX",
            save_node="7",
            model_loader_node=str(GENERATION_MODEL_NODE),
            comfy_category="unet",
            supports_negative_prompt=False,
            prompt_node="4",
            guidance_node="5",
            clip_loader_node=str(GENERATION_CLIP_NODE),
            lora_node=str(PROMPT_LORA_NODE),
            lora_node_img2img=str(IMG2IMG_LORA_NODE),
            img2img_load_node="15",
            img2img_encode_node="14",
        ),
        variation=VariationSpec(
            family="flux",
            templates={
                "weak": flux_weakvary_template,
                "strong": flux_strongvary_template,
            },
            ksampler_node=str(VARIATION_WORKFLOW_STEPS_NODE),
            save_node="34",
            model_loader_node=str(VARIATION_MODEL_NODE),
            load_image_node="33",
            resize_node="36",
            vae_encode_node="22",
            vae_decode_node="11",
            lora_node=str(VARY_LORA_NODE),
            clip_node=str(VARIATION_CLIP_NODE),
            prompt_node="8",
            batch_node=str(FLUX_VAR_BATCH_NODE),
            guidance_node="5",
            vae_loader_node="3",
        ),
        upscale=UpscaleSpec(
            family="flux",
            template=flux_upscale_template,
            upscale_node="104",
            save_node="58",
            model_loader_node=str(UPSCALE_MODEL_NODE),
            load_image_node="115",
            lora_node=str(UPSCALE_LORA_NODE),
            helper_latent_node=str(UPSCALE_HELPER_LATENT_NODE),
            latent_model_type="FLUX",
            pos_prompt_node="1",
            neg_prompt_node="1",
            upscale_model_loader_node="103",
            clip_loader_node=str(UPSCALE_CLIP_NODE),
            vae_loader_node="8:2",
        ),
        enhancer_prompt_key="flux",
    ),
    "sdxl": ModelSpec(
        key="sdxl",
        label="SDXL",
        defaults=DefaultKeys(
            guidance_key="default_guidance_sdxl",
            guidance_fallback=7.0,
            steps_key="sdxl_steps",
            steps_fallback=26,
            style_key="default_style_sdxl",
        ),
        generation=GenerationSpec(
            family="checkpoint",
            text2img_template=sdxl_prompt_template,
            img2img_template=sdxl_img2img_prompt,
            ksampler_node=str(SDXL_KSAMPLER_NODE),
            initial_ksampler_node=None,
            latent_node=str(SDXL_LATENT_NODE),
            latent_model_type="SDXL",
            save_node=str(SDXL_SAVE_IMAGE_NODE),
            model_loader_node=str(SDXL_CHECKPOINT_LOADER_NODE),
            comfy_category="unet",
            supports_negative_prompt=True,
            clip_skip_node=str(SDXL_CLIP_SKIP_NODE),
            pos_prompt_node=str(SDXL_POS_PROMPT_NODE),
            neg_prompt_node=str(SDXL_NEG_PROMPT_NODE),
            lora_node=str(SDXL_LORA_NODE),
            img2img_load_node=str(SDXL_IMG2IMG_LOAD_IMAGE_NODE),
            img2img_encode_node=str(SDXL_IMG2IMG_VAE_ENCODE_NODE),
        ),
        variation=VariationSpec(
            family="checkpoint",
            templates={"default": sdxl_variation_prompt},
            ksampler_node=str(SDXL_VAR_KSAMPLER_NODE),
            save_node=str(SDXL_VAR_SAVE_IMAGE_NODE),
            model_loader_node=str(SDXL_CHECKPOINT_LOADER_NODE),
            load_image_node=str(SDXL_VAR_LOAD_IMAGE_NODE),
            resize_node=str(SDXL_VAR_RESIZE_NODE),
            vae_encode_node=str(SDXL_VAR_VAE_ENCODE_NODE),
            vae_decode_node=str(SDXL_VAR_VAE_DECODE_NODE),
            lora_node=str(SDXL_VAR_LORA_NODE),
            clip_skip_node=str(SDXL_VAR_CLIP_SKIP_NODE),
            pos_prompt_node=str(SDXL_VAR_POS_PROMPT_NODE),
            neg_prompt_node=str(SDXL_VAR_NEG_PROMPT_NODE),
            batch_node=str(SDXL_VAR_BATCH_NODE),
        ),
        upscale=UpscaleSpec(
            family="checkpoint",
            template=sdxl_upscale_prompt,
            upscale_node=str(SDXL_UPSCALE_ULTIMATE_NODE),
            save_node=str(SDXL_UPSCALE_SAVE_IMAGE_NODE),
            model_loader_node=str(SDXL_CHECKPOINT_LOADER_NODE),
            load_image_node=str(SDXL_UPSCALE_LOAD_IMAGE_NODE),
            lora_node=str(SDXL_UPSCALE_LORA_NODE),
            helper_latent_node=str(SDXL_UPSCALE_HELPER_LATENT_NODE),
            latent_model_type="SDXL",
            pos_prompt_node=str(SDXL_UPSCALE_POS_PROMPT_NODE),
            neg_prompt_node=str(SDXL_UPSCALE_NEG_PROMPT_NODE),
            clip_skip_node=str(SDXL_UPSCALE_CLIP_SKIP_NODE),
            upscale_model_loader_node=str(SDXL_UPSCALE_MODEL_LOADER_NODE),
        ),
        enhancer_prompt_key="sdxl",
    ),
    "qwen": ModelSpec(
        key="qwen",
        label="Qwen Image",
        defaults=DefaultKeys(
            guidance_key="default_guidance_qwen",
            guidance_fallback=5.5,
            steps_key="qwen_steps",
            steps_fallback=28,
            style_key="default_style_qwen",
        ),
        generation=GenerationSpec(
            family="checkpoint",
            text2img_template=qwen_prompt,
            img2img_template=qwen_img2img_prompt,
            ksampler_node=str(QWEN_KSAMPLER_NODE),
            initial_ksampler_node=None,
            latent_node=str(QWEN_LATENT_NODE),
            latent_model_type="QWEN",
            save_node=str(QWEN_SAVE_IMAGE_NODE),
            model_loader_node=str(QWEN_UNET_LOADER_NODE),
            comfy_category="unet",
            supports_negative_prompt=True,
            pos_prompt_node=str(QWEN_POS_PROMPT_NODE),
            neg_prompt_node=str(QWEN_NEG_PROMPT_NODE),
            lora_node=str(QWEN_LORA_NODE),
            img2img_load_node=str(QWEN_IMG2IMG_LOAD_IMAGE_NODE),
            img2img_encode_node=str(QWEN_IMG2IMG_VAE_ENCODE_NODE),
            clip_loader_node=str(QWEN_CLIP_LOADER_NODE),
            vae_loader_node=str(QWEN_VAE_LOADER_NODE),
            ksampler_model_ref=(str(QWEN_SAMPLING_NODE), 0),
        ),
        variation=VariationSpec(
            family="checkpoint",
            templates={"default": qwen_variation_prompt},
            ksampler_node=str(QWEN_VAR_KSAMPLER_NODE),
            save_node=str(QWEN_VAR_SAVE_IMAGE_NODE),
            model_loader_node=str(QWEN_UNET_LOADER_NODE),
            load_image_node=str(QWEN_VAR_LOAD_IMAGE_NODE),
            resize_node=str(QWEN_VAR_RESIZE_NODE),
            vae_encode_node=str(QWEN_VAR_VAE_ENCODE_NODE),
            vae_decode_node=str(QWEN_VAR_VAE_DECODE_NODE),
            lora_node=str(QWEN_LORA_NODE),
            clip_loader_node=str(QWEN_CLIP_LOADER_NODE),
            pos_prompt_node=str(QWEN_VAR_POS_PROMPT_NODE),
            neg_prompt_node=str(QWEN_VAR_NEG_PROMPT_NODE),
            batch_node=str(QWEN_VAR_BATCH_NODE),
            vae_loader_node=str(QWEN_VAE_LOADER_NODE),
        ),
        upscale=UpscaleSpec(
            family="checkpoint",
            template=qwen_upscale_prompt,
            upscale_node=str(QWEN_UPSCALE_ULTIMATE_NODE),
            save_node=str(QWEN_UPSCALE_SAVE_IMAGE_NODE),
            model_loader_node=str(QWEN_UNET_LOADER_NODE),
            load_image_node=str(QWEN_UPSCALE_LOAD_IMAGE_NODE),
            lora_node=str(QWEN_LORA_NODE),
            helper_latent_node=str(QWEN_UPSCALE_HELPER_LATENT_NODE),
            latent_model_type="QWEN",
            pos_prompt_node=str(QWEN_UPSCALE_POS_PROMPT_NODE),
            neg_prompt_node=str(QWEN_UPSCALE_NEG_PROMPT_NODE),
            clip_skip_node=None,
            upscale_model_loader_node=str(QWEN_UPSCALE_MODEL_LOADER_NODE),
            clip_loader_node=str(QWEN_CLIP_LOADER_NODE),
            vae_loader_node=str(QWEN_VAE_LOADER_NODE),
        ),
        enhancer_prompt_key="qwen",
    ),
    "wan": ModelSpec(
        key="wan",
        label="WAN 2.2",
        defaults=DefaultKeys(
            guidance_key="default_guidance_wan",
            guidance_fallback=6.0,
            steps_key="wan_steps",
            steps_fallback=30,
            style_key="default_style_wan",
        ),
        generation=GenerationSpec(
            family="checkpoint",
            text2img_template=wan_prompt,
            img2img_template=wan_img2img_prompt,
            ksampler_node=str(WAN_SAMPLER_NODE),
            initial_ksampler_node=None,
            latent_node=str(WAN_IMAGE_EMBEDS_NODE),
            latent_model_type="WAN",
            save_node=str(WAN_VIDEO_SAVE_NODE),
            model_loader_node=str(WAN_MODEL_LOADER_NODE),
            comfy_category="diffusion_models",
            supports_negative_prompt=True,
            pos_prompt_node=str(WAN_TEXT_ENCODER_NODE),
            neg_prompt_node=str(WAN_TEXT_ENCODER_NODE),
            img2img_load_node=str(WAN_IMAGE_LOADER_NODE),
            img2img_encode_node=str(WAN_IMAGE_ENCODE_NODE),
            clip_loader_node=str(WAN_T5_LOADER_NODE),
            vae_loader_node=str(WAN_VAE_LOADER_NODE),
            t5_loader_node=str(WAN_T5_LOADER_NODE),
            text_encoder_node=str(WAN_TEXT_ENCODER_NODE),
            cache_args_node=str(WAN_CACHE_ARGS_NODE),
            slg_args_node=str(WAN_SLG_ARGS_NODE),
            experimental_args_node=str(WAN_EXPERIMENTAL_ARGS_NODE),
            video_decode_node=str(WAN_DECODE_NODE),
            image_loader_node=str(WAN_IMAGE_LOADER_NODE),
            image_resize_node=str(WAN_IMAGE_RESIZE_NODE),
            image_encode_node=str(WAN_IMAGE_ENCODE_NODE),
        ),
        variation=VariationSpec(
            family="checkpoint",
            templates={"default": wan_variation_prompt},
            ksampler_node=str(WAN_SAMPLER_NODE),
            save_node=str(WAN_VIDEO_SAVE_NODE),
            model_loader_node=str(WAN_MODEL_LOADER_NODE),
            load_image_node=str(WAN_IMAGE_LOADER_NODE),
            resize_node=str(WAN_IMAGE_RESIZE_NODE),
            vae_encode_node=str(WAN_IMAGE_ENCODE_NODE),
            vae_decode_node=str(WAN_DECODE_NODE),
            clip_loader_node=str(WAN_T5_LOADER_NODE),
            text_encoder_node=str(WAN_TEXT_ENCODER_NODE),
            t5_loader_node=str(WAN_T5_LOADER_NODE),
            cache_args_node=str(WAN_CACHE_ARGS_NODE),
            slg_args_node=str(WAN_SLG_ARGS_NODE),
            experimental_args_node=str(WAN_EXPERIMENTAL_ARGS_NODE),
            latent_node=str(WAN_IMAGE_EMBEDS_NODE),
            video_decode_node=str(WAN_DECODE_NODE),
        ),
        upscale=None,
        enhancer_prompt_key="wan",
        supports_animation=True,
        animation_template=wan_image_to_video_prompt,
    ),
}


MODEL_TYPE_ALIASES = {
    "flux": "flux",
    "sdxl": "sdxl",
    "qwen": "qwen",
    "wan": "wan",
}


PREFIX_TO_MODEL_TYPE = {
    "flux": "flux",
    "sdxl": "sdxl",
    "qwen": "qwen",
    "wan": "wan",
}


_QWEN_FILENAME_HINTS = ("qwen", "auraflow")
_WAN_FILENAME_HINTS = ("wan",)


def _path_component_matches_hint(component: str, hints: tuple[str, ...]) -> bool:
    """Return True if the given path component suggests a model family."""

    for hint in hints:
        if not hint:
            continue
        if component.startswith(hint):
            return True
        if f"_{hint}" in component or f"-{hint}" in component:
            return True
    return False


def resolve_model_type_from_prefix(selected_model_name_with_prefix: Optional[str]) -> tuple[str, Optional[str]]:
    """Return (model_type, actual_model_name) from a prefixed selection string."""

    if not selected_model_name_with_prefix:
        return "flux", None

    norm = selected_model_name_with_prefix.strip()
    if ":" in norm:
        prefix, name = norm.split(":", 1)
        key = PREFIX_TO_MODEL_TYPE.get(prefix.strip().lower())
        if key:
            return key, name.strip()

    lowered = norm.lower()
    if lowered.endswith((".gguf", ".sft")):
        return "flux", norm

    if lowered.endswith((".safetensors", ".ckpt", ".pth")):
        normalized_path = lowered.replace("\\", "/")
        path_parts = [part for part in normalized_path.split("/") if part]
        for part in reversed(path_parts):
            if _path_component_matches_hint(part, _QWEN_FILENAME_HINTS):
                return "qwen", norm
            if _path_component_matches_hint(part, _WAN_FILENAME_HINTS):
                return "wan", norm
        return "sdxl", norm

    return "flux", norm


def get_model_spec(model_type: str) -> ModelSpec:
    if model_type not in MODEL_REGISTRY:
        raise KeyError(f"Unknown model type '{model_type}'")
    return MODEL_REGISTRY[model_type]


def get_enhancer_prompt_for_model(model_type: str) -> str:
    spec = get_model_spec(model_type)
    return get_model_type_enhancer_prompt(spec.enhancer_prompt_key)


def get_guidance_field_name(model_type: str) -> str:
    """Return the job-data field name that stores guidance for a model."""

    guidance_key = get_model_spec(model_type).defaults.guidance_key
    if guidance_key.startswith("default_"):
        return guidance_key[len("default_"):]
    return guidance_key
