# --- START OF FILE updater.py ---
import sys
import os
import time
import shutil
import subprocess
import errno
import traceback
import re
from typing import Optional

try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
    _PSUTIL_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False
    _PSUTIL_IMPORT_ERROR = exc

def log(message):
    """Logs a message to a dedicated update log file."""
    try:
        with open("update_log.txt", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception:
        # If logging fails, print to stderr as a fallback
        print(message, file=sys.stderr)

def _is_process_running(pid):
    """Return ``True`` if a process with ``pid`` appears to be running."""
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists but we may not have permission to signal it.
        return True
    except OSError as exc:  # pragma: no cover - platform specific errnos
        if getattr(exc, "errno", None) in {errno.ESRCH}:
            return False
        return True
    else:
        return True


def _wait_for_parent_termination(parent_pid, timeout):
    """Wait for the parent process to terminate using available tooling."""
    if _PSUTIL_AVAILABLE:
        try:
            parent_process = psutil.Process(parent_pid)  # type: ignore[arg-type]
            parent_process.wait(timeout=timeout)
            log("Parent process has terminated.")
            return True
        except psutil.NoSuchProcess:  # type: ignore[attr-defined]
            log("Parent process already terminated.")
            return True
        except psutil.TimeoutExpired as exc:  # type: ignore[attr-defined]
            log(
                "Warning: Timeout while waiting for parent process: "
                f"{exc}. Continuing update anyway."
            )
            return False
        except Exception as exc:  # pragma: no cover - defensive
            log(
                "Warning: Error while waiting for parent process: "
                f"{exc}. Continuing update anyway."
            )
            return False

    # Fallback when psutil is unavailable.
    if _PSUTIL_IMPORT_ERROR is not None:
        log(
            f"psutil not available ({_PSUTIL_IMPORT_ERROR}). Using fallback wait strategy."
        )

    end_time = time.time() + timeout
    while time.time() < end_time:
        if not _is_process_running(parent_pid):
            log("Parent process appears to have terminated (fallback).")
            return True
        time.sleep(0.5)

    if not _is_process_running(parent_pid):
        log("Parent process terminated after fallback wait.")
        return True

    log(
        "Warning: Fallback wait timed out while waiting for parent process. "
        "Continuing update anyway."
    )
    return False


_VERSION_PATTERN = re.compile(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]")


def _safe_read_version(version_file):
    """Attempt to read the application version from ``version_file``."""
    try:
        with open(version_file, "r", encoding="utf-8") as fh:
            contents = fh.read()
    except FileNotFoundError:
        return None
    except Exception as exc:  # pragma: no cover - defensive
        log(f"Warning: Failed to read version info from {version_file}: {exc}")
        return None

    match = _VERSION_PATTERN.search(contents)
    if match:
        return match.group(1).strip()
    return None


def _normalise_version_string(raw_version: Optional[str]) -> Optional[str]:
    if not raw_version:
        return None

    cleaned = raw_version.strip()
    if not cleaned:
        return None

    if cleaned.lower().startswith("v") and len(cleaned) > 1 and cleaned[1].isdigit():
        cleaned = cleaned[1:]
    return cleaned or None


def _bump_patch_version(current_version: Optional[str]) -> Optional[str]:
    if not current_version:
        return None

    base, dash, suffix = current_version.partition("-")
    parts = base.split(".")
    if not parts:
        return current_version

    numeric_parts = []
    for part in parts:
        if not part.isdigit():
            return current_version
        numeric_parts.append(int(part))

    numeric_parts[-1] += 1
    bumped = ".".join(str(part) for part in numeric_parts)
    if dash:
        bumped = f"{bumped}-{suffix}"
    return bumped


def _determine_target_version(
    target_tag: Optional[str],
    extracted_source_dir: str,
    dest_dir: str,
) -> Optional[str]:
    """Determine the version the application should report after the update."""

    from_tag = _normalise_version_string(target_tag)
    if from_tag:
        log(f"Using target tag to set version: {from_tag}")
        return from_tag

    extracted_version = _safe_read_version(os.path.join(extracted_source_dir, "version_info.py"))
    if extracted_version:
        log(f"Detected version from extracted files: {extracted_version}")
        return extracted_version

    current_version = _safe_read_version(os.path.join(dest_dir, "version_info.py"))
    if current_version:
        bumped = _bump_patch_version(current_version)
        if bumped and bumped != current_version:
            log(
                "No explicit version provided. Automatically incrementing patch "
                f"version from {current_version} to {bumped}."
            )
            return bumped
        log("No explicit version provided and unable to increment current version.")

    log("Unable to determine target version for this update.")
    return None


def _update_version_file(dest_dir: str, new_version: str) -> None:
    version_file = os.path.join(dest_dir, "version_info.py")
    current_version = _safe_read_version(version_file)
    if current_version == new_version:
        log(f"Version info already up to date ({new_version}).")
        return

    try:
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        else:
            lines = ["\"\"\"Centralised application version metadata.\"\"\"\n", "\n"]

        replaced = False
        for idx, line in enumerate(lines):
            if _VERSION_PATTERN.search(line):
                lines[idx] = f'APP_VERSION = "{new_version}"\n'
                replaced = True
                break

        if not replaced:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] = lines[-1] + "\n"
            lines.append(f'APP_VERSION = "{new_version}"\n')

        with open(version_file, "w", encoding="utf-8") as fh:
            fh.writelines(lines)

        log(f"Updated version info file to {new_version}.")
    except Exception as exc:  # pragma: no cover - defensive
        log(f"Warning: Failed to update version info file: {exc}")


