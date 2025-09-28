"""Curated ComfyUI workflow definitions for Qwen Image."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence, Tuple

from prompt_templates import QWEN_NEG_PROMPT_NODE, QWEN_POS_PROMPT_NODE, QWEN_SAVE_IMAGE_NODE
from workflows.qwen_templates import (
    qwen_img2img_template,
    qwen_text_to_image_template,
    qwen_upscale_template,
    qwen_variation_template,
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


def load_qwen_image_workflows() -> Sequence[WorkflowDescriptor]:
    """Return the curated Qwen Image workflows shipped with the configurator."""

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

    base_catalogue.extend(_variant_workflows())
    return tuple(base_catalogue)


def _variant_workflows() -> Iterable[WorkflowDescriptor]:
    """Additional curated variants built on top of the base workflows."""

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


def _patched_template(
    *, source_factory: TemplateFactory, positive: str, negative: str, filename_prefix: str
) -> TemplateFactory:
    def factory() -> dict:
        template = source_factory()
        template[str(QWEN_POS_PROMPT_NODE)]["inputs"]["text"] = positive
        template[str(QWEN_NEG_PROMPT_NODE)]["inputs"]["text"] = negative
        template[str(QWEN_SAVE_IMAGE_NODE)]["inputs"]["filename_prefix"] = filename_prefix
        return template

    return factory

