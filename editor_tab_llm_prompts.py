import tkinter as tk
from tkinter import ttk, scrolledtext
import traceback
from editor_utils import silent_showinfo, silent_showerror, save_json_config, load_llm_prompts_config_util
from editor_constants import (
    LLM_PROMPTS_FILE_NAME, ENTRY_BG_COLOR, TEXT_COLOR_NORMAL,
    ENTRY_INSERT_COLOR, SELECT_BG_COLOR, SELECT_FG_COLOR
)

class LLMPromptsTab:
    def __init__(self, editor_app_ref, parent_notebook):
        self.editor_app = editor_app_ref
        self.notebook = parent_notebook

        self.llm_prompts_tab_frame = ttk.Frame(self.notebook, padding="10", style="Tenos.TFrame")
        self.notebook.add(self.llm_prompts_tab_frame, text=' LLM Prompts ')

        self.llm_prompt_widgets = {}
        self.llm_prompts_config_data = {}

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
            
            text_widget = scrolledtext.ScrolledText(tab_frame, wrap=tk.WORD, height=10, width=80,
                                                      font=("Consolas", 10), bg=ENTRY_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                                      insertbackground=ENTRY_INSERT_COLOR, selectbackground=SELECT_BG_COLOR,
                                                      selectforeground=SELECT_FG_COLOR, borderwidth=1, relief="sunken")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            self.llm_prompt_widgets[config_key] = text_widget

        
        create_prompt_sub_tab(llm_sub_notebook, "Flux Prompt", 'enhancer_system_prompt')
        create_prompt_sub_tab(llm_sub_notebook, "SDXL Prompt", 'enhancer_system_prompt_sdxl')
        create_prompt_sub_tab(llm_sub_notebook, "Kontext Prompt", 'enhancer_system_prompt_kontext')


    def load_and_populate_llm_prompts(self):
        """Loads LLM prompts from file and populates the UI widgets."""
        self.llm_prompts_config_data = load_llm_prompts_config_util()

        for key, widget in self.llm_prompt_widgets.items():
            if widget.winfo_exists():
                widget.delete('1.0', tk.END)
                widget.insert(tk.END, self.llm_prompts_config_data.get(key, ''))

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
            silent_showwarning("No Prompts", "No LLM prompt fields found to save.", parent=self.editor_app.master)
            return

        
        for key_original in self.llm_prompts_config_data:
            if key_original not in updated_prompts_from_ui:
                updated_prompts_from_ui[key_original] = self.llm_prompts_config_data[key_original]
                save_needed = True

        if not save_needed:
            silent_showinfo("No Changes", "No changes detected in LLM prompts.", parent=self.editor_app.master)
            return

        if save_json_config(LLM_PROMPTS_FILE_NAME, updated_prompts_from_ui, "LLM prompts"):
            self.llm_prompts_config_data = updated_prompts_from_ui
            
            if hasattr(self.editor_app, 'llm_prompts_config'):
                 self.editor_app.llm_prompts_config = self.llm_prompts_config_data.copy()
            silent_showinfo("Success", "LLM prompts saved successfully!", parent=self.editor_app.master)
