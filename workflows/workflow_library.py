"""Curated ComfyUI workflow catalogue spanning all supported engines."""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable, Iterable, List, Sequence, Tuple

from kontext_templates import get_kontext_workflow
from prompt_templates import QWEN_NEG_PROMPT_NODE, QWEN_POS_PROMPT_NODE, QWEN_SAVE_IMAGE_NODE
from workflows.flux_templates import (
    flux_img2img_template,
    flux_strong_variation_template,
    flux_text_to_image_template,
    flux_upscale_template,
    flux_weak_variation_template,
)
from workflows.qwen_templates import (
    qwen_image_edit_template,
    qwen_img2img_template,
    qwen_text_to_image_template,
    qwen_upscale_template,
    qwen_variation_template,
)
from workflows.sdxl_templates import (
    sdxl_img2img_template,
    sdxl_text_to_image_template,
    sdxl_upscale_template,
    sdxl_variation_template,
)

TemplateFactory = Callable[[], dict]


@dataclass(frozen=True, slots=True)
class WorkflowDescriptor:
    """Metadata describing a packaged ComfyUI workflow."""

    slug: str
    title: str
    description: str
    use_cases: Tuple[str, ...]
    template_factory: TemplateFactory
    documentation_url: str | None = None

    def build_template(self) -> dict:
        """Return a fresh workflow template instance for consumption."""

        return self.template_factory()


@dataclass(frozen=True, slots=True)
class WorkflowGroup:
    """Logical grouping of curated workflows for a specific engine."""

    key: str
    title: str
    description: str
    workflows: Tuple[WorkflowDescriptor, ...]


def load_workflow_catalogue() -> Sequence[WorkflowGroup]:
    """Return the curated workflow catalogue grouped by engine."""

    return (
        _build_flux_group(),
        _build_sdxl_group(),
        _build_qwen_group(),
        _build_qwen_edit_group(),
        _build_kontext_group(),
    )


def _build_flux_group() -> WorkflowGroup:
    catalogue: List[WorkflowDescriptor] = [
        WorkflowDescriptor(
            slug="flux_text_to_image",
            title="Signature Text-to-Image",
            description=(
                "Baseline Flux generation graph tuned for GGUF checkpoints with PowerLoRA staging,"
                " ideal for concept exploration and rapid iteration."
            ),
            use_cases=("Concept art", "Character design", "Environment lookdev"),
            template_factory=flux_text_to_image_template,
        ),
        WorkflowDescriptor(
            slug="flux_img2img",
            title="Guided Img2Img Remix",
            description=(
                "Image-to-image remix pipeline that resizes references, encodes to latents,"
                " and provides denoise control for faithful restyling."
            ),
            use_cases=("Pose transfer", "Lighting experiments", "Restyle iterations"),
            template_factory=flux_img2img_template,
        ),
        WorkflowDescriptor(
            slug="flux_variation_weak",
            title="Variation Studio (Soft)",
            description=(
                "Weak variation branch for subtle alternates leveraging repeat latent batching"
                " and lower denoise values."
            ),
            use_cases=("Lookbook alternates", "Minor adjustments", "Series cohesion"),
            template_factory=flux_weak_variation_template,
        ),
        WorkflowDescriptor(
            slug="flux_variation_strong",
            title="Variation Studio (Bold)",
            description=(
                "Strong variation workflow prepared for dramatic reinterpretations with"
                " higher denoise and sampler steps."
            ),
            use_cases=("Style flips", "Mood rework", "Exploratory studies"),
            template_factory=flux_strong_variation_template,
        ),
        WorkflowDescriptor(
            slug="flux_upscale",
            title="Ultimate Upscale Finisher",
            description=(
                "High-resolution upscale finisher pairing UltimateSDUpscale helpers with"
                " Flux latents for crisp final renders."
            ),
            use_cases=("Print prep", "Hero frames", "Marketing stills"),
            template_factory=flux_upscale_template,
        ),
    ]

    return WorkflowGroup(
        key="flux",
        title="Flux",
        description="Flux.1 GGUF-ready graphs covering generation, remixing, variations, and upscale workflows.",
        workflows=tuple(catalogue),
    )


