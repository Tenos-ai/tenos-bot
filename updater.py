# --- START OF FILE updater.py ---
import sys
import os
import time
import shutil
import subprocess
import psutil
import traceback

def log(message):
    """Logs a message to a dedicated update log file."""
    try:
        with open("update_log.txt", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception:
        # If logging fails, print to stderr as a fallback
        print(message, file=sys.stderr)

def main():
    log("Updater script started.")
    if len(sys.argv) != 4:
        log(f"FATAL: Incorrect number of arguments. Expected 3, got {len(sys.argv) - 1}")
        log(f"Arguments: {sys.argv}")
        return

    parent_pid = int(sys.argv[1])
    source_dir = sys.argv[2]
    dest_dir = sys.argv[3]

    log(f"Parent PID: {parent_pid}")
    log(f"Source (temp) dir: {source_dir}")
    log(f"Destination (app) dir: {dest_dir}")

    # 1. Wait for the main application to close
    try:
        log(f"Waiting for parent process {parent_pid} to terminate...")
        parent_process = psutil.Process(parent_pid)
        parent_process.wait(timeout=30)
        log("Parent process has terminated.")
    except psutil.NoSuchProcess:
        log("Parent process already terminated.")
    except (psutil.TimeoutExpired, Exception) as e:
        log(f"Warning: Error or timeout while waiting for parent process: {e}. Continuing update anyway.")

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
        traceback.print_exc(file=open("update_log.txt", "a"))
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
        traceback.print_exc(file=open("update_log.txt", "a"))

if __name__ == "__main__":
    main()
# --- END OF FILE updater.py ---