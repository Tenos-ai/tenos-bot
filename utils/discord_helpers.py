"""Utility helpers for building Discord messages and registering queue jobs."""

from __future__ import annotations

import textwrap
from typing import Any, Mapping, MutableMapping, TypedDict

import discord

from queue_manager import queue_manager
from websocket_client import get_initialized_websocket_client


class JobMessageDetails(TypedDict, total=False):
    """Typed structure for message details returned by generation workflows."""

    user_mention: str
    prompt_to_display: str
    enhancer_used: bool
    display_preference: str
    total_runs: int
    run_number: int
    model_type: str
    seed: Any
    aspect_ratio: str | None
    steps: Any
    guidance_sdxl: Any
    guidance_flux: Any
    mp_size: Any
    style: str
    is_img2img: bool
    img_strength_percent: Any
    negative_prompt: str | None
    enhancer_applied_message_for_first_run: str | None
    description: str
    image_index: Any
    original_job_id: str
    is_remixed: bool
    enhancer_reference_text: str | None
    upscale_factor: Any
    denoise: Any
    model_warning_message: str | None


class JobResult(TypedDict, total=False):
    status: str
    job_id: str
    job_data_for_qm: MutableMapping[str, Any]
    comfy_prompt_id: str | None
    view_type: str | None
    view_args: Mapping[str, Any] | None
    message_content_details: JobMessageDetails


def _format_seed_line(details: Mapping[str, Any]) -> str:
    """Generate the seed / guidance portion for job messages."""

    seed = details.get("seed")
    base = f"\n> **Seed:** `{seed}`"

    aspect_ratio = details.get("aspect_ratio")
    if aspect_ratio:
        base += f", **AR:** `{aspect_ratio}`"

    steps = details.get("steps")
    if steps:
        base += f", **Steps:** `{steps}`"

    model_type = str(details.get("model_type") or "").lower()
    if model_type in {"sdxl", "qwen"}:
        guidance = details.get("guidance_sdxl")
        if guidance is not None:
            label = "Guidance (Qwen)" if model_type == "qwen" else "Guidance (SDXL)"
            base += f", **{label}:** `{guidance}`"
    else:
        guidance = details.get("guidance_flux")
        if guidance is not None:
            base += f", **Guidance (Flux):** `{guidance}`"

    mp_size = details.get("mp_size")
    if mp_size is not None:
        base += f", **MP:** `{mp_size}`"

    return base


def format_generation_status(details: Mapping[str, Any]) -> str:
    """Return the status string used when a new generation job is queued."""

    prompt = str(details.get("prompt_to_display") or "")
    prompt_short = textwrap.shorten(prompt, 1000, placeholder="...") if prompt else ""
    content = f"{details.get('user_mention', 'User')}: `{prompt_short}`"

    if details.get("enhancer_used") and details.get("display_preference") == "enhanced":
        content += " ✨"

    total_runs = details.get("total_runs")
    model_type = str(details.get("model_type") or "").upper()
    if isinstance(total_runs, int) and total_runs > 1:
        run_number = details.get("run_number", 1)
        content += f" (Job {run_number}/{total_runs}"
        content += f" - {model_type})" if model_type else ")"
    else:
        content += f" ({model_type})" if model_type else ""

    content += _format_seed_line(details)

    style = details.get("style")
    content += f"\n> **Style:** `{style}`"

    if details.get("is_img2img"):
        strength = details.get("img_strength_percent")
        if strength is not None:
            content += f", **Strength:** `{strength}%`"

    negative_prompt = details.get("negative_prompt")
    if negative_prompt:
        shortened_negative = textwrap.shorten(str(negative_prompt), 100, placeholder="...")
        content += f"\n> **No:** `{shortened_negative}`"

    content += "\n> **Status:** Queued..."

    enhancer_message = details.get("enhancer_applied_message_for_first_run")
    if enhancer_message:
        content += enhancer_message

    return content


