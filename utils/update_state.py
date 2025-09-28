"""Utilities for tracking update status to avoid repeated downloads."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

_UPDATE_STATE_FILE = "update_state.json"


@dataclass
class UpdateState:
    """Structured representation of updater bookkeeping information."""

    last_successful_tag: Optional[str] = None
    pending_tag: Optional[str] = None

    @classmethod
    def load(cls, base_dir: Optional[str] = None) -> "UpdateState":
        path = _resolve_path(base_dir)
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(payload, dict):
            return cls()
        return cls(
            last_successful_tag=_coerce_optional_str(payload.get("last_successful_tag")),
            pending_tag=_coerce_optional_str(payload.get("pending_tag")),
        )

    def save(self, base_dir: Optional[str] = None) -> None:
        path = _resolve_path(base_dir)
        data: Dict[str, Any] = asdict(self)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except OSError:
            # Saving update state should not be fatal to the app; swallow errors.
            pass

    def mark_pending(self, tag: str, base_dir: Optional[str] = None) -> None:
        self.pending_tag = tag
        self.save(base_dir)

    def mark_success(self, tag: str, base_dir: Optional[str] = None) -> None:
        self.last_successful_tag = tag
        self.pending_tag = None
        self.save(base_dir)


def _coerce_optional_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _resolve_path(base_dir: Optional[str]) -> str:
    directory = base_dir if base_dir else os.getcwd()
    return os.path.join(directory, _UPDATE_STATE_FILE)
