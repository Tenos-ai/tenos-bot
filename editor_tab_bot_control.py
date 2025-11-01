import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import sys
import psutil
import subprocess
import platform
import threading
import traceback

from editor_utils import silent_showinfo, silent_showerror, silent_showwarning
from editor_constants import (
    BOT_SCRIPT_NAME, FRAME_BG_COLOR, TEXT_COLOR_NORMAL, ENTRY_BG_COLOR,
    ENTRY_INSERT_COLOR, SELECT_BG_COLOR, SELECT_FG_COLOR,
    LOG_STDOUT_FG, LOG_STDERR_FG, LOG_INFO_FG, LOG_WORKER_FG,
    TENOS_LIGHT_BLUE_ACCENT2, TENOS_DARK_BLUE_BG
)


class BotControlTab:
    def __init__(self, editor_app_ref, parent_notebook):
        self.editor_app = editor_app_ref
        self.notebook = parent_notebook

        self.bot_control_tab_frame = ttk.Frame(self.notebook, padding="10", style="Tenos.TFrame")
        self.notebook.add(self.bot_control_tab_frame, text=' Bot Control ')

        self.bot_process = None

        self._create_bot_control_widgets()
        self.update_script_status_display()

    def _create_bot_control_widgets(self):
        """Creates the UI elements for the Bot Control tab."""
        top_controls_frame = ttk.Frame(self.bot_control_tab_frame, style="Tenos.TFrame")
        top_controls_frame.pack(fill=tk.X, pady=5)

        self.status_label_widget = ttk.Label(top_controls_frame, text="Bot Status: Unknown", font=('Arial', 11, 'bold'), style="Tenos.TLabel")
        self.status_label_widget.pack(side=tk.LEFT, padx=(0, 20))

        self.start_stop_button_widget = ttk.Button(top_controls_frame, text="Start Bot", command=self.toggle_bot_script_execution)
        self.start_stop_button_widget.pack(side=tk.LEFT, padx=5)

        ttk.Button(top_controls_frame, text="Clear Log Display", command=self.clear_bot_log_display).pack(side=tk.LEFT, padx=5)

        log_display_frame = ttk.LabelFrame(self.bot_control_tab_frame, text="Bot Log Output", style="Tenos.TLabelframe")
        log_display_frame.pack(fill="both", expand=True, pady=(10, 0))
        if not hasattr(self.editor_app, 'log_display') or not self.editor_app.log_display:
             # Fallback: create a local one if main app didn't (should not happen with current structure)
            print("Warning: editor_app.log_display not found, creating local for BotControlTab.")
            self.editor_app.log_display = scrolledtext.ScrolledText(log_display_frame, state='disabled', wrap=tk.WORD,
                                                     height=15, width=80, font=("Consolas", 9),
                                                     bg=ENTRY_BG_COLOR, fg=TEXT_COLOR_NORMAL, insertbackground=ENTRY_INSERT_COLOR,
                                                     selectbackground=SELECT_BG_COLOR, selectforeground=SELECT_FG_COLOR,
                                                     borderwidth=1, relief="sunken")
            self.editor_app.log_display.pack(fill="both", expand=True, padx=5, pady=5)
            self.editor_app.log_display.tag_configure("stdout", foreground=LOG_STDOUT_FG)
            self.editor_app.log_display.tag_configure("stderr", foreground=LOG_STDERR_FG)
            self.editor_app.log_display.tag_configure("info", foreground=LOG_INFO_FG, font=("Consolas", 9, "italic"))
            self.editor_app.log_display.tag_configure("worker", foreground=LOG_WORKER_FG, font=("Consolas", 9, "bold"))
        else:
             self.editor_app.log_display.pack(in_=log_display_frame, fill="both", expand=True, padx=5, pady=5)


    def is_bot_script_running(self):
        """Checks if the bot script process is currently running."""
        return self.editor_app.bot_process is not None and self.editor_app.bot_process.poll() is None

    def toggle_bot_script_execution(self):
        """Starts or stops the bot script based on its current state."""
        if self.is_bot_script_running():
            self.stop_bot_script()
        else:
            self.start_bot_script()
        if self.editor_app.master.winfo_exists():
            self.editor_app.master.after(500, self.update_script_status_display)

    def stop_bot_script(self):
        """Stops the running bot script."""
        if not self.is_bot_script_running():
            self.editor_app.log_queue.put(("info", "--- Bot script is already stopped ---\n"))
            self.update_script_status_display()
            return

        self.editor_app.log_queue.put(("info", "--- Stopping Bot script ---\n"))
        self.editor_app.stop_readers.set()

        try:
            parent_process = psutil.Process(self.editor_app.bot_process.pid)
            child_processes = parent_process.children(recursive=True)
            for child in child_processes:
                try: child.terminate()
                except psutil.NoSuchProcess: pass

            
            gone, alive = psutil.wait_procs(child_processes, timeout=3)
            for p_alive in alive:
                try: p_alive.kill()
                except psutil.NoSuchProcess: pass

            
            try:
                parent_process.terminate()
                parent_process.wait(timeout=3)
                self.editor_app.log_queue.put(("info", f"Bot script process {parent_process.pid} terminated.\n"))
            except psutil.TimeoutExpired:
                self.editor_app.log_queue.put(("info", f"Bot script process {parent_process.pid} did not terminate gracefully, attempting to kill.\n"))
                try:
                    parent_process.kill()
                    parent_process.wait(timeout=3)
                    self.editor_app.log_queue.put(("info", f"Bot script process {parent_process.pid} killed.\n"))
                except Exception as e_kill:
                    self.editor_app.log_queue.put(("stderr", f"Error killing bot script process {parent_process.pid}: {e_kill}\n"))
            except psutil.NoSuchProcess:
                self.editor_app.log_queue.put(("info", f"Bot script process {parent_process.pid} already exited.\n"))

        except psutil.NoSuchProcess:
            self.editor_app.log_queue.put(("info", "Bot script process already exited or not found by psutil.\n"))
        except Exception as e_psutil:
            self.editor_app.log_queue.put(("stderr", f"Error managing bot script process with psutil: {e_psutil}\n"))
            traceback.print_exc()
            
            if self.editor_app.bot_process and self.editor_app.bot_process.poll() is None:
                try:
                    self.editor_app.bot_process.terminate()
                    self.editor_app.bot_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.editor_app.bot_process.kill()
                    self.editor_app.bot_process.wait(timeout=2)
                except Exception as e_popen_term:
                     self.editor_app.log_queue.put(("stderr", f"Error fallback terminating Popen: {e_popen_term}\n"))
        finally:
            
            for thread_item in self.editor_app.reader_threads:
                if thread_item.is_alive():
                    thread_item.join(timeout=1.0)
            self.editor_app.reader_threads = []
            self.editor_app.bot_process = None
            self.editor_app.stop_readers.clear()
            self.update_script_status_display()


    def start_bot_script(self):
        """Starts the bot script as a subprocess."""
        if self.is_bot_script_running():
            silent_showwarning("Already Running", "The bot script appears to be already running.", parent=self.editor_app.master)
            return
        editor_dir = os.path.dirname(os.path.abspath(__file__))
        script_full_path = os.path.join(editor_dir, BOT_SCRIPT_NAME)

        if not os.path.exists(script_full_path):
            silent_showerror("Script Not Found", f"Bot script '{BOT_SCRIPT_NAME}' not found at expected location:\n{script_full_path}", parent=self.editor_app.master)
            return

        python_exe_path = sys.executable
        if not python_exe_path:
            silent_showerror("Python Error", "Could not determine the Python executable path.", parent=self.editor_app.master)
            return

        try:
            command_list = [python_exe_path, "-u", script_full_path]
            self.editor_app.log_queue.put(("info", f"--- Starting Bot script: {' '.join(command_list)} ---\n"))

            process_environment = os.environ.copy()
            process_environment["PYTHONIOENCODING"] = "utf-8"
            if platform.system() == "Windows":
                process_environment["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"

            
            creation_flags_val = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

            self.editor_app.bot_process = subprocess.Popen(
                command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=process_environment,
                creationflags=creation_flags_val,
                # cwd=editor_dir # Optionally set current working directory if script expects it
            )

            self.editor_app.stop_readers.clear()
            self.editor_app.reader_threads = []

            stdout_reader_thread = threading.Thread(target=self._read_pipe_to_queue, args=(self.editor_app.bot_process.stdout, "stdout"), daemon=True)
            stderr_reader_thread = threading.Thread(target=self._read_pipe_to_queue, args=(self.editor_app.bot_process.stderr, "stderr"), daemon=True)
            self.editor_app.reader_threads.extend([stdout_reader_thread, stderr_reader_thread])
            stdout_reader_thread.start()
            stderr_reader_thread.start()

        except FileNotFoundError:
            silent_showerror("Execution Error", f"Could not execute bot script. Ensure Python is installed and '{BOT_SCRIPT_NAME}' is present.", parent=self.editor_app.master)
            self.editor_app.bot_process = None
        except Exception as e:
            silent_showerror("Start Error", f"Failed to start bot script:\n{e}", parent=self.editor_app.master)
            traceback.print_exc()
            self.editor_app.bot_process = None
        finally:
            self.update_script_status_display()

    def _read_pipe_to_queue(self, pipe, pipe_name_tag):
        """Reads lines from a subprocess pipe and puts them into the log_queue."""
        try:
            for line_data in iter(pipe.readline, ''):
                if self.editor_app.stop_readers.is_set():
                    break
                self.editor_app.log_queue.put((pipe_name_tag, line_data))
        except ValueError as e_val_err:
            if 'I/O operation on closed file' not in str(e_val_err).lower():
                print(f"EditorBotControl: ValueError reading pipe {pipe_name_tag}: {e_val_err}")
                # traceback.print_exc() # Optional: for more detail
        except Exception as e_pipe_read:
            print(f"EditorBotControl: Unexpected error reading pipe {pipe_name_tag}: {e_pipe_read}")
            traceback.print_exc()
        finally:
            if pipe and not pipe.closed:
                try: pipe.close()
                except Exception: pass

    def clear_bot_log_display(self):
        """Clears the content of the bot log display ScrolledText widget."""
        try:
            if hasattr(self.editor_app, 'log_display') and self.editor_app.log_display.winfo_exists():
                self.editor_app.log_display.config(state='normal')
                self.editor_app.log_display.delete('1.0', tk.END)
                self.editor_app.log_display.config(state='disabled')
                self.editor_app.log_queue.put(("info", "--- Log Display Cleared Manually ---\n"))
        except tk.TclError as e_tcl:
            if "invalid command name" not in str(e_tcl).lower():
                print(f"EditorBotControl: TclError clearing log display: {e_tcl}")
        except Exception as e_clear_log:
            print(f"EditorBotControl: Unexpected error clearing log display: {e_clear_log}")
            traceback.print_exc()

    def update_script_status_display(self):
        """Updates the status label and button text based on script running state."""
        try:
            is_running_flag = self.is_bot_script_running()
            if hasattr(self, 'status_label_widget') and self.status_label_widget.winfo_exists():
                status_text_val = "Bot Status: Running" if is_running_flag else "Bot Status: Stopped"
                status_color_val = TENOS_LIGHT_BLUE_ACCENT2 if is_running_flag else TENOS_DARK_BLUE_BG
                self.status_label_widget.config(text=status_text_val, foreground=status_color_val)

            if hasattr(self, 'start_stop_button_widget') and self.start_stop_button_widget.winfo_exists():
                 self.start_stop_button_widget.config(text="Stop Bot" if is_running_flag else "Start Bot")
        except tk.TclError as e_tcl_status:
            if "invalid command name" not in str(e_tcl_status).lower():
                print(f"EditorBotControl: TclError updating script status display: {e_tcl_status}")
        except Exception as e_status_update:
            print(f"EditorBotControl: Unexpected error updating script status display: {e_status_update}")
            # traceback.print_exc() # Optional for more detail
