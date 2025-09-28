"""Coordinator responsible for keeping update state consistent."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from services.update_service import UpdateResult, UpdateService
from utils.update_state import UpdateState
from utils.versioning import normalise_tag


LogCallback = Callable[[str, str], None]


@dataclass(slots=True)
class UpdateCoordinator:
    """Encapsulates update state reconciliation and service access."""

    repo_owner: str
    repo_name: str
    current_version: str
    app_base_dir: str
    log_callback: LogCallback
    _state: UpdateState = field(init=False, repr=False)
    _service: UpdateService = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._state = UpdateState.load(base_dir=self.app_base_dir)
        self._service = UpdateService(
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            current_version=self.current_version,
            app_base_dir=self.app_base_dir,
            update_state=self._state,
            log_callback=self.log_callback,
        )
        self._reconcile_state()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def state(self) -> UpdateState:
        return self._state

    def download_latest_release(self) -> UpdateResult:
        return self._service.download_latest_release()

    def should_run_auto_update(self, auto_update_enabled: bool) -> bool:
        """Return True if auto-update should run at startup."""

        if not auto_update_enabled:
            return False
        if self._state.pending_tag:
            self.log_callback(
                "info",
                f"--- Update {self._state.pending_tag} already queued, skipping auto-check. ---\n",
            )
            return False
        return True

    def clear_pending_update(self) -> None:
        """Drop any pending tag so update loops can recover gracefully."""

        if not self._state.pending_tag:
            return

        pending = self._state.pending_tag
        self._state.pending_tag = None
        self._state.save(base_dir=self.app_base_dir)
        self.log_callback("worker", f"Cleared pending update flag for {pending}.\n")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _reconcile_state(self) -> None:
        """Normalise pending state so the updater never loops indefinitely."""

        pending_tag = self._state.pending_tag
        last_success = self._state.last_successful_tag

        normalised_current = normalise_tag(self.current_version)
        normalised_pending = normalise_tag(pending_tag)
        normalised_success = normalise_tag(last_success)

        if pending_tag and normalised_pending == normalised_current:
            # We already booted into the version that was pending – clear it.
            self.log_callback(
                "worker",
                f"Pending update {pending_tag} matches running version; marking as applied.\n",
            )
            self._state.mark_success(pending_tag, base_dir=self.app_base_dir)
            return

        if normalised_success is None and normalised_current is not None:
            # First run from a fresh install – establish a baseline so we
            # never loop on the first update check.
            self.log_callback(
                "worker",
                f"Recording current version {self.current_version} as baseline update state.\n",
            )
            self._state.mark_success(self.current_version, base_dir=self.app_base_dir)

