import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog
import json
import os
import traceback
from editor_utils import (
    silent_showinfo,
    silent_showerror,
    silent_showwarning,
    silent_askyesno,
    silent_askstring,
    save_json_config,
)
from editor_constants import (
    STYLES_CONFIG_FILE_NAME, CANVAS_BG_COLOR, FRAME_BG_COLOR, TEXT_COLOR_NORMAL,
    LISTBOX_BG, LISTBOX_FG, LISTBOX_SELECT_BG, LISTBOX_SELECT_FG,
    ENTRY_BG_COLOR, BOLD_TLABEL_STYLE, ACCENT_TLABEL_STYLE
)

class LoraStylesTab:
    def __init__(self, editor_app_ref, parent_notebook):
        self.editor_app = editor_app_ref
        self.notebook = parent_notebook

        self.lora_styles_tab_frame = ttk.Frame(self.notebook, padding="10", style="Tenos.TFrame")
        self.notebook.add(self.lora_styles_tab_frame, text=' LoRA Styles ')

        
        left_frame = ttk.Frame(self.lora_styles_tab_frame, style="Tenos.TFrame")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Label(left_frame, text="Available Styles:", style="Tenos.TLabel").pack(anchor='w', pady=(0, 2))
        listbox_container_frame = ttk.Frame(left_frame, style="Tenos.TFrame")
        listbox_container_frame.pack(side=tk.TOP, fill=tk.Y, expand=True)

        self.style_listbox_widget = tk.Listbox(listbox_container_frame, width=30, height=25,
                                        bg=LISTBOX_BG, fg=LISTBOX_FG,
                                        selectbackground=LISTBOX_SELECT_BG, selectforeground=LISTBOX_SELECT_FG,
                                        highlightthickness=0, borderwidth=1, relief="sunken",
                                        font=('Arial', 9), exportselection=False)
        self.style_listbox_widget.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        self.style_listbox_widget.bind('<<ListboxSelect>>', self.on_style_selected_in_listbox)

        listbox_scrollbar_widget = ttk.Scrollbar(listbox_container_frame, orient="vertical", command=self.style_listbox_widget.yview, style="Tenos.Vertical.TScrollbar")
        listbox_scrollbar_widget.pack(side=tk.RIGHT, fill=tk.Y)
        self.style_listbox_widget.config(yscrollcommand=listbox_scrollbar_widget.set)

        style_buttons_frame = ttk.Frame(left_frame, style="Tenos.TFrame")
        style_buttons_frame.pack(side=tk.BOTTOM, pady=5)
        ttk.Button(style_buttons_frame, text="Add New Style", command=self.add_new_style_entry).pack(pady=2)
        ttk.Button(style_buttons_frame, text="Delete Selected Style", command=self.delete_selected_style_entry).pack(pady=2)

        
        self.style_details_outer_frame = ttk.Frame(self.lora_styles_tab_frame, style="Tenos.TFrame")
        self.style_details_outer_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        detail_canvas_widget = tk.Canvas(self.style_details_outer_frame, bg=CANVAS_BG_COLOR, highlightthickness=0)
        detail_scrollbar_widget = ttk.Scrollbar(self.style_details_outer_frame, orient="vertical", command=detail_canvas_widget.yview, style="Tenos.Vertical.TScrollbar")
        detail_canvas_widget.associated_scrollbar = detail_scrollbar_widget

        self.style_details_scrollable_frame = ttk.Frame(detail_canvas_widget, style="Tenos.TFrame")
        self.style_details_scrollable_frame.bind(
            "<Configure>", lambda event, c=detail_canvas_widget: self.editor_app._debounce_canvas_configure(c, event)
        )
        detail_canvas_widget.create_window((0, 0), window=self.style_details_scrollable_frame, anchor="nw")
        detail_canvas_widget.configure(yscrollcommand=detail_scrollbar_widget.set)

        detail_canvas_widget.pack(side="top", fill="both", expand=True)
        

        ttk.Button(self.style_details_outer_frame, text="Save LoRA Styles Config", command=self.save_current_styles_config).pack(side=tk.BOTTOM, pady=10)

        # This dictionary will hold Tkinter variables for the currently displayed style's LoRA slots
        # Key: style_name, Value: {lora_key: {var_name: tk.Var}, '__model_type_var': tk.StringVar}
        self.current_style_vars = {}

        self.populate_lora_styles_tab()


    def populate_lora_styles_tab(self):
        """Populates the style listbox. Details are populated on selection."""
        current_selection_indices = self.style_listbox_widget.curselection()
        selected_style_name_before_reload = None
        if current_selection_indices:
            try: selected_style_name_before_reload = self.style_listbox_widget.get(current_selection_indices[0])
            except tk.TclError: pass

        self.style_listbox_widget.delete(0, tk.END)
        
        style_keys_for_listbox = sorted([str(k) for k in self.editor_app.styles_config.keys() if k != 'off'])
        for style_name_iter in style_keys_for_listbox:
            self.style_listbox_widget.insert(tk.END, style_name_iter)

        
        for widget_iter in self.style_details_scrollable_frame.winfo_children():
            widget_iter.destroy()

        new_selection_index = -1
        if selected_style_name_before_reload and selected_style_name_before_reload in style_keys_for_listbox:
            new_selection_index = style_keys_for_listbox.index(selected_style_name_before_reload)
        elif style_keys_for_listbox:
            new_selection_index = 0

        if new_selection_index != -1:
            self.style_listbox_widget.selection_set(new_selection_index)
            self.style_listbox_widget.activate(new_selection_index)
            self.style_listbox_widget.see(new_selection_index)
            self.display_style_details(style_keys_for_listbox[new_selection_index])
        else:
            ttk.Label(self.style_details_scrollable_frame, text="Select a style or add a new one.", style="Tenos.TLabel").pack(padx=10, pady=10)
        self.style_details_scrollable_frame.event_generate("<Configure>")


    def on_style_selected_in_listbox(self, event=None):
        """Handles selection change in the style listbox."""
        selection_indices = self.style_listbox_widget.curselection()
        if not selection_indices:
            
            for widget_iter in self.style_details_scrollable_frame.winfo_children():
                widget_iter.destroy()
            ttk.Label(self.style_details_scrollable_frame, text="Select a style or add a new one.", style="Tenos.TLabel").pack(padx=10, pady=10)
            self.style_details_scrollable_frame.event_generate("<Configure>")
            return
        try:
            selected_style_name = self.style_listbox_widget.get(selection_indices[0])
            self.display_style_details(selected_style_name)
        except tk.TclError:
             pass
        except Exception as e:
            print(f"EditorLoraStyles: Unexpected error in on_style_selected_in_listbox: {e}")
            traceback.print_exc()

    def display_style_details(self, style_name_to_display):
        """Displays the LoRA slots and controls for the given style name."""
        
        for widget_iter in self.style_details_scrollable_frame.winfo_children():
            widget_iter.destroy()
        self.current_style_vars = {}

        if style_name_to_display == "off":
            ttk.Label(self.style_details_scrollable_frame, text="'off' style cannot be modified.", style="Tenos.TLabel").pack(padx=10, pady=10)
            self.style_details_scrollable_frame.event_generate("<Configure>")
            return

        current_style_data = self.editor_app.styles_config.get(style_name_to_display)
        if not isinstance(current_style_data, dict):
            current_style_data = {"favorite": False, "model_type": "all"}
            self.editor_app.styles_config[style_name_to_display] = current_style_data

        
        header_frame = ttk.Frame(self.style_details_scrollable_frame, style="Tenos.TFrame")
        header_frame.pack(fill=tk.X, pady=(5,15), padx=5)
        ttk.Label(header_frame, text=f"Editing Style: {style_name_to_display}", style="Bold.TLabel").pack(side=tk.LEFT, anchor='w')
        
        
        model_type_frame = ttk.Frame(header_frame, style="Tenos.TFrame")
        model_type_frame.pack(side=tk.RIGHT)
        ttk.Label(model_type_frame, text="Model Type:", style="Tenos.TLabel").pack(side=tk.LEFT, padx=(0,5))
        model_type_var = tk.StringVar(value=current_style_data.get('model_type', 'all'))
        model_type_combo = ttk.Combobox(model_type_frame, textvariable=model_type_var, values=["all", "flux", "sdxl", "qwen", "wan"], state="readonly", width=10, style="Tenos.TCombobox")
        model_type_combo.pack(side=tk.LEFT)
        model_type_var.trace_add("write", lambda *args, s=style_name_to_display: self._update_style_model_type(s))

        self.current_style_vars[style_name_to_display] = {'__model_type_var': model_type_var}

        
        def get_lora_slot_number(lora_key_str):
            try: return int(lora_key_str.split('_')[1])
            except (IndexError, ValueError): return float('inf')

        lora_slots_for_ui = {k: v for k, v in current_style_data.items() if k.startswith("lora_") and isinstance(v, dict)}
        sorted_lora_keys_for_display = sorted(lora_slots_for_ui.keys(), key=get_lora_slot_number)

        for lora_slot_key_str in sorted_lora_keys_for_display:
            slot_index_num = get_lora_slot_number(lora_slot_key_str)
            lora_slot_data_from_config = lora_slots_for_ui[lora_slot_key_str]

            lora_slot_frame = ttk.LabelFrame(self.style_details_scrollable_frame, text=f"Slot {slot_index_num}", style="Tenos.TLabelframe")
            lora_slot_frame.pack(fill=tk.X, pady=5, padx=5, anchor='n')

            current_slot_tk_vars = {}

            on_var_tk = tk.BooleanVar(value=lora_slot_data_from_config.get('on', False))
            enabled_check = tk.Checkbutton(lora_slot_frame, text="Enabled", variable=on_var_tk, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL, selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR, activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
            enabled_check.grid(row=0, column=0, padx=5, pady=5, sticky='w')
            current_slot_tk_vars['on'] = on_var_tk

            ttk.Label(lora_slot_frame, text="File:", style="Tenos.TLabel").grid(row=1, column=0, padx=5, pady=2, sticky='w')
            lora_file_str = str(lora_slot_data_from_config.get('lora', 'None'))
            display_lora_list_for_combo = self.editor_app.available_loras[:]
            if lora_file_str != 'None' and lora_file_str not in display_lora_list_for_combo:
                display_lora_list_for_combo.insert(1, lora_file_str)
            
            lora_var_tk = tk.StringVar(value=lora_file_str)
            lora_combo_widget = ttk.Combobox(lora_slot_frame, textvariable=lora_var_tk, values=display_lora_list_for_combo, state="readonly", width=38, style="Tenos.TCombobox")
            lora_combo_widget.grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky='ew')
            current_slot_tk_vars['lora'] = lora_var_tk

            ttk.Label(lora_slot_frame, text="Strength:", style="Tenos.TLabel").grid(row=2, column=0, padx=5, pady=2, sticky='w')
            try: current_strength_val = float(lora_slot_data_from_config.get('strength', 0.0))
            except (ValueError, TypeError): current_strength_val = 0.0
            strength_var_tk = tk.DoubleVar(value=round(current_strength_val, 2))
            strength_spinbox_widget = ttk.Spinbox(lora_slot_frame, textvariable=strength_var_tk, from_=-2.0, to=2.0, increment=0.05, format="%.2f", width=8, wrap=True, style="Tenos.TSpinbox")
            strength_spinbox_widget.grid(row=2, column=1, padx=5, pady=2, sticky='w')
            current_slot_tk_vars['strength'] = strength_var_tk

            remove_slot_button = ttk.Button(lora_slot_frame, text="Remove Slot",
                                      command=lambda s=style_name_to_display, k=lora_slot_key_str: self.remove_lora_slot_from_style(s, k))
            remove_slot_button.grid(row=0, column=3, rowspan=3, padx=(10, 5), pady=5, sticky='ne')

            self.current_style_vars[style_name_to_display][lora_slot_key_str] = current_slot_tk_vars

            on_var_tk.trace_add("write", lambda *args, s=style_name_to_display, k=lora_slot_key_str: self._update_lora_slot_data(s, k))
            lora_var_tk.trace_add("write", lambda *args, s=style_name_to_display, k=lora_slot_key_str: self._update_lora_slot_data(s, k))
            strength_var_tk.trace_add("write", lambda *args, s=style_name_to_display, k=lora_slot_key_str: self._update_lora_slot_data(s, k))

            lora_slot_frame.columnconfigure(1, weight=1)
            lora_slot_frame.columnconfigure(3, weight=0)

        next_slot_num_to_add = len(sorted_lora_keys_for_display) + 1
        if next_slot_num_to_add <= 5:
            add_lora_slot_button = ttk.Button(self.style_details_scrollable_frame, text=f"Add New LoRA Slot",
                                     command=lambda s=style_name_to_display: self.add_lora_slot_to_style(s))
            add_lora_slot_button.pack(pady=15, anchor='center')
        else:
            ttk.Label(self.style_details_scrollable_frame, text="Maximum LoRA slots (5) reached.", style="Tenos.TLabel").pack(pady=15)

        self.style_details_scrollable_frame.event_generate("<Configure>")

    def _update_style_model_type(self, style_name):
        if style_name in self.editor_app.styles_config and style_name in self.current_style_vars:
            model_type_var = self.current_style_vars[style_name].get('__model_type_var')
            if model_type_var:
                self.editor_app.styles_config[style_name]['model_type'] = model_type_var.get()

    def _update_lora_slot_data(self, style_name, lora_key_str):
        if style_name not in self.editor_app.styles_config or style_name == "off": return
        
        slot_tk_vars = self.current_style_vars.get(style_name, {}).get(lora_key_str)
        if not slot_tk_vars: return

        try:
            if lora_key_str not in self.editor_app.styles_config[style_name]:
                self.editor_app.styles_config[style_name][lora_key_str] = {}

            self.editor_app.styles_config[style_name][lora_key_str]['on'] = slot_tk_vars['on'].get()
            self.editor_app.styles_config[style_name][lora_key_str]['lora'] = slot_tk_vars['lora'].get()
            self.editor_app.styles_config[style_name][lora_key_str]['strength'] = round(float(slot_tk_vars['strength'].get()), 3)
        except (tk.TclError, ValueError) as e:
            print(f"EditorLoraStyles: Handled TclError/ValueError updating data for {style_name}/{lora_key_str}: {e}")
        except Exception as e:
            print(f"EditorLoraStyles: Error updating LoRA data from UI for {style_name}/{lora_key_str}: {e}")
            traceback.print_exc()

    def add_new_style_entry(self):
        new_style_name_input = silent_askstring("New Style", "Enter the name for the new style:", parent=self.editor_app.master)
        if new_style_name_input and new_style_name_input.strip():
            new_style_name_clean = new_style_name_input.strip()
            if new_style_name_clean == "off":
                silent_showerror("Invalid Name", "'off' is a reserved style name.", parent=self.editor_app.master)
                return
            if new_style_name_clean in self.editor_app.styles_config:
                silent_showerror("Duplicate Style", f"A style named '{new_style_name_clean}' already exists.", parent=self.editor_app.master)
                return
            
            self.editor_app.styles_config[new_style_name_clean] = {
                "favorite": False,
                "model_type": "all",
                "lora_1": {'on': False, 'lora': 'None', 'strength': 0.0}
            }

            self.current_style_vars[new_style_name_clean] = {}
            self.populate_lora_styles_tab()
            try:
                all_style_keys_in_listbox = list(self.style_listbox_widget.get(0, tk.END))
                if new_style_name_clean in all_style_keys_in_listbox:
                    new_index_in_list = all_style_keys_in_listbox.index(new_style_name_clean)
                    self.style_listbox_widget.selection_clear(0, tk.END)
                    self.style_listbox_widget.selection_set(new_index_in_list)
                    self.style_listbox_widget.activate(new_index_in_list)
                    self.style_listbox_widget.see(new_index_in_list)
                    self.display_style_details(new_style_name_clean)
            except tk.TclError: pass
        elif new_style_name_input is not None:
            silent_showerror("Invalid Name", "Style name cannot be empty.", parent=self.editor_app.master)

    def delete_selected_style_entry(self):
        selection_indices = self.style_listbox_widget.curselection()
        if not selection_indices:
            silent_showwarning("No Selection", "Please select a style to delete.", parent=self.editor_app.master)
            return
        try:
            style_name_to_delete = self.style_listbox_widget.get(selection_indices[0])
            if style_name_to_delete == "off":
                silent_showerror("Cannot Delete", "'off' style cannot be deleted.", parent=self.editor_app.master)
                return

            if silent_askyesno("Delete Confirmation", f"Delete style '{style_name_to_delete}'?", parent=self.editor_app.master):
                if style_name_to_delete in self.editor_app.styles_config:
                    del self.editor_app.styles_config[style_name_to_delete]
                if style_name_to_delete in self.current_style_vars:
                    del self.current_style_vars[style_name_to_delete]

                if save_json_config(STYLES_CONFIG_FILE_NAME, self.editor_app.styles_config, "styles config"):
                     silent_showinfo("Style Deleted", f"Style '{style_name_to_delete}' deleted.", parent=self.editor_app.master)

                self.populate_lora_styles_tab()
                self.editor_app.config_manager.load_bot_settings_data(self.editor_app.llm_models_config)
                self.editor_app.populate_bot_settings_tab()
                self.editor_app.favorites_tab_manager.populate_all_favorites_sub_tabs()

        except tk.TclError:
            silent_showerror("Error", "Could not get selected style.", parent=self.editor_app.master)
        except Exception as e:
            silent_showerror("Error", f"An error occurred while deleting style: {e}", parent=self.editor_app.master)
            traceback.print_exc()

    def add_lora_slot_to_style(self, style_name_target):
        if style_name_target not in self.editor_app.styles_config or style_name_target == "off": return
        
        lora_keys = [k for k in self.editor_app.styles_config[style_name_target] if k.startswith("lora_")]
        next_slot_num = len(lora_keys) + 1
        
        if next_slot_num > 5:
            silent_showinfo("Maximum Slots Reached", "A style can have a maximum of 5 LoRA slots.", parent=self.editor_app.master)
            return

        lora_key_to_add_str = f"lora_{next_slot_num}"
        self.editor_app.styles_config[style_name_target][lora_key_to_add_str] = {'on': False, 'lora': 'None', 'strength': 0.0}
        self.display_style_details(style_name_target)

    def remove_lora_slot_from_style(self, style_name_target, lora_key_to_remove_str):
        if style_name_target in self.editor_app.styles_config and lora_key_to_remove_str in self.editor_app.styles_config[style_name_target]:
            if silent_askyesno("Confirm Remove Slot", f"Remove {lora_key_to_remove_str} from '{style_name_target}'?", parent=self.editor_app.master):
                del self.editor_app.styles_config[style_name_target][lora_key_to_remove_str]
                if style_name_target in self.current_style_vars and lora_key_to_remove_str in self.current_style_vars[style_name_target]:
                    del self.current_style_vars[style_name_target][lora_key_to_remove_str]
                self.display_style_details(style_name_target)
        else:
            silent_showwarning("Slot Not Found", f"Could not find {lora_key_to_remove_str} in '{style_name_target}'.", parent=self.editor_app.master)

    def save_current_styles_config(self):
        current_selection_indices = self.style_listbox_widget.curselection()
        if current_selection_indices:
            try:
                selected_style_name = self.style_listbox_widget.get(current_selection_indices[0])
                self._update_style_model_type(selected_style_name)
                if selected_style_name in self.current_style_vars:
                    for lora_key in self.current_style_vars[selected_style_name]:
                        if lora_key != '__model_type_var':
                            self._update_lora_slot_data(selected_style_name, lora_key)
            except (tk.TclError, IndexError): pass

        if save_json_config(STYLES_CONFIG_FILE_NAME, self.editor_app.styles_config, "LoRA styles config"):
            silent_showinfo("Success", "LoRA styles saved successfully!", parent=self.editor_app.master)
            self.editor_app.styles_config = self.editor_app.styles_config_loader_func()
            self.populate_lora_styles_tab()
            self.editor_app.config_manager.load_bot_settings_data(self.editor_app.llm_models_config)
            self.editor_app.populate_bot_settings_tab()
            self.editor_app.favorites_tab_manager.populate_all_favorites_sub_tabs()
