"""Utilities for working with curated Qwen Image workflows."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from workflows.qwen_image_library import WorkflowDescriptor, load_qwen_image_workflows


@dataclass(slots=True)
class ExportSummary:
    """Details about an export operation."""

    written_files: List[str]


class QwenWorkflowService:
    """Expose curated ComfyUI graphs tailored for Qwen Image."""

    def __init__(self) -> None:
        self._workflows: tuple[WorkflowDescriptor, ...] = tuple(load_qwen_image_workflows())
        self._workflow_lookup = {workflow.slug: workflow for workflow in self._workflows}

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def list_workflows(self) -> Sequence[WorkflowDescriptor]:
        return self._workflows

    def search_workflows(self, query: str) -> Sequence[WorkflowDescriptor]:
        """Return workflows whose metadata matches the query string."""

        normalized = query.strip().lower()
        if not normalized:
            return self._workflows

        matches = []
        for descriptor in self._workflows:
            haystacks = [descriptor.slug, descriptor.title]
            haystacks.extend(descriptor.use_cases)
            if any(normalized in (value or "").lower() for value in haystacks):
                matches.append(descriptor)
        return tuple(matches)

    def get_workflow(self, slug: str) -> WorkflowDescriptor | None:
        return self._workflow_lookup.get(slug)

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------
    def export_all(self, target_directory: str) -> ExportSummary:
        os.makedirs(target_directory, exist_ok=True)
        written_files = [
            self._write_json(os.path.join(target_directory, f"{workflow.slug}.json"), workflow)
            for workflow in self._workflows
        ]
        return ExportSummary(written_files=written_files)

    def export_selected(self, target_directory: str, slugs: Iterable[str]) -> ExportSummary:
        os.makedirs(target_directory, exist_ok=True)
        written_files = []
        for slug in slugs:
            descriptor = self.get_workflow(slug)
            if descriptor is None:
                continue
            file_path = os.path.join(target_directory, f"{descriptor.slug}.json")
            written_files.append(self._write_json(file_path, descriptor))
        return ExportSummary(written_files=written_files)

    def export_to_file(self, destination_path: str, slug: str) -> str:
        descriptor = self.get_workflow(slug)
        if descriptor is None:
            raise KeyError(f"Unknown workflow slug: {slug}")
        os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
        return self._write_json(destination_path, descriptor)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _write_json(self, file_path: str, descriptor: WorkflowDescriptor) -> str:
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(descriptor.build_template(), fh, indent=2)
        return os.path.basename(file_path)

