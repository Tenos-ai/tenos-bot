import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext 
import os
import json 
import traceback
import threading
import queue
import platform 
import subprocess 
import psutil 
import git 
import shutil 
import requests

from editor_constants import (
    TENOS_DARK_BLUE_BG, TENOS_MEDIUM_BLUE_ACCENT, TENOS_LIGHT_BLUE_ACCENT2,
    TENOS_WHITE_FG, TENOS_BLACK_DETAIL,
    DOMINANT_BG, WIDGET_BG, TEXT_COLOR_NORMAL, TEXT_COLOR_DISABLED,
    BACKGROUND_COLOR, FRAME_BG_COLOR, CANVAS_BG_COLOR,
    ENTRY_BG_COLOR, ENTRY_FG_COLOR, ENTRY_INSERT_COLOR,
    SELECT_BG_COLOR, SELECT_FG_COLOR,
    BUTTON_BG_COLOR, BUTTON_FG_COLOR, BUTTON_ACTIVE_BG_COLOR, BUTTON_ACTIVE_FG_COLOR,
    BORDER_COLOR,
    SCROLLBAR_TROUGH_COLOR, SCROLLBAR_SLIDER_COLOR,
    LISTBOX_BG, LISTBOX_FG, LISTBOX_SELECT_BG, LISTBOX_SELECT_FG,
    ACTIVE_TAB_BG, INACTIVE_TAB_BG, ACTIVE_TAB_FG, INACTIVE_TAB_FG,
    LOG_STDOUT_FG, LOG_STDERR_FG, LOG_INFO_FG, LOG_WORKER_FG,
    BOLD_TLABEL_STYLE, ACCENT_TLABEL_STYLE,
    CONFIG_FILE_NAME, SETTINGS_FILE_NAME, STYLES_CONFIG_FILE_NAME,
    LLM_MODELS_FILE_NAME, LLM_PROMPTS_FILE_NAME,
    MODELS_LIST_FILE_NAME, CHECKPOINTS_LIST_FILE_NAME, CLIP_LIST_FILE_NAME,
    ICON_PATH_ICO, ICON_PATH_PNG,
    BOT_SCRIPT_NAME
)

from editor_utils import (
    silent_showinfo, silent_showerror, silent_askyesno, silent_askstring, browse_folder_dialog,
    load_llm_models_config_util, load_llm_prompts_config_util, load_styles_config_editor_util,
    save_json_config
)
from editor_config_manager import EditorConfigManager
from editor_tab_lora_styles import LoraStylesTab
from editor_tab_favorites import FavoritesTab
from editor_tab_llm_prompts import LLMPromptsTab
from editor_tab_bot_control import BotControlTab
from editor_tab_admin_control import AdminControlTab

class ConfigEditor:
    def __init__(self, master_tk_root):
        self.master = master_tk_root
        self.master.title("Tenos.ai Configurator v1.2.3")
        self.master.geometry("850x950")
        self.master.configure(bg=BACKGROUND_COLOR)

        self.style = ttk.Style()
        self._configure_main_editor_style()

        def silence_bell_global(): pass
        self.master.bell = silence_bell_global
        self.master.option_add('*Dialog.msg.font', ('Arial', 10))
        self.master.option_add('*Dialog.msg.Bell', '0')
        self.master.option_add("*TCombobox*Listbox*Background", LISTBOX_BG)
        self.master.option_add("*TCombobox*Listbox*Foreground", LISTBOX_FG)
        self.master.option_add("*TCombobox*Listbox*selectBackground", SELECT_BG_COLOR)
        self.master.option_add("*TCombobox*Listbox*selectForeground", SELECT_FG_COLOR)
        self.master.option_add("*TCombobox*Listbox.font", ('Arial', 9))

        self._set_application_icon()

        self.bot_process = None
        self.log_queue = queue.Queue()
        self.stop_readers = threading.Event()
        self.reader_threads = []
        self.worker_queue = queue.Queue()
        self.worker_thread = None

        self.llm_models_config = load_llm_models_config_util()
        self.llm_prompts_config = load_llm_prompts_config_util()
        self.styles_config_loader_func = load_styles_config_editor_util
        self.styles_config = self.styles_config_loader_func()

        self.config_manager = EditorConfigManager(self)
        self.config_manager.load_main_config_data()
        self.config_manager.load_bot_settings_data(self.llm_models_config)

        self.available_models = []
        self.available_checkpoints = []
        self.available_clips_t5 = []
        self.available_clips_l = []
        self.available_loras = ["None"]
        self.available_upscale_models = ["None"]
        self.available_vaes = ["None"]
        self.load_available_files()

        self.config_vars = {}
        self.settings_vars = {}
        self.bot_settings_widgets = {}

        self.provider_display_map = { k: v.get("display_name", k.capitalize()) for k, v in self.llm_models_config.get("providers", {}).items() }
        self.display_prompt_map = { "enhanced": "Show Enhanced Prompt ✨", "original": "Show Original Prompt ✍️" }

        self._create_menu_bar()
        self._create_restart_note_label()

        self.notebook = ttk.Notebook(self.master, style="Tenos.TNotebook")
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self._create_main_config_tab_structure()
        
        self.admin_control_tab_manager = AdminControlTab(self, self.notebook)

        self._create_bot_settings_tab_structure()
        self.populate_bot_settings_tab()

        self.lora_styles_tab_manager = LoraStylesTab(self, self.notebook)
        self.favorites_tab_manager = FavoritesTab(self, self.notebook)
        self.llm_prompts_tab_manager = LLMPromptsTab(self, self.notebook)

        self._initialize_shared_log_display_widget()
        self.bot_control_tab_manager = BotControlTab(self, self.notebook)

        if self.master.winfo_exists():
            self.master.after(100, self._process_gui_updates_loop)
            self.master.after(2000, self._check_settings_file_for_changes)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing_main_window)

    def _set_application_icon(self):
        if os.path.exists(ICON_PATH_ICO):
            try: self.master.iconbitmap(ICON_PATH_ICO)
            except tk.TclError:
                if os.path.exists(ICON_PATH_PNG):
                    try: self.master.iconphoto(False, tk.PhotoImage(file=ICON_PATH_PNG))
                    except tk.TclError: pass
    
    def _create_menu_bar(self):
        self.menu_bar = tk.Menu(self.master, bg=BACKGROUND_COLOR, fg=TEXT_COLOR_NORMAL, activebackground=SELECT_BG_COLOR, activeforeground=SELECT_FG_COLOR, relief="flat", borderwidth=0)
        self.master.config(menu=self.menu_bar)
        file_menu = tk.Menu(self.menu_bar, tearoff=0, bg=WIDGET_BG, fg=TEXT_COLOR_NORMAL, relief="flat", activebackground=SELECT_BG_COLOR, activeforeground=SELECT_FG_COLOR)
        file_menu.add_command(label="Save All Configs", command=self.save_all_configurations_from_menu)
        file_menu.add_separator(background=BORDER_COLOR)
        file_menu.add_command(label="Exit", command=self.on_closing_main_window)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        tools_menu = tk.Menu(self.menu_bar, tearoff=0, bg=WIDGET_BG, fg=TEXT_COLOR_NORMAL, relief="flat", activebackground=SELECT_BG_COLOR, activeforeground=SELECT_FG_COLOR)
        tools_menu.add_command(label="Install/Update Custom Nodes", command=lambda: self.run_worker_task_on_editor(self._worker_install_custom_nodes, "Installing Nodes"))
        tools_menu.add_command(label="Scan Models/Clips/Checkpoints", command=lambda: self.run_worker_task_on_editor(self._worker_scan_models_clips_checkpoints, "Scanning Files"))
        tools_menu.add_command(label="Refresh LLM Models List", command=lambda: self.run_worker_task_on_editor(self._worker_update_llm_models_list, "Refreshing LLMs"))
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)
        help_menu = tk.Menu(self.menu_bar, tearoff=0, bg=WIDGET_BG, fg=TEXT_COLOR_NORMAL, relief="flat", activebackground=SELECT_BG_COLOR, activeforeground=SELECT_FG_COLOR)
        help_menu.add_command(label="About", command=self.show_about_dialog)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

    def _create_restart_note_label(self):
        restart_note_frame = ttk.Frame(self.master, style="Tenos.TFrame")
        restart_note_frame.pack(fill=tk.X, padx=10, pady=(5,0))
        ttk.Label(restart_note_frame, text="Note: Changes to paths (Main Config) or API Keys require a bot restart to take effect.", style="Tenos.TLabel", font=('Arial', 9, 'italic'), foreground=TENOS_LIGHT_BLUE_ACCENT2).pack(side=tk.LEFT)

    def _initialize_shared_log_display_widget(self):
        self.log_display = scrolledtext.ScrolledText( self.master, state='disabled', wrap=tk.WORD, height=1, width=1, font=("Consolas", 9), bg=ENTRY_BG_COLOR, fg=TEXT_COLOR_NORMAL, insertbackground=ENTRY_INSERT_COLOR, selectbackground=SELECT_BG_COLOR, selectforeground=SELECT_FG_COLOR, borderwidth=1, relief="sunken" )
        self.log_display.tag_configure("stdout", foreground=LOG_STDOUT_FG)
        self.log_display.tag_configure("stderr", foreground=LOG_STDERR_FG)
        self.log_display.tag_configure("info", foreground=LOG_INFO_FG, font=("Consolas", 9, "italic"))
        self.log_display.tag_configure("worker", foreground=LOG_WORKER_FG, font=("Consolas", 9, "bold"))

    def _configure_main_editor_style(self):
        s = self.style; s.theme_use('default')
        s.configure(".", background=BACKGROUND_COLOR, foreground=TEXT_COLOR_NORMAL, fieldbackground=ENTRY_BG_COLOR, borderwidth=1, font=('Arial', 9))
        s.map(".", background=[("disabled", "#3a3a3a"), ("active", BUTTON_ACTIVE_BG_COLOR)], foreground=[("disabled", TEXT_COLOR_DISABLED)], fieldbackground=[("disabled", "#303030")])
        s.configure("TFrame", background=FRAME_BG_COLOR); s.configure("Tenos.TFrame", background=FRAME_BG_COLOR)
        s.configure("TLabel", background=FRAME_BG_COLOR, foreground=TEXT_COLOR_NORMAL, padding=2)
        s.configure(BOLD_TLABEL_STYLE, font=('Arial', 10, 'bold'), background=FRAME_BG_COLOR, foreground=TEXT_COLOR_NORMAL)
        s.configure(ACCENT_TLABEL_STYLE, foreground=TENOS_MEDIUM_BLUE_ACCENT, background=FRAME_BG_COLOR)
        s.configure("TButton", background=BUTTON_BG_COLOR, foreground=BUTTON_FG_COLOR, bordercolor=BORDER_COLOR, lightcolor=BUTTON_BG_COLOR, darkcolor=BUTTON_BG_COLOR, padding=(8, 4), relief="raised", font=('Arial', 9, 'bold'))
        s.map("TButton", background=[("active", BUTTON_ACTIVE_BG_COLOR), ("pressed", BUTTON_ACTIVE_BG_COLOR), ("disabled", "#555555")], foreground=[("active", BUTTON_ACTIVE_FG_COLOR), ("pressed", BUTTON_ACTIVE_FG_COLOR), ("disabled", TEXT_COLOR_DISABLED)], relief=[("pressed", "sunken"), ("!pressed", "raised")], bordercolor=[("active", TENOS_LIGHT_BLUE_ACCENT2)])
        s.configure("TNotebook", background=BACKGROUND_COLOR, tabmargins=[2, 5, 2, 0], borderwidth=0); s.configure("TNotebook.Tab", background=INACTIVE_TAB_BG, foreground=INACTIVE_TAB_FG, padding=[10, 5], font=('Arial', 10), borderwidth=1, relief="raised")
        s.map("TNotebook.Tab", background=[("selected", ACTIVE_TAB_BG), ("active", TENOS_LIGHT_BLUE_ACCENT2)], foreground=[("selected", ACTIVE_TAB_FG), ("active", BACKGROUND_COLOR)], relief=[("selected", "flat")], focuscolor=[("selected", SELECT_BG_COLOR)])
        s.configure("Tenos.TNotebook", background=BACKGROUND_COLOR)
        s.configure("TEntry", fieldbackground=ENTRY_BG_COLOR, foreground=ENTRY_FG_COLOR, insertcolor=ENTRY_INSERT_COLOR, bordercolor=BORDER_COLOR, borderwidth=1, relief="sunken", padding=4, font=('Arial', 9))
        s.map("TEntry", fieldbackground=[("focus", TENOS_DARK_BLUE_BG), ("disabled", "#303030")], foreground=[("disabled", TEXT_COLOR_DISABLED)], bordercolor=[("focus", TENOS_LIGHT_BLUE_ACCENT2)])
        s.configure("Tenos.TEntry", fieldbackground=ENTRY_BG_COLOR)
        s.configure("TCombobox", fieldbackground=ENTRY_BG_COLOR, foreground=ENTRY_FG_COLOR, selectbackground=SELECT_BG_COLOR, selectforeground=SELECT_FG_COLOR, insertcolor=ENTRY_INSERT_COLOR, arrowcolor=TEXT_COLOR_NORMAL, arrowsize=16, borderwidth=1, padding=3, relief="sunken", font=('Arial', 9))
        s.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG_COLOR), ("focus", TENOS_DARK_BLUE_BG), ("disabled", "#303030")], foreground=[("disabled", TEXT_COLOR_DISABLED)], bordercolor=[("focus", TENOS_LIGHT_BLUE_ACCENT2)], arrowcolor=[("disabled", TEXT_COLOR_DISABLED), ("hover", TENOS_LIGHT_BLUE_ACCENT2)], background=[("active", BUTTON_ACTIVE_BG_COLOR)])
        s.configure("Tenos.TCombobox", fieldbackground=ENTRY_BG_COLOR)
        s.configure("TSpinbox", fieldbackground=ENTRY_BG_COLOR, foreground=ENTRY_FG_COLOR, insertcolor=ENTRY_INSERT_COLOR, arrowsize=12, borderwidth=1, buttonbackground=BUTTON_BG_COLOR, relief="sunken", padding=3, font=('Arial', 9))
        s.map("TSpinbox", fieldbackground=[("focus", TENOS_DARK_BLUE_BG), ("disabled", "#303030")], foreground=[("disabled", TEXT_COLOR_DISABLED)], buttonbackground=[("active", BUTTON_ACTIVE_BG_COLOR), ("disabled", WIDGET_BG)], buttonforeground=[("disabled", TEXT_COLOR_DISABLED)], bordercolor=[("focus", TENOS_LIGHT_BLUE_ACCENT2)])
        s.configure("Tenos.TSpinbox", fieldbackground=ENTRY_BG_COLOR)
        s.configure("TCheckbutton", background=FRAME_BG_COLOR, foreground=TEXT_COLOR_NORMAL, indicatorbackground=WIDGET_BG, indicatorforeground=TENOS_WHITE_FG, indicatordiameter=13, indicatormargin=3, indicatorrelief="flat", padding=(5,3))
        s.map("TCheckbutton", indicatorbackground=[("active", ENTRY_BG_COLOR), ("selected", TENOS_MEDIUM_BLUE_ACCENT)], indicatorforeground=[("selected", TENOS_WHITE_FG), ("!selected", TENOS_WHITE_FG)], background=[("active", FRAME_BG_COLOR)])
        s.configure("Tenos.TCheckbutton", background=FRAME_BG_COLOR)
        s.configure("TScrollbar", troughcolor=SCROLLBAR_TROUGH_COLOR, background=SCROLLBAR_SLIDER_COLOR, gripcount=0, borderwidth=0, relief="flat", arrowsize=14, arrowcolor=TEXT_COLOR_NORMAL)
        s.map("TScrollbar", background=[("active", TENOS_LIGHT_BLUE_ACCENT2), ("disabled", "#444444")], troughcolor=[("disabled", BACKGROUND_COLOR)], arrowcolor=[("disabled", TEXT_COLOR_DISABLED)])
        s.configure("Tenos.Vertical.TScrollbar", background=SCROLLBAR_SLIDER_COLOR)
        s.configure("TLabelframe", background=FRAME_BG_COLOR, bordercolor=BORDER_COLOR, borderwidth=1, relief="solid", padding=6); s.configure("TLabelframe.Label", background=FRAME_BG_COLOR, foreground=TEXT_COLOR_NORMAL, font=('Arial', 10, 'bold'), padding=(0,0,0,3))
        s.configure("Tenos.TLabelframe", background=FRAME_BG_COLOR)

    def _create_main_config_tab_structure(self):
        self.main_config_tab_frame = ttk.Frame(self.notebook, padding=0, style="Tenos.TFrame")
        self.notebook.add(self.main_config_tab_frame, text=' Main Config ')
        
        self.main_config_notebook = ttk.Notebook(self.main_config_tab_frame, style="Tenos.TNotebook")
        self.main_config_notebook.pack(expand=True, fill="both", padx=5, pady=5)
        
        self.paths_tab_frame = ttk.Frame(self.main_config_notebook, padding="10", style="Tenos.TFrame")
        self.endpoints_tab_frame = ttk.Frame(self.main_config_notebook, padding="10", style="Tenos.TFrame")
        self.api_keys_tab_frame = ttk.Frame(self.main_config_notebook, padding="10", style="Tenos.TFrame")
        
        self.main_config_notebook.add(self.paths_tab_frame, text=" File Paths ")
        self.main_config_notebook.add(self.endpoints_tab_frame, text=" Endpoint URLs ")
        self.main_config_notebook.add(self.api_keys_tab_frame, text=" API Keys ")
        
        ttk.Button(self.main_config_tab_frame, text="Save Main Config", command=self.config_manager.save_main_config_data).pack(side="bottom", pady=10)
        
        self.populate_main_config_sub_tabs()

    def populate_main_config_sub_tabs(self):
        self.config_vars.clear()
        
        def create_config_row(parent_frame, section_name, item_key_name, is_path=False, is_port=False):
            row_frame = ttk.Frame(parent_frame, style="Tenos.TFrame")
            row_frame.pack(fill=tk.X, pady=2)
            ttk.Label(row_frame, text=f"{item_key_name.replace('_', ' ').title()}:", style="Tenos.TLabel", width=25).pack(side=tk.LEFT, padx=(5,10))
            current_item_val = self.config_manager.config.get(section_name, {}).get(item_key_name, "")
            tk_var = tk.StringVar(value=str(current_item_val) if current_item_val is not None else "")
            self.config_vars[f"{section_name}.{item_key_name}"] = tk_var
            show_char_val = "*" if "KEY" in item_key_name.upper() else ""
            entry_widget_item = ttk.Entry(row_frame, textvariable=tk_var, width=(10 if is_port else 60), show=show_char_val, style="Tenos.TEntry")
            entry_widget_item.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if is_path:
                browse_btn = ttk.Button(row_frame, text="Browse...", command=lambda s=section_name, k=item_key_name: self._browse_folder_for_main_config(s, k))
                browse_btn.pack(side=tk.LEFT, padx=5)

        for widget in self.paths_tab_frame.winfo_children(): widget.destroy()
        for section in ["OUTPUTS", "MODELS", "CLIP", "LORAS", "NODES"]:
            ttk.Label(self.paths_tab_frame, text=section.replace("_", " ").title(), style=BOLD_TLABEL_STYLE).pack(fill=tk.X, pady=(10,5))
            for key in self.config_manager.config_template_definition[section]:
                create_config_row(self.paths_tab_frame, section, key, is_path=True)
                
        for widget in self.endpoints_tab_frame.winfo_children(): widget.destroy()
        for section in ["COMFYUI_API", "BOT_INTERNAL_API"]:
            ttk.Label(self.endpoints_tab_frame, text=section.replace("_", " ").title(), style=BOLD_TLABEL_STYLE).pack(fill=tk.X, pady=(10,5))
            create_config_row(self.endpoints_tab_frame, section, "HOST")
            create_config_row(self.endpoints_tab_frame, section, "PORT", is_port=True)

        for widget in self.api_keys_tab_frame.winfo_children(): widget.destroy()
        for section in ["BOT_API", "LLM_ENHANCER"]:
            ttk.Label(self.api_keys_tab_frame, text=section.replace("_", " ").title(), style=BOLD_TLABEL_STYLE).pack(fill=tk.X, pady=(10,5))
            for key in self.config_manager.config_template_definition[section]:
                create_config_row(self.api_keys_tab_frame, section, key)

    def _browse_folder_for_main_config(self, section_name, key_name):
        var_lookup_key = f"{section_name}.{key_name}"
        initial_dir_val = self.config_vars[var_lookup_key].get() if var_lookup_key in self.config_vars else None
        selected_folder_path = browse_folder_dialog(parent=self.master, initialdir=initial_dir_val or os.getcwd(), title=f"Select Folder for {key_name}")
        if selected_folder_path and var_lookup_key in self.config_vars: self.config_vars[var_lookup_key].set(selected_folder_path)

    def _create_bot_settings_tab_structure(self):
        self.bot_settings_tab_frame = ttk.Frame(self.notebook, padding="10", style="Tenos.TFrame")
        self.notebook.add(self.bot_settings_tab_frame, text=' Bot Settings ')
        canvas = tk.Canvas(self.bot_settings_tab_frame, bg=CANVAS_BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.bot_settings_tab_frame, orient="vertical", command=canvas.yview, style="Tenos.Vertical.TScrollbar")
        canvas.associated_scrollbar = scrollbar
        self.scrollable_bot_settings_content_frame = ttk.Frame(canvas, style="Tenos.TFrame")
        self.scrollable_bot_settings_content_frame.bind("<Configure>", lambda e, c=canvas: self._debounce_canvas_configure(c,e))
        canvas.create_window((0,0), window=self.scrollable_bot_settings_content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set); canvas.pack(side="left",fill="both",expand=True)
        ttk.Button(self.bot_settings_tab_frame, text="Save Bot Settings", command=self.config_manager.save_bot_settings_data).pack(side="bottom",pady=10)

    def populate_bot_settings_tab(self):
        settings_content_grid = self.scrollable_bot_settings_content_frame.winfo_children()[0] if self.scrollable_bot_settings_content_frame.winfo_children() else None
        if settings_content_grid:
            for widget_item in settings_content_grid.winfo_children(): widget_item.destroy()
        else:
            settings_content_grid = ttk.Frame(self.scrollable_bot_settings_content_frame, padding=(10,5), style="Tenos.TFrame")
            settings_content_grid.pack(fill="x",expand=True); settings_content_grid.columnconfigure(1,weight=1)
        self.settings_vars.clear(); self.bot_settings_widgets.clear(); current_row_idx = 0
        current_settings_template_dict = self.config_manager.settings_template_factory()
        def create_setting_row_ui(label_txt, widget_class, options_data=None, var_key_name=None, is_llm_model_selector_field=False, is_text_area_field=False, **widget_kwargs):
            nonlocal current_row_idx
            label_ui = ttk.Label(settings_content_grid, text=label_txt + ":", style="Tenos.TLabel")
            label_ui.grid(row=current_row_idx, column=0, sticky="nw" if is_text_area_field else "w", padx=5, pady=5)
            if is_llm_model_selector_field: self.bot_settings_widgets['llm_model_label'] = label_ui
            tk_var_instance = None
            if var_key_name in ['default_guidance', 'upscale_factor', 'default_guidance_sdxl']: tk_var_instance = tk.DoubleVar()
            elif var_key_name in ['steps', 'default_batch_size']: tk_var_instance = tk.IntVar()
            elif var_key_name in ['remix_mode', 'llm_enhancer_enabled']: tk_var_instance = tk.BooleanVar()
            else: tk_var_instance = tk.StringVar()
            current_setting_val = self.config_manager.settings.get(var_key_name)
            if current_setting_val is not None:
                try:
                    if var_key_name == 'llm_provider': tk_var_instance.set(self.provider_display_map.get(current_setting_val, current_setting_val))
                    elif var_key_name == 'display_prompt_preference': tk_var_instance.set(self.display_prompt_map.get(current_setting_val, current_setting_val))
                    else: tk_var_instance.set(current_setting_val)
                except (ValueError, tk.TclError): tk_var_instance.set(current_settings_template_dict.get(var_key_name, ''))
            ui_element = None
            if is_text_area_field:
                ui_element = scrolledtext.ScrolledText(settings_content_grid, wrap=tk.WORD, height=3, width=40, font=("Arial",9),bg=ENTRY_BG_COLOR,fg=TEXT_COLOR_NORMAL,insertbackground=ENTRY_INSERT_COLOR,relief="sunken",borderwidth=1)
                ui_element.insert(tk.END, tk_var_instance.get() if tk_var_instance.get() else "")
            elif widget_class == ttk.Combobox:
                safe_options_list = options_data if isinstance(options_data, list) else []
                if var_key_name == 'llm_provider':
                    disp_opts = [self.provider_display_map.get(k, k) for k in safe_options_list]
                    ui_element = ttk.Combobox(settings_content_grid,textvariable=tk_var_instance,values=disp_opts,state="readonly",width=40,style="Tenos.TCombobox")
                    tk_var_instance.trace_add("write", lambda *a, vk=var_key_name: self.on_llm_provider_change_for_editor(vk))
                elif var_key_name == 'display_prompt_preference':
                    ui_element = ttk.Combobox(settings_content_grid,textvariable=tk_var_instance,values=safe_options_list,state="readonly",width=40,style="Tenos.TCombobox")
                else:
                    curr_str_val = str(current_setting_val) if current_setting_val is not None else ''
                    if curr_str_val and curr_str_val not in safe_options_list and var_key_name != 'llm_model':
                        safe_options_list = [curr_str_val] + [opt for opt in safe_options_list if opt != curr_str_val]
                    ui_element = ttk.Combobox(settings_content_grid,textvariable=tk_var_instance,values=safe_options_list,state="readonly",width=40,style="Tenos.TCombobox")
                    if curr_str_val and curr_str_val not in options_data and var_key_name != 'llm_model': tk_var_instance.set(curr_str_val)
                    elif not curr_str_val and safe_options_list: tk_var_instance.set(safe_options_list[0])
            elif widget_class == ttk.Spinbox: ui_element = ttk.Spinbox(settings_content_grid,textvariable=tk_var_instance,wrap=True,width=10,style="Tenos.TSpinbox",**widget_kwargs)
            elif widget_class == tk.Checkbutton: ui_element = tk.Checkbutton(settings_content_grid,variable=tk_var_instance,bg=FRAME_BG_COLOR,fg=TEXT_COLOR_NORMAL,selectcolor=ENTRY_BG_COLOR,activebackground=FRAME_BG_COLOR,activeforeground=TEXT_COLOR_NORMAL,highlightthickness=0,borderwidth=0)
            else: ui_element = ttk.Entry(settings_content_grid,textvariable=tk_var_instance,width=42,style="Tenos.TEntry")
            ui_element.grid(row=current_row_idx,column=1,sticky="ew",padx=5,pady=5)
            self.settings_vars[var_key_name] = tk_var_instance; self.bot_settings_widgets[var_key_name] = ui_element; current_row_idx +=1
        ttk.Label(settings_content_grid,text="Core Defaults",style=BOLD_TLABEL_STYLE).grid(row=current_row_idx,column=0,columnspan=2,sticky='w',pady=(10,5),padx=5); current_row_idx+=1
        combined_model_names = [f"Flux: {m}" for m in self.available_models] + [f"SDXL: {c}" for c in self.available_checkpoints]
        create_setting_row_ui("Selected Model", ttk.Combobox, combined_model_names, 'selected_model')
        create_setting_row_ui("Selected T5 Clip", ttk.Combobox, self.available_clips_t5, 'selected_t5_clip')
        create_setting_row_ui("Selected Clip-L", ttk.Combobox, self.available_clips_l, 'selected_clip_l')
        create_setting_row_ui("Selected Upscale Model", ttk.Combobox, self.available_upscale_models, 'selected_upscale_model')
        create_setting_row_ui("Selected VAE", ttk.Combobox, self.available_vaes, 'selected_vae')
        style_key_names = sorted([str(k) for k in self.styles_config.keys()])
        create_setting_row_ui("Default Style", ttk.Combobox, style_key_names, 'default_style')
        create_setting_row_ui("Default Steps", ttk.Spinbox, var_key_name='steps', from_=4, to=128, increment=4)
        create_setting_row_ui("Default Guidance (Flux)", ttk.Spinbox, var_key_name='default_guidance', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui("Default Guidance (SDXL)", ttk.Spinbox, var_key_name='default_guidance_sdxl', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui("Default SDXL Negative Prompt", scrolledtext.ScrolledText, var_key_name='default_sdxl_negative_prompt', is_text_area_field=True)
        create_setting_row_ui("Default Batch Size", ttk.Spinbox, var_key_name='default_batch_size', from_=1, to=4, increment=1)
        mp_size_val_options = ["0.25", "0.5", "1", "1.25", "1.5", "1.75", "2", "2.5", "3", "4"]
        create_setting_row_ui("Default MP Target Size (Std Gen)", ttk.Combobox, mp_size_val_options, 'default_mp_size')
        create_setting_row_ui("Default Upscale Factor", ttk.Spinbox, var_key_name='upscale_factor', from_=1.5, to=4.0, increment=0.05, format="%.2f")
        ttk.Label(settings_content_grid,text="Variation Settings",style=BOLD_TLABEL_STYLE).grid(row=current_row_idx,column=0,columnspan=2,sticky='w',pady=(15,5),padx=5); current_row_idx+=1
        create_setting_row_ui("Default Variation Mode", ttk.Combobox, ['weak','strong'], 'default_variation_mode')
        create_setting_row_ui("Variation Remix Mode", tk.Checkbutton, var_key_name='remix_mode')
        ttk.Label(settings_content_grid,text="LLM Enhancer & Display",style=BOLD_TLABEL_STYLE).grid(row=current_row_idx,column=0,columnspan=2,sticky='w',pady=(15,5),padx=5); current_row_idx+=1
        create_setting_row_ui("LLM Prompt Enhancer", tk.Checkbutton, var_key_name='llm_enhancer_enabled')
        llm_provider_keys = list(self.llm_models_config.get('providers',{}).keys())
        create_setting_row_ui("LLM Provider", ttk.Combobox, llm_provider_keys, 'llm_provider')
        initial_llm_provider = self.config_manager.settings.get('llm_provider', llm_provider_keys[0] if llm_provider_keys else 'gemma')
        initial_llm_models_for_provider = self.llm_models_config.get('providers',{}).get(initial_llm_provider,{}).get('models',[])
        initial_llm_provider_display_name = self.provider_display_map.get(initial_llm_provider, initial_llm_provider.capitalize())
        create_setting_row_ui(f"LLM Model ({initial_llm_provider_display_name})", ttk.Combobox, initial_llm_models_for_provider, 'llm_model', is_llm_model_selector_field=True)
        if 'llm_model' in self.settings_vars:
            model_key_for_provider = f"llm_model_{initial_llm_provider}"
            initial_model_val_for_provider = self.config_manager.settings.get(model_key_for_provider, "")
            if initial_model_val_for_provider in initial_llm_models_for_provider: self.settings_vars['llm_model'].set(initial_model_val_for_provider)
            elif initial_llm_models_for_provider: self.settings_vars['llm_model'].set(initial_llm_models_for_provider[0])
            else: self.settings_vars['llm_model'].set("")
        display_prompt_preference_options = [self.display_prompt_map[k_pref_disp] for k_pref_disp in sorted(self.display_prompt_map.keys())]
        create_setting_row_ui("Prompt Display Preference", ttk.Combobox, display_prompt_preference_options, 'display_prompt_preference')
        if self.scrollable_bot_settings_content_frame.winfo_exists(): self.scrollable_bot_settings_content_frame.event_generate("<Configure>")

    def on_llm_provider_change_for_editor(self, var_key_name_that_changed):
        if var_key_name_that_changed != 'llm_provider': return
        selected_provider_display_name = self.settings_vars['llm_provider'].get()
        actual_provider_internal_key = next((k_internal for k_internal, v_display in self.provider_display_map.items() if v_display == selected_provider_display_name), None)
        if not actual_provider_internal_key: actual_provider_internal_key = selected_provider_display_name.lower()
        llm_model_combobox_widget = self.bot_settings_widgets.get('llm_model')
        if not llm_model_combobox_widget: return
        new_llm_model_options = self.llm_models_config.get('providers', {}).get(actual_provider_internal_key, {}).get('models', [])
        llm_model_combobox_widget['values'] = new_llm_model_options
        model_setting_key_for_new_provider = f"llm_model_{actual_provider_internal_key}"
        current_model_for_new_provider = self.config_manager.settings.get(model_setting_key_for_new_provider, "")
        if current_model_for_new_provider in new_llm_model_options: self.settings_vars['llm_model'].set(current_model_for_new_provider)
        elif new_llm_model_options: self.settings_vars['llm_model'].set(new_llm_model_options[0])
        else: self.settings_vars['llm_model'].set("")
        llm_model_label_widget = self.bot_settings_widgets.get('llm_model_label')
        if llm_model_label_widget:
            new_provider_display = self.provider_display_map.get(actual_provider_internal_key, actual_provider_internal_key.capitalize())
            llm_model_label_widget.config(text=f"LLM Model ({new_provider_display}):")

    def load_available_files(self):
        self.available_models = []; self.available_checkpoints = []; self.available_clips_t5 = []; self.available_clips_l = []; self.available_loras = ["None"]; self.available_upscale_models = ["None"]; self.available_vaes = ["None"]
        try:
            if os.path.exists(MODELS_LIST_FILE_NAME):
                with open(MODELS_LIST_FILE_NAME,'r') as f_ml: models_data = json.load(f_ml)
                if isinstance(models_data,dict): self.available_models = sorted(list(set(m_name for model_type_list in [models_data.get(type_key,[]) for type_key in ['safetensors','sft','gguf']] for m_name in model_type_list if isinstance(m_name,str))),key=str.lower)
        except Exception: pass
        try:
            if os.path.exists(CHECKPOINTS_LIST_FILE_NAME):
                with open(CHECKPOINTS_LIST_FILE_NAME,'r') as f_cp: checkpoints_data = json.load(f_cp)
                if isinstance(checkpoints_data,dict):
                    sdxl_chkpts = checkpoints_data.get('checkpoints',[]) if isinstance(checkpoints_data.get('checkpoints'),list) else []
                    if not sdxl_chkpts:
                        for k_cp,v_cp_list in checkpoints_data.items():
                            if isinstance(v_cp_list,list) and k_cp != 'favorites': sdxl_chkpts.extend(c_name for c_name in v_cp_list if isinstance(c_name,str))
                    self.available_checkpoints = sorted(list(set(sdxl_chkpts)),key=str.lower)
        except Exception: pass
        try:
            if os.path.exists(CLIP_LIST_FILE_NAME):
                with open(CLIP_LIST_FILE_NAME,'r') as f_cl: clips_data = json.load(f_cl)
                if isinstance(clips_data,dict):
                    self.available_clips_t5 = sorted([c_name for c_name in clips_data.get('t5',[]) if isinstance(c_name,str)],key=str.lower)
                    self.available_clips_l = sorted([c_name for c_name in clips_data.get('clip_L',[]) if isinstance(c_name,str)],key=str.lower)
        except Exception: pass
        lora_folder = self.config_manager.config.get('LORAS',{}).get('LORA_FILES',''); upscale_folder = self.config_manager.config.get('MODELS',{}).get('UPSCALE_MODELS',''); vae_folder = self.config_manager.config.get('MODELS',{}).get('VAE_MODELS','')
        if lora_folder and os.path.isdir(lora_folder):
            try: self.available_loras.extend(sorted([f_name for f_name in os.listdir(lora_folder) if f_name.lower().endswith(('.safetensors','.pt','.ckpt'))],key=str.lower))
            except Exception: pass
        if upscale_folder and os.path.isdir(upscale_folder):
            try: self.available_upscale_models.extend(sorted([f_name for f_name in os.listdir(upscale_folder) if f_name.lower().endswith(('.pth','.onnx','.safetensors','.pt','.bin'))],key=str.lower))
            except Exception: pass
        if vae_folder and os.path.isdir(vae_folder):
            try: self.available_vaes.extend(sorted([f_name for f_name in os.listdir(vae_folder) if f_name.lower().endswith(('.pt','.safetensors','.pth','.ckpt'))],key=str.lower))
            except Exception: pass

    def _debounce_canvas_configure(self, canvas_widget, event=None):
        if hasattr(canvas_widget, '_debounce_id_config_editor'):
            try: self.master.after_cancel(canvas_widget._debounce_id_config_editor)
            except (tk.TclError, AttributeError): pass
        try: canvas_widget._debounce_id_config_editor = self.master.after(50, lambda c=canvas_widget: self._safe_canvas_bbox_configure(c))
        except AttributeError: pass

    def _safe_canvas_bbox_configure(self, canvas_widget):
        try:
            if canvas_widget.winfo_exists():
                canvas_widget.update_idletasks(); canvas_widget.configure(scrollregion=canvas_widget.bbox("all"))
                if hasattr(canvas_widget,'associated_scrollbar'):
                    scrollbar = canvas_widget.associated_scrollbar
                    if scrollbar and scrollbar.winfo_exists():
                        bbox = canvas_widget.bbox("all"); content_h = bbox[3]-bbox[1] if bbox else 0
                        if content_h <= canvas_widget.winfo_height():
                            if scrollbar.winfo_ismapped(): scrollbar.pack_forget()
                        else:
                            if not scrollbar.winfo_ismapped(): scrollbar.pack(side="right",fill="y")
        except tk.TclError: pass
        except Exception: pass

    def _process_gui_updates_loop(self):
        log_msgs_batch = []; max_logs = 50; current_logs = 0
        try:
            while current_logs < max_logs: log_msgs_batch.append(self.log_queue.get_nowait()); current_logs +=1
        except queue.Empty: pass
        except Exception: pass
        if log_msgs_batch:
            try:
                if hasattr(self,'log_display') and self.log_display.winfo_exists():
                    self.log_display.config(state='normal')
                    for src_disp, line_disp in log_msgs_batch: self.log_display.insert(tk.END, line_disp, (src_disp if src_disp in ["stdout","stderr","info","worker"] else "stdout",))
                    self.log_display.see(tk.END); self.log_display.config(state='disabled')
            except tk.TclError: pass
            except Exception: pass
        try:
            worker_status_update = self.worker_queue.get_nowait()
            if worker_status_update.get("type") == "task_complete":
                task_name_done = worker_status_update.get("task_name","Task"); success_status = worker_status_update.get("success",False); message_details = worker_status_update.get("message","No details.")
                if success_status:
                    if task_name_done == "Refreshing LLMs":
                        self.log_queue.put(("info", "--- LLM models reloaded, updating UI. ---\n"))
                        self.llm_models_config = load_llm_models_config_util()
                        self.config_manager.load_bot_settings_data(self.llm_models_config)
                        self.populate_bot_settings_tab()
                    silent_showinfo(f"{task_name_done} Complete", message_details, parent=self.master)
                    if task_name_done == "Scanning Files":
                        self.load_available_files(); self.populate_bot_settings_tab()
                        if hasattr(self, 'favorites_tab_manager'): self.favorites_tab_manager.populate_all_favorites_sub_tabs()
                else: silent_showerror(f"{task_name_done} Failed", message_details, parent=self.master)
        except queue.Empty: pass
        except Exception: pass
        if self.master.winfo_exists(): self.master.after(100, self._process_gui_updates_loop)

    def _check_settings_file_for_changes(self):
        try:
            if os.path.exists(SETTINGS_FILE_NAME):
                current_mtime = os.path.getmtime(SETTINGS_FILE_NAME)
                if self.config_manager.settings_last_mtime != 0 and abs(current_mtime - self.config_manager.settings_last_mtime) > 1e-6:
                    self.log_queue.put(("info", "--- Detected external change in settings.json. Reloading automatically. ---\n"))
                    self.config_manager.load_bot_settings_data(self.llm_models_config)
                    self.populate_bot_settings_tab()
            if self.master.winfo_exists(): self.master.after(2000, self._check_settings_file_for_changes)
        except FileNotFoundError:
             if self.master.winfo_exists(): self.master.after(2000, self._check_settings_file_for_changes)
        except Exception:
            if self.master.winfo_exists(): self.master.after(5000, self._check_settings_file_for_changes)

    def run_worker_task_on_editor(self, task_function_to_run, task_display_name_str):
        if self.worker_thread and self.worker_thread.is_alive(): silent_showwarning("Busy","Background task running.",parent=self.master); return
        self.log_queue.put(("info",f"--- Starting {task_display_name_str} ---\n"))
        while not self.worker_queue.empty():
            try: self.worker_queue.get_nowait()
            except queue.Empty: break
        self.worker_thread = threading.Thread(target=self._worker_thread_target_for_editor, args=(task_function_to_run, task_display_name_str, (), {}), daemon=True)
        self.worker_thread.start()

    def _worker_thread_target_for_editor(self, task_func_target, task_name_ui, args_for_task, kwargs_for_task):
        success_flag_worker = False; message_str_worker = f"{task_name_ui} failed."
        try:
            result_message_worker = task_func_target(*args_for_task, **kwargs_for_task)
            success_flag_worker = True; message_str_worker = result_message_worker if isinstance(result_message_worker, str) else f"{task_name_ui} completed."
        except Exception as e_task_exec: success_flag_worker = False; message_str_worker = f"{task_name_ui} failed: {e_task_exec}"
        self.worker_queue.put({"type":"task_complete","task_name":task_name_ui,"success":success_flag_worker,"message":message_str_worker})
        self.log_queue.put(("info",f"--- Finished {task_name_ui} (Success: {success_flag_worker}) ---\n"))

    def _worker_install_custom_nodes(self):
        custom_nodes_path_str = self.config_manager.config.get('NODES',{}).get('CUSTOM_NODES')
        if not (custom_nodes_path_str and isinstance(custom_nodes_path_str,str) and os.path.isdir(custom_nodes_path_str)):
            msg_err = "Custom Nodes path not set/invalid in Main Config."; self.log_queue.put(("stderr", f"Install Custom Nodes Error: {msg_err}\n")); return msg_err
        repositories_to_install = ["https://github.com/rgthree/rgthree-comfy.git", "https://github.com/ssitu/ComfyUI_UltimateSDUpscale.git", "https://github.com/jamesWalker55/comfyui-various.git", "https://github.com/city96/ComfyUI-GGUF.git", "https://github.com/tsogzark/ComfyUI-load-image-from-url.git","https://github.com/BobsBlazed/Bobs_Latent_Optimizer.git","https://github.com/Tenos-ai/Tenos-Resize-to-1-M-Pixels.git"]
        installation_results = []; errors_encountered_install = False
        for idx, repo_url_str in enumerate(repositories_to_install):
            repo_name_short = repo_url_str.split('/')[-1].replace('.git',''); repo_target_path = os.path.join(custom_nodes_path_str, repo_name_short)
            current_action_str = "Updating" if os.path.exists(repo_target_path) else "Cloning"
            self.log_queue.put(("worker", f"{current_action_str} {repo_name_short} ({idx+1}/{len(repositories_to_install)})...\n"))
            try:
                if not os.path.exists(repo_target_path): git.Repo.clone_from(repo_url_str, repo_target_path, progress=ProgressPrinter(repo_name_short, self.log_queue)); installation_results.append(f"Cloned {repo_name_short}: Success")
                else: git.Repo(repo_target_path).remotes.origin.pull(progress=ProgressPrinter(repo_name_short, self.log_queue)); installation_results.append(f"Updated {repo_name_short}: Success")
            except git.GitCommandError as e_git_cmd: error_detail_git = e_git_cmd.stderr.strip() if e_git_cmd.stderr else str(e_git_cmd); installation_results.append(f"{current_action_str} {repo_name_short}: FAILED (Git: {error_detail_git})"); errors_encountered_install = True; self.log_queue.put(("stderr",f"Git Command Error {repo_name_short}: {error_detail_git}\n"))
            except Exception as e_other_install: installation_results.append(f"{current_action_str} {repo_name_short}: FAILED ({type(e_other_install).__name__}: {str(e_other_install)})"); errors_encountered_install = True; self.log_queue.put(("stderr",f"Error {current_action_str.lower()}ing {repo_name_short}: {str(e_other_install)}\n"))
        local_nodes_source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"nodes")
        if os.path.isdir(local_nodes_source_dir):
            self.log_queue.put(("worker",f"Copying local nodes from '{local_nodes_source_dir}' to '{custom_nodes_path_str}'...\n"))
            try: shutil.copytree(local_nodes_source_dir,custom_nodes_path_str,dirs_exist_ok=True); installation_results.append("Copied local nodes: Success")
            except Exception as e_copy_local: installation_results.append(f"Copied local nodes: FAILED ({type(e_copy_local).__name__}: {str(e_copy_local)})"); errors_encountered_install = True; self.log_queue.put(("stderr",f"Error copying local nodes: {str(e_copy_local)}\n"))
        else: installation_results.append("Copy local nodes: Skipped (local 'nodes' folder not found)")
        summary_prefix_str = "Custom Node Installation Succeeded" if not errors_encountered_install else "Custom Node Installation Completed with Errors"
        return f"{summary_prefix_str}:\n\n" + "\n".join(installation_results)

    def _worker_scan_models_clips_checkpoints(self):
        scan_errors_list = []
        try: import model_scanner
        except ImportError: err_msg = "Scan Error: model_scanner.py module not found."; self.log_queue.put(("stderr", f"{err_msg}\n")); return err_msg
        current_main_config = self.config_manager.config
        paths_map = {"Flux Models": current_main_config.get('MODELS',{}).get('MODEL_FILES'), "CLIP Files": current_main_config.get('CLIP',{}).get('CLIP_FILES'), "SDXL Checkpoints": current_main_config.get('MODELS',{}).get('CHECKPOINTS_FOLDER')}
        valid_paths_exist = any(pth_val and isinstance(pth_val,str) and os.path.isdir(pth_val) for pth_val in paths_map.values())
        if not valid_paths_exist: msg = "No valid paths configured for scanning."; self.log_queue.put(("stderr",f"{msg}\n")); return msg
        try:
            if paths_map["Flux Models"] and os.path.isdir(paths_map["Flux Models"]): self.log_queue.put(("worker","Scanning Flux models...\n")); model_scanner.update_models_list(CONFIG_FILE_NAME,MODELS_LIST_FILE_NAME)
            if paths_map["CLIP Files"] and os.path.isdir(paths_map["CLIP Files"]): self.log_queue.put(("worker","Scanning CLIPs...\n")); model_scanner.scan_clip_files(CONFIG_FILE_NAME,CLIP_LIST_FILE_NAME)
            if paths_map["SDXL Checkpoints"] and os.path.isdir(paths_map["SDXL Checkpoints"]): self.log_queue.put(("worker","Scanning SDXL checkpoints...\n")); model_scanner.update_checkpoints_list(CONFIG_FILE_NAME,CHECKPOINTS_LIST_FILE_NAME)
        except Exception as e_scan_call: scan_errors_list.append(f"Error during scan call: {e_scan_call}"); self.log_queue.put(("stderr",f"Scan Call Error: {e_scan_call}\n")); traceback.print_exc()
        if scan_errors_list: return "File Scanning Completed with Issues:\n"+"\n".join(scan_errors_list)
        return "File scanning finished. Lists updated. \n(UI dropdowns will refresh after this message)."

    def _worker_update_llm_models_list(self):
        """Worker task to fetch latest LLM models and update llm_models.json."""
        keys = self.config_manager.config.get('LLM_ENHANCER', {})
        openai_key = keys.get('OPENAI_API_KEY')
        gemini_key = keys.get('GEMINI_API_KEY')
        groq_key = keys.get('GROQ_API_KEY')
        updated_models_data = load_llm_models_config_util()
        results_log = []
        
        if openai_key:
            try:
                headers = {'Authorization': f'Bearer {openai_key}'}
                response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
                response.raise_for_status()
                models = response.json().get('data', [])
                
                chat_model_prefixes = ['gpt-4', 'gpt-3.5', 'o1', 'o3', 'o4']
                
                openai_model_ids = sorted([
                    m['id'] for m in models 
                    if any(m['id'].startswith(p) for p in chat_model_prefixes)
                ])
                
                updated_models_data['providers']['openai']['models'] = openai_model_ids
                results_log.append(f"OpenAI: Found {len(openai_model_ids)} chat models.")
            except Exception as e:
                msg = f"Failed to fetch OpenAI models: {e}"
                results_log.append(f"OpenAI: {msg}"); self.log_queue.put(("stderr", msg + "\n"))
        else: results_log.append("OpenAI: Skipped (no API key).")

        if groq_key:
            try:
                headers = {'Authorization': f'Bearer {groq_key}'}
                response = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=10)
                response.raise_for_status()
                models = response.json().get('data', [])
                # Groq's API currently only serves chat models, so we can list all of them.
                groq_model_ids = sorted([m['id'] for m in models])
                updated_models_data['providers']['groq']['models'] = groq_model_ids
                results_log.append(f"Groq: Found {len(groq_model_ids)} chat models.")
            except Exception as e:
                msg = f"Failed to fetch Groq models: {e}"
                results_log.append(f"Groq: {msg}"); self.log_queue.put(("stderr", msg + "\n"))
        else: results_log.append("Groq: Skipped (no API key).")

        if gemini_key:
            try:
                response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}", timeout=10)
                response.raise_for_status()
                models = response.json().get('models', [])
                gemini_model_ids = sorted([
                    m['name'].replace('models/', '') for m in models 
                    if any('generateContent' in method for method in m.get('supportedGenerationMethods', []))
                ])
                updated_models_data['providers']['gemini']['models'] = gemini_model_ids
                results_log.append(f"Gemini: Found {len(gemini_model_ids)} chat models.")
            except Exception as e:
                msg = f"Failed to fetch Gemini models: {e}"
                results_log.append(f"Gemini: {msg}"); self.log_queue.put(("stderr", msg + "\n"))
        else: results_log.append("Gemini: Skipped (no API key).")

        if save_json_config(LLM_MODELS_FILE_NAME, updated_models_data, "LLM models config"):
            return "LLM Models list updated successfully.\n\n" + "\n".join(results_log)
        else:
            raise Exception("Failed to save the updated llm_models.json file.")

    def show_about_dialog(self):
        editor_title = self.master.title(); version_str = editor_title.split('v')[-1].strip() if 'v' in editor_title else "Unknown"
        about_message = (f"Tenos.ai Configuration Tool\n\nVersion: {version_str}\n\nConfigure paths, settings, styles, and favorites for the Tenos.ai Discord bot.\nEnsure ComfyUI paths in 'Main Config' are correct.\nRestart the bot via 'Bot Control' tab after making significant changes.")
        silent_showinfo("About Tenos.ai Configurator", about_message, parent=self.master)

    def save_all_configurations_from_menu(self):
        if not silent_askyesno("Confirm Save All", "Save changes in ALL tabs?", parent=self.master): return
        self.config_manager.save_main_config_data()
        self.llm_prompts_tab_manager.save_llm_prompts_data()
        self.lora_styles_tab_manager.save_current_styles_config()
        self.favorites_tab_manager.save_all_favorites_data()
        self.config_manager.save_bot_settings_data()
        self.admin_control_tab_manager._save_blocklist() # <-- Use specific save method
        silent_showinfo("Save All Triggered", "All save operations triggered. Check console/messages for status.", parent=self.master)

    def on_closing_main_window(self):
        if self.bot_control_tab_manager.is_bot_script_running():
             if silent_askyesno("Exit Confirmation", "Bot script running. Stop bot and exit configurator?", parent=self.master):
                  self.bot_control_tab_manager.stop_bot_script()
                  if self.master.winfo_exists(): self.master.after(1000, self._perform_destroy_main_window)
             else: return
        else: self._perform_destroy_main_window()

    def _perform_destroy_main_window(self):
        self.stop_readers.set()
        for thread_item_cleanup in self.reader_threads:
            if thread_item_cleanup.is_alive(): thread_item_cleanup.join(timeout=0.5)
        self.admin_control_tab_manager.save_user_cache_on_exit()
        if self.master.winfo_exists(): self.master.destroy()

class ProgressPrinter(git.RemoteProgress):
    def __init__(self, repo_name_str_param, log_queue_ref_param):
        super().__init__(); self.repo_name = repo_name_str_param; self.log_queue = log_queue_ref_param
    def update(self, op_code_val_progress, cur_count_val_progress, max_count_val_progress=None, message_str_progress=''):
        output_str_progress = f"Git ({self.repo_name}): {message_str_progress.splitlines()[0]}"
        self.log_queue.put(("worker", output_str_progress + "\n"))

if __name__ == "__main__":
    try:
        root_tk_window = tk.Tk()
        app_main_instance = ConfigEditor(root_tk_window)
        root_tk_window.mainloop()
    except Exception as main_app_execution_error:
        traceback.print_exc()
        try:
            error_dialog_fallback_root = tk.Tk(); error_dialog_fallback_root.withdraw()
            messagebox.showerror("Fatal Error - Config Editor Application", f"Could not start Config Editor application:\n{main_app_execution_error}\n\nCheck console output for detailed traceback.", parent=None)
            error_dialog_fallback_root.destroy()
        except Exception: pass