def _build_sdxl_group() -> WorkflowGroup:
    catalogue: List[WorkflowDescriptor] = [
        WorkflowDescriptor(
            slug="sdxl_text_to_image",
            title="Illustration Text-to-Image",
            description=(
                "Starter SDXL workflow leveraging CLIP skip, PowerLoRA, and tuned sampler defaults"
                " for illustrative output."
            ),
            use_cases=("Key art", "Stylised posters", "Booru-style prompts"),
            template_factory=sdxl_text_to_image_template,
        ),
        WorkflowDescriptor(
            slug="sdxl_img2img",
            title="Precision Img2Img",
            description=(
                "SDXL image-to-image template that resizes sources to target megapixels and"
                " balances fidelity with creative control."
            ),
            use_cases=("Retouching", "Pose transfer", "Brand consistency"),
            template_factory=sdxl_img2img_template,
        ),
        WorkflowDescriptor(
            slug="sdxl_variation",
            title="Variation Playground",
            description=(
                "Latent variation studio for SDXL with configurable denoise and batch options"
                " for cohesive alternates."
            ),
            use_cases=("Series exploration", "Shot matching", "Mood boards"),
            template_factory=sdxl_variation_template,
        ),
        WorkflowDescriptor(
            slug="sdxl_upscale",
            title="Ultimate Upscale Finisher",
            description=(
                "High-res upscale chain combining UltimateSDUpscale, helper latents, and PowerLoRA"
                " to polish SDXL renders."
            ),
            use_cases=("Print-ready exports", "Billboard imagery", "Campaign hero shots"),
            template_factory=sdxl_upscale_template,
        ),
    ]

    return WorkflowGroup(
        key="sdxl",
        title="SDXL",
        description="SDXL tuned graphs for text-to-image, image remixing, variations, and upscaling.",
        workflows=tuple(catalogue),
    )


def _build_qwen_group() -> WorkflowGroup:
    base_catalogue: List[WorkflowDescriptor] = [
        WorkflowDescriptor(
            slug="qwen_text_to_image",
            title="Signature Text-to-Image",
            description=(
                "Baseline Qwen Image workflow tuned for fast iteration with the official checkpoint,"
                " including LoRA staging and CLIP skip presets."
            ),
            use_cases=("Concept art", "Character ideation", "Environmental mood boards"),
            template_factory=qwen_text_to_image_template,
            documentation_url="https://docs.comfy.org/tutorials/image/qwen/qwen-image",
        ),
        WorkflowDescriptor(
            slug="qwen_image_to_image",
            title="Guided Img2Img Remix",
            description=(
                "Image-to-image pipeline that handles resizing, VAE encode/decode, and denoise tuning"
                " for restyling existing renders with Qwen guidance."
            ),
            use_cases=("Pose transfer", "Light retouching", "Consistent series variations"),
            template_factory=qwen_img2img_template,
            documentation_url="https://docs.comfy.org/tutorials/image/qwen/qwen-image",
        ),
        WorkflowDescriptor(
            slug="qwen_variation",
            title="Batch Variation Studio",
            description=(
                "Batch latent variations leveraging repeat latent batching for controlled multi-shot outputs"
                " around a single concept."
            ),
            use_cases=("Lookbook alternates", "Mood explorations", "Style drift control"),
            template_factory=qwen_variation_template,
        ),
        WorkflowDescriptor(
            slug="qwen_upscale",
            title="Ultimate Upscale Finisher",
            description=(
                "High-resolution upscaling flow pairing UltimateSDUpscale with helper latent nodes and"
                " preset prompt accents for detail preservation."
            ),
            use_cases=("Print prep", "Hero frame cleanup", "Marketing stills"),
            template_factory=qwen_upscale_template,
        ),
    ]

    base_catalogue.extend(_qwen_variant_workflows())
    return WorkflowGroup(
        key="qwen",
        title="Qwen Image",
        description="Signature Qwen Image blueprints spanning generation, img2img, variations, and upscale flows.",
        workflows=tuple(base_catalogue),
    )