def main():
    log("Updater script started.")
    if not _PSUTIL_AVAILABLE and _PSUTIL_IMPORT_ERROR is not None:
        log(
            "psutil module not found. Some functionality will fall back to "
            "a basic implementation."
        )
        log(f"psutil import error: {_PSUTIL_IMPORT_ERROR}")
    if len(sys.argv) not in {4, 5}:
        log(
            f"FATAL: Incorrect number of arguments. Expected 3 or 4, got {len(sys.argv) - 1}"
        )
        log(f"Arguments: {sys.argv}")
        return

    parent_pid = int(sys.argv[1])
    source_dir = sys.argv[2]
    dest_dir = sys.argv[3]
    target_tag = sys.argv[4] if len(sys.argv) == 5 else None

    log(f"Parent PID: {parent_pid}")
    log(f"Source (temp) dir: {source_dir}")
    log(f"Destination (app) dir: {dest_dir}")
    if target_tag:
        log(f"Target release tag: {target_tag}")

    # 1. Wait for the main application to close
    log(f"Waiting for parent process {parent_pid} to terminate...")
    _wait_for_parent_termination(parent_pid, timeout=30)

    # A brief additional delay to ensure file handles are released
    time.sleep(2)

    # 2. Define files and folders to preserve
    preserve_list = [
        'config.json',
        'settings.json',
        'styles_config.json',
        'llm_prompts.json',
        'llm_models.json',
        'cliplist.json',
        'modelslist.json',
        'checkpointslist.json',
        'blocklist.json',
        'user_cache.json',
        'lastprompt.json',
        'first_run_complete.flag',
        'update_log.txt',
        'logs',      # Preserve the entire logs directory
        'output',    # Preserve the entire output directory
        '.git'       # Preserve git info if it exists
    ]
    log(f"Preserving the following items: {preserve_list}")

    # Ensure directories look sane before proceeding.
    if not os.path.isdir(source_dir):
        log(f"FATAL: Source directory does not exist or is not a directory: {source_dir}")
        return
    if not os.path.isdir(dest_dir):
        log(f"FATAL: Destination directory does not exist or is not a directory: {dest_dir}")
        return
    if os.path.abspath(source_dir) == os.path.abspath(dest_dir):
        log("FATAL: Source and destination directories are identical. Aborting update.")
        return

    # 3. Copy new files, overwriting old ones
    try:
        # The zip from GitHub usually extracts into a subfolder. We need to find that subfolder.
        extracted_subfolders = [
            entry
            for entry in os.listdir(source_dir)
            if os.path.isdir(os.path.join(source_dir, entry))
        ]

        preferred_subfolders = [
            entry
            for entry in extracted_subfolders
            if not entry.startswith("__MACOSX") and not entry.startswith(".")
        ]

        candidate_list = preferred_subfolders or extracted_subfolders

        if len(candidate_list) == 1:
            actual_source_path = os.path.join(source_dir, candidate_list[0])
            log(f"Actual source content is in: {actual_source_path}")
        elif len(candidate_list) > 1:
            candidate_list.sort()
            actual_source_path = os.path.join(source_dir, candidate_list[0])
            log(
                "Multiple subfolders detected in extracted archive. Selecting the first "
                f"candidate ({actual_source_path})."
            )
        else:
            # Some archives may unpack directly into the root; fall back to source_dir
            actual_source_path = source_dir
            log(
                "Extracted archive did not contain a subfolder. "
                "Falling back to using the root of the extracted archive."
            )

        target_version = _determine_target_version(target_tag, actual_source_path, dest_dir)

        for item_name in os.listdir(actual_source_path):
            if item_name in preserve_list:
                log(f"Skipping preserved item: {item_name}")
                continue

            source_item_path = os.path.join(actual_source_path, item_name)
            dest_item_path = os.path.join(dest_dir, item_name)

            try:
                if os.path.isdir(source_item_path):
                    log(f"Copying directory: {source_item_path} -> {dest_item_path}")
                    if os.path.exists(dest_item_path):
                        shutil.rmtree(dest_item_path)
                    shutil.copytree(source_item_path, dest_item_path)
                else: # It's a file
                    log(f"Copying file: {source_item_path} -> {dest_item_path}")
                    shutil.copy2(source_item_path, dest_item_path)
            except Exception as e_copy_item:
                 log(f"ERROR copying {item_name}: {e_copy_item}")

        log("File copy process completed.")

        if target_version:
            _update_version_file(dest_dir, target_version)
        else:
            log("Warning: No version information could be determined for this update.")

    except Exception as e:
        log(f"FATAL: An error occurred during the file copy process: {e}")
        with open("update_log.txt", "a") as log_file:
            traceback.print_exc(file=log_file)
        # Do not relaunch if the copy failed catastrophically
        return

    # 4. Clean up the temporary update directory
    try:
        log(f"Cleaning up temporary directory: {source_dir}")
        shutil.rmtree(source_dir)
        log("Cleanup complete.")
    except Exception as e:
        log(f"Warning: Failed to clean up temporary directory {source_dir}: {e}")

    # 5. Relaunch the main application
    try:
        main_script_path = os.path.join(dest_dir, 'config_editor_main.py')
        log(f"Relaunching application: {sys.executable} {main_script_path}")
        
        # Use Popen to detach the new process from the updater
        subprocess.Popen([sys.executable, main_script_path], cwd=dest_dir)
        
        log("Relaunch command issued.")
    except Exception as e:
        log(f"FATAL: Failed to relaunch the application: {e}")
        with open("update_log.txt", "a") as log_file:
            traceback.print_exc(file=log_file)

if __name__ == "__main__":
    main()
# --- END OF FILE updater.py ---