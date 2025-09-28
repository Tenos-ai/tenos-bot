"""Background update workflow for the Tenos.ai configurator."""
from __future__ import annotations

from dataclasses import dataclass
import os
import tempfile
from typing import Callable, Dict, Optional
import zipfile

import requests

from utils.update_state import UpdateState
from utils.versioning import is_remote_version_newer


class UpdateServiceError(RuntimeError):
    """Raised when the updater cannot complete successfully."""


@dataclass(slots=True)
class UpdateResult:
    """Result payload returned after an update attempt."""

    message: str
    requires_restart: bool = False
    update_info: Optional[Dict[str, str]] = None


class UpdateService:
    """Encapsulates the GitHub release download logic for updates."""

    def __init__(
        self,
        *,
        repo_owner: str,
        repo_name: str,
        current_version: str,
        app_base_dir: str,
        update_state: UpdateState,
        log_callback: Callable[[str, str], None],
        session_factory: Callable[[], requests.Session] | None = None,
    ) -> None:
        self._repo_owner = repo_owner
        self._repo_name = repo_name
        self._current_version = current_version
        self._app_base_dir = app_base_dir
        self._update_state = update_state
        self._log_callback = log_callback
        self._session_factory = session_factory or requests.Session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def download_latest_release(self) -> UpdateResult:
        """Fetch and unpack the newest GitHub release if one exists."""

        api_url = f"https://api.github.com/repos/{self._repo_owner}/{self._repo_name}/releases/latest"
        self._log_worker(f"Fetching latest release metadata from {api_url}…")

        session = self._session_factory()
        try:
            session.headers.update(
                {
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"TenosAI-Configurator/{self._current_version}",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
            )

            try:
                response = session.get(api_url, timeout=20)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise UpdateServiceError(f"Unable to contact GitHub Releases: {exc}") from exc

            release_data = response.json()

            tag_name = release_data.get("tag_name")
            zip_url = release_data.get("zipball_url")

            if not tag_name or not zip_url:
                raise UpdateServiceError("Latest release metadata is missing a tag name or download URL.")

            if self._update_state.pending_tag and self._update_state.pending_tag == tag_name:
                self._log_worker(f"Update for {tag_name} already pending. Skipping duplicate download.")
                return UpdateResult(message=f"Update {tag_name} is already queued.")

            if self._update_state.last_successful_tag and self._update_state.last_successful_tag == tag_name:
                self._log_worker(f"Release {tag_name} already applied previously. No action required.")
                return UpdateResult(message=f"Already running {tag_name}.")

            if not is_remote_version_newer(tag_name, self._current_version):
                self._log_worker(
                    f"Current version v{self._current_version} is already up to date compared to {tag_name}."
                )
                return UpdateResult(message="You are running the latest version.")

            download_dir = tempfile.mkdtemp(prefix="tenos_update_")
            archive_path = os.path.join(download_dir, "release.zip")

            self._log_worker(f"Downloading release {tag_name}…")
            try:
                with session.get(zip_url, stream=True, timeout=30) as download_stream:
                    download_stream.raise_for_status()
                    with open(archive_path, "wb") as archive_file:
                        for chunk in download_stream.iter_content(chunk_size=8192):
                            if chunk:
                                archive_file.write(chunk)
            except requests.RequestException as exc:
                raise UpdateServiceError(f"Failed to download release archive: {exc}") from exc

            self._log_worker("Download complete. Extracting archive…")
            try:
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(download_dir)
            except zipfile.BadZipFile as exc:
                raise UpdateServiceError("Downloaded update archive is corrupted.") from exc

            self._update_state.mark_pending(tag_name, base_dir=self._app_base_dir)
            self._log_info("Handing off to updater. The configurator will restart to apply changes.")

            update_info = {
                "temp_dir": download_dir,
                "dest_dir": self._app_base_dir,
                "target_tag": tag_name,
            }

            return UpdateResult(
                message=f"Update {tag_name} downloaded. The application will restart to apply it.",
                requires_restart=True,
                update_info=update_info,
            )
        finally:
            try:
                session.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _log_worker(self, message: str) -> None:
        self._log_callback("worker", f"{message}\n")

    def _log_info(self, message: str) -> None:
        self._log_callback("info", f"{message}\n")

