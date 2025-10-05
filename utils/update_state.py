"""Utilities for tracking application update state.

This module provides a lightweight persistence layer for storing
whether an application update is pending and which version was last
successfully applied.  The :class:`UpdateState` helper is intentionally
minimal so that callers can safely use it from UI code without worrying
about complicated error handling.  All file operations fail silently so
that a corrupt or missing state file never prevents the main
application from launching.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional


_STATE_FILE_NAME = "update_state.json"


def _resolve_state_path(base_dir: Optional[str]) -> str:
    """Return the fully qualified path to the update state file."""
    directory = base_dir or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(directory, _STATE_FILE_NAME)


@dataclass
class UpdateState:
    """Simple container persisted to :data:`_STATE_FILE_NAME`.

    Attributes
    ----------
    pending_tag:
        Version tag that has been downloaded but not yet applied.
    last_successful_tag:
        Version tag that was last installed successfully.
    """

    pending_tag: Optional[str] = field(default=None)
    last_successful_tag: Optional[str] = field(default=None)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, base_dir: Optional[str] = None) -> "UpdateState":
        """Load the update state from disk.

        Any problem reading or parsing the file results in an empty
        :class:`UpdateState` instance so that callers never see an
        exception during application start-up.
        """
        state_path = _resolve_state_path(base_dir)
        try:
            with open(state_path, "r", encoding="utf-8") as file_obj:
                payload = json.load(file_obj)
        except FileNotFoundError:
            return cls()
        except (OSError, json.JSONDecodeError):
            return cls()

        pending_tag = payload.get("pending_tag")
        last_successful_tag = payload.get("last_successful_tag")
        return cls(pending_tag=pending_tag, last_successful_tag=last_successful_tag)

    # ------------------------------------------------------------------
    def save(self, base_dir: Optional[str] = None) -> None:
        """Persist the update state to disk.

        The directory is created automatically when necessary.
        """
        state_path = _resolve_state_path(base_dir)
        try:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, "w", encoding="utf-8") as file_obj:
                json.dump(
                    {
                        "pending_tag": self.pending_tag,
                        "last_successful_tag": self.last_successful_tag,
                    },
                    file_obj,
                    indent=2,
                )
        except OSError:
            # Saving the update state should never be fatal for the
            # application.  Ignore filesystem errors silently.
            pass

    # ------------------------------------------------------------------
    def mark_pending(self, tag_name: Optional[str], base_dir: Optional[str] = None) -> None:
        """Record a version tag as pending and persist the change."""
        self.pending_tag = tag_name
        self.save(base_dir=base_dir)

    # ------------------------------------------------------------------
    def mark_success(self, tag_name: Optional[str], base_dir: Optional[str] = None) -> None:
        """Record a successful update and persist the change."""
        self.last_successful_tag = tag_name
        self.pending_tag = None
        self.save(base_dir=base_dir)

# End of file