def _qwen_variant_workflows() -> Iterable[WorkflowDescriptor]:
    cinematic_template = _patched_template(
        source_factory=qwen_text_to_image_template,
        positive=(
            "cinematic portrait of a traveller, moody volumetric lighting, 85mm lens, shallow depth of field,"
            " award-winning photography"
        ),
        negative=(
            "poorly lit, flat composition, artifact, distorted anatomy, overexposed, low contrast, text overlay"
        ),
        filename_prefix="qwenbot/CINEMATIC",
    )

    product_template = _patched_template(
        source_factory=qwen_text_to_image_template,
        positive=(
            "studio shot of a futuristic smart speaker, floating display holograms, premium lighting rig,"
            " seamless white backdrop, product photography"
        ),
        negative=(
            "dirty, scratched surface, fingerprints, low detail, out of frame, watermark, branding mismatch"
        ),
        filename_prefix="qwenbot/PRODUCT",
    )

    return (
        WorkflowDescriptor(
            slug="qwen_cinematic_portrait",
            title="Cinematic Portrait Blueprint",
            description=(
                "Preconfigured prompt emphasizing portrait lighting, depth, and lens characteristics for"
                " quickly iterating dramatic hero shots."
            ),
            use_cases=("Key art", "Character reveal", "Poster frames"),
            template_factory=cinematic_template,
        ),
        WorkflowDescriptor(
            slug="qwen_product_showcase",
            title="Product Showcase Kit",
            description=(
                "Tailored text-to-image setup with product photography phrasing to accelerate marketing"
                " renders and hero shots of hardware concepts."
            ),
            use_cases=("E-commerce visuals", "Investor decks", "Packaging mock-ups"),
            template_factory=product_template,
        ),
    )


def _patched_template(*, source_factory: TemplateFactory, positive: str, negative: str, filename_prefix: str) -> TemplateFactory:
    def factory() -> dict:
        template = source_factory()
        template[str(QWEN_POS_PROMPT_NODE)]["inputs"]["text"] = positive
        template[str(QWEN_NEG_PROMPT_NODE)]["inputs"]["text"] = negative
        template[str(QWEN_SAVE_IMAGE_NODE)]["inputs"]["filename_prefix"] = filename_prefix
        return template

    return factory


def _build_qwen_edit_group() -> WorkflowGroup:
    catalogue = (
        WorkflowDescriptor(
            slug="qwen_edit_single",
            title="Qwen Image Edit",
            description=(
                "Single-image diffusion edit flow with denoise, CFG, and LoRA staging controls for precise revisions."
            ),
            use_cases=("Object swaps", "Targeted style shifts", "Lighting adjustments"),
            template_factory=qwen_image_edit_template,
        ),
    )

    return WorkflowGroup(
        key="qwen_edit",
        title="Qwen Edit",
        description="Diffusion-powered editing graphs that mirror the /edit command defaults for Qwen Image Edit.",
        workflows=catalogue,
    )


def _build_kontext_group() -> WorkflowGroup:
    catalogue = (
        WorkflowDescriptor(
            slug="kontext_single_image",
            title="Single Image Edit",
            description=(
                "Kontext edit graph for single-image instructions with latent preparation and Flux guidance."
            ),
            use_cases=("Solo subject edits", "Lighting polish", "Instructional retouch"),
            template_factory=partial(get_kontext_workflow, 1),
        ),
        WorkflowDescriptor(
            slug="kontext_dual_stitch",
            title="Dual Image Stitch Edit",
            description=(
                "Kontext edit pipeline prepared for two reference images, including horizontal stitching"
                " before latent encoding."
            ),
            use_cases=("A/B blend", "Outfit swap", "Side-by-side composites"),
            template_factory=partial(get_kontext_workflow, 2),
        ),
        WorkflowDescriptor(
            slug="kontext_triple_grid",
            title="Triple Image Grid Edit",
            description=(
                "Kontext edit graph that merges three references into a vertical grid prior to processing"
                " the instruction."
            ),
            use_cases=("Storyboarding", "Panel exploration", "Multi-angle edits"),
            template_factory=partial(get_kontext_workflow, 3),
        ),
        WorkflowDescriptor(
            slug="kontext_quad_grid",
            title="Quad Image Grid Edit",
            description=(
                "Kontext edit flow assembling four references into a two-by-two grid for large composite"
                " edit instructions."
            ),
            use_cases=("Moodboard merge", "Lookbook assembly", "Complex composites"),
            template_factory=partial(get_kontext_workflow, 4),
        ),
    )

    return WorkflowGroup(
        key="kontext",
        title="Kontext",
        description="Instruction-first Flux edit graphs supporting 1–4 reference images with automatic stitching.",
        workflows=catalogue,
    )


__all__ = ["WorkflowDescriptor", "WorkflowGroup", "load_workflow_catalogue"]
