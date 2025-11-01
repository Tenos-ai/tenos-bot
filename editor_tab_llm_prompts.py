import difflib
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

from editor_utils import save_json_config, load_llm_prompts_config_util
from editor_constants import LLM_PROMPTS_FILE_NAME

class LLMPromptsTab:
    def __init__(self, editor_app_ref, parent_notebook):
        self.editor_app = editor_app_ref
        self.notebook = parent_notebook

        self.llm_prompts_tab_frame = ttk.Frame(self.notebook, padding="10", style="Tenos.TFrame")
        self.notebook.add(self.llm_prompts_tab_frame, text=' LLM Prompts ')

        self.llm_prompt_widgets = {}
        self.llm_prompts_config_data = {}
        self.history_entries = []

        self.history_var = tk.StringVar()
        self.history_combo = None

        self._create_prompt_editing_widgets()
        self.load_and_populate_llm_prompts()

        ttk.Button(self.llm_prompts_tab_frame, text="Save LLM Prompts", command=self.save_llm_prompts_data).pack(side=tk.BOTTOM, pady=10)

    def _create_prompt_editing_widgets(self):
        """Creates the UI structure for editing LLM prompts using a sub-notebook."""
        llm_sub_notebook = ttk.Notebook(self.llm_prompts_tab_frame, style="Tenos.TNotebook")
        llm_sub_notebook.pack(expand=True, fill="both", padx=0, pady=5)

        def create_prompt_sub_tab(parent, title, config_key):
            tab_frame = ttk.Frame(parent, padding="5", style="Tenos.TFrame")
            parent.add(tab_frame, text=f" {title} ")

            text_widget = scrolledtext.ScrolledText(
                tab_frame,
                wrap=tk.WORD,
                height=12,
                width=90,
                font=("Consolas", 10),
                relief="groove",
                borderwidth=1
            )
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            self.editor_app.register_theme_widget(text_widget, {
                "bg": "ENTRY_BG_COLOR",
                "fg": "TEXT_COLOR_NORMAL",
                "insertbackground": "ENTRY_INSERT_COLOR",
                "selectbackground": "SELECT_BG_COLOR",
                "selectforeground": "SELECT_FG_COLOR"
            })
            self.llm_prompt_widgets[config_key] = text_widget


        create_prompt_sub_tab(llm_sub_notebook, "Flux Prompt", 'enhancer_system_prompt')
        create_prompt_sub_tab(llm_sub_notebook, "SDXL Prompt", 'enhancer_system_prompt_sdxl')
        create_prompt_sub_tab(llm_sub_notebook, "Kontext Prompt", 'enhancer_system_prompt_kontext')

        self._create_history_controls()

    def _create_history_controls(self):
        history_frame = ttk.Frame(self.llm_prompts_tab_frame, style="Tenos.TFrame")
        history_frame.pack(fill=tk.X, pady=(6, 4))
        ttk.Label(history_frame, text="Session History:", style="Tenos.TLabel").pack(side=tk.LEFT)
        self.history_combo = ttk.Combobox(history_frame, textvariable=self.history_var, state="readonly", width=40, style="Tenos.TCombobox")
        self.history_combo.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(history_frame, text="Diff vs Selected", command=self._show_history_diff).pack(side=tk.LEFT, padx=4)
        ttk.Button(history_frame, text="Restore Snapshot", command=self._restore_history_entry).pack(side=tk.LEFT, padx=4)

    def _add_history_snapshot(self, label, data):
        self.history_entries.append({
            "label": label,
            "data": data.copy()
        })
        self._update_history_combo()

    def _update_history_combo(self):
        if not self.history_combo:
            return
        values = [entry["label"] for entry in self.history_entries]
        self.history_combo.configure(values=values)
        if values:
            self.history_combo.current(len(values) - 1)

    def _get_selected_history(self):
        if not self.history_entries or not self.history_combo:
            return None
        label = self.history_var.get()
        for entry in self.history_entries:
            if entry["label"] == label:
                return entry
        return None

    def _show_history_diff(self):
        snapshot = self._get_selected_history()
        if not snapshot:
            self.editor_app.show_status_message("Select a history snapshot to diff against.", level="warning")
            return
        diff_lines = []
        for key, widget in self.llm_prompt_widgets.items():
            current_text = widget.get("1.0", tk.END).splitlines()
            previous_text = snapshot["data"].get(key, "").splitlines()
            section_diff = list(difflib.unified_diff(previous_text, current_text, fromfile=f"{key} (snapshot)", tofile=f"{key} (current)", lineterm=""))
            if section_diff:
                diff_lines.append("\n".join(section_diff))
        if not diff_lines:
            self.editor_app.show_status_message("No differences between the current prompts and the selected snapshot.", level="info")
            return
        diff_window = tk.Toplevel(self.editor_app.master)
        diff_window.title("Prompt Differences")
        diff_window.geometry("820x520")
        text_area = scrolledtext.ScrolledText(diff_window, wrap=tk.WORD, font=("Consolas", 10))
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.insert(tk.END, "\n\n".join(diff_lines))
        text_area.configure(state='disabled')

    def _restore_history_entry(self):
        snapshot = self._get_selected_history()
        if not snapshot:
            self.editor_app.show_status_message("Select a history snapshot to restore.", level="warning")
            return
        for key, widget in self.llm_prompt_widgets.items():
            if widget.winfo_exists():
                widget.delete('1.0', tk.END)
                widget.insert(tk.END, snapshot["data"].get(key, ""))
        self.editor_app.show_status_message(f"Restored prompts from '{snapshot['label']}'.", level="info")


    def load_and_populate_llm_prompts(self):
        """Loads LLM prompts from file and populates the UI widgets."""
        self.llm_prompts_config_data = load_llm_prompts_config_util()
        self.history_entries.clear()

        for key, widget in self.llm_prompt_widgets.items():
            if widget.winfo_exists():
                widget.delete('1.0', tk.END)
                widget.insert(tk.END, self.llm_prompts_config_data.get(key, ''))

        self._add_history_snapshot(f"Loaded {datetime.now().strftime('%H:%M:%S')}", self.llm_prompts_config_data)

    def save_llm_prompts_data(self):
        """Saves the LLM prompts from the UI widgets back to the file."""
        updated_prompts_from_ui = {}
        save_needed = False

        for key, widget_instance in self.llm_prompt_widgets.items():
            if isinstance(widget_instance, scrolledtext.ScrolledText) and widget_instance.winfo_exists():
                current_text_in_widget = widget_instance.get("1.0", tk.END).strip()
                updated_prompts_from_ui[key] = current_text_in_widget
                
                if current_text_in_widget != self.llm_prompts_config_data.get(key, "").strip():
                    save_needed = True
            else: 
                updated_prompts_from_ui[key] = self.llm_prompts_config_data.get(key, '')
        
        if not updated_prompts_from_ui:
            self.editor_app.show_status_message("No LLM prompt fields found to save.", level="warning")
            return

        
        for key_original in self.llm_prompts_config_data:
            if key_original not in updated_prompts_from_ui:
                updated_prompts_from_ui[key_original] = self.llm_prompts_config_data[key_original]
                save_needed = True

        if not save_needed:
            self.editor_app.show_status_message("No changes detected in LLM prompts.", level="info")
            return

        if save_json_config(LLM_PROMPTS_FILE_NAME, updated_prompts_from_ui, "LLM prompts"):
            self.llm_prompts_config_data = updated_prompts_from_ui

            if hasattr(self.editor_app, 'llm_prompts_config'):
                 self.editor_app.llm_prompts_config = self.llm_prompts_config_data.copy()
            self._add_history_snapshot(f"Saved {datetime.now().strftime('%H:%M:%S')}", self.llm_prompts_config_data)
            self.editor_app.show_status_message("LLM prompts saved successfully!", level="success")
        else:
            self.editor_app.show_status_message("Failed to save LLM prompts.", level="error", duration=2200)
