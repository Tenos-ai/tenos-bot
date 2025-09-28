"""Helpers for resolving user-provided workflow overrides."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Tuple

from settings_manager import _get_default_settings, load_settings
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

WorkflowFactory = Callable[[], Dict[str, dict]]


DEFAULT_FACTORIES: Dict[Tuple[str, str], WorkflowFactory] = {
    ("flux", "text_to_image"): flux_text_to_image_template,
    ("flux", "img2img"): flux_img2img_template,
    ("flux", "upscale"): flux_upscale_template,
    ("flux", "variation_weak"): flux_weak_variation_template,
    ("flux", "variation_strong"): flux_strong_variation_template,
    ("sdxl", "text_to_image"): sdxl_text_to_image_template,
    ("sdxl", "img2img"): sdxl_img2img_template,
    ("sdxl", "upscale"): sdxl_upscale_template,
    ("sdxl", "variation"): sdxl_variation_template,
    ("qwen", "text_to_image"): qwen_text_to_image_template,
    ("qwen", "img2img"): qwen_img2img_template,
    ("qwen", "upscale"): qwen_upscale_template,
    ("qwen", "variation"): qwen_variation_template,
    ("qwen", "edit"): qwen_image_edit_template,
}


WORKFLOW_OVERRIDE_SLOTS: Dict[str, Dict[str, str]] = {
    "flux": {
        "text_to_image": "Flux – /gen (text-to-image)",
        "img2img": "Flux – /img2img",
        "variation_weak": "Flux – Variation (weak)",
        "variation_strong": "Flux – Variation (strong)",
        "upscale": "Flux – Upscale",
    },
    "sdxl": {
        "text_to_image": "SDXL – /gen (text-to-image)",
        "img2img": "SDXL – /img2img",
        "variation": "SDXL – Variation",
        "upscale": "SDXL – Upscale",
    },
    "qwen": {
        "text_to_image": "Qwen – /gen (text-to-image)",
        "img2img": "Qwen – /img2img",
        "variation": "Qwen – Variation",
        "upscale": "Qwen – Upscale",
        "edit": "Qwen – Image Edit (/edit)",
    },
}


def _load_custom_payload(path: str) -> Dict[str, dict] | None:
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        print(f"Custom workflow override missing at {candidate}")
        return None

    try:
        with candidate.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse custom workflow {candidate}: {exc}")
        return None
    except OSError as exc:
        print(f"Unable to read custom workflow {candidate}: {exc}")
        return None

    if not isinstance(payload, dict):
        print(f"Custom workflow {candidate} is not a JSON object; ignoring override.")
        return None

    # Ensure keys are strings to match ComfyUI expectations.
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def load_workflow_template(
    engine: str,
    workflow: str,
    *,
    settings: Dict[str, object] | None = None,
) -> Dict[str, dict]:
    """Return the workflow template for the requested engine/slot."""

    engine_key = (engine or "").strip().lower()
    workflow_key = (workflow or "").strip().lower()
    factory = DEFAULT_FACTORIES.get((engine_key, workflow_key))
    if factory is None:
        raise ValueError(f"Unknown workflow slot: {engine_key}:{workflow_key}")

    if settings is None:
        try:
            settings = load_settings()
        except Exception:
            settings = _get_default_settings()

    custom_map = settings.get("custom_workflows") if isinstance(settings, dict) else None
    if isinstance(custom_map, dict):
        engine_map = custom_map.get(engine_key)
        if isinstance(engine_map, dict):
            custom_path = engine_map.get(workflow_key)
            if isinstance(custom_path, str) and custom_path.strip():
                loaded = _load_custom_payload(custom_path.strip())
                if loaded:
                    return loaded

    return factory()


__all__ = ["load_workflow_template", "WORKFLOW_OVERRIDE_SLOTS"]