def format_rerun_status(details: Mapping[str, Any], run_index: int, run_total: int) -> str:
    """Return the status string for rerun jobs."""

    prompt = str(details.get("prompt_to_display") or "")
    prompt_short = textwrap.shorten(prompt, 1000, placeholder="...") if prompt else ""
    model_type = str(details.get("model_type") or "").upper()

    content = f"{details.get('user_mention', 'User')}: `{prompt_short}`"
    if details.get("enhancer_used") and details.get("display_preference") == "enhanced":
        content += " ✨"

    content += f" (Rerun {run_index}/{run_total}"
    content += f" - {model_type})" if model_type else ")"

    content += _format_seed_line(details)

    style = details.get("style")
    content += f"\n> **Style:** `{style}`"

    if details.get("is_img2img"):
        strength = details.get("img_strength_percent")
        if strength is not None:
            content += f", **Strength:** `{strength}%`"

    negative_prompt = details.get("negative_prompt")
    if negative_prompt:
        shortened_negative = textwrap.shorten(str(negative_prompt), 100, placeholder="...")
        content += f"\n> **No:** `{shortened_negative}`"

    content += "\n> **Status:** Queued..."

    return content


def format_upscale_status(details: Mapping[str, Any]) -> str:
    """Return the status string for queued upscale jobs."""

    prompt = str(details.get("prompt_to_display") or "")
    prompt_short = textwrap.shorten(prompt, 70, placeholder="...") if prompt else ""

    content = (
        f"{details.get('user_mention', 'User')}: Upscaling image #{details.get('image_index')} "
        f"from job `{details.get('original_job_id')}` (Workflow: {details.get('model_type')})\n"
        f"> **Using Prompt:** `{prompt_short}`\n"
    )

    content += (
        f"> **Seed:** `{details.get('seed')}`"
        f", **Style:** `{details.get('style')}`"
        f", **Orig AR:** `{details.get('aspect_ratio')}`\n"
        f"> **Factor:** `{details.get('upscale_factor')}`"
        f", **Denoise:** `{details.get('denoise')}`\n"
        f"> **Status:** Queued..."
    )

    return content


def format_variation_status(details: Mapping[str, Any]) -> str:
    """Return the status string for variation jobs."""

    prompt = str(details.get("prompt_to_display") or "")
    prompt_short = textwrap.shorten(prompt, 50, placeholder="...") if prompt else ""
    description = details.get("description", "Variation")
    model_type = details.get("model_type")

    content = (
        f"{details.get('user_mention', 'User')}: `{prompt_short}` "
        f"({description} on img #{details.get('image_index')} from `{details.get('original_job_id')}`"
    )
    content += f" - {model_type})" if model_type else ")"

    content += (
        f"\n> **Seed:** `{details.get('seed')}`"
        f", **AR:** `{details.get('aspect_ratio')}`"
        f", **Steps:** `{details.get('steps')}`"
        f", **Style:** `{details.get('style')}`"
    )

    if details.get("is_remixed"):
        content += "\n> `(Remixed Prompt)`"

    enhancer_text = details.get("enhancer_reference_text")
    if enhancer_text:
        content += f"\n{enhancer_text.strip()}"

    content += "\n> **Status:** Queued..."

    return content


async def register_job_with_queue(result: Mapping[str, Any], sent_message: discord.Message | None) -> bool:
    """Persist job metadata, attach Discord message IDs, and register websocket tracking."""

    job_id = result.get("job_id")
    job_data = result.get("job_data_for_qm")

    if not job_id or not isinstance(job_data, Mapping):
        print(f"Warning: Job registration skipped due to missing payload (job_id={job_id}).")
        return False

    payload: dict[str, Any] = dict(job_data)

    comfy_prompt_id = result.get("comfy_prompt_id")
    if comfy_prompt_id is not None and "comfy_prompt_id" not in payload:
        payload["comfy_prompt_id"] = comfy_prompt_id

    if sent_message is not None:
        payload["message_id"] = sent_message.id
        payload["channel_id"] = getattr(sent_message.channel, "id", payload.get("channel_id"))

    queue_manager.add_job(job_id, payload)

    if sent_message is not None:
        ws_client = get_initialized_websocket_client()
        if ws_client is None:
            print("Warning: Websocket client not yet initialised; skipping prompt registration.")
        else:
            if comfy_prompt_id:
                try:
                    await ws_client.register_prompt(comfy_prompt_id, sent_message.id, sent_message.channel.id)
                except Exception as websocket_error:
                    print(
                        "Warning: Failed to register prompt "
                        f"{comfy_prompt_id} for job {job_id} with websocket: {websocket_error}"
                    )

    return True


__all__ = [
    "JobMessageDetails",
    "JobResult",
    "format_generation_status",
    "format_rerun_status",
    "format_upscale_status",
    "format_variation_status",
    "register_job_with_queue",
]
