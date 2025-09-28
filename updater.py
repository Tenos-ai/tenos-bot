# --- START OF FILE updater.py ---
import os
import time
import shutil
import subprocess
import traceback
import sys

try:  # pragma: no cover - optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover - psutil is optional for the updater
    psutil = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from utils.update_state import UpdateState
except Exception:  # pragma: no cover - updater should still run without state tracking
    UpdateState = None

def log(message):
    """Logs a message to a dedicated update log file."""
    try:
        with open("update_log.txt", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception:
        # If logging fails, print to stderr as a fallback
        print(message, file=sys.stderr)


def _clear_pending(dest_dir: str) -> None:
    if UpdateState is None:
        return
    try:
        state = UpdateState.load(base_dir=dest_dir)
        state.pending_tag = None
        state.save(base_dir=dest_dir)
    except Exception as exc:  # pragma: no cover - best effort cleanup
        log(f"Warning: Unable to clear pending update flag: {exc}")


def _process_exists(pid: int) -> bool:
    """Best-effort check to determine if a process is still alive."""

    if pid <= 0:
        return False

    if psutil is not None:
        try:
            psutil.Process(pid)
            return True
        except psutil.NoSuchProcess:  # type: ignore[attr-defined]
            return False
        except Exception:
            pass

    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    try:  # pragma: no cover - Windows-specific branch
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def _wait_for_parent_termination(parent_pid: int, timeout: float = 30.0) -> None:
    """Wait until the parent process exits before applying the update."""

    if parent_pid <= 0:
        return

    deadline = time.time() + timeout

    if psutil is not None:
        try:
            parent_process = psutil.Process(parent_pid)
            parent_process.wait(timeout=timeout)
            log("Parent process has terminated.")
            return
        except psutil.NoSuchProcess:  # type: ignore[attr-defined]
            log("Parent process already terminated.")
            return
        except Exception as exc:
            log(f"Warning: psutil wait failed ({exc}); falling back to polling.")

    while time.time() < deadline:
        if not _process_exists(parent_pid):
            log("Parent process has terminated (polled).")
            return
        time.sleep(1)

    log("Warning: Timeout waiting for parent process. Continuing update.")


def main():
    log("Updater script started.")
    if len(sys.argv) not in (4, 5):
        log(f"FATAL: Incorrect number of arguments. Expected 3 or 4, got {len(sys.argv) - 1}")
        log(f"Arguments: {sys.argv}")
        return

    parent_pid = int(sys.argv[1])
    source_dir = sys.argv[2]
    dest_dir = sys.argv[3]
    target_tag = sys.argv[4] if len(sys.argv) == 5 else None
    handoff_started = False

    log(f"Parent PID: {parent_pid}")
    log(f"Source (temp) dir: {source_dir}")
    log(f"Destination (app) dir: {dest_dir}")

    # 1. Wait for the main application to close
    log(f"Waiting for parent process {parent_pid} to terminate…")
    _wait_for_parent_termination(parent_pid)

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

    # 3. Copy new files, overwriting old ones
    try:
        # The zip from GitHub extracts into a subfolder. We need to find that subfolder.
        extracted_subfolders = [f for f in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, f))]
        if len(extracted_subfolders) != 1:
            log(f"FATAL: Expected one subfolder in extracted zip, but found {len(extracted_subfolders)}. Contents: {os.listdir(source_dir)}")
            _clear_pending(dest_dir)
            return
        
        actual_source_path = os.path.join(source_dir, extracted_subfolders[0])
        log(f"Actual source content is in: {actual_source_path}")

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

    except Exception as e:
        log(f"FATAL: An error occurred during the file copy process: {e}")
        with open("update_log.txt", "a") as fh:
            traceback.print_exc(file=fh)
        _clear_pending(dest_dir)
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
        handoff_started = True

        log("Relaunch command issued.")
    except Exception as e:
        log(f"FATAL: Failed to relaunch the application: {e}")
        with open("update_log.txt", "a") as fh:
            traceback.print_exc(file=fh)
        _clear_pending(dest_dir)

    if UpdateState is not None and handoff_started:
        try:
            state = UpdateState.load(base_dir=dest_dir)
            if target_tag:
                state.mark_success(target_tag, base_dir=dest_dir)
            else:
                state.pending_tag = None
                state.save(base_dir=dest_dir)
            log(f"Update state recorded for tag {target_tag}")
        except Exception as state_err:
            log(f"Warning: Unable to record update state: {state_err}")

if __name__ == "__main__":
    main()
# --- END OF FILE updater.py ---