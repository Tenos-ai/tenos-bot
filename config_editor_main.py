# --- START OF FILE config_editor_main.py ---
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import os
import json
import traceback
import threading
import queue
import platform
import subprocess
import psutil
import requests
import re
import sys
from datetime import datetime
import zipfile
import tempfile

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
from utils.update_state import UpdateState
from utils.versioning import normalise_tag, is_remote_version_newer
from version_info import APP_VERSION

class ConfigEditor:
    def __init__(self, master_tk_root):
        self.master = master_tk_root
        self.master.title("Tenos.ai Configurator v1.2.4")
        self.master.geometry("850x950")
        self.master.configure(bg=BACKGROUND_COLOR)

        self.style = ttk.Style()
        self._configure_main_editor_style()

        self.bot_process = None
        self.log_queue = queue.Queue()
        self.stop_readers = threading.Event()
        self.reader_threads = []
        self.worker_queue = queue.Queue()
        self.worker_thread = None
        self.config_vars = {}
        self.settings_vars = {}
        self.bot_settings_widgets = {}
        self.log_display = None

        self.app_base_dir = os.path.dirname(os.path.abspath(__file__))
        self.current_version = APP_VERSION
        self.update_state = UpdateState.load(base_dir=self.app_base_dir)
        self._reconcile_update_state()

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

        self.provider_display_map = { k: v.get("display_name", k.capitalize()) for k, v in self.llm_models_config.get("providers", {}).items() }
        self.display_prompt_map = { "enhanced": "Show Enhanced Prompt ✨", "original": "Show Original Prompt ✍️" }

        self._create_menu_bar()
        self._create_restart_note_label()

        self.notebook = ttk.Notebook(self.master, style="Tenos.TNotebook")
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self._create_main_config_tab_structure()
        self.admin_control_tab_manager = AdminControlTab(self, self.notebook)
        self._create_bot_settings_tab_structure()
        self.lora_styles_tab_manager = LoraStylesTab(self, self.notebook)
        self.favorites_tab_manager = FavoritesTab(self, self.notebook)
        self.llm_prompts_tab_manager = LLMPromptsTab(self, self.notebook)
        self.bot_control_tab_manager = BotControlTab(self, self.notebook)

        self.refresh_all_ui_tabs()

        if self.master.winfo_exists():
            self.master.after(100, self._process_gui_updates_loop)
            self.master.after(200, self._check_for_first_run)
            self.master.after(500, self._check_for_startup_update)
            self.master.after(2000, self._check_settings_file_for_changes)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing_main_window)
        
    def refresh_all_ui_tabs(self):
        self.load_available_files()
        self.populate_main_config_sub_tabs()
        self.admin_control_tab_manager.populate_admin_tab()
        self.populate_bot_settings_tab()
        self.lora_styles_tab_manager.populate_lora_styles_tab()
        self.favorites_tab_manager.populate_all_favorites_sub_tabs()
        self.llm_prompts_tab_manager.load_and_populate_llm_prompts()

    def _reconcile_update_state(self):
        try:
            pending_tag = self.update_state.pending_tag
            last_success = self.update_state.last_successful_tag

            normalised_current = normalise_tag(self.current_version)
            normalised_pending = normalise_tag(pending_tag)
            normalised_success = normalise_tag(last_success)

            if pending_tag and normalised_pending == normalised_current:
                self.log_queue.put(("worker", f"Pending update {pending_tag} matches running version; marking as applied.\n"))
                self.update_state.mark_success(pending_tag, base_dir=self.app_base_dir)
                return

            if normalised_success is None and normalised_current is not None:
                self.log_queue.put(("worker", f"Recording current version {self.current_version} as baseline update state.\n"))
                self.update_state.mark_success(self.current_version, base_dir=self.app_base_dir)
        except Exception:
            # Update bookkeeping should never block the UI. Fail silently but log in debug console.
            traceback.print_exc()

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
        file_menu.add_command(label="Export Config & Settings", command=self.export_config_and_settings)
        file_menu.add_separator(background=BORDER_COLOR)
        file_menu.add_command(label="Exit", command=self.on_closing_main_window)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        tools_menu = tk.Menu(self.menu_bar, tearoff=0, bg=WIDGET_BG, fg=TEXT_COLOR_NORMAL, relief="flat", activebackground=SELECT_BG_COLOR, activeforeground=SELECT_FG_COLOR)
        tools_menu.add_command(label="Update Application", command=lambda: self.run_worker_task_on_editor(self._worker_update_application, "Updating Application"))
        tools_menu.add_separator(background=BORDER_COLOR)
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
        self.app_settings_tab_frame = ttk.Frame(self.main_config_notebook, padding="10", style="Tenos.TFrame")
        
        self.main_config_notebook.add(self.paths_tab_frame, text=" File Paths ")
        self.main_config_notebook.add(self.endpoints_tab_frame, text=" Endpoint URLs ")
        self.main_config_notebook.add(self.api_keys_tab_frame, text=" API Keys ")
        self.main_config_notebook.add(self.app_settings_tab_frame, text=" App Settings ")
        
        ttk.Button(self.main_config_tab_frame, text="Save Main Config", command=self.config_manager.save_main_config_data).pack(side="bottom", pady=10)
        
    def populate_main_config_sub_tabs(self):
        self.config_vars.clear()
        
        for parent_frame in [self.paths_tab_frame, self.endpoints_tab_frame, self.api_keys_tab_frame, self.app_settings_tab_frame]:
            for widget in parent_frame.winfo_children():
                widget.destroy()

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

        for section in ["OUTPUTS", "MODELS", "CLIP", "LORAS", "NODES"]:
            ttk.Label(self.paths_tab_frame, text=section.replace("_", " ").title(), style=BOLD_TLABEL_STYLE).pack(fill=tk.X, pady=(10,5))
            for key in self.config_manager.config_template_definition.get(section, {}):
                create_config_row(self.paths_tab_frame, section, key, is_path=True)
                
        for section in ["COMFYUI_API", "BOT_INTERNAL_API"]:
            ttk.Label(self.endpoints_tab_frame, text=section.replace("_", " ").title(), style=BOLD_TLABEL_STYLE).pack(fill=tk.X, pady=(10,5))
            for key in self.config_manager.config_template_definition.get(section, {}):
                create_config_row(self.endpoints_tab_frame, section, key, is_port=(key=="PORT"))

        for section in ["BOT_API", "LLM_ENHANCER"]:
            ttk.Label(self.api_keys_tab_frame, text=section.replace("_", " ").title(), style=BOLD_TLABEL_STYLE).pack(fill=tk.X, pady=(10,5))
            for key in self.config_manager.config_template_definition.get(section, {}):
                create_config_row(self.api_keys_tab_frame, section, key)

        app_settings = self.config_manager.config.get("APP_SETTINGS", {})
        auto_update_var = tk.BooleanVar(value=app_settings.get("AUTO_UPDATE_ON_STARTUP", False))
        self.config_vars["APP_SETTINGS.AUTO_UPDATE_ON_STARTUP"] = auto_update_var
        auto_update_check = ttk.Checkbutton(self.app_settings_tab_frame, 
                                           text="Automatically check for updates on startup", 
                                           variable=auto_update_var,
                                           style="Tenos.TCheckbutton")
        auto_update_check.pack(anchor='w', padx=5, pady=5)
        # Add import/export buttons for config and settings in the App Settings tab
        ttk.Button(self.app_settings_tab_frame, text="Import Config & Settings", command=self.import_config_and_settings).pack(anchor='w', padx=5, pady=5)
        ttk.Button(self.app_settings_tab_frame, text="Export Config & Settings", command=self.export_config_and_settings).pack(anchor='w', padx=5, pady=5)

    def _browse_folder_for_main_config(self, section_name, key_name):
        var_lookup_key = f"{section_name}.{key_name}"
        initial_dir_val = self.config_vars[var_lookup_key].get() if var_lookup_key in self.config_vars else None
        selected_folder_path = browse_folder_dialog(parent=self.master, initialdir=initial_dir_val or os.getcwd(), title=f"Select Folder for {key_name}")
        if selected_folder_path and var_lookup_key in self.config_vars: self.config_vars[var_lookup_key].set(selected_folder_path)

    def _create_bot_settings_tab_structure(self):
        self.bot_settings_tab_frame = ttk.Frame(self.notebook, padding="5", style="Tenos.TFrame")
        self.notebook.add(self.bot_settings_tab_frame, text=' Bot Settings ')
        
        self.bot_settings_notebook = ttk.Notebook(self.bot_settings_tab_frame, style="Tenos.TNotebook")
        self.bot_settings_notebook.pack(expand=True, fill="both", padx=0, pady=5)

        self.bot_settings_general_tab = ttk.Frame(self.bot_settings_notebook, padding="5", style="Tenos.TFrame")
        self.bot_settings_flux_tab = ttk.Frame(self.bot_settings_notebook, padding="5", style="Tenos.TFrame")
        self.bot_settings_sdxl_tab = ttk.Frame(self.bot_settings_notebook, padding="5", style="Tenos.TFrame")
        self.bot_settings_kontext_tab = ttk.Frame(self.bot_settings_notebook, padding="5", style="Tenos.TFrame")
        self.bot_settings_llm_tab = ttk.Frame(self.bot_settings_notebook, padding="5", style="Tenos.TFrame")
        
        self.bot_settings_notebook.add(self.bot_settings_general_tab, text=" General ")
        self.bot_settings_notebook.add(self.bot_settings_flux_tab, text=" Flux ")
        self.bot_settings_notebook.add(self.bot_settings_sdxl_tab, text=" SDXL ")
        self.bot_settings_notebook.add(self.bot_settings_kontext_tab, text=" Kontext ")
        self.bot_settings_notebook.add(self.bot_settings_llm_tab, text=" LLM ")

        # Create the scrollable content frames for each sub-tab once
        self.general_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_general_tab)
        self.flux_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_flux_tab)
        self.sdxl_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_sdxl_tab)
        self.kontext_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_kontext_tab)
        self.llm_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_llm_tab)

        buttons_frame = ttk.Frame(self.bot_settings_tab_frame, style="Tenos.TFrame")
        buttons_frame.pack(side="bottom", fill="x", pady=(10,0), padx=5)
        ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_bot_settings_to_defaults).pack(side="left", padx=(0,5))
        ttk.Button(buttons_frame, text="Save Bot Settings", command=self.config_manager.save_bot_settings_data).pack(side="left")

    def _create_scrollable_sub_tab_frame(self, parent_tab_frame):
        for widget_child in parent_tab_frame.winfo_children():
            widget_child.destroy()
        container_frame = ttk.Frame(parent_tab_frame, style="Tenos.TFrame")
        container_frame.pack(fill="both", expand=True)
        canvas_widget = tk.Canvas(container_frame, bg=CANVAS_BG_COLOR, highlightthickness=0)
        scrollbar_widget = ttk.Scrollbar(container_frame, orient="vertical", command=canvas_widget.yview, style="Tenos.Vertical.TScrollbar")
        canvas_widget.associated_scrollbar = scrollbar_widget
        scrollable_content_frame = ttk.Frame(canvas_widget, style="Tenos.TFrame")
        scrollable_content_frame.bind(
            "<Configure>", lambda event, c=canvas_widget: self._debounce_canvas_configure(c, event)
        )
        canvas_widget.create_window((0, 0), window=scrollable_content_frame, anchor="nw")
        canvas_widget.configure(yscrollcommand=scrollbar_widget.set)
        canvas_widget.pack(side="left", fill="both", expand=True)
        return scrollable_content_frame
        
    def populate_bot_settings_tab(self):
        self.settings_vars.clear()
        self.bot_settings_widgets.clear()
        current_settings_template_dict = self.config_manager.settings_template_factory()

        # Clear existing widgets from all content frames before repopulating
        for frame in [self.general_settings_content_frame, self.flux_settings_content_frame, self.sdxl_settings_content_frame, self.kontext_settings_content_frame, self.llm_settings_content_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        def create_setting_row_ui(parent_frame, label_txt, widget_class, options_data=None, var_key_name=None, is_llm_model_selector_field=False, is_text_area_field=False, **widget_kwargs):
            container = ttk.Frame(parent_frame, style="Tenos.TFrame")
            container.pack(fill='x', padx=5, pady=2)
            label_ui = ttk.Label(container, text=label_txt + ":", style="Tenos.TLabel", width=25)
            label_ui.pack(side='left', anchor='w', padx=(0, 10))
            if is_llm_model_selector_field: self.bot_settings_widgets['llm_model_label'] = label_ui
            
            tk_var_instance = None
            if var_key_name in ['default_guidance', 'upscale_factor', 'default_guidance_sdxl', 'default_mp_size', 'kontext_guidance', 'kontext_mp_size']: tk_var_instance = tk.DoubleVar()
            elif var_key_name in ['steps', 'sdxl_steps', 'default_batch_size', 'kontext_steps', 'variation_batch_size']: tk_var_instance = tk.IntVar()
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
                ui_element = scrolledtext.ScrolledText(container, wrap=tk.WORD, height=3, width=40, font=("Arial",9),bg=ENTRY_BG_COLOR,fg=TEXT_COLOR_NORMAL,insertbackground=ENTRY_INSERT_COLOR,relief="sunken",borderwidth=1)
                ui_element.insert(tk.END, tk_var_instance.get() if tk_var_instance.get() else "")
            elif widget_class == ttk.Combobox:
                safe_options_list = options_data if isinstance(options_data, list) else []
                curr_str_val = str(current_setting_val) if current_setting_val is not None else ''
                if curr_str_val and curr_str_val not in safe_options_list and var_key_name != 'llm_model':
                    safe_options_list = [curr_str_val] + [opt for opt in safe_options_list if opt != curr_str_val]
                
                ui_element = ttk.Combobox(container, textvariable=tk_var_instance, values=safe_options_list, state="readonly", width=40, style="Tenos.TCombobox")
                
                if var_key_name == 'llm_provider':
                    disp_opts = [self.provider_display_map.get(k, k) for k in safe_options_list]
                    ui_element.config(values=disp_opts)
                    tk_var_instance.trace_add("write", lambda *a, vk=var_key_name: self.on_llm_provider_change_for_editor(vk))
                elif var_key_name == 'display_prompt_preference':
                    disp_opts = [self.display_prompt_map.get(k, k) for k in sorted(self.display_prompt_map.keys())]
                    ui_element.config(values=disp_opts)
                
                if curr_str_val and curr_str_val not in options_data and var_key_name != 'llm_model': tk_var_instance.set(curr_str_val)
                elif not curr_str_val and safe_options_list: tk_var_instance.set(safe_options_list[0])
            elif widget_class == ttk.Spinbox: ui_element = ttk.Spinbox(container, textvariable=tk_var_instance, wrap=True, width=12, style="Tenos.TSpinbox", **widget_kwargs)
            elif widget_class == ttk.Checkbutton: ui_element = ttk.Checkbutton(container, variable=tk_var_instance, style="Tenos.TCheckbutton")
            else: ui_element = ttk.Entry(container, textvariable=tk_var_instance, width=42, style="Tenos.TEntry")
            
            ui_element.pack(side='left', fill='x', expand=True)
            self.settings_vars[var_key_name] = tk_var_instance
            self.bot_settings_widgets[var_key_name] = ui_element

        # --- General Tab ---
        create_setting_row_ui(self.general_settings_content_frame, "Selected Model", ttk.Combobox, [f"Flux: {m}" for m in self.available_models] + [f"SDXL: {c}" for c in self.available_checkpoints], 'selected_model')
        create_setting_row_ui(self.general_settings_content_frame, "Selected T5 Clip", ttk.Combobox, self.available_clips_t5, 'selected_t5_clip')
        create_setting_row_ui(self.general_settings_content_frame, "Selected Clip-L", ttk.Combobox, self.available_clips_l, 'selected_clip_l')
        create_setting_row_ui(self.general_settings_content_frame, "Selected Upscale Model", ttk.Combobox, self.available_upscale_models, 'selected_upscale_model')
        create_setting_row_ui(self.general_settings_content_frame, "Selected VAE", ttk.Combobox, self.available_vaes, 'selected_vae')
        ttk.Separator(self.general_settings_content_frame, orient='horizontal').pack(fill='x', pady=10)
        create_setting_row_ui(self.general_settings_content_frame, "Default Variation Mode", ttk.Combobox, ['weak','strong'], 'default_variation_mode')
        create_setting_row_ui(self.general_settings_content_frame, "Variation Remix Mode", ttk.Checkbutton, var_key_name='remix_mode')
        create_setting_row_ui(self.general_settings_content_frame, "Default Batch Size (/gen)", ttk.Spinbox, var_key_name='default_batch_size', from_=1, to=4, increment=1)
        create_setting_row_ui(self.general_settings_content_frame, "Default Batch Size (Vary)", ttk.Spinbox, var_key_name='variation_batch_size', from_=1, to=4, increment=1)
        create_setting_row_ui(self.general_settings_content_frame, "Default Upscale Factor", ttk.Spinbox, var_key_name='upscale_factor', from_=1.5, to=4.0, increment=0.05, format="%.2f")
        create_setting_row_ui(self.general_settings_content_frame, "Default MP Size", ttk.Spinbox, var_key_name='default_mp_size', from_=0.1, to=8.0, increment=0.05, format="%.2f")

        # --- Flux Tab ---
        flux_styles = sorted([name for name, data in self.styles_config.items() if data.get('model_type', 'all') in ['all', 'flux']])
        create_setting_row_ui(self.flux_settings_content_frame, "Default Style", ttk.Combobox, flux_styles, 'default_style_flux')
        create_setting_row_ui(self.flux_settings_content_frame, "Default Steps", ttk.Spinbox, var_key_name='steps', from_=4, to=128, increment=4)
        create_setting_row_ui(self.flux_settings_content_frame, "Default Guidance", ttk.Spinbox, var_key_name='default_guidance', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        
        # --- SDXL Tab ---
        sdxl_styles = sorted([name for name, data in self.styles_config.items() if data.get('model_type', 'all') in ['all', 'sdxl']])
        create_setting_row_ui(self.sdxl_settings_content_frame, "Default Style", ttk.Combobox, sdxl_styles, 'default_style_sdxl')
        create_setting_row_ui(self.sdxl_settings_content_frame, "Default Steps", ttk.Spinbox, var_key_name='sdxl_steps', from_=4, to=128, increment=2)
        create_setting_row_ui(self.sdxl_settings_content_frame, "Default Guidance", ttk.Spinbox, var_key_name='default_guidance_sdxl', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(self.sdxl_settings_content_frame, "Default Negative Prompt", scrolledtext.ScrolledText, var_key_name='default_sdxl_negative_prompt', is_text_area_field=True)

        # --- Kontext Tab ---
        create_setting_row_ui(self.kontext_settings_content_frame, "Selected Kontext Model", ttk.Combobox, self.available_models, 'selected_kontext_model')
        create_setting_row_ui(self.kontext_settings_content_frame, "Default Steps", ttk.Spinbox, var_key_name='kontext_steps', from_=4, to=128, increment=4)
        create_setting_row_ui(self.kontext_settings_content_frame, "Default Guidance", ttk.Spinbox, var_key_name='kontext_guidance', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(self.kontext_settings_content_frame, "Default MP Size", ttk.Spinbox, var_key_name='kontext_mp_size', from_=0.1, to=8.0, increment=0.05, format="%.2f")

        # --- LLM Tab ---
        create_setting_row_ui(self.llm_settings_content_frame, "LLM Prompt Enhancer", ttk.Checkbutton, var_key_name='llm_enhancer_enabled')
        llm_provider_keys = list(self.llm_models_config.get('providers',{}).keys())
        create_setting_row_ui(self.llm_settings_content_frame, "LLM Provider", ttk.Combobox, llm_provider_keys, 'llm_provider')
        initial_llm_provider = self.config_manager.settings.get('llm_provider', llm_provider_keys[0] if llm_provider_keys else 'gemini')
        initial_llm_models_for_provider = self.llm_models_config.get('providers',{}).get(initial_llm_provider,{}).get('models',[])
        initial_llm_provider_display_name = self.provider_display_map.get(initial_llm_provider, initial_llm_provider.capitalize())
        create_setting_row_ui(self.llm_settings_content_frame, f"LLM Model ({initial_llm_provider_display_name})", ttk.Combobox, initial_llm_models_for_provider, 'llm_model', is_llm_model_selector_field=True)
        if 'llm_model' in self.settings_vars:
            model_key_for_provider = f"llm_model_{initial_llm_provider}"
            initial_model_val_for_provider = self.config_manager.settings.get(model_key_for_provider, "")
            if initial_model_val_for_provider in initial_llm_models_for_provider: self.settings_vars['llm_model'].set(initial_model_val_for_provider)
            elif initial_llm_models_for_provider: self.settings_vars['llm_model'].set(initial_llm_models_for_provider[0])
            else: self.settings_vars['llm_model'].set("")
        create_setting_row_ui(self.llm_settings_content_frame, "Prompt Display Preference", ttk.Combobox, list(self.display_prompt_map.keys()), 'display_prompt_preference')
        
        for frame in [self.general_settings_content_frame, self.flux_settings_content_frame, self.sdxl_settings_content_frame, self.kontext_settings_content_frame, self.llm_settings_content_frame]:
            if frame.winfo_exists():
                frame.event_generate("<Configure>")

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
                if self.log_display and self.log_display.winfo_exists():
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
            elif worker_status_update.get("type") == "restart_required":
                update_info = worker_status_update.get("update_info")
                self._restart_application(update_info=update_info)
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

    def _worker_update_application(self):
        """Downloads the latest release and prepares for update via external script."""
        repo_owner = "Tenos-ai"
        repo_name = "Tenos-Bot"
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

        try:
            if self.update_state.pending_tag:
                pending = self.update_state.pending_tag
                self.log_queue.put(("worker", f"Update {pending} already pending. Restart to apply it.\n"))
                return f"Update {pending} already pending."

            self.log_queue.put(("worker", f"Fetching latest release from {api_url}...\n"))
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            release_data = response.json()
            tag_name = release_data.get("tag_name")
            zip_url = release_data.get("zipball_url")

            if not tag_name or not zip_url:
                raise ValueError("Could not find tag_name or zipball_url in the release data.")

            if self.update_state.last_successful_tag and normalise_tag(self.update_state.last_successful_tag) == normalise_tag(tag_name):
                self.log_queue.put(("worker", f"Release {tag_name} already applied.\n"))
                return f"Already running {tag_name}."

            if not is_remote_version_newer(tag_name, self.current_version):
                self.log_queue.put(("worker", f"Current version {self.current_version} is up to date with {tag_name}.\n"))
                return "You are running the latest version."

            self.log_queue.put(("worker", f"Latest release found: {tag_name}\n"))
            self.log_queue.put(("worker", f"Downloading from: {zip_url}\n"))

            # Download the zip file
            zip_response = requests.get(zip_url, stream=True, timeout=60)
            zip_response.raise_for_status()

            # Create a temporary directory to extract the update
            temp_dir = tempfile.mkdtemp()
            self.log_queue.put(("worker", f"Created temporary update directory: {temp_dir}\n"))

            temp_zip_path = os.path.join(temp_dir, "release.zip")

            with open(temp_zip_path, 'wb') as f:
                for chunk in zip_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.log_queue.put(("worker", "Download complete. Extracting...\n"))

            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            self.log_queue.put(("worker", "Extraction complete.\n"))

            self.update_state.mark_pending(tag_name, base_dir=self.app_base_dir)

            updater_script_path = os.path.join(self.app_base_dir, "updater.py")
            if not os.path.exists(updater_script_path):
                raise FileNotFoundError("updater.py script not found. Cannot proceed with update.")

            self.log_queue.put(("info", "Handing off to updater.py. This application will now close.\n"))

            # This will queue a restart, which will trigger the handoff
            self.worker_queue.put({"type": "restart_required", "update_info": {
                "temp_dir": temp_dir,
                "dest_dir": self.app_base_dir,
                "target_tag": tag_name
            }})

            return "Update downloaded. The application will restart to apply it."

        except Exception as e:
            self.log_queue.put(("stderr", f"An error occurred during update: {e}\n"))
            traceback.print_exc()
            self.update_state.pending_tag = None
            self.update_state.save(base_dir=self.app_base_dir)
            return f"Update failed: {e}"

    def _worker_install_custom_nodes(self, *args, **kwargs):
        # This function no longer uses git, but we can keep the signature for compatibility
        # if other worker tasks use args/kwargs.
        custom_nodes_path_str = self.config_manager.config.get('NODES',{}).get('CUSTOM_NODES')
        if not (custom_nodes_path_str and isinstance(custom_nodes_path_str,str) and os.path.isdir(custom_nodes_path_str)):
            msg_err = "Custom Nodes path not set/invalid in Main Config."; self.log_queue.put(("stderr", f"Install Custom Nodes Error: {msg_err}\n")); return msg_err
        
        # Repositories to clone if they don't exist
        repositories_to_clone = {
            "rgthree-comfy": "https://github.com/rgthree/rgthree-comfy.git",
            "ComfyUI_UltimateSDUpscale": "https://github.com/ssitu/ComfyUI_UltimateSDUpscale.git",
            "comfyui-various": "https://github.com/jamesWalker55/comfyui-various.git",
            "ComfyUI-GGUF": "https://github.com/city96/ComfyUI-GGUF.git",
            "ComfyUI-load-image-from-url": "https://github.com/tsogzark/ComfyUI-load-image-from-url.git",
            "Bobs_Latent_Optimizer": "https://github.com/BobsBlazed/Bobs_Latent_Optimizer.git",
            "Tenos-Resize-to-1-M-Pixels": "https://github.com/Tenos-ai/Tenos-Resize-to-1-M-Pixels.git"
        }
        
        installation_results = []; errors_encountered_install = False
        
        for repo_name, repo_url in repositories_to_clone.items():
            repo_target_path = os.path.join(custom_nodes_path_str, repo_name)
            if not os.path.exists(repo_target_path):
                self.log_queue.put(("worker", f"Cloning {repo_name}...\n"))
                try:
                    # Using subprocess for direct git clone
                    subprocess.run(['git', 'clone', repo_url, repo_target_path], check=True, capture_output=True, text=True)
                    installation_results.append(f"Cloned {repo_name}: Success")
                except subprocess.CalledProcessError as e_git_cmd:
                    error_detail_git = e_git_cmd.stderr.strip()
                    installation_results.append(f"Cloning {repo_name}: FAILED (Git: {error_detail_git})")
                    errors_encountered_install = True
                    self.log_queue.put(("stderr", f"Git Clone Error for {repo_name}: {error_detail_git}\n"))
                except FileNotFoundError:
                    msg = "Git command not found. Please ensure Git is installed and in your system's PATH."
                    installation_results.append(f"Cloning {repo_name}: FAILED ({msg})")
                    errors_encountered_install = True
                    self.log_queue.put(("stderr", msg + "\n"))
                    # Stop trying if git is not found
                    break
                except Exception as e_other_install:
                    installation_results.append(f"Cloning {repo_name}: FAILED ({type(e_other_install).__name__}: {str(e_other_install)})")
                    errors_encountered_install = True
                    self.log_queue.put(("stderr", f"Error cloning {repo_name}: {str(e_other_install)}\n"))
            else:
                installation_results.append(f"Skipped {repo_name}: Directory already exists.")

        local_nodes_source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"nodes")
        if os.path.isdir(local_nodes_source_dir):
            self.log_queue.put(("worker",f"Copying local nodes from '{local_nodes_source_dir}' to '{custom_nodes_path_str}'...\n"))
            try:
                shutil.copytree(local_nodes_source_dir, custom_nodes_path_str, dirs_exist_ok=True)
                installation_results.append("Copied local nodes: Success")
            except Exception as e_copy_local:
                installation_results.append(f"Copied local nodes: FAILED ({type(e_copy_local).__name__}: {str(e_copy_local)})")
                errors_encountered_install = True
                self.log_queue.put(("stderr", f"Error copying local nodes: {str(e_copy_local)}\n"))
        else:
            installation_results.append("Copy local nodes: Skipped (local 'nodes' folder not found)")

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
        """Trigger save for all config-related entities."""
        if not silent_askyesno("Confirm Save All", "Save changes in ALL tabs?", parent=self.master): return
        self.config_manager.save_main_config_data()
        self.llm_prompts_tab_manager.save_llm_prompts_data()
        self.lora_styles_tab_manager.save_current_styles_config()
        self.favorites_tab_manager.save_all_favorites_data()
        self.config_manager.save_bot_settings_data()
        self.admin_control_tab_manager._save_blocklist()
        silent_showinfo("Save All Triggered", "All save operations triggered. Check console/messages for status.", parent=self.master)

    def reset_bot_settings_to_defaults(self):
        """
        Reset all bot settings to their default values defined in the settings template.
        Prompts the user for confirmation before resetting, then refreshes the UI and saves.
        """
        if not silent_askyesno("Confirm Reset", "Are you sure you want to reset all bot settings to their default values?", parent=self.master):
            return
        try:
            # Obtain a fresh copy of the default settings
            default_settings = self.config_manager.settings_template_factory().copy()
            # Update the config manager's in-memory settings
            self.config_manager.settings = default_settings
            # Refresh the UI to reflect the default values
            self.populate_bot_settings_tab()
            # Persist the default settings to disk
            self.config_manager.save_bot_settings_data()
            silent_showinfo("Reset Complete", "Bot settings have been reset to defaults.", parent=self.master)
        except Exception as e_reset:
            silent_showerror("Reset Error", f"Failed to reset settings to defaults:\n{e_reset}", parent=self.master)

    def export_config_and_settings(self):
        """Export the main config and bot settings to a single JSON file."""
        try:
            file_path = filedialog.asksaveasfilename(title="Export Config & Settings", defaultextension=".json", filetypes=[("JSON Files","*.json"), ("All Files","*.*")], parent=self.master)
            if not file_path:
                return
            export_data = {
                'config': self.config_manager.config,
                'settings': self.config_manager.settings,
                'styles_config': self.styles_config,
                'llm_models': self.llm_models_config,
                'llm_prompts': self.llm_prompts_config
            }
            with open(file_path, 'w', encoding='utf-8') as f_out:
                json.dump(export_data, f_out, indent=2)
            silent_showinfo("Export Complete", f"Exported configuration to {os.path.basename(file_path)}", parent=self.master)
        except Exception as e_exp:
            silent_showerror("Export Error", f"Failed to export configuration:\n{e_exp}", parent=self.master)

    def import_config_and_settings(self):
        """Import main config and bot settings from a previously exported JSON file."""
        try:
            file_path = filedialog.askopenfilename(title="Import Config & Settings", filetypes=[("JSON Files","*.json"), ("All Files","*.*")], parent=self.master)
            if not file_path:
                return
            with open(file_path, 'r', encoding='utf-8') as f_in:
                imported_data = json.load(f_in)
            if not isinstance(imported_data, dict):
                silent_showerror("Import Error", "Invalid file format. Expected a JSON object.", parent=self.master)
                return
            # Update config and settings
            if 'config' in imported_data and isinstance(imported_data['config'], dict):
                self.config_manager.config = imported_data['config']
                save_json_config(CONFIG_FILE_NAME, self.config_manager.config, "main config")
            if 'settings' in imported_data and isinstance(imported_data['settings'], dict):
                self.config_manager.settings = imported_data['settings']
                save_json_config(SETTINGS_FILE_NAME, self.config_manager.settings, "bot settings")
            # Optional data
            if 'styles_config' in imported_data and isinstance(imported_data['styles_config'], dict):
                self.styles_config = imported_data['styles_config']
            if 'llm_models' in imported_data and isinstance(imported_data['llm_models'], dict):
                self.llm_models_config = imported_data['llm_models']
            if 'llm_prompts' in imported_data and isinstance(imported_data['llm_prompts'], dict):
                self.llm_prompts_config = imported_data['llm_prompts']
            # Refresh UI
            self.refresh_all_ui_tabs()
            silent_showinfo("Import Complete", f"Imported configuration from {os.path.basename(file_path)}", parent=self.master)
        except Exception as e_imp:
            silent_showerror("Import Error", f"Failed to import configuration:\n{e_imp}", parent=self.master)
    
    def _restart_application(self, update_info=None):
        """Gracefully stops the bot and restarts the configurator application."""
        self.log_queue.put(("info", "--- Restarting application ---\n"))
        if self.bot_control_tab_manager.is_bot_script_running():
            self.bot_control_tab_manager.stop_bot_script()
        self.master.after(1500, self._execute_restart, update_info)

    def _execute_restart(self, update_info=None):
        """Performs the actual restart, handing off to updater.py if this is an update."""
        try:
            # Ensure log readers are stopped
            self.stop_readers.set()
            for thread_item in self.reader_threads:
                if thread_item.is_alive():
                    thread_item.join(timeout=0.2)
            
            current_pid = os.getpid()
            python_exe = sys.executable

            if update_info:
                # This is an update restart. Launch updater.py
                temp_dir = update_info["temp_dir"]
                dest_dir = update_info["dest_dir"]
                updater_script = os.path.join(dest_dir, "updater.py")
                target_tag = update_info.get("target_tag")

                command = [python_exe, updater_script, str(current_pid), temp_dir, dest_dir]
                if target_tag:
                    command.append(target_tag)

                self.log_queue.put(("info", f"Executing updater: {' '.join(command)}\n"))

                # Use Popen to launch the updater in a new, detached process
                subprocess.Popen(command)
                
                # Now, exit this main application
                self.master.destroy()

            else:
                # This is a regular restart (not an update)
                os.execl(python_exe, python_exe, *sys.argv)

        except Exception as e:
            self.log_queue.put(("stderr", f"FATAL: Failed to execute restart: {e}\n"))
            self.update_state.pending_tag = None
            self.update_state.save(base_dir=self.app_base_dir)
            silent_showerror("Restart Failed", f"Could not restart the application.\nPlease close and start it manually.\n\nError: {e}", parent=self.master)


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

    def _check_for_startup_update(self):
        """Checks if auto-update is enabled and runs the updater if so."""
        try:
            app_settings = self.config_manager.config.get("APP_SETTINGS", {})
            if not bool(app_settings.get("AUTO_UPDATE_ON_STARTUP", False)):
                return

            if self.update_state.pending_tag:
                pending = self.update_state.pending_tag
                self.log_queue.put(("info", f"--- Update {pending} already queued, skipping auto-check. ---\n"))
                return

            self.log_queue.put(("info", "--- Auto-update enabled, checking for updates... ---\n"))
            self.run_worker_task_on_editor(self._worker_update_application, "Startup Update Check")
        except Exception as e:
            self.log_queue.put(("stderr", f"Error during startup update check: {e}\n"))

    def _check_for_first_run(self):
        """Shows a welcome/instruction dialog on the first launch."""
        flag_file = 'first_run_complete.flag'
        if not os.path.exists(flag_file):
            welcome_message = (
                "Welcome to the Tenos.ai Configurator!\n\n"
                "It looks like this is your first time running the tool.\n\n"
                "**IMPORTANT FIRST STEPS:**\n\n"
                "1. Go to the 'Main Config' tab and set all the paths, especially the 'CUSTOM_NODES' path for ComfyUI.\n\n"
                "2. Click 'Save Main Config' at the bottom of that tab.\n\n"
                "3. Use the 'Tools' menu at the top to run:\n"
                "   - 'Install/Update Custom Nodes'\n"
                "   - 'Scan Models/Clips/Checkpoints'\n\n"
                "Once these steps are done, you can start the bot from the 'Bot Control' tab."
            )
            silent_showinfo("First-Time Setup", welcome_message, parent=self.master)
            
            try:
                with open(flag_file, 'w') as f:
                    f.write(f"First run setup prompt shown on: {datetime.now().isoformat()}")
            except OSError as e:
                silent_showerror("First Run Warning", f"Could not create the first run flag file. You may see this message again.\n\nError: {e}", parent=self.master)

class ProgressPrinter:
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
# --- END OF FILE config_editor_main.py ---
