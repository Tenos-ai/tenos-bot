from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from workflows import WorkflowDescriptor, WorkflowGroup, load_workflow_catalogue


@dataclass(slots=True)
class ExportSummary:
    """Details about an export operation."""

    written_files: List[str]


class WorkflowLibraryService:
    """Expose curated ComfyUI graphs grouped by engine."""

    def __init__(self) -> None:
        self._groups: tuple[WorkflowGroup, ...] = tuple(load_workflow_catalogue())
        self._group_lookup = {group.key: group for group in self._groups}
        self._workflow_lookup = {
            descriptor.slug: descriptor
            for group in self._groups
            for descriptor in group.workflows
        }

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def list_groups(self) -> Sequence[WorkflowGroup]:
        return self._groups

    def list_workflows(self, group_key: str | None = None) -> Sequence[WorkflowDescriptor]:
        return self._resolve_descriptors(group_key)

    def search_workflows(
        self, query: str, *, group_key: str | None = None
    ) -> Sequence[WorkflowDescriptor]:
        """Return workflows whose metadata matches the query string."""

        descriptors = self._resolve_descriptors(group_key)
        normalized = query.strip().lower()
        if not normalized:
            return descriptors

        matches = []
        for descriptor in descriptors:
            haystacks = [descriptor.slug, descriptor.title]
            haystacks.extend(descriptor.use_cases)
            if any(normalized in (value or "").lower() for value in haystacks):
                matches.append(descriptor)
        return tuple(matches)

    def get_group(self, key: str) -> WorkflowGroup | None:
        return self._group_lookup.get(key)

    def get_workflow(self, slug: str) -> WorkflowDescriptor | None:
        return self._workflow_lookup.get(slug)

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------
    def export_all(self, target_directory: str, *, group_key: str | None = None) -> ExportSummary:
        os.makedirs(target_directory, exist_ok=True)
        descriptors = self._resolve_descriptors(group_key)
        written_files = [
            self._write_json(os.path.join(target_directory, f"{workflow.slug}.json"), workflow)
            for workflow in descriptors
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
    def _resolve_descriptors(self, group_key: str | None) -> Sequence[WorkflowDescriptor]:
        if group_key:
            group = self._group_lookup.get(group_key)
            return group.workflows if group else ()
        return tuple(descriptor for group in self._groups for descriptor in group.workflows)

    def _write_json(self, file_path: str, descriptor: WorkflowDescriptor) -> str:
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(descriptor.build_template(), fh, indent=2)
        return os.path.basename(file_path)


__all__ = ["WorkflowLibraryService", "ExportSummary"]
