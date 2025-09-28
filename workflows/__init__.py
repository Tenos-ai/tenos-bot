"""Workflow catalogues for Tenos.ai."""

from __future__ import annotations

__all__ = [
    "WorkflowDescriptor",
    "load_qwen_image_workflows",
    "load_workflow_template",
    "WORKFLOW_OVERRIDE_SLOTS",
]

from .custom_loader import WORKFLOW_OVERRIDE_SLOTS, load_workflow_template
from .qwen_image_library import WorkflowDescriptor, load_qwen_image_workflows

