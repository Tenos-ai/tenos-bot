"""System-level diagnostics for ComfyUI and Qwen integrations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional, Sequence

try:  # pragma: no cover - optional dependency during tests
    from comfyui_api import ConnectionRefusedError, get_available_comfyui_models
except Exception:  # pragma: no cover - provide a lightweight stub for test environments
    class ConnectionRefusedError(RuntimeError):
        """Fallback connection error when comfyui_api dependencies are unavailable."""

        pass

    def get_available_comfyui_models(*_args, **_kwargs):  # type: ignore[override]
        raise ConnectionRefusedError("ComfyUI API unavailable")

from services.workflow_library_service import WorkflowLibraryService
from utils.update_state import UpdateState

Severity = Literal["ok", "info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class DiagnosticItem:
    """Individual diagnostic message with severity metadata."""

    label: str
    message: str
    severity: Severity
    detail: Optional[str] = None


@dataclass(frozen=True, slots=True)
class DiagnosticsReport:
    """Aggregated diagnostic information for the configurator."""

    comfy_connected: bool
    model_inventory: Dict[str, Sequence[str]]
    qwen_ready: bool
    workflow_group_counts: Dict[str, int]
    style_count: int
    issues: Sequence[DiagnosticItem]


def collect_system_diagnostics(
    *,
    app_base_dir: str,
    settings: Optional[Dict[str, object]] = None,
    workflow_service: Optional[WorkflowLibraryService] = None,
    styles_config: Optional[Dict[str, dict]] = None,
) -> DiagnosticsReport:
    """Gather a best-effort health snapshot for GUI presentation."""

    issues: list[DiagnosticItem] = []

    model_inventory: Dict[str, Sequence[str]] = {
        "unet": (),
        "checkpoint": (),
        "clip": (),
        "vae": (),
        "upscaler": (),
    }

    comfy_connected = False
    try:
        model_inventory = {
            key: tuple(value)
            for key, value in get_available_comfyui_models(suppress_summary_print=True).items()
        }
        comfy_connected = True
    except ConnectionRefusedError as exc:
        issues.append(
            DiagnosticItem(
                label="ComfyUI API",
                message="ComfyUI instance refused the connection",
                severity="error",
                detail=str(exc),
            )
        )
    except Exception as exc:  # pragma: no cover - defensive guard for unexpected errors
        issues.append(
            DiagnosticItem(
                label="ComfyUI API",
                message="Unable to reach ComfyUI",
                severity="error",
                detail=str(exc),
            )
        )

    if settings is None:
        from settings_manager import _get_default_settings, load_settings

        try:
            settings = load_settings()
        except Exception:
            settings = _get_default_settings()

    selected_model_setting = str(settings.get("selected_model", "") or "").strip()
    qwen_selected = selected_model_setting.startswith("Qwen:")

    checkpoints = tuple(model_inventory.get("checkpoint", ()))
    has_qwen_checkpoint = any("qwen" in ckpt.lower() for ckpt in checkpoints)

    qwen_ready = has_qwen_checkpoint
    if qwen_selected and not has_qwen_checkpoint:
        issues.append(
            DiagnosticItem(
                label="Qwen Checkpoint",
                message="Selected Qwen model not found in ComfyUI",
                severity="warning",
                detail="Refresh the ComfyUI checkpoints list or install the model.",
            )
        )

    if workflow_service is None:
        workflow_service = WorkflowLibraryService()

    try:
        group_counts = {
            group.key: len(group.workflows) for group in workflow_service.list_groups()
        }
    except Exception as exc:  # pragma: no cover - service should not fail, but guard regardless
        group_counts = {}
        issues.append(
            DiagnosticItem(
                label="Workflow Library",
                message="Unable to load curated workflows",
                severity="error",
                detail=str(exc),
            )
        )

    total_workflows = sum(group_counts.values())
    if total_workflows == 0:
        issues.append(
            DiagnosticItem(
                label="Workflow Library",
                message="No curated workflows available",
                severity="warning",
            )
        )

    if styles_config is None:
        from settings_manager import load_styles_config

        try:
            styles_config = load_styles_config()
        except Exception:
            styles_config = {"off": {}}

    style_count = len(styles_config)
    if style_count <= 1:
        issues.append(
            DiagnosticItem(
                label="Style Presets",
                message="Only the default style preset is configured",
                severity="info",
                detail="Add style presets for richer LoRA staging across models.",
            )
        )

    update_state = UpdateState.load(base_dir=app_base_dir)
    if update_state.pending_tag and update_state.pending_tag != update_state.last_successful_tag:
        issues.append(
            DiagnosticItem(
                label="Updater",
                message=f"Update {update_state.pending_tag} awaiting restart",
                severity="warning",
            )
        )

    return DiagnosticsReport(
        comfy_connected=comfy_connected,
        model_inventory=model_inventory,
        qwen_ready=qwen_ready,
        workflow_group_counts=group_counts,
        style_count=style_count,
        issues=tuple(issues),
    )
