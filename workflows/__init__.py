"""Workflow catalogues for Tenos.ai."""

from __future__ import annotations

__all__ = [
    "WorkflowDescriptor",
    "WorkflowGroup",
    "load_workflow_catalogue",
    "load_workflow_template",
    "WORKFLOW_OVERRIDE_SLOTS",
]

from .custom_loader import WORKFLOW_OVERRIDE_SLOTS, load_workflow_template
from .workflow_library import WorkflowDescriptor, WorkflowGroup, load_workflow_catalogue

