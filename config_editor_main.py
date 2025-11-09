# --- START OF FILE config_editor_main.py ---
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
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
import difflib
import shutil

from settings_shared import (
    WAN_CHECKPOINT_KEY,
    WAN_I2V_HIGH_NOISE_KEY,
    WAN_I2V_LOW_NOISE_KEY,
    WAN_T2V_HIGH_NOISE_KEY,
    WAN_T2V_LOW_NOISE_KEY,
    sync_wan_checkpoint_alias,
)


KSAMPLER_SAMPLER_OPTIONS = [
    "euler",
    "euler_cfg_pp",
    "euler_ancestral",
    "euler_ancestral_cfg_pp",
    "heun",
    "heunpp2",
    "dpm_2",
    "dpm_2_ancestral",
    "lms",
    "dpm_fast",
    "dpm_adaptive",
    "dpmpp_2s_ancestral",
    "dpmpp_2s_ancestral_cfg_pp",
    "dpmpp_sde",
    "dpmpp_sde_gpu",
    "dpmpp_2m",
    "dpmpp_2m_cfg_pp",
    "dpmpp_2m_sde",
    "dpmpp_2m_sde_gpu",
    "dpmpp_2m_sde_heun",
    "dpmpp_2m_sde_heun_gpu",
    "dpmpp_3m_sde",
    "dpmpp_3m_sde_gpu",
    "ddpm",
    "lcm",
    "ipndm",
    "ipndm_v",
    "deis",
    "res_multistep",
    "res_multistep_cfg_pp",
    "res_multistep_ancestral",
    "res_multistep_ancestral_cfg_pp",
    "gradient_estimation",
    "gradient_estimation_cfg_pp",
    "er_sde",
    "seeds_2",
    "seeds_3",
    "sa_solver",
    "sa_solver_pece",
]

KSAMPLER_SCHEDULER_OPTIONS = [
    "simple",
    "sgm_uniform",
    "karras",
    "exponential",
    "ddim_uniform",
    "beta",
    "normal",
    "linear_quadratic",
    "kl_optimal",
]


DEFAULT_STATUS_DURATION = object()


class Tooltip:
    """Lightweight tooltip that follows the active theme."""

    def __init__(self, widget, text, color_getter, delay=500):
        self.widget = widget
        self.text = text
        self.color_getter = color_getter
        self.delay = delay
        self._after_id = None
        self.tip_window = None

        self.widget.bind("<Enter>", self._schedule)
        self.widget.bind("<Leave>", self._hide)
        self.widget.bind("<FocusOut>", self._hide)

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self):
        if self.tip_window or not self.widget.winfo_viewable():
            return
        try:
            x_root = self.widget.winfo_rootx() + 20
            y_root = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except tk.TclError:
            return

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        bg = self.color_getter("TOOLTIP_BG", "#1E293B")
        fg = self.color_getter("TOOLTIP_FG", "#F8FAFC")
        border = self.color_getter("BORDER_COLOR", "#1E293B")
        tw.configure(bg=border)

        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            relief=tk.FLAT,
            padx=8,
            pady=4,
            wraplength=320,
            background=bg,
            foreground=fg,
            font=("Segoe UI", 10)
        )
        label.pack()
        tw.wm_geometry(f"+{x_root}+{y_root}")

    def _hide(self, _event=None):
        self._cancel()
        if self.tip_window is not None:
            try:
                self.tip_window.destroy()
            except tk.TclError:
                pass
            self.tip_window = None


class StatusBanner(ttk.Frame):
    """Single place to surface transient status, prompts, and progress."""

    def __init__(self, master, color_getter, register_theme_callback):
        super().__init__(master, style="Tenos.TFrame")
        self.color_getter = color_getter
        self._hide_after_id = None
        self._active_actions = []

        self.columnconfigure(1, weight=1)

        self.icon_var = tk.StringVar(value="")
        self.message_var = tk.StringVar(value="")

        self.icon_label = ttk.Label(self, textvariable=self.icon_var, width=2, anchor="center", style="Tenos.TLabel")
        self.icon_label.grid(row=0, column=0, padx=(10, 4), pady=6)

        self.message_label = ttk.Label(self, textvariable=self.message_var, style="Tenos.TLabel", wraplength=640, anchor="w")
        self.message_label.grid(row=0, column=1, sticky="ew", pady=6)

        self.action_frame = ttk.Frame(self, style="Tenos.TFrame")
        self.action_frame.grid(row=0, column=2, padx=(6, 10), pady=6, sticky="e")

        self.progress = ttk.Progressbar(self.action_frame, mode="indeterminate", length=140, style="Tenos.Horizontal.TProgressbar")

        register_theme_callback(self._refresh_theme)
        self._refresh_theme()

    def _refresh_theme(self):
        try:
            self.configure(style="Tenos.TFrame")
            self.message_label.configure(style="Tenos.TLabel")
            self.icon_label.configure(style="Tenos.TLabel")
            bg = self.color_getter("FRAME_BG_COLOR")
            if bg:
                self.configure(padding=(0, 0, 0, 4))
        except tk.TclError:
            pass

    def _cancel_hide(self):
        if self._hide_after_id:
            try:
                self.after_cancel(self._hide_after_id)
            except tk.TclError:
                pass
            self._hide_after_id = None

    def clear(self):
        self._cancel_hide()
        self.icon_var.set("")
        self.message_var.set("")
        for widget in self._active_actions:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self._active_actions.clear()
        try:
            self.progress.stop()
            self.progress.pack_forget()
        except tk.TclError:
            pass
        self.pack_forget()

    def show(self, message, level="info", duration=2000, icon=None, allow_dismiss=False):
        self._cancel_hide()
        self._ensure_visible()
        self._install_actions([])
        try:
            self.progress.stop()
            self.progress.pack_forget()
        except tk.TclError:
            pass
        symbol_map = {
            "info": "ℹ", "warning": "⚠", "error": "✖", "success": "✔", "question": "?"
        }
        self.icon_var.set(icon if icon is not None else symbol_map.get(level, "ℹ"))
        self.message_var.set(message)

        fg = self.color_getter("TEXT_COLOR_NORMAL")
        if level == "error":
            fg = self.color_getter("ERROR_FG", "#F05252")
        elif level == "warning":
            fg = self.color_getter("WARNING_FG", "#F59E0B")
        elif level == "success":
            fg = self.color_getter("SUCCESS_FG", "#10B981")
        elif level == "question":
            fg = self.color_getter("ACCENT_FG", "#2C7BE5")
        try:
            self.message_label.configure(foreground=fg)
            self.icon_label.configure(foreground=fg)
        except tk.TclError:
            pass

        if duration:
            self._hide_after_id = self.after(duration, self.clear)
        elif allow_dismiss:
            dismiss_btn = ttk.Button(self.action_frame, text="Dismiss", command=self.clear, style="Tenos.Command.TButton")
            dismiss_btn.pack(side=tk.LEFT, padx=4)
            self._install_actions([dismiss_btn])

    def _ensure_visible(self):
        if not self.winfo_ismapped():
            self.pack(fill=tk.X, pady=(0, 4))

    def show_progress(self, message, level="info"):
        self.show(message, level=level, duration=None, icon="…", allow_dismiss=False)
        try:
            if not self.progress.winfo_ismapped():
                self.progress.pack(side=tk.RIGHT, padx=4)
            self.progress.start(12)
        except tk.TclError:
            pass

    def _install_actions(self, widgets):
        for widget in self._active_actions:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self._active_actions = widgets

    def ask_yes_no(self, title, message):
        result_var = tk.BooleanVar(value=False)
        decided = tk.BooleanVar(value=False)

        def _respond(value):
            result_var.set(value)
            decided.set(True)
            self.clear()

        self._ensure_visible()
        self.show(f"{title}: {message}", level="question", duration=None, icon="?")

        yes_btn = ttk.Button(self.action_frame, text="Yes", command=lambda: _respond(True))
        no_btn = ttk.Button(self.action_frame, text="No", command=lambda: _respond(False))
        yes_btn.pack(side=tk.LEFT, padx=4)
        no_btn.pack(side=tk.LEFT, padx=4)
        self._install_actions([yes_btn, no_btn])

        self.wait_variable(decided)
        return result_var.get()

    def ask_string(self, title, prompt, initialvalue="", show=None, validate=None):
        result_var = tk.StringVar(value=initialvalue or "")
        decided = tk.BooleanVar(value=False)

        def _commit():
            value = result_var.get()
            if callable(validate) and not validate(value):
                self.show("Please enter a valid value.", level="warning", duration=2000)
                return
            decided.set(True)
            self.clear()

        def _cancel():
            result_var.set("")
            decided.set(True)
            self.clear()

        self._ensure_visible()
        self.show(f"{title}: {prompt}", level="question", duration=None, icon="✎")

        entry = ttk.Entry(self.action_frame, textvariable=result_var, width=28, show=show)
        entry.pack(side=tk.LEFT, padx=(0, 6))
        ok_btn = ttk.Button(self.action_frame, text="OK", command=_commit)
        cancel_btn = ttk.Button(self.action_frame, text="Cancel", command=_cancel)
        ok_btn.pack(side=tk.LEFT, padx=4)
        cancel_btn.pack(side=tk.LEFT, padx=4)
        self._install_actions([entry, ok_btn, cancel_btn])

        try:
            entry.focus_set()
            entry.icursor(tk.END)
        except tk.TclError:
            pass

        self.wait_variable(decided)
        return result_var.get() or None


class SearchableListDialog(tk.Toplevel):
    """Popup dialog with live filtering for long option lists."""

    def __init__(self, master, title, values, color_getter):
        super().__init__(master)
        color_getter = color_getter or (lambda _key, default=None: default)
        self.result = None
        self.title(title)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)
        self.configure(bg=color_getter("FRAME_BG_COLOR", "#111827"))
        self._color_getter = color_getter

        self.minsize(320, 320)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Type to filter:", style="Tenos.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        self.filter_var = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self.filter_var)
        entry.grid(row=0, column=0, sticky="ew", padx=12, pady=(0, 12))

        self.listbox = tk.Listbox(self, activestyle="none", selectmode=tk.SINGLE, borderwidth=1, relief=tk.SOLID)
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._apply_theme_to_listbox()

        button_bar = ttk.Frame(self, style="Tenos.TFrame")
        button_bar.grid(row=2, column=0, sticky="e", padx=12, pady=(0, 12))
        ttk.Button(button_bar, text="Select", command=self._confirm).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="Cancel", command=self._cancel).pack(side=tk.LEFT)

        self.values = list(values)
        self._filtered_values = self.values
        self._populate_list()

        entry.bind("<KeyRelease>", self._on_filter_change)
        entry.bind("<Return>", lambda _e: self._confirm())
        self.listbox.bind("<Return>", lambda _e: self._confirm())
        self.listbox.bind("<Double-Button-1>", lambda _e: self._confirm())
        self.listbox.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Escape>", lambda _e: self._cancel())

        self.after(50, entry.focus_set)
        self.after(75, self._center_over_master)
        self.wait_window(self)

    def _apply_theme_to_listbox(self):
        try:
            bg = self._color_getter("LISTBOX_BG", "#0F172A")
            fg = self._color_getter("LISTBOX_FG", "#E2E8F0")
            sel_bg = self._color_getter("LISTBOX_SELECT_BG", "#2563EB")
            sel_fg = self._color_getter("LISTBOX_SELECT_FG", "#FFFFFF")
            border = self._color_getter("BORDER_COLOR", "#1E293B")
            self.listbox.configure(
                background=bg,
                foreground=fg,
                selectbackground=sel_bg,
                selectforeground=sel_fg,
                highlightcolor=border,
                highlightbackground=border,
            )
        except tk.TclError:
            pass

    def _center_over_master(self):
        try:
            self.update_idletasks()
            master = self.master
            master.update_idletasks()
            master_width = master.winfo_width() or 800
            master_height = master.winfo_height() or 600
            width = max(360, min(int(master_width * 0.55), 720))
            height = max(320, min(int(master_height * 0.7), 720))
            master_x = master.winfo_rootx()
            master_y = master.winfo_rooty()
            pos_x = master_x + (master_width - width) // 2
            pos_y = master_y + (master_height - height) // 2
            self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        except tk.TclError:
            pass

    def _populate_list(self):
        self.listbox.delete(0, tk.END)
        for value in self._filtered_values:
            self.listbox.insert(tk.END, value)

    def _on_filter_change(self, _event=None):
        needle = self.filter_var.get().lower()
        if not needle:
            self._filtered_values = self.values
        else:
            self._filtered_values = [v for v in self.values if needle in str(v).lower()]
        self._populate_list()

    def _confirm(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        self.result = self._filtered_values[selection[0]]
        self._cleanup()

    def _cancel(self):
        self.result = None
        self._cleanup()

    def _cleanup(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


class SideNavigationView(ttk.Frame):
    """Provides a list-driven navigation layout to reduce nested notebooks."""

    def __init__(self, master, sections, on_select=None, listbox_width=22):
        super().__init__(master, style="Tenos.TFrame")
        self.sections = sections
        self.on_select = on_select
        self.section_frames = {}

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            self,
            exportselection=False,
            activestyle="none",
            width=listbox_width,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.listbox.grid(row=0, column=0, sticky="ns", padx=(0, 10), pady=4)

        self.content_container = ttk.Frame(self, style="Tenos.TFrame")
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.rowconfigure(0, weight=1)

        for index, (section_key, section_label) in enumerate(self.sections):
            self.listbox.insert(tk.END, section_label)
            frame = ttk.Frame(self.content_container, style="Tenos.TFrame")
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_remove()
            self.section_frames[section_key] = frame
            if index == 0:
                self._current_key = section_key

        self.listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        if self.sections:
            self.listbox.selection_set(0)
            self.show_section(self.sections[0][0])

    def show_section(self, section_key):
        if section_key not in self.section_frames:
            return
        for key, frame in self.section_frames.items():
            if frame.winfo_ismapped():
                frame.grid_remove()
        self.section_frames[section_key].grid()
        self._current_key = section_key
        if callable(self.on_select):
            self.on_select(section_key)

    def _on_listbox_select(self, _event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        section_key = self.sections[index][0]
        self.show_section(section_key)

    def get_section_frame(self, section_key):
        return self.section_frames.get(section_key)


class CollapsibleSection(ttk.Frame):
    """Reusable collapsible panel for grouping related controls."""

    def __init__(self, master, title, color_getter, initially_open=True):
        super().__init__(master, style="Tenos.TFrame")
        self.color_getter = color_getter
        self._open = initially_open

        self.columnconfigure(0, weight=1)

        header = ttk.Frame(self, style="SectionHeader.TFrame")
        header.grid(row=0, column=0, sticky="ew")

        self.toggle_symbol = tk.StringVar(value="▼" if initially_open else "►")
        toggle_btn = ttk.Button(header, textvariable=self.toggle_symbol, width=2, command=self.toggle, style="Toggle.TButton")
        toggle_btn.pack(side=tk.LEFT, padx=(0, 6), pady=4)

        ttk.Label(header, text=title, style="SectionHeader.TLabel").pack(side=tk.LEFT, pady=4)

        self.content = ttk.Frame(self, style="SectionBody.TFrame")
        self.content.grid(row=1, column=0, sticky="nsew")

        if not initially_open:
            self.content.grid_remove()

    def toggle(self):
        self._open = not self._open
        if self._open:
            self.content.grid()
            self.toggle_symbol.set("▼")
        else:
            self.content.grid_remove()
            self.toggle_symbol.set("►")

    def body(self):
        return self.content

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
    QWEN_MODELS_FILE_NAME, QWEN_EDIT_MODELS_FILE_NAME, WAN_MODELS_FILE_NAME,
    ICON_PATH_ICO, ICON_PATH_PNG,
    BOT_SCRIPT_NAME
)

from editor_utils import (
    silent_askyesno, silent_askstring, browse_folder_dialog,
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
try:
    from version_info import APP_VERSION
except ModuleNotFoundError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        from version_info import APP_VERSION
    except ModuleNotFoundError:
        APP_VERSION = "unknown"

class ConfigEditor:
    def __init__(self, master_tk_root):
        self.master = master_tk_root

        version_display = None
        if APP_VERSION and APP_VERSION.lower() != "unknown":
            version_display = APP_VERSION
            if not version_display.lower().startswith("v"):
                version_display = f"v{version_display}"

        if version_display:
            self.master.title(f"Tenos.ai Configurator {version_display}")
        else:
            self.master.title("Tenos.ai Configurator")
        self.master.minsize(960, 640)

        self.base_colors = {
            "BACKGROUND_COLOR": BACKGROUND_COLOR,
            "FRAME_BG_COLOR": FRAME_BG_COLOR,
            "WIDGET_BG": WIDGET_BG,
            "TEXT_COLOR_NORMAL": TEXT_COLOR_NORMAL,
            "TEXT_COLOR_DISABLED": TEXT_COLOR_DISABLED,
            "ENTRY_BG_COLOR": ENTRY_BG_COLOR,
            "ENTRY_FG_COLOR": ENTRY_FG_COLOR,
            "ENTRY_INSERT_COLOR": ENTRY_INSERT_COLOR,
            "SELECT_BG_COLOR": SELECT_BG_COLOR,
            "SELECT_FG_COLOR": SELECT_FG_COLOR,
            "BUTTON_BG_COLOR": BUTTON_BG_COLOR,
            "BUTTON_FG_COLOR": BUTTON_FG_COLOR,
            "BUTTON_ACTIVE_BG_COLOR": BUTTON_ACTIVE_BG_COLOR,
            "BUTTON_ACTIVE_FG_COLOR": BUTTON_ACTIVE_FG_COLOR,
            "BORDER_COLOR": BORDER_COLOR,
            "TENOS_LIGHT_BLUE_ACCENT2": TENOS_LIGHT_BLUE_ACCENT2,
            "TENOS_MEDIUM_BLUE_ACCENT": TENOS_MEDIUM_BLUE_ACCENT,
            "TENOS_DARK_BLUE_BG": TENOS_DARK_BLUE_BG,
            "TENOS_WHITE_FG": TENOS_WHITE_FG,
            "TENOS_BLACK_DETAIL": TENOS_BLACK_DETAIL,
            "CANVAS_BG_COLOR": CANVAS_BG_COLOR,
            "SCROLLBAR_TROUGH_COLOR": SCROLLBAR_TROUGH_COLOR,
            "SCROLLBAR_SLIDER_COLOR": SCROLLBAR_SLIDER_COLOR,
            "LISTBOX_BG": LISTBOX_BG,
            "LISTBOX_FG": LISTBOX_FG,
            "LISTBOX_SELECT_BG": LISTBOX_SELECT_BG,
            "LISTBOX_SELECT_FG": LISTBOX_SELECT_FG,
            "ACTIVE_TAB_BG": ACTIVE_TAB_BG,
            "INACTIVE_TAB_BG": INACTIVE_TAB_BG,
            "ACTIVE_TAB_FG": ACTIVE_TAB_FG,
            "INACTIVE_TAB_FG": INACTIVE_TAB_FG,
            "LOG_STDOUT_FG": LOG_STDOUT_FG,
            "LOG_STDERR_FG": LOG_STDERR_FG,
            "LOG_INFO_FG": LOG_INFO_FG,
            "LOG_WORKER_FG": LOG_WORKER_FG,
            "TOOLTIP_BG": "#1F2937",
            "TOOLTIP_FG": "#F8FAFC",
            "ACCENT_FG": TENOS_LIGHT_BLUE_ACCENT2,
            "SUCCESS_FG": "#22C55E",
            "WARNING_FG": "#F59E0B",
            "ERROR_FG": "#F05252",
        }

        self.theme_presets = {
            "dark": dict(self.base_colors),
            "light": {
                "BACKGROUND_COLOR": "#F5F7FB",
                "FRAME_BG_COLOR": "#FFFFFF",
                "WIDGET_BG": "#FFFFFF",
                "TEXT_COLOR_NORMAL": "#1F2933",
                "TEXT_COLOR_DISABLED": "#9AA5B1",
                "ENTRY_BG_COLOR": "#FFFFFF",
                "ENTRY_FG_COLOR": "#1F2933",
                "ENTRY_INSERT_COLOR": "#2C7BE5",
                "SELECT_BG_COLOR": "#2C7BE5",
                "SELECT_FG_COLOR": "#FFFFFF",
                "BUTTON_BG_COLOR": "#2C7BE5",
                "BUTTON_FG_COLOR": "#FFFFFF",
                "BUTTON_ACTIVE_BG_COLOR": "#1B6AD6",
                "BUTTON_ACTIVE_FG_COLOR": "#FFFFFF",
                "BORDER_COLOR": "#D0D7E2",
                "TENOS_LIGHT_BLUE_ACCENT2": "#4F83F1",
                "TENOS_MEDIUM_BLUE_ACCENT": "#3756CC",
                "TENOS_DARK_BLUE_BG": "#E4EDFC",
                "TENOS_WHITE_FG": "#FFFFFF",
                "TENOS_BLACK_DETAIL": "#111827",
                "CANVAS_BG_COLOR": "#F1F5FB",
                "SCROLLBAR_TROUGH_COLOR": "#E5E9F2",
                "SCROLLBAR_SLIDER_COLOR": "#C7D2FE",
                "LISTBOX_BG": "#FFFFFF",
                "LISTBOX_FG": "#1F2933",
                "LISTBOX_SELECT_BG": "#2C7BE5",
                "LISTBOX_SELECT_FG": "#FFFFFF",
                "ACTIVE_TAB_BG": "#FFFFFF",
                "INACTIVE_TAB_BG": "#E8EEF9",
                "ACTIVE_TAB_FG": "#1F2933",
                "INACTIVE_TAB_FG": "#4B5563",
                "LOG_STDOUT_FG": "#2563EB",
                "LOG_STDERR_FG": "#B91C1C",
                "LOG_INFO_FG": "#2563EB",
                "LOG_WORKER_FG": "#0F766E",
                "TOOLTIP_BG": "#1E40AF",
                "TOOLTIP_FG": "#F8FAFC",
                "ACCENT_FG": "#1D4ED8",
                "SUCCESS_FG": "#0F766E",
                "WARNING_FG": "#B45309",
                "ERROR_FG": "#B91C1C",
            }
        }

        self.current_theme_name = "dark"
        self.theme_colors = dict(self.theme_presets[self.current_theme_name])
        self._theme_subscribers = []
        self.theme_watchers = []

        self.style = ttk.Style()
        self._configure_main_editor_style()
        self.master.configure(bg=self.color("BACKGROUND_COLOR"))

        self.bot_process = None
        self.log_queue = queue.Queue()
        self.stop_readers = threading.Event()
        self.reader_threads = []
        self.worker_queue = queue.Queue()
        self.worker_thread = None
        self.config_vars = {}
        self.settings_vars = {}
        self.bot_settings_widgets = {}
        self.config_input_widgets = {}
        self.config_row_metadata = {}
        self.settings_row_metadata = {}
        self.config_search_matches = []
        self.settings_search_matches = []
        self._config_search_alerted = False
        self._settings_search_alerted = False
        self.config_search_var = None
        self.settings_search_var = None
        self.config_search_entry = None
        self.settings_search_entry = None
        self.config_clear_search_btn = None
        self.settings_clear_search_btn = None
        self.last_focused_config_key = None
        self.last_focused_setting_key = None
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
        self.available_qwen_models = []
        self.available_qwen_edit_models = []
        self.available_wan_models = []
        self.available_wan_video_models = []
        self.available_clips_t5 = []
        self.available_clips_l = []
        self.available_qwen_clips = []
        self.available_wan_clips = []
        self.available_wan_vision = []
        self.available_loras = ["None"]
        self.available_upscale_models = ["None"]
        self.available_vaes = ["None"]
        self.available_qwen_vaes = ["None"]
        self.available_wan_vaes = ["None"]

        self.provider_display_map = { k: v.get("display_name", k.capitalize()) for k, v in self.llm_models_config.get("providers", {}).items() }
        self.display_prompt_map = { "enhanced": "Show Enhanced Prompt ✨", "original": "Show Original Prompt ✍️" }
        self.notification_style_display_map = {
            "timed": "Auto-dismiss (Timed)",
            "sticky": "Stay Until Dismissed"
        }

        self.config_help_text = {
            "OUTPUTS.UPSCALES": "Directory where upscaled images are saved after processing.",
            "OUTPUTS.VARIATIONS": "Storage location for variation batches generated from a prompt.",
            "OUTPUTS.GENERATIONS": "Primary folder for brand-new image generations.",
            "MODELS.MODEL_FILES": "Root directory containing your Flux model checkpoints.",
            "MODELS.CHECKPOINTS_FOLDER": "Location for SDXL checkpoints used by the bot.",
            "MODELS.QWEN_MODELS": "Folder containing Qwen diffusion checkpoints (e.g., qwen2-vl).",
            "MODELS.WAN_MODELS": "Folder containing WAN diffusion checkpoints for text/video workflows.",
            "MODELS.UPSCALE_MODELS": "Folder with upscale models available to ComfyUI.",
            "MODELS.VAE_MODELS": "Directory containing VAE files referenced by SDXL.",
            "TEXT_ENCODERS.QWEN_TEXT_ENCODERS": "Directory with Qwen text encoder weights (text & image encoders).",
            "TEXT_ENCODERS.WAN_TEXT_ENCODERS": "Directory containing WAN text encoder weights.",
            "TEXT_ENCODERS.WAN_VISION_ENCODERS": "Directory for WAN vision encoders used during animation workflows.",
            "CLIP.CLIP_FILES": "Folder where CLIP model files are stored.",
            "LORAS.LORA_FILES": "Directory with LoRA assets available for selection.",
            "NODES.CUSTOM_NODES": "ComfyUI custom nodes folder used during node installation.",
            "COMFYUI_API.HOST": "Hostname for your ComfyUI server.",
            "COMFYUI_API.PORT": "Port exposed by the ComfyUI API service.",
            "BOT_INTERNAL_API.HOST": "Host for the Tenos internal bot API.",
            "BOT_INTERNAL_API.PORT": "Internal API port for bot coordination.",
            "BOT_INTERNAL_API.AUTH_TOKEN": "Token required for the configurator to talk to the bot API.",
            "BOT_API.KEY": "Public bot command API key issued by Tenos.",
            "ADMIN.USERNAME": "Default administrator Discord username for privileged actions.",
            "ADMIN.ID": "Discord snowflake ID for the administrator account.",
            "LLM_ENHANCER.OPENAI_API_KEY": "Key used when sending prompt enhancement requests to OpenAI.",
            "LLM_ENHANCER.GEMINI_API_KEY": "Key used for Google Gemini prompt enhancements.",
            "LLM_ENHANCER.GROQ_API_KEY": "Key used for Groq LLM prompt enhancements.",
            "APP_SETTINGS.AUTO_UPDATE_ON_STARTUP": "When enabled the configurator will check for updates on launch.",
            "APP_SETTINGS.STATUS_NOTIFICATION_STYLE": "Controls whether editor status banners auto-dismiss or stay until dismissed.",
            "APP_SETTINGS.STATUS_NOTIFICATION_DURATION_MS": "Duration (ms) before timed notifications close automatically."
        }

        self.settings_help_text = {
            "selected_model": "Default Flux/SDXL/Qwen/WAN model used for general image generation.",
            "active_model_family": "Sets which model family is active for new /gen requests.",
            "selected_kontext_model": "Flux model dedicated to Kontext workflows.",
            "selected_t5_clip": "T5 text encoder paired with your primary model.",
            "selected_clip_l": "CLIP-L encoder providing textual guidance to Flux.",
            "selected_vae": "VAE loaded for color-space decoding during SDXL generations.",
            "default_flux_model": "Default Flux checkpoint loaded for text-to-image runs.",
            "default_sdxl_checkpoint": "Default SDXL checkpoint loaded for text-to-image runs.",
            "default_qwen_checkpoint": "Default Qwen diffusion checkpoint for image workflows.",
            "default_qwen_edit_checkpoint": "Default Qwen Edit checkpoint used for image edit runs.",
            "default_wan_checkpoint": "Legacy WAN checkpoint slot (mirrors the T2V high-noise UNet).",
            WAN_T2V_HIGH_NOISE_KEY: "WAN T2V high-noise UNet used for standard /gen video runs.",
            WAN_T2V_LOW_NOISE_KEY: "WAN T2V low-noise UNet paired with high-noise model during generation.",
            WAN_I2V_HIGH_NOISE_KEY: "WAN I2V high-noise UNet used for image-to-video conversions.",
            WAN_I2V_LOW_NOISE_KEY: "WAN I2V low-noise UNet used during image-to-video conversions.",
            "default_wan_low_noise_unet": "Legacy WAN low-noise slot (mirrors the T2V low-noise UNet).",
            "default_style_flux": "Starting style applied to Flux prompts.",
            "default_style_sdxl": "Starting style applied to SDXL prompts.",
            "default_style_qwen": "Starting style applied to Qwen prompts.",
            "default_style_wan": "Starting style applied to WAN prompts.",
            "default_variation_mode": "Controls how strongly variation prompts deviate.",
            "variation_batch_size": "Number of variation images generated at once.",
            "default_batch_size": "Default image count per generation request.",
            "upscale_factor": "Multiplier used when upscaling images via the bot.",
            "default_mp_size": "Target megapixel size for Flux renders.",
            "steps": "Number of inference steps Flux will run.",
            "sdxl_steps": "Number of inference steps for SDXL workflows.",
            "qwen_steps": "Number of inference steps for Qwen workflows.",
            "qwen_edit_steps": "Number of inference steps for Qwen Edit workflows.",
            "wan_steps": "Number of inference steps for WAN workflows.",
            "default_guidance": "Flux guidance scale balancing prompt adherence.",
            "default_guidance_sdxl": "Guidance scale for SDXL prompts.",
            "default_guidance_qwen": "Guidance scale for Qwen prompts.",
            "default_guidance_qwen_edit": "Guidance scale for Qwen Edit prompts.",
            "default_guidance_wan": "Guidance scale for WAN prompts.",
            "flux_ksampler_sampler": "Default sampler used by Flux generations.",
            "flux_ksampler_scheduler": "Default scheduler algorithm for Flux sampling.",
            "flux_ksampler_cfg": "Base CFG value supplied to the Flux KSampler.",
            "flux_ksampler_denoise": "Default denoise factor applied to Flux KSampler outputs.",
            "sdxl_ksampler_sampler": "Default sampler used by SDXL generations.",
            "sdxl_ksampler_scheduler": "Default scheduler algorithm for SDXL sampling.",
            "sdxl_ksampler_cfg": "Base CFG value supplied to the SDXL KSampler.",
            "sdxl_ksampler_denoise": "Default denoise factor applied to SDXL KSampler outputs.",
            "qwen_ksampler_sampler": "Default sampler used by Qwen generations.",
            "qwen_ksampler_scheduler": "Default scheduler algorithm for Qwen sampling.",
            "qwen_ksampler_cfg": "Base CFG value supplied to the Qwen KSampler.",
            "qwen_ksampler_denoise": "Default denoise factor applied to Qwen KSampler outputs.",
            "qwen_edit_ksampler_sampler": "Default sampler used by Qwen Edit generations.",
            "qwen_edit_ksampler_scheduler": "Default scheduler for the Qwen Edit sampler.",
            "qwen_edit_ksampler_cfg": "Base CFG value for Qwen Edit sampling.",
            "qwen_edit_ksampler_denoise": "Default denoise strength for Qwen Edit sampling.",
            "qwen_edit_cfg_rescale": "CFG rescale multiplier applied to Qwen Edit sampling runs.",
            "wan_stage1_add_noise": "Controls whether WAN stage 1 injects fresh noise before sampling.",
            "wan_stage1_noise_mode": "Noise selection mode for WAN stage 1.",
            "wan_stage1_noise_seed": "Seed used to generate WAN stage 1 noise.",
            "wan_stage1_seed": "Primary seed applied to WAN stage 1 sampling.",
            "wan_stage1_steps": "Total steps executed by WAN stage 1.",
            "wan_stage1_cfg": "CFG value for the high-noise WAN sampler.",
            "wan_stage1_sampler": "Sampler algorithm for WAN stage 1.",
            "wan_stage1_scheduler": "Scheduler used by WAN stage 1.",
            "wan_stage1_start": "Start step offset for WAN stage 1.",
            "wan_stage1_end": "End step target for WAN stage 1.",
            "wan_stage1_return_with_leftover_noise": "Whether WAN stage 1 returns latent noise for chaining.",
            "wan_stage1_denoise": "Denoise factor applied after WAN stage 1 sampling.",
            "wan_stage2_add_noise": "Controls noise injection for WAN stage 2.",
            "wan_stage2_noise_mode": "Noise selection mode for WAN stage 2.",
            "wan_stage2_noise_seed": "Seed used to generate WAN stage 2 noise.",
            "wan_stage2_seed": "Primary seed applied to WAN stage 2 sampling.",
            "wan_stage2_steps": "Total steps executed by WAN stage 2.",
            "wan_stage2_cfg": "CFG value for the low-noise WAN sampler.",
            "wan_stage2_sampler": "Sampler algorithm for WAN stage 2.",
            "wan_stage2_scheduler": "Scheduler used by WAN stage 2.",
            "wan_stage2_start": "Start step offset for WAN stage 2.",
            "wan_stage2_end": "End step target for WAN stage 2.",
            "wan_stage2_return_with_leftover_noise": "Whether WAN stage 2 returns latent noise for chaining.",
            "wan_stage2_denoise": "Denoise factor applied after WAN stage 2 sampling.",
            "flux_upscale_model": "Preferred upscaler for Flux renders.",
            "flux_upscale_sampler": "Sampler used by the Flux upscale workflow.",
            "flux_upscale_scheduler": "Scheduler used by the Flux upscale workflow.",
            "flux_upscale_steps": "Number of sampling steps for Flux upscales.",
            "flux_upscale_cfg": "CFG value for Flux upscaling.",
            "flux_upscale_denoise": "Denoise factor for Flux upscaling.",
            "sdxl_upscale_model": "Preferred upscaler for SDXL renders.",
            "sdxl_upscale_sampler": "Sampler used by the SDXL upscale workflow.",
            "sdxl_upscale_scheduler": "Scheduler used by the SDXL upscale workflow.",
            "sdxl_upscale_steps": "Number of sampling steps for SDXL upscales.",
            "sdxl_upscale_cfg": "CFG value for SDXL upscaling.",
            "sdxl_upscale_denoise": "Denoise factor for SDXL upscaling.",
            "qwen_upscale_model": "Preferred upscaler for Qwen renders.",
            "qwen_upscale_sampler": "Sampler used by the Qwen upscale workflow.",
            "qwen_upscale_scheduler": "Scheduler used by the Qwen upscale workflow.",
            "qwen_upscale_steps": "Number of sampling steps for Qwen upscales.",
            "qwen_upscale_cfg": "CFG value for Qwen upscaling.",
            "qwen_upscale_denoise": "Denoise factor for Qwen upscaling.",
            "default_sdxl_negative_prompt": "Baseline negative prompt applied to SDXL generations.",
            "default_qwen_negative_prompt": "Baseline negative prompt applied to Qwen generations.",
            "default_qwen_edit_negative_prompt": "Baseline negative prompt applied to Qwen Edit generations.",
            "default_wan_negative_prompt": "Baseline negative prompt applied to WAN generations.",
            "kontext_guidance": "Guidance scale used in Kontext operations.",
            "kontext_steps": "Inference steps used for Kontext prompts.",
            "kontext_mp_size": "Megapixel target for Kontext renders.",
            "remix_mode": "When enabled variations remix inputs for greater diversity.",
            "llm_enhancer_enabled": "Toggle LLM powered prompt enhancement before sending to ComfyUI.",
            "llm_provider": "Select which LLM provider backs prompt enhancement.",
            "llm_model": "Specific LLM model used for prompt enhancement with the selected provider.",
            "display_prompt_preference": "Choose whether to show enhanced or original prompts in the UI.",
            "default_qwen_clip": "Default CLIP encoder paired with Qwen checkpoints.",
            "default_qwen_vae": "Default VAE for decoding Qwen latents.",
            "default_qwen_edit_clip": "Default CLIP encoder paired with Qwen Edit checkpoints.",
            "default_qwen_edit_vae": "Default VAE for decoding Qwen Edit latents.",
            "qwen_edit_denoise": "Denoise strength applied during Qwen Edit image blending.",
            "qwen_edit_shift": "Seed shift applied to Qwen Edit sampling runs.",
            "default_wan_clip": "Default WAN text encoder for still-image runs.",
            "default_wan_vae": "Default VAE for decoding WAN latents.",
            "default_wan_vision_clip": "Default WAN vision encoder used during animation.",
            "wan_animation_resolution": "Default resolution for WAN 1-click animations (width x height).",
            "wan_animation_duration": "Number of frames rendered by the WAN animation workflow.",
            "wan_animation_motion_profile": "Guides the LLM to bias WAN animations toward slowmo/low/medium/high motion."
        }

        self.status_banner = StatusBanner(self.master, self.color, self.register_theme_subscriber)

        self.master.show_status_message = self.show_status_message
        self.master.ask_status_yes_no = self.ask_status_yes_no
        self.master.ask_status_string = self.ask_status_string

        self._digits_validator = self.master.register(lambda P: P.isdigit() or P == "")
        self._spinbox_validator_cache = {}

        self._create_menu_bar()

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

    def color(self, key, default=None):
        if key in self.theme_colors:
            return self.theme_colors[key]
        if key in self.base_colors:
            return self.base_colors[key]
        return default

    def register_theme_subscriber(self, callback):
        if callback not in self._theme_subscribers:
            self._theme_subscribers.append(callback)
        try:
            callback()
        except Exception:
            pass

    def register_theme_widget(self, widget, mapping):
        def _apply():
            if not widget or not widget.winfo_exists():
                return
            config = {}
            for option, color_key in mapping.items():
                config[option] = self.color(color_key, color_key if isinstance(color_key, str) else color_key)
            try:
                widget.configure(**config)
            except tk.TclError:
                pass
        self.register_theme_subscriber(_apply)

    def _notify_theme_change(self):
        for callback in list(self._theme_subscribers):
            try:
                callback()
            except Exception:
                continue
        try:
            self.master.configure(bg=self.color("BACKGROUND_COLOR"))
        except tk.TclError:
            pass

    def set_theme(self, theme_name):
        if theme_name not in self.theme_presets:
            return
        self.current_theme_name = theme_name
        self.theme_colors = dict(self.base_colors)
        self.theme_colors.update(self.theme_presets[theme_name])
        self._configure_main_editor_style()
        self._notify_theme_change()

    def toggle_theme(self):
        new_theme = "light" if self.current_theme_name == "dark" else "dark"
        self.set_theme(new_theme)

    def show_status_message(self, message, level="info", duration=DEFAULT_STATUS_DURATION):
        resolved_duration = duration
        allow_dismiss = False
        app_prefs = {}
        if hasattr(self, "config_manager") and getattr(self.config_manager, "config", None):
            app_prefs = self.config_manager.config.get("APP_SETTINGS", {}) or {}

        if duration is DEFAULT_STATUS_DURATION:
            style = str(app_prefs.get("STATUS_NOTIFICATION_STYLE", "timed")).lower()
            if style == "sticky":
                resolved_duration = None
                allow_dismiss = True
            else:
                try:
                    preferred = int(app_prefs.get("STATUS_NOTIFICATION_DURATION_MS", 2000))
                except (TypeError, ValueError):
                    preferred = 2000
                resolved_duration = max(500, min(60000, preferred))
        else:
            resolved_duration = duration
            if resolved_duration is None:
                allow_dismiss = True

        self.status_banner.show(message, level=level, duration=resolved_duration, allow_dismiss=allow_dismiss)

    def ask_status_yes_no(self, title, message):
        return self.status_banner.ask_yes_no(title, message)

    def ask_status_string(self, title, prompt, **kwargs):
        return self.status_banner.ask_string(title, prompt, **kwargs)

    def attach_tooltip(self, widget, text):
        if not text:
            return None
        tooltip = Tooltip(widget, text, self.color)
        setattr(widget, "_tenos_tooltip", tooltip)
        return tooltip

    def _validate_spinbox_value(self, var_key, value, minimum, maximum, is_float):
        tk_var = self.settings_vars.get(var_key)
        if tk_var is None:
            return True

        def _coerce_numeric(raw):
            if is_float:
                return float(raw)
            return int(float(raw))

        try:
            numeric = _coerce_numeric(value)
        except (ValueError, TypeError):
            try:
                current_val = tk_var.get()
                numeric = _coerce_numeric(current_val)
            except (tk.TclError, ValueError, TypeError):
                if minimum is not None:
                    numeric = minimum
                else:
                    numeric = 0.0 if is_float else 0

        if minimum is not None:
            numeric = max(minimum, numeric)
        if maximum is not None:
            numeric = min(maximum, numeric)

        try:
            tk_var.set(numeric)
        except tk.TclError:
            return False
        return True

    def _get_spinbox_validator_command(self, var_key, minimum, maximum, is_float):
        cache_key = (var_key, minimum, maximum, is_float)
        if cache_key not in self._spinbox_validator_cache:
            def _validator(value, key=var_key, min_value=minimum, max_value=maximum, float_flag=is_float):
                return self._validate_spinbox_value(key, value, min_value, max_value, float_flag)

            self._spinbox_validator_cache[cache_key] = self.master.register(_validator)
        return self._spinbox_validator_cache[cache_key]

    def _remember_focus(self, scope, key):
        if scope == "config":
            self.last_focused_config_key = key
        elif scope == "settings":
            self.last_focused_setting_key = key

    def refresh_all_ui_tabs(self):
        self.load_available_files()
        self.populate_main_config_sub_tabs()
        self.admin_control_tab_manager.populate_admin_tab()
        self.populate_bot_settings_tab()
        self.lora_styles_tab_manager.populate_lora_styles_tab()
        self.favorites_tab_manager.populate_all_favorites_sub_tabs()
        self.llm_prompts_tab_manager.load_and_populate_llm_prompts()

    def get_ordered_llm_models_for_provider(self, provider_key):
        provider_data = self.llm_models_config.get('providers', {}).get(provider_key, {})
        models = [m.strip() for m in provider_data.get('models', []) if isinstance(m, str)]
        favorites = [m.strip() for m in provider_data.get('favorites', []) if isinstance(m, str)]

        seen = set()
        ordered_models = []

        for fav_model in favorites:
            if fav_model in models and fav_model not in seen:
                ordered_models.append(fav_model)
                seen.add(fav_model)

        for model in sorted(models, key=str.lower):
            if model not in seen:
                ordered_models.append(model)
                seen.add(model)

        return ordered_models

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
        self.menu_bar = tk.Menu(
            self.master,
            bg=self.color("BACKGROUND_COLOR"),
            fg=self.color("TEXT_COLOR_NORMAL"),
            activebackground=self.color("SELECT_BG_COLOR"),
            activeforeground=self.color("SELECT_FG_COLOR"),
            relief="flat",
            borderwidth=0
        )
        self.master.config(menu=self.menu_bar)
        file_menu = tk.Menu(
            self.menu_bar,
            tearoff=0,
            bg=self.color("WIDGET_BG"),
            fg=self.color("TEXT_COLOR_NORMAL"),
            relief="flat",
            activebackground=self.color("SELECT_BG_COLOR"),
            activeforeground=self.color("SELECT_FG_COLOR")
        )
        file_menu.add_command(label="Save All Configs\tCtrl+S", command=self.save_all_configurations_from_menu)
        file_menu.add_command(label="Export Config & Settings", command=self.export_config_and_settings)
        file_menu.add_separator(background=self.color("BORDER_COLOR"))
        file_menu.add_command(label="Exit", command=self.on_closing_main_window)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        tools_menu = tk.Menu(
            self.menu_bar,
            tearoff=0,
            bg=self.color("WIDGET_BG"),
            fg=self.color("TEXT_COLOR_NORMAL"),
            relief="flat",
            activebackground=self.color("SELECT_BG_COLOR"),
            activeforeground=self.color("SELECT_FG_COLOR")
        )
        tools_menu.add_command(label="Update Application", command=lambda: self.run_worker_task_on_editor(self._worker_update_application, "Updating Application"))
        tools_menu.add_separator(background=self.color("BORDER_COLOR"))
        tools_menu.add_command(label="Install/Update Custom Nodes", command=lambda: self.run_worker_task_on_editor(self._worker_install_custom_nodes, "Installing Nodes"))
        tools_menu.add_command(label="Scan Models/Clips/Checkpoints", command=lambda: self.run_worker_task_on_editor(self._worker_scan_models_clips_checkpoints, "Scanning Files"))
        tools_menu.add_command(label="Refresh LLM Models List", command=lambda: self.run_worker_task_on_editor(self._worker_update_llm_models_list, "Refreshing LLMs"))
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)
        view_menu = tk.Menu(
            self.menu_bar,
            tearoff=0,
            bg=self.color("WIDGET_BG"),
            fg=self.color("TEXT_COLOR_NORMAL"),
            relief="flat",
            activebackground=self.color("SELECT_BG_COLOR"),
            activeforeground=self.color("SELECT_FG_COLOR")
        )
        self.theme_toggle_var = tk.BooleanVar(value=self.current_theme_name == "light")
        view_menu.add_checkbutton(label="Use Light Theme", variable=self.theme_toggle_var, command=self._on_theme_toggle)
        self.menu_bar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(
            self.menu_bar,
            tearoff=0,
            bg=self.color("WIDGET_BG"),
            fg=self.color("TEXT_COLOR_NORMAL"),
            relief="flat",
            activebackground=self.color("SELECT_BG_COLOR"),
            activeforeground=self.color("SELECT_FG_COLOR")
        )
        help_menu.add_command(label="About", command=self.show_about_dialog)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        self.master.bind_all("<Control-s>", lambda event: self.save_all_configurations_from_menu())
        self.master.bind_all("<Control-Shift-s>", lambda event: self.config_manager.save_main_config_data())
        self.master.bind_all("<Control-Alt-s>", lambda event: self.config_manager.save_bot_settings_data())
        self.master.bind_all("<F5>", lambda event: self.refresh_all_ui_tabs())

    def _on_theme_toggle(self):
        self.set_theme("light" if self.theme_toggle_var.get() else "dark")

    def _configure_main_editor_style(self):
        s = self.style
        s.theme_use('clam')

        base_font = ('Segoe UI', 10)
        header_font = ('Segoe UI Semibold', 11)
        s.configure(
            ".",
            background=self.color("BACKGROUND_COLOR"),
            foreground=self.color("TEXT_COLOR_NORMAL"),
            fieldbackground=self.color("ENTRY_BG_COLOR"),
            borderwidth=1,
            font=base_font
        )
        s.map(
            ".",
            background=[("disabled", self.color("FRAME_BG_COLOR"))],
            foreground=[("disabled", self.color("TEXT_COLOR_DISABLED"))],
            fieldbackground=[("disabled", self.color("FRAME_BG_COLOR"))]
        )

        s.configure("TFrame", background=self.color("FRAME_BG_COLOR"))
        s.configure("Tenos.TFrame", background=self.color("FRAME_BG_COLOR"))
        s.configure("TLabel", background=self.color("FRAME_BG_COLOR"), foreground=self.color("TEXT_COLOR_NORMAL"), padding=2)
        s.configure(BOLD_TLABEL_STYLE, font=('Segoe UI Semibold', 11), background=self.color("FRAME_BG_COLOR"), foreground=self.color("TEXT_COLOR_NORMAL"))
        s.configure(ACCENT_TLABEL_STYLE, foreground=self.color("TENOS_MEDIUM_BLUE_ACCENT"), background=self.color("FRAME_BG_COLOR"))
        s.configure("Tenos.Header.TFrame", background=self.color("FRAME_BG_COLOR"))
        s.configure("Tenos.Header.TLabel", background=self.color("FRAME_BG_COLOR"), foreground=self.color("TEXT_COLOR_NORMAL"), font=('Segoe UI Semibold', 14))
        s.configure("Tenos.Subtle.TLabel", background=self.color("FRAME_BG_COLOR"), foreground=self.color("TEXT_COLOR_DISABLED"), font=('Segoe UI', 10))
        s.configure("Tenos.Command.TFrame", background=self.color("FRAME_BG_COLOR"))
        s.configure("Tenos.Command.TLabel", background=self.color("FRAME_BG_COLOR"), foreground=self.color("TEXT_COLOR_NORMAL"))
        s.configure("SearchHighlight.TLabel", background=self.color("FRAME_BG_COLOR"), foreground=self.color("ACCENT_FG"), font=('Segoe UI Semibold', 10))

        s.configure(
            "TButton",
            background=self.color("BUTTON_BG_COLOR"),
            foreground=self.color("BUTTON_FG_COLOR"),
            bordercolor=self.color("BORDER_COLOR"),
            padding=(10, 6),
            relief="raised",
            font=('Segoe UI Semibold', 10)
        )
        s.map(
            "TButton",
            background=[("active", self.color("BUTTON_ACTIVE_BG_COLOR")), ("pressed", self.color("BUTTON_ACTIVE_BG_COLOR")), ("disabled", self.color("FRAME_BG_COLOR"))],
            foreground=[("active", self.color("BUTTON_ACTIVE_FG_COLOR")), ("pressed", self.color("BUTTON_ACTIVE_FG_COLOR")), ("disabled", self.color("TEXT_COLOR_DISABLED"))],
            relief=[("pressed", "sunken"), ("!pressed", "raised")]
        )

        s.configure(
            "Tenos.Command.TButton",
            background=self.color("FRAME_BG_COLOR"),
            foreground=self.color("ACCENT_FG"),
            bordercolor=self.color("BORDER_COLOR"),
            padding=(10, 6),
            relief="groove",
            font=('Segoe UI Semibold', 10)
        )
        s.map(
            "Tenos.Command.TButton",
            background=[("pressed", self.color("TENOS_DARK_BLUE_BG")), ("active", self.color("TENOS_DARK_BLUE_BG")), ("disabled", self.color("FRAME_BG_COLOR"))],
            foreground=[("pressed", self.color("TENOS_WHITE_FG")), ("active", self.color("TENOS_WHITE_FG")), ("disabled", self.color("TEXT_COLOR_DISABLED"))],
            relief=[("pressed", "sunken"), ("!pressed", "groove")]
        )

        s.configure("Toggle.TButton", width=2, padding=2)
        s.map("Toggle.TButton", background=[("active", self.color("BUTTON_ACTIVE_BG_COLOR"))])

        s.configure(
            "TNotebook",
            background=self.color("BACKGROUND_COLOR"),
            tabmargins=[2, 6, 2, 0],
            borderwidth=0
        )
        s.configure(
            "TNotebook.Tab",
            background=self.color("INACTIVE_TAB_BG"),
            foreground=self.color("INACTIVE_TAB_FG"),
            padding=[14, 7],
            font=('Segoe UI Semibold', 10),
            borderwidth=1,
            relief="ridge"
        )
        s.map(
            "TNotebook.Tab",
            background=[("selected", self.color("ACTIVE_TAB_BG")), ("active", self.color("TENOS_LIGHT_BLUE_ACCENT2"))],
            foreground=[("selected", self.color("ACTIVE_TAB_FG")), ("active", self.color("BACKGROUND_COLOR"))],
            relief=[("selected", "flat")]
        )
        s.configure("Tenos.TNotebook", background=self.color("BACKGROUND_COLOR"))

        s.configure(
            "TEntry",
            fieldbackground=self.color("ENTRY_BG_COLOR"),
            foreground=self.color("ENTRY_FG_COLOR"),
            insertcolor=self.color("ENTRY_INSERT_COLOR"),
            bordercolor=self.color("BORDER_COLOR"),
            borderwidth=1,
            relief="groove",
            padding=5,
            font=base_font
        )
        s.map("TEntry", fieldbackground=[("focus", self.color("TENOS_DARK_BLUE_BG"))], bordercolor=[("focus", self.color("TENOS_LIGHT_BLUE_ACCENT2"))])

        s.configure(
            "Tenos.Search.TEntry",
            fieldbackground=self.color("FRAME_BG_COLOR"),
            foreground=self.color("TEXT_COLOR_NORMAL"),
            insertcolor=self.color("ENTRY_INSERT_COLOR"),
            bordercolor=self.color("BORDER_COLOR"),
            borderwidth=1,
            relief="groove",
            padding=(10, 6),
            font=base_font
        )
        s.map("Tenos.Search.TEntry", fieldbackground=[("focus", self.color("BACKGROUND_COLOR"))], bordercolor=[("focus", self.color("TENOS_LIGHT_BLUE_ACCENT2"))])

        s.configure(
            "TCombobox",
            fieldbackground=self.color("ENTRY_BG_COLOR"),
            foreground=self.color("ENTRY_FG_COLOR"),
            selectbackground=self.color("SELECT_BG_COLOR"),
            selectforeground=self.color("SELECT_FG_COLOR"),
            insertcolor=self.color("ENTRY_INSERT_COLOR"),
            arrowcolor=self.color("TEXT_COLOR_NORMAL"),
            arrowsize=16,
            borderwidth=1,
            padding=4,
            relief="groove",
            font=base_font
        )
        s.map(
            "TCombobox",
            fieldbackground=[("readonly", self.color("ENTRY_BG_COLOR")), ("focus", self.color("TENOS_DARK_BLUE_BG"))],
            bordercolor=[("focus", self.color("TENOS_LIGHT_BLUE_ACCENT2"))],
            arrowcolor=[("disabled", self.color("TEXT_COLOR_DISABLED")), ("hover", self.color("TENOS_LIGHT_BLUE_ACCENT2"))]
        )

        s.configure(
            "TSpinbox",
            fieldbackground=self.color("ENTRY_BG_COLOR"),
            foreground=self.color("ENTRY_FG_COLOR"),
            insertcolor=self.color("ENTRY_INSERT_COLOR"),
            arrowsize=12,
            borderwidth=1,
            relief="groove",
            padding=4,
            font=base_font
        )
        s.map("TSpinbox", fieldbackground=[("focus", self.color("TENOS_DARK_BLUE_BG"))], bordercolor=[("focus", self.color("TENOS_LIGHT_BLUE_ACCENT2"))])

        s.configure(
            "TCheckbutton",
            background=self.color("FRAME_BG_COLOR"),
            foreground=self.color("TEXT_COLOR_NORMAL"),
            padding=(6, 4)
        )

        s.configure(
            "Tenos.Switch.TCheckbutton",
            background=self.color("FRAME_BG_COLOR"),
            foreground=self.color("TEXT_COLOR_NORMAL"),
            padding=(8, 4),
            font=('Segoe UI Semibold', 10)
        )
        s.map("Tenos.Switch.TCheckbutton", foreground=[("selected", self.color("ACCENT_FG"))])

        s.configure(
            "Tenos.Highlight.TCheckbutton",
            background=self.color("FRAME_BG_COLOR"),
            foreground=self.color("ACCENT_FG"),
            padding=(6, 4)
        )

        s.configure(
            "TScrollbar",
            troughcolor=self.color("SCROLLBAR_TROUGH_COLOR"),
            background=self.color("SCROLLBAR_SLIDER_COLOR"),
            borderwidth=0,
            relief="flat",
            arrowsize=14
        )
        s.map("TScrollbar", background=[("active", self.color("TENOS_LIGHT_BLUE_ACCENT2"))])
        s.configure("Tenos.Vertical.TScrollbar", background=self.color("SCROLLBAR_SLIDER_COLOR"))

        s.configure("SectionHeader.TFrame", background=self.color("FRAME_BG_COLOR"))
        s.configure("SectionHeader.TLabel", background=self.color("FRAME_BG_COLOR"), foreground=self.color("TEXT_COLOR_NORMAL"), font=header_font)
        s.configure("SectionBody.TFrame", background=self.color("FRAME_BG_COLOR"), padding=(6, 4, 6, 12))
        s.configure("Help.TLabel", background=self.color("FRAME_BG_COLOR"), foreground=self.color("ACCENT_FG"), font=('Segoe UI Semibold', 10))
        s.configure("Tenos.Horizontal.TProgressbar", troughcolor=self.color("SCROLLBAR_TROUGH_COLOR"), background=self.color("TENOS_LIGHT_BLUE_ACCENT2"))

        self.master.option_add("*Font", base_font)
        self.master.option_add("*TCombobox*Listbox*Background", self.color("LISTBOX_BG"))
        self.master.option_add("*TCombobox*Listbox*Foreground", self.color("LISTBOX_FG"))
        self.master.option_add("*TCombobox*Listbox*selectBackground", self.color("LISTBOX_SELECT_BG"))
        self.master.option_add("*TCombobox*Listbox*selectForeground", self.color("LISTBOX_SELECT_FG"))
        self.master.option_add("*TCombobox*Listbox.font", ('Segoe UI', 10))

    def _create_main_config_tab_structure(self):
        self.main_config_tab_frame = ttk.Frame(self.notebook, padding=0, style="Tenos.TFrame")
        self.notebook.add(self.main_config_tab_frame, text=' Main Config ')

        self.config_search_var = tk.StringVar()
        search_container = ttk.Frame(self.main_config_tab_frame, style="Tenos.Command.TFrame", padding=(8, 8, 8, 10))
        search_container.pack(fill=tk.X, padx=5, pady=(4, 0))
        search_container.columnconfigure(1, weight=1)

        ttk.Label(search_container, text="Quick Filter", style="Tenos.TLabel").grid(row=0, column=0, sticky="w")

        self.config_search_entry = ttk.Entry(search_container, textvariable=self.config_search_var, style="Tenos.Search.TEntry")
        self.config_search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.config_search_entry.bind("<Return>", lambda _e: self._focus_first_config_match())
        self.config_search_entry.bind("<Escape>", lambda _e: self.config_search_var.set(""))

        self.config_clear_search_btn = ttk.Button(
            search_container,
            text="Clear",
            style="Tenos.Command.TButton",
            command=lambda: self.config_search_var.set("")
        )
        self.config_clear_search_btn.grid(row=0, column=2, padx=(8, 0))
        self.config_clear_search_btn.state(["disabled"])

        ttk.Label(
            search_container,
            text="Filter config entries instantly. Press Enter to jump to the first match.",
            style="Tenos.Subtle.TLabel"
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.config_search_var.trace_add("write", self._apply_config_search_filter)

        sections = [
            ("getting_started", "Getting Started"),
            ("paths", "File Paths"),
            ("endpoints", "Endpoint URLs"),
            ("api_keys", "API Keys"),
            ("app_settings", "App Settings"),
        ]

        self.main_config_nav = SideNavigationView(self.main_config_tab_frame, sections)
        self.main_config_nav.pack(expand=True, fill="both", padx=5, pady=5)

        self.getting_started_frame = self.main_config_nav.get_section_frame("getting_started")
        self.paths_tab_frame = self.main_config_nav.get_section_frame("paths")
        self.endpoints_tab_frame = self.main_config_nav.get_section_frame("endpoints")
        self.api_keys_tab_frame = self.main_config_nav.get_section_frame("api_keys")
        self.app_settings_tab_frame = self.main_config_nav.get_section_frame("app_settings")

        self.main_config_action_bar = ttk.Frame(self.main_config_tab_frame, style="Tenos.TFrame")
        self.main_config_action_bar.pack(fill=tk.X, padx=5, pady=(0, 10))
        ttk.Button(self.main_config_action_bar, text="Save Main Config", command=self.config_manager.save_main_config_data).pack(side=tk.LEFT)
        self.main_config_status_var = tk.StringVar(value="")
        status_label = ttk.Label(self.main_config_action_bar, textvariable=self.main_config_status_var, style="Tenos.TLabel")
        status_label.pack(side=tk.RIGHT)

        self.register_theme_widget(
            self.main_config_nav.listbox,
            {
                "bg": "LISTBOX_BG",
                "fg": "LISTBOX_FG",
                "selectbackground": "LISTBOX_SELECT_BG",
                "selectforeground": "LISTBOX_SELECT_FG",
                "highlightbackground": "BORDER_COLOR",
                "highlightcolor": "BORDER_COLOR"
            }
        )
        
    def populate_main_config_sub_tabs(self):
        self.config_vars.clear()
        self.config_input_widgets.clear()
        self.config_row_metadata.clear()
        self.config_search_matches = []
        self._config_search_alerted = False

        frames = {
            "paths": self.paths_tab_frame,
            "endpoints": self.endpoints_tab_frame,
            "api_keys": self.api_keys_tab_frame,
            "app_settings": self.app_settings_tab_frame,
        }

        self._populate_getting_started_panel(self.getting_started_frame)

        for frame in frames.values():
            for widget in frame.winfo_children():
                widget.destroy()

        def build_section(parent, title, initially_open=True):
            section = CollapsibleSection(parent, title, self.color, initially_open=initially_open)
            section.pack(fill=tk.X, padx=6, pady=(4, 2))
            return section.body()

        def create_config_row(parent_frame, section_name, item_key_name, nav_section_key, is_path=False, is_port=False):
            row_frame = ttk.Frame(parent_frame, style="Tenos.TFrame")
            row_frame.pack(fill=tk.X, pady=3)
            row_frame.columnconfigure(1, weight=1)

            label_text = item_key_name.replace('_', ' ').title()
            label_widget = ttk.Label(row_frame, text=f"{label_text}:", style="Tenos.TLabel")
            label_widget.grid(row=0, column=0, sticky="w", padx=(0, 10))

            current_item_val = self.config_manager.config.get(section_name, {}).get(item_key_name, "")
            var_key = f"{section_name}.{item_key_name}"
            tk_var = tk.StringVar(value=str(current_item_val) if current_item_val is not None else "")
            self.config_vars[var_key] = tk_var

            upper_key_name = item_key_name.upper()
            show_char_val = "*" if ("KEY" in upper_key_name or "TOKEN" in upper_key_name) else ""

            entry_widget = ttk.Entry(row_frame, textvariable=tk_var, width=(12 if is_port else 50), show=show_char_val, style="Tenos.TEntry")
            entry_widget.grid(row=0, column=1, sticky="ew")
            entry_widget.bind("<FocusIn>", lambda _e, key=var_key: self._remember_focus("config", key))
            self.config_input_widgets[var_key] = entry_widget

            if is_port:
                entry_widget.configure(validate='key', validatecommand=(self._digits_validator, '%P'))

            next_column = 2
            if is_path:
                browse_btn = ttk.Button(row_frame, text="Browse…", command=lambda s=section_name, k=item_key_name: self._browse_folder_for_main_config(s, k))
                browse_btn.grid(row=0, column=next_column, padx=(8, 0))
                next_column += 1

            help_text = self.config_help_text.get(f"{section_name}.{item_key_name}") or f"{label_text} for {section_name.replace('_', ' ').title()}"
            help_label = ttk.Label(row_frame, text="?", style="Help.TLabel")
            help_label.grid(row=0, column=next_column, padx=(8, 0))
            self.attach_tooltip(help_label, help_text)

            self.config_row_metadata[var_key] = {
                "frame": row_frame,
                "pack": {"fill": tk.X, "pady": 3},
                "label": label_text,
                "help_text": help_text or "",
                "label_widget": label_widget,
                "default_style": "Tenos.TLabel",
                "highlight_style": "SearchHighlight.TLabel",
                "focus_widget": entry_widget,
                "section": nav_section_key,
            }

        outputs_body = build_section(self.paths_tab_frame, "Output Locations")
        for key in self.config_manager.config_template_definition.get("OUTPUTS", {}):
            create_config_row(outputs_body, "OUTPUTS", key, nav_section_key="paths", is_path=True)

        models_body = build_section(self.paths_tab_frame, "Model Assets")
        for key in self.config_manager.config_template_definition.get("MODELS", {}):
            create_config_row(models_body, "MODELS", key, nav_section_key="paths", is_path=True)

        text_encoders_body = build_section(self.paths_tab_frame, "Text Encoders", initially_open=False)
        for key in self.config_manager.config_template_definition.get("TEXT_ENCODERS", {}):
            create_config_row(text_encoders_body, "TEXT_ENCODERS", key, nav_section_key="paths", is_path=True)

        clip_body = build_section(self.paths_tab_frame, "CLIP Resources", initially_open=False)
        for key in self.config_manager.config_template_definition.get("CLIP", {}):
            create_config_row(clip_body, "CLIP", key, nav_section_key="paths", is_path=True)

        lora_body = build_section(self.paths_tab_frame, "LoRA Libraries", initially_open=False)
        for key in self.config_manager.config_template_definition.get("LORAS", {}):
            create_config_row(lora_body, "LORAS", key, nav_section_key="paths", is_path=True)

        nodes_body = build_section(self.paths_tab_frame, "Custom Nodes", initially_open=False)
        for key in self.config_manager.config_template_definition.get("NODES", {}):
            create_config_row(nodes_body, "NODES", key, nav_section_key="paths", is_path=True)

        comfy_section = build_section(self.endpoints_tab_frame, "ComfyUI API")
        for key in self.config_manager.config_template_definition.get("COMFYUI_API", {}):
            create_config_row(comfy_section, "COMFYUI_API", key, nav_section_key="endpoints", is_port=(key == "PORT"))

        internal_api_section = build_section(self.endpoints_tab_frame, "Bot Internal API", initially_open=False)
        for key in self.config_manager.config_template_definition.get("BOT_INTERNAL_API", {}):
            create_config_row(internal_api_section, "BOT_INTERNAL_API", key, nav_section_key="endpoints", is_port=(key == "PORT"))

        bot_api_section = build_section(self.api_keys_tab_frame, "Public Bot API")
        for key in self.config_manager.config_template_definition.get("BOT_API", {}):
            create_config_row(bot_api_section, "BOT_API", key, nav_section_key="api_keys")

        llm_section = build_section(self.api_keys_tab_frame, "LLM Enhancer Keys", initially_open=False)
        for key in self.config_manager.config_template_definition.get("LLM_ENHANCER", {}):
            create_config_row(llm_section, "LLM_ENHANCER", key, nav_section_key="api_keys")

        admin_section = build_section(self.api_keys_tab_frame, "Admin Defaults", initially_open=False)
        for key in self.config_manager.config_template_definition.get("ADMIN", {}):
            create_config_row(admin_section, "ADMIN", key, nav_section_key="api_keys")

        app_settings_body = build_section(self.app_settings_tab_frame, "Application Preferences")
        app_settings = self.config_manager.config.get("APP_SETTINGS", {})
        auto_update_var = tk.BooleanVar(value=app_settings.get("AUTO_UPDATE_ON_STARTUP", False))
        self.config_vars["APP_SETTINGS.AUTO_UPDATE_ON_STARTUP"] = auto_update_var

        app_settings_row = ttk.Frame(app_settings_body, style="Tenos.TFrame")
        app_settings_row.pack(fill=tk.X, pady=4)
        auto_update_check = ttk.Checkbutton(app_settings_row,
                                           text="Automatically check for updates on startup",
                                           variable=auto_update_var,
                                           style="Tenos.TCheckbutton")
        auto_update_check.pack(side=tk.LEFT)
        self.config_input_widgets["APP_SETTINGS.AUTO_UPDATE_ON_STARTUP"] = auto_update_check
        self.attach_tooltip(auto_update_check, self.config_help_text.get("APP_SETTINGS.AUTO_UPDATE_ON_STARTUP"))

        self.config_row_metadata["APP_SETTINGS.AUTO_UPDATE_ON_STARTUP"] = {
            "frame": app_settings_row,
            "pack": {"fill": tk.X, "pady": 4},
            "label": "Automatically check for updates on startup",
            "help_text": self.config_help_text.get("APP_SETTINGS.AUTO_UPDATE_ON_STARTUP", ""),
            "label_widget": auto_update_check,
            "default_style": "Tenos.TCheckbutton",
            "highlight_style": "Tenos.Highlight.TCheckbutton",
            "focus_widget": auto_update_check,
            "section": "app_settings",
        }

        notif_style_var = tk.StringVar(value=str(app_settings.get("STATUS_NOTIFICATION_STYLE", "timed")).lower())
        self.config_vars["APP_SETTINGS.STATUS_NOTIFICATION_STYLE"] = notif_style_var
        notif_style_row = ttk.Frame(app_settings_body, style="Tenos.TFrame")
        notif_style_row.pack(fill=tk.X, pady=4)
        ttk.Label(notif_style_row, text="Status Notification Style:", style="Tenos.TLabel").grid(row=0, column=0, sticky="w")
        notif_style_combo = ttk.Combobox(
            notif_style_row,
            textvariable=notif_style_var,
            state="readonly",
            values=["timed", "sticky"],
            width=18,
            style="Tenos.TCombobox"
        )
        notif_style_combo.grid(row=0, column=1, padx=(12, 0), sticky="w")
        self.config_input_widgets["APP_SETTINGS.STATUS_NOTIFICATION_STYLE"] = notif_style_combo
        self.attach_tooltip(notif_style_combo, self.config_help_text.get("APP_SETTINGS.STATUS_NOTIFICATION_STYLE"))
        self.config_row_metadata["APP_SETTINGS.STATUS_NOTIFICATION_STYLE"] = {
            "frame": notif_style_row,
            "pack": {"fill": tk.X, "pady": 4},
            "label": "Status Notification Style",
            "help_text": self.config_help_text.get("APP_SETTINGS.STATUS_NOTIFICATION_STYLE", ""),
            "label_widget": notif_style_combo,
            "default_style": "Tenos.TCombobox",
            "highlight_style": None,
            "focus_widget": notif_style_combo,
            "section": "app_settings",
        }

        duration_default = app_settings.get("STATUS_NOTIFICATION_DURATION_MS", 2000)
        try:
            duration_default = int(duration_default)
        except (TypeError, ValueError):
            duration_default = 2000
        duration_default = max(500, min(60000, duration_default))

        notif_duration_var = tk.StringVar(value=str(duration_default))
        self.config_vars["APP_SETTINGS.STATUS_NOTIFICATION_DURATION_MS"] = notif_duration_var
        notif_duration_row = ttk.Frame(app_settings_body, style="Tenos.TFrame")
        notif_duration_row.pack(fill=tk.X, pady=4)
        ttk.Label(notif_duration_row, text="Notification Duration (ms):", style="Tenos.TLabel").grid(row=0, column=0, sticky="w")
        notif_duration_spin = ttk.Spinbox(
            notif_duration_row,
            from_=500,
            to=60000,
            increment=250,
            textvariable=notif_duration_var,
            width=12,
            validate='key',
            validatecommand=(self._digits_validator, '%P'),
            style="TSpinbox"
        )
        notif_duration_spin.grid(row=0, column=1, padx=(12, 0), sticky="w")
        self.config_input_widgets["APP_SETTINGS.STATUS_NOTIFICATION_DURATION_MS"] = notif_duration_spin
        self.attach_tooltip(notif_duration_spin, self.config_help_text.get("APP_SETTINGS.STATUS_NOTIFICATION_DURATION_MS"))
        self.config_row_metadata["APP_SETTINGS.STATUS_NOTIFICATION_DURATION_MS"] = {
            "frame": notif_duration_row,
            "pack": {"fill": tk.X, "pady": 4},
            "label": "Notification Duration (ms)",
            "help_text": self.config_help_text.get("APP_SETTINGS.STATUS_NOTIFICATION_DURATION_MS", ""),
            "label_widget": notif_duration_spin,
            "default_style": "TSpinbox",
            "highlight_style": None,
            "focus_widget": notif_duration_spin,
            "section": "app_settings",
        }

        def _sync_app_notification_duration(*_args):
            style_key = str(notif_style_var.get()).lower()
            try:
                notif_duration_spin.configure(state='normal' if style_key == 'timed' else 'disabled')
            except tk.TclError:
                pass

        notif_style_var.trace_add('write', lambda *args: _sync_app_notification_duration())
        self.master.after(10, _sync_app_notification_duration)

        buttons_row = ttk.Frame(app_settings_body, style="Tenos.TFrame")
        buttons_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(buttons_row, text="Import Config & Settings", command=self.import_config_and_settings).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(buttons_row, text="Export Config & Settings", command=self.export_config_and_settings).pack(side=tk.LEFT)

        self._apply_config_search_filter()

        if self.last_focused_config_key and self.last_focused_config_key in self.config_input_widgets:
            try:
                self.config_input_widgets[self.last_focused_config_key].focus_set()
            except tk.TclError:
                pass

    def _populate_getting_started_panel(self, frame):
        for child in frame.winfo_children():
            child.destroy()

        intro = ttk.Label(frame, text="Welcome to the Tenos.ai Configurator", style=BOLD_TLABEL_STYLE)
        intro.pack(anchor="w", padx=6, pady=(6, 4))

        summary = ttk.Label(
            frame,
            text=("Follow the checklist below on first launch. You can revisit this panel any time "
                  "to confirm the basics are configured."),
            style="Tenos.TLabel",
            wraplength=520,
            justify=tk.LEFT
        )
        summary.pack(anchor="w", padx=6, pady=(0, 8))

        steps = [
            "Map your output, model, and node folders in the File Paths section.",
            "Confirm ComfyUI and Bot Internal API endpoints respond to requests.",
            "Paste any required API keys for LLM prompt enhancement or public bot access.",
            "Adjust update preferences, then Save Main Config before closing."
        ]

        for step in steps:
            ttk.Label(frame, text=f"• {step}", style="Tenos.TLabel", wraplength=520, justify=tk.LEFT).pack(anchor="w", padx=12, pady=2)

    def _open_search_dialog(self, title, options, tk_var):
        if not options:
            self.show_status_message("No options available for search.", level="warning")
            return
        dialog = SearchableListDialog(self.master, f"Select {title}", options, self.color)
        if dialog.result:
            tk_var.set(dialog.result)

    def _apply_config_search_filter(self, *_args):
        if self.config_search_var is None:
            return
        query = (self.config_search_var.get() or "").strip().lower()
        matches = []

        for key, metadata in self.config_row_metadata.items():
            frame = metadata.get("frame")
            pack_kwargs = metadata.get("pack", {})
            label_text = metadata.get("label", "")
            help_text = metadata.get("help_text", "")
            label_widget = metadata.get("label_widget")
            default_style = metadata.get("default_style")
            highlight_style = metadata.get("highlight_style")

            haystack = " ".join(filter(None, [label_text, key, help_text])).lower()
            matches_query = not query or query in haystack

            if matches_query:
                matches.append(key)
                if frame and frame.winfo_manager() == "":
                    try:
                        frame.pack(**pack_kwargs)
                    except tk.TclError:
                        pass
                if label_widget and highlight_style:
                    try:
                        label_widget.configure(style=highlight_style if query else default_style)
                    except tk.TclError:
                        pass
            else:
                if frame and frame.winfo_manager():
                    try:
                        frame.pack_forget()
                    except tk.TclError:
                        pass
                if label_widget and default_style:
                    try:
                        label_widget.configure(style=default_style)
                    except tk.TclError:
                        pass

        if not query:
            for key, metadata in self.config_row_metadata.items():
                frame = metadata.get("frame")
                pack_kwargs = metadata.get("pack", {})
                if frame and frame.winfo_manager() == "":
                    try:
                        frame.pack(**pack_kwargs)
                    except tk.TclError:
                        pass
                label_widget = metadata.get("label_widget")
                default_style = metadata.get("default_style")
                if label_widget and default_style:
                    try:
                        label_widget.configure(style=default_style)
                    except tk.TclError:
                        pass

        self.config_search_matches = matches

        if self.config_clear_search_btn:
            try:
                if query:
                    self.config_clear_search_btn.state(["!disabled"])
                else:
                    self.config_clear_search_btn.state(["disabled"])
            except tk.TclError:
                pass

        if query and not matches and not self._config_search_alerted:
            self.show_status_message("No matching config entries found.", level="warning", duration=1600)
            self._config_search_alerted = True
        elif not query or matches:
            self._config_search_alerted = False

    def _focus_first_config_match(self):
        if not self.config_search_matches:
            if self.config_search_var and self.config_search_var.get().strip():
                self.show_status_message("No config entries match your search.", level="warning", duration=1600)
            return

        match_key = self.config_search_matches[0]
        metadata = self.config_row_metadata.get(match_key)
        if not metadata:
            return

        self._ensure_main_config_section_visible(metadata.get("section"))
        target_widget = metadata.get("focus_widget") or metadata.get("label_widget")
        if target_widget and target_widget.winfo_exists():
            try:
                target_widget.focus_set()
            except tk.TclError:
                pass

    def _ensure_main_config_section_visible(self, section_key):
        if not section_key or not hasattr(self, "main_config_nav"):
            return
        nav = self.main_config_nav
        try:
            for index, (key, _label) in enumerate(nav.sections):
                if key == section_key:
                    nav.listbox.selection_clear(0, tk.END)
                    nav.listbox.selection_set(index)
                    nav.listbox.activate(index)
                    nav.show_section(section_key)
                    break
        except tk.TclError:
            pass

    def _apply_settings_search_filter(self, *_args):
        if self.settings_search_var is None:
            return
        query = (self.settings_search_var.get() or "").strip().lower()
        matches = []

        for key, metadata in self.settings_row_metadata.items():
            frame = metadata.get("frame")
            pack_kwargs = metadata.get("pack", {})
            label_text = metadata.get("label", "")
            help_text = metadata.get("help_text", "")
            label_widget = metadata.get("label_widget")
            default_style = metadata.get("default_style")
            highlight_style = metadata.get("highlight_style")

            haystack = " ".join(filter(None, [label_text, key, help_text])).lower()
            matches_query = not query or query in haystack

            if matches_query:
                matches.append(key)
                if frame and frame.winfo_manager() == "":
                    try:
                        frame.pack(**pack_kwargs)
                    except tk.TclError:
                        pass
                if label_widget and highlight_style:
                    try:
                        label_widget.configure(style=highlight_style if query else default_style)
                    except tk.TclError:
                        pass
            else:
                if frame and frame.winfo_manager():
                    try:
                        frame.pack_forget()
                    except tk.TclError:
                        pass
                if label_widget and default_style:
                    try:
                        label_widget.configure(style=default_style)
                    except tk.TclError:
                        pass

        if not query:
            for key, metadata in self.settings_row_metadata.items():
                frame = metadata.get("frame")
                pack_kwargs = metadata.get("pack", {})
                if frame and frame.winfo_manager() == "":
                    try:
                        frame.pack(**pack_kwargs)
                    except tk.TclError:
                        pass
                label_widget = metadata.get("label_widget")
                default_style = metadata.get("default_style")
                if label_widget and default_style:
                    try:
                        label_widget.configure(style=default_style)
                    except tk.TclError:
                        pass

        self.settings_search_matches = matches

        if self.settings_clear_search_btn:
            try:
                if query:
                    self.settings_clear_search_btn.state(["!disabled"])
                else:
                    self.settings_clear_search_btn.state(["disabled"])
            except tk.TclError:
                pass

        if query and not matches and not self._settings_search_alerted:
            self.show_status_message("No matching bot settings found.", level="warning", duration=1600)
            self._settings_search_alerted = True
        elif not query or matches:
            self._settings_search_alerted = False

    def _focus_first_settings_match(self):
        if not self.settings_search_matches:
            if self.settings_search_var and self.settings_search_var.get().strip():
                self.show_status_message("No bot settings match your search.", level="warning", duration=1600)
            return

        match_key = self.settings_search_matches[0]
        metadata = self.settings_row_metadata.get(match_key)
        if not metadata:
            return

        self._ensure_settings_section_visible(metadata.get("section"))
        target_widget = metadata.get("focus_widget") or metadata.get("label_widget")
        if target_widget and target_widget.winfo_exists():
            try:
                target_widget.focus_set()
            except tk.TclError:
                pass

    def _ensure_settings_section_visible(self, section_key):
        if not section_key or not hasattr(self, "bot_settings_nav"):
            return
        nav = self.bot_settings_nav
        try:
            for index, (key, _label) in enumerate(nav.sections):
                if key == section_key:
                    nav.listbox.selection_clear(0, tk.END)
                    nav.listbox.selection_set(index)
                    nav.listbox.activate(index)
                    nav.show_section(section_key)
                    break
        except tk.TclError:
            pass

    def _open_config_folder(self):
        base_dir = getattr(self, "app_base_dir", os.getcwd())
        config_path = os.path.abspath(os.path.join(base_dir, CONFIG_FILE_NAME))
        folder_path = os.path.dirname(config_path)
        if not os.path.isdir(folder_path):
            folder_path = base_dir

        try:
            if sys.platform.startswith("win"):
                os.startfile(folder_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
            self.show_status_message("Opened configuration folder in your file explorer.", level="info", duration=1600)
        except Exception as exc:
            self.show_status_message(f"Unable to open config folder: {exc}", level="error", duration=2200)
    def _browse_folder_for_main_config(self, section_name, key_name):
        var_lookup_key = f"{section_name}.{key_name}"
        initial_dir_val = self.config_vars[var_lookup_key].get() if var_lookup_key in self.config_vars else None
        selected_folder_path = browse_folder_dialog(parent=self.master, initialdir=initial_dir_val or os.getcwd(), title=f"Select Folder for {key_name}")
        if selected_folder_path and var_lookup_key in self.config_vars: self.config_vars[var_lookup_key].set(selected_folder_path)

    def _create_bot_settings_tab_structure(self):
        self.bot_settings_tab_frame = ttk.Frame(self.notebook, padding="5", style="Tenos.TFrame")
        self.notebook.add(self.bot_settings_tab_frame, text=' Bot Settings ')

        self.settings_search_var = tk.StringVar()
        settings_search_container = ttk.Frame(self.bot_settings_tab_frame, style="Tenos.Command.TFrame", padding=(8, 8, 8, 10))
        settings_search_container.pack(fill=tk.X, padx=5, pady=(0, 0))
        settings_search_container.columnconfigure(1, weight=1)

        ttk.Label(settings_search_container, text="Search Settings", style="Tenos.TLabel").grid(row=0, column=0, sticky="w")

        self.settings_search_entry = ttk.Entry(settings_search_container, textvariable=self.settings_search_var, style="Tenos.Search.TEntry")
        self.settings_search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.settings_search_entry.bind("<Return>", lambda _e: self._focus_first_settings_match())
        self.settings_search_entry.bind("<Escape>", lambda _e: self.settings_search_var.set(""))

        self.settings_clear_search_btn = ttk.Button(
            settings_search_container,
            text="Clear",
            style="Tenos.Command.TButton",
            command=lambda: self.settings_search_var.set("")
        )
        self.settings_clear_search_btn.grid(row=0, column=2, padx=(8, 0))
        self.settings_clear_search_btn.state(["disabled"])

        ttk.Label(
            settings_search_container,
            text="Find settings across categories. Press Enter to focus the first match.",
            style="Tenos.Subtle.TLabel"
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.settings_search_var.trace_add("write", self._apply_settings_search_filter)

        sections = [
            ("general", "General"),
            ("flux", "Flux"),
            ("sdxl", "SDXL"),
            ("qwen", "Qwen"),
            ("qwen_edit", "Qwen Edit"),
            ("wan", "WAN"),
            ("kontext", "Kontext"),
            ("llm", "LLM"),
        ]

        self.bot_settings_nav = SideNavigationView(self.bot_settings_tab_frame, sections)
        self.bot_settings_nav.pack(expand=True, fill="both", padx=5, pady=5)

        self.general_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("general"))
        self.flux_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("flux"))
        self.sdxl_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("sdxl"))
        self.qwen_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("qwen"))
        self.qwen_edit_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("qwen_edit"))
        self.wan_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("wan"))
        self.kontext_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("kontext"))
        self.llm_settings_content_frame = self._create_scrollable_sub_tab_frame(self.bot_settings_nav.get_section_frame("llm"))

        buttons_frame = ttk.Frame(self.bot_settings_tab_frame, style="Tenos.TFrame")
        buttons_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        ttk.Button(buttons_frame, text="Reset to Defaults", command=self.reset_bot_settings_to_defaults).pack(side=tk.LEFT)
        ttk.Button(buttons_frame, text="Save Bot Settings", command=self.config_manager.save_bot_settings_data).pack(side=tk.LEFT, padx=(8, 0))
        self.bot_settings_status_var = tk.StringVar(value="")
        ttk.Label(buttons_frame, textvariable=self.bot_settings_status_var, style="Tenos.TLabel").pack(side=tk.RIGHT)

        self.register_theme_widget(
            self.bot_settings_nav.listbox,
            {
                "bg": "LISTBOX_BG",
                "fg": "LISTBOX_FG",
                "selectbackground": "LISTBOX_SELECT_BG",
                "selectforeground": "LISTBOX_SELECT_FG",
                "highlightbackground": "BORDER_COLOR",
                "highlightcolor": "BORDER_COLOR"
            }
        )
    def _create_scrollable_sub_tab_frame(self, parent_tab_frame):
        for widget_child in parent_tab_frame.winfo_children():
            widget_child.destroy()
        container_frame = ttk.Frame(parent_tab_frame, style="Tenos.TFrame")
        container_frame.pack(fill="both", expand=True)
        canvas_widget = tk.Canvas(container_frame, bg=self.color("CANVAS_BG_COLOR"), highlightthickness=0)
        self.register_theme_widget(canvas_widget, {"bg": "CANVAS_BG_COLOR"})
        scrollbar_widget = ttk.Scrollbar(container_frame, orient="vertical", command=canvas_widget.yview, style="Tenos.Vertical.TScrollbar")
        canvas_widget.associated_scrollbar = scrollbar_widget
        scrollable_content_frame = ttk.Frame(canvas_widget, style="Tenos.TFrame")
        scrollable_content_frame.bind(
            "<Configure>", lambda event, c=canvas_widget: self._debounce_canvas_configure(c, event)
        )
        canvas_widget.create_window((0, 0), window=scrollable_content_frame, anchor="nw")
        canvas_widget.configure(yscrollcommand=scrollbar_widget.set)
        canvas_widget.pack(side="left", fill="both", expand=True)
        scrollbar_widget.pack(side="right", fill="y")
        return scrollable_content_frame
    def populate_bot_settings_tab(self):
        self.settings_vars.clear()
        self._spinbox_validator_cache.clear()
        self.bot_settings_widgets.clear()
        self.settings_row_metadata.clear()
        self.settings_search_matches = []
        self._settings_search_alerted = False
        current_settings_template_dict = self.config_manager.settings_template_factory()

        for frame in [
            self.general_settings_content_frame,
            self.flux_settings_content_frame,
            self.sdxl_settings_content_frame,
            self.qwen_settings_content_frame,
            self.qwen_edit_settings_content_frame,
            self.wan_settings_content_frame,
            self.kontext_settings_content_frame,
            self.llm_settings_content_frame,
        ]:
            for widget in frame.winfo_children():
                widget.destroy()

        def create_setting_row_ui(parent_frame, label_txt, widget_class, options_data=None, var_key_name=None,
                                   section_key=None, is_llm_model_selector_field=False, is_text_area_field=False,
                                   quick_actions=None, help_key=None, **widget_kwargs):
            container = ttk.Frame(parent_frame, style="Tenos.TFrame")
            container.pack(fill=tk.X, padx=6, pady=3)
            container.columnconfigure(1, weight=1)

            label_ui = ttk.Label(container, text=label_txt + ":", style="Tenos.TLabel")
            label_ui.grid(row=0, column=0, sticky='w', padx=(0, 10))
            help_text = self.settings_help_text.get(help_key or var_key_name, f"{label_txt} setting.")
            help_label = ttk.Label(container, text="?", style="Help.TLabel")

            tk_var_instance = None
            if var_key_name in [
                'default_guidance',
                'upscale_factor',
                'default_guidance_sdxl',
                'default_guidance_qwen',
                'default_guidance_qwen_edit',
                'default_guidance_wan',
                'default_mp_size',
                'kontext_guidance',
                'kontext_mp_size',
                'default_qwen_shift',
                'default_wan_shift',
                'qwen_edit_denoise',
                'qwen_edit_shift',
                'flux_ksampler_cfg',
                'flux_ksampler_denoise',
                'sdxl_ksampler_cfg',
                'sdxl_ksampler_denoise',
                'qwen_ksampler_cfg',
                'qwen_ksampler_denoise',
                'qwen_edit_ksampler_cfg',
                'qwen_edit_ksampler_denoise',
                'wan_stage1_cfg',
                'wan_stage1_denoise',
                'wan_stage2_cfg',
                'wan_stage2_denoise',
                'flux_upscale_cfg',
                'flux_upscale_denoise',
                'sdxl_upscale_cfg',
                'sdxl_upscale_denoise',
                'qwen_upscale_cfg',
                'qwen_upscale_denoise',
            ]:
                tk_var_instance = tk.DoubleVar()
            elif var_key_name in [
                'steps', 'sdxl_steps', 'qwen_steps', 'qwen_edit_steps', 'wan_steps', 'default_batch_size',
                'kontext_steps', 'variation_batch_size', 'wan_animation_duration',
                'wan_stage1_noise_seed', 'wan_stage1_seed', 'wan_stage1_steps', 'wan_stage1_start', 'wan_stage1_end',
                'wan_stage2_noise_seed', 'wan_stage2_seed', 'wan_stage2_steps', 'wan_stage2_start', 'wan_stage2_end',
                'flux_upscale_steps', 'sdxl_upscale_steps', 'qwen_upscale_steps'
            ]:
                tk_var_instance = tk.IntVar()
            elif var_key_name in ['remix_mode', 'llm_enhancer_enabled']:
                tk_var_instance = tk.BooleanVar()
            else:
                tk_var_instance = tk.StringVar()

            current_setting_val = self.config_manager.settings.get(var_key_name)
            if current_setting_val is not None:
                try:
                    if var_key_name == 'llm_provider':
                        tk_var_instance.set(self.provider_display_map.get(current_setting_val, current_setting_val))
                    elif var_key_name == 'display_prompt_preference':
                        tk_var_instance.set(self.display_prompt_map.get(current_setting_val, current_setting_val))
                    elif var_key_name == 'status_notification_style':
                        tk_var_instance.set(self.notification_style_display_map.get(current_setting_val, current_setting_val))
                    else:
                        tk_var_instance.set(current_setting_val)
                except (ValueError, tk.TclError):
                    tk_var_instance.set(current_settings_template_dict.get(var_key_name, ''))

            ui_element = None
            actions = list(quick_actions or [])

            if is_text_area_field:
                ui_element = scrolledtext.ScrolledText(
                    container,
                    wrap=tk.WORD,
                    height=4,
                    width=48,
                    font=("Segoe UI", 10),
                    relief="groove",
                    borderwidth=1
                )
                ui_element.insert(tk.END, tk_var_instance.get() if tk_var_instance.get() else "")
                self.register_theme_widget(ui_element, {
                    "bg": "ENTRY_BG_COLOR",
                    "fg": "ENTRY_FG_COLOR",
                    "insertbackground": "ENTRY_INSERT_COLOR"
                })
            elif widget_class == ttk.Combobox:
                safe_options_list = options_data if isinstance(options_data, list) else []
                display_options = safe_options_list
                if var_key_name == 'llm_provider':
                    display_options = [self.provider_display_map.get(k, k) for k in safe_options_list]
                elif var_key_name == 'display_prompt_preference':
                    display_options = [self.display_prompt_map.get(k, k) for k in sorted(self.display_prompt_map.keys())]

                current_display_value = tk_var_instance.get()
                if current_display_value and current_display_value not in display_options:
                    display_options = [current_display_value] + [opt for opt in display_options if opt != current_display_value]

                ui_element = ttk.Combobox(
                    container,
                    textvariable=tk_var_instance,
                    values=display_options,
                    state="readonly",
                    width=40,
                    style="Tenos.TCombobox"
                )

                if var_key_name == 'llm_provider':
                    tk_var_instance.trace_add("write", lambda *args, vk=var_key_name: self.on_llm_provider_change_for_editor(vk))
                if display_options and not tk_var_instance.get():
                    tk_var_instance.set(display_options[0])
                if display_options and len(display_options) > 15:
                    actions.append(("Search", lambda opts=display_options, var=tk_var_instance: self._open_search_dialog(label_txt, opts, var)))
            elif widget_class == ttk.Spinbox:
                spinbox_kwargs = {
                    "textvariable": tk_var_instance,
                    "wrap": False,
                    "width": 12,
                    "style": "Tenos.TSpinbox",
                }
                spinbox_kwargs.update(widget_kwargs)
                ui_element = ttk.Spinbox(container, **spinbox_kwargs)
                min_val = widget_kwargs.get('from_', None)
                max_val = widget_kwargs.get('to', None)
                validator_cmd = self._get_spinbox_validator_command(
                    var_key_name,
                    min_val,
                    max_val,
                    isinstance(tk_var_instance, tk.DoubleVar)
                )
                ui_element.configure(validate='focusout', validatecommand=(validator_cmd, '%P'))
            elif widget_class == ttk.Checkbutton:
                ui_element = ttk.Checkbutton(container, variable=tk_var_instance, style="Tenos.TCheckbutton")
            else:
                ui_element = ttk.Entry(container, textvariable=tk_var_instance, width=42, style="Tenos.TEntry")

            ui_element.grid(row=0, column=1, sticky='ew')
            if hasattr(ui_element, 'bind'):
                ui_element.bind("<FocusIn>", lambda _e, key=var_key_name: self._remember_focus("settings", key))

            actions_column = 2
            if actions:
                action_frame = ttk.Frame(container, style="Tenos.TFrame")
                action_frame.grid(row=0, column=actions_column, padx=(0, 0))
                for text_action, callback in actions:
                    ttk.Button(action_frame, text=text_action, command=callback).pack(side=tk.LEFT, padx=2)
                actions_column += 1

            help_label.grid(row=0, column=actions_column, padx=(8, 0))
            self.attach_tooltip(help_label, help_text)

            if is_llm_model_selector_field:
                self.bot_settings_widgets['llm_model_label'] = label_ui
                self.bot_settings_widgets['llm_model_label_base'] = label_txt

            self.settings_vars[var_key_name] = tk_var_instance
            self.bot_settings_widgets[var_key_name] = ui_element

            metadata_section = section_key or 'general'
            self.settings_row_metadata[var_key_name] = {
                "frame": container,
                "pack": {"fill": tk.X, "padx": 6, "pady": 3},
                "label": label_txt,
                "help_text": help_text or "",
                "label_widget": label_ui,
                "default_style": "Tenos.TLabel",
                "highlight_style": "SearchHighlight.TLabel",
                "focus_widget": ui_element,
                "section": metadata_section,
            }

            return ui_element

        # General Tab Sections
        general_models_section = CollapsibleSection(self.general_settings_content_frame, "Model Selection", self.color)
        general_models_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        active_family_options = ['flux', 'sdxl', 'qwen', 'wan']
        create_setting_row_ui(
            general_models_section.body(),
            "Active Model Family",
            ttk.Combobox,
            active_family_options,
            'active_model_family',
            section_key='general'
        )
        create_setting_row_ui(
            general_models_section.body(),
            "Default Editing Workflow",
            ttk.Combobox,
            ['kontext', 'qwen'],
            'default_editing_mode',
            section_key='general'
        )
        general_defaults_section = CollapsibleSection(self.general_settings_content_frame, "Generation Defaults", self.color)
        general_defaults_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        create_setting_row_ui(general_defaults_section.body(), "Default Variation Mode", ttk.Combobox, ['weak', 'strong'], 'default_variation_mode', section_key='general')
        create_setting_row_ui(general_defaults_section.body(), "Variation Remix Mode", ttk.Checkbutton, var_key_name='remix_mode', section_key='general')
        create_setting_row_ui(general_defaults_section.body(), "Default Batch Size (/gen)", ttk.Spinbox, var_key_name='default_batch_size', section_key='general', from_=1, to=6, increment=1)
        create_setting_row_ui(general_defaults_section.body(), "Default Batch Size (Vary)", ttk.Spinbox, var_key_name='variation_batch_size', section_key='general', from_=1, to=6, increment=1)
        create_setting_row_ui(general_defaults_section.body(), "Default Upscale Factor", ttk.Spinbox, var_key_name='upscale_factor', section_key='general', from_=1.0, to=4.0, increment=0.05, format="%.2f")
        create_setting_row_ui(general_defaults_section.body(), "Default MP Size", ttk.Spinbox, var_key_name='default_mp_size', section_key='general', from_=0.1, to=8.0, increment=0.05, format="%.2f")

        # Flux Section
        flux_styles = sorted([name for name, data in self.styles_config.items() if data.get('model_type', 'all') in ['all', 'flux']])
        flux_section = CollapsibleSection(self.flux_settings_content_frame, "Flux Defaults", self.color)
        flux_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        create_setting_row_ui(flux_section.body(), "Default Model", ttk.Combobox, self.available_models, 'default_flux_model', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Selected T5 Clip", ttk.Combobox, self.available_clips_t5, 'selected_t5_clip', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Selected Clip-L", ttk.Combobox, self.available_clips_l, 'selected_clip_l', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Default Flux VAE", ttk.Combobox, self.available_vaes, 'default_flux_vae', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Default Style", ttk.Combobox, flux_styles, 'default_style_flux', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Default Steps", ttk.Spinbox, var_key_name='steps', section_key='flux', from_=4, to=128, increment=4)
        create_setting_row_ui(flux_section.body(), "Default Guidance", ttk.Spinbox, var_key_name='default_guidance', section_key='flux', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(flux_section.body(), "KSampler Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'flux_ksampler_sampler', section_key='flux')
        create_setting_row_ui(flux_section.body(), "KSampler Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'flux_ksampler_scheduler', section_key='flux')
        create_setting_row_ui(flux_section.body(), "KSampler CFG", ttk.Spinbox, var_key_name='flux_ksampler_cfg', section_key='flux', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(flux_section.body(), "KSampler Denoise", ttk.Spinbox, var_key_name='flux_ksampler_denoise', section_key='flux', from_=0.0, to=1.0, increment=0.01, format="%.2f")
        create_setting_row_ui(flux_section.body(), "Upscale Model", ttk.Combobox, self.available_upscale_models, 'flux_upscale_model', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Upscale Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'flux_upscale_sampler', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Upscale Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'flux_upscale_scheduler', section_key='flux')
        create_setting_row_ui(flux_section.body(), "Upscale Steps", ttk.Spinbox, var_key_name='flux_upscale_steps', section_key='flux', from_=1, to=256, increment=1)
        create_setting_row_ui(flux_section.body(), "Upscale CFG", ttk.Spinbox, var_key_name='flux_upscale_cfg', section_key='flux', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(flux_section.body(), "Upscale Denoise", ttk.Spinbox, var_key_name='flux_upscale_denoise', section_key='flux', from_=0.0, to=1.0, increment=0.01, format="%.2f")

        # SDXL Section
        sdxl_styles = sorted([name for name, data in self.styles_config.items() if data.get('model_type', 'all') in ['all', 'sdxl']])
        sdxl_section = CollapsibleSection(self.sdxl_settings_content_frame, "SDXL Defaults", self.color)
        sdxl_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        create_setting_row_ui(sdxl_section.body(), "Default Checkpoint", ttk.Combobox, self.available_checkpoints, 'default_sdxl_checkpoint', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "Default Style", ttk.Combobox, sdxl_styles, 'default_style_sdxl', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "Default SDXL CLIP", ttk.Combobox, self.available_clips_l, 'default_sdxl_clip', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "Default SDXL VAE", ttk.Combobox, self.available_vaes, 'default_sdxl_vae', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "Default Steps", ttk.Spinbox, var_key_name='sdxl_steps', section_key='sdxl', from_=4, to=128, increment=2)
        create_setting_row_ui(sdxl_section.body(), "Default Guidance", ttk.Spinbox, var_key_name='default_guidance_sdxl', section_key='sdxl', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(sdxl_section.body(), "KSampler Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'sdxl_ksampler_sampler', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "KSampler Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'sdxl_ksampler_scheduler', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "KSampler CFG", ttk.Spinbox, var_key_name='sdxl_ksampler_cfg', section_key='sdxl', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(sdxl_section.body(), "KSampler Denoise", ttk.Spinbox, var_key_name='sdxl_ksampler_denoise', section_key='sdxl', from_=0.0, to=1.0, increment=0.01, format="%.2f")
        create_setting_row_ui(sdxl_section.body(), "Upscale Model", ttk.Combobox, self.available_upscale_models, 'sdxl_upscale_model', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "Upscale Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'sdxl_upscale_sampler', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "Upscale Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'sdxl_upscale_scheduler', section_key='sdxl')
        create_setting_row_ui(sdxl_section.body(), "Upscale Steps", ttk.Spinbox, var_key_name='sdxl_upscale_steps', section_key='sdxl', from_=1, to=256, increment=1)
        create_setting_row_ui(sdxl_section.body(), "Upscale CFG", ttk.Spinbox, var_key_name='sdxl_upscale_cfg', section_key='sdxl', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(sdxl_section.body(), "Upscale Denoise", ttk.Spinbox, var_key_name='sdxl_upscale_denoise', section_key='sdxl', from_=0.0, to=1.0, increment=0.01, format="%.2f")
        create_setting_row_ui(sdxl_section.body(), "Default Negative Prompt", scrolledtext.ScrolledText, var_key_name='default_sdxl_negative_prompt', section_key='sdxl', is_text_area_field=True)

        qwen_styles = sorted([name for name, data in self.styles_config.items() if data.get('model_type', 'all') in ['all', 'qwen']])
        qwen_section = CollapsibleSection(self.qwen_settings_content_frame, "Qwen Defaults", self.color)
        qwen_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        create_setting_row_ui(qwen_section.body(), "Default Model", ttk.Combobox, self.available_qwen_models, 'default_qwen_checkpoint', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "Default Style", ttk.Combobox, qwen_styles, 'default_style_qwen', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "Default Steps", ttk.Spinbox, var_key_name='qwen_steps', section_key='qwen', from_=4, to=128, increment=2)
        create_setting_row_ui(qwen_section.body(), "Default Guidance", ttk.Spinbox, var_key_name='default_guidance_qwen', section_key='qwen', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(qwen_section.body(), "Default Negative Prompt", scrolledtext.ScrolledText, var_key_name='default_qwen_negative_prompt', section_key='qwen', is_text_area_field=True)
        qwen_clip_options = list(dict.fromkeys(['None'] + self.available_qwen_clips))
        create_setting_row_ui(qwen_section.body(), "Default Qwen CLIP", ttk.Combobox, qwen_clip_options, 'default_qwen_clip', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "Default Qwen VAE", ttk.Combobox, self.available_qwen_vaes, 'default_qwen_vae', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "Default Qwen Shift", ttk.Spinbox, var_key_name='default_qwen_shift', section_key='qwen', from_=0.0, to=10.0, increment=0.1, format="%.2f")
        create_setting_row_ui(qwen_section.body(), "KSampler Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'qwen_ksampler_sampler', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "KSampler Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'qwen_ksampler_scheduler', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "KSampler CFG", ttk.Spinbox, var_key_name='qwen_ksampler_cfg', section_key='qwen', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(qwen_section.body(), "KSampler Denoise", ttk.Spinbox, var_key_name='qwen_ksampler_denoise', section_key='qwen', from_=0.0, to=1.0, increment=0.01, format="%.2f")
        create_setting_row_ui(qwen_section.body(), "Upscale Model", ttk.Combobox, self.available_upscale_models, 'qwen_upscale_model', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "Upscale Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'qwen_upscale_sampler', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "Upscale Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'qwen_upscale_scheduler', section_key='qwen')
        create_setting_row_ui(qwen_section.body(), "Upscale Steps", ttk.Spinbox, var_key_name='qwen_upscale_steps', section_key='qwen', from_=1, to=256, increment=1)
        create_setting_row_ui(qwen_section.body(), "Upscale CFG", ttk.Spinbox, var_key_name='qwen_upscale_cfg', section_key='qwen', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(qwen_section.body(), "Upscale Denoise", ttk.Spinbox, var_key_name='qwen_upscale_denoise', section_key='qwen', from_=0.0, to=1.0, increment=0.01, format="%.2f")

        qwen_edit_section = CollapsibleSection(self.qwen_edit_settings_content_frame, "Qwen Edit Defaults", self.color)
        qwen_edit_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        create_setting_row_ui(qwen_edit_section.body(), "Default Model", ttk.Combobox, self.available_qwen_edit_models, 'default_qwen_edit_checkpoint', section_key='qwen_edit')
        create_setting_row_ui(qwen_edit_section.body(), "Default Steps", ttk.Spinbox, var_key_name='qwen_edit_steps', section_key='qwen_edit', from_=4, to=128, increment=2)
        create_setting_row_ui(qwen_edit_section.body(), "Default Guidance", ttk.Spinbox, var_key_name='default_guidance_qwen_edit', section_key='qwen_edit', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(qwen_edit_section.body(), "Default Negative Prompt", scrolledtext.ScrolledText, var_key_name='default_qwen_edit_negative_prompt', section_key='qwen_edit', is_text_area_field=True)
        qwen_edit_clip_options = list(dict.fromkeys(['None'] + self.available_qwen_clips))
        create_setting_row_ui(qwen_edit_section.body(), "Default Qwen Edit CLIP", ttk.Combobox, qwen_edit_clip_options, 'default_qwen_edit_clip', section_key='qwen_edit')
        create_setting_row_ui(qwen_edit_section.body(), "Default Qwen Edit VAE", ttk.Combobox, self.available_qwen_vaes, 'default_qwen_edit_vae', section_key='qwen_edit')
        create_setting_row_ui(qwen_edit_section.body(), "Qwen Edit Denoise", ttk.Spinbox, var_key_name='qwen_edit_denoise', section_key='qwen_edit', from_=0.0, to=1.0, increment=0.01, format="%.2f")
        create_setting_row_ui(qwen_edit_section.body(), "Qwen Edit Shift", ttk.Spinbox, var_key_name='qwen_edit_shift', section_key='qwen_edit', from_=0.0, to=10.0, increment=0.1, format="%.2f")
        create_setting_row_ui(qwen_edit_section.body(), "CFG Rescale", ttk.Spinbox, var_key_name='qwen_edit_cfg_rescale', section_key='qwen_edit', from_=0.0, to=2.0, increment=0.05, format="%.2f")
        create_setting_row_ui(qwen_edit_section.body(), "KSampler Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'qwen_edit_ksampler_sampler', section_key='qwen_edit')
        create_setting_row_ui(qwen_edit_section.body(), "KSampler Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'qwen_edit_ksampler_scheduler', section_key='qwen_edit')
        create_setting_row_ui(qwen_edit_section.body(), "KSampler CFG", ttk.Spinbox, var_key_name='qwen_edit_ksampler_cfg', section_key='qwen_edit', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(qwen_edit_section.body(), "KSampler Denoise", ttk.Spinbox, var_key_name='qwen_edit_ksampler_denoise', section_key='qwen_edit', from_=0.0, to=1.0, increment=0.01, format="%.2f")

        wan_styles = sorted([name for name, data in self.styles_config.items() if data.get('model_type', 'all') in ['all', 'wan']])
        wan_section = CollapsibleSection(self.wan_settings_content_frame, "WAN Defaults", self.color)
        wan_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        create_setting_row_ui(wan_section.body(), "T2V High-Noise UNet", ttk.Combobox, self.available_wan_models, WAN_T2V_HIGH_NOISE_KEY, section_key='wan')
        create_setting_row_ui(wan_section.body(), "T2V Low-Noise UNet", ttk.Combobox, self.available_wan_video_models, WAN_T2V_LOW_NOISE_KEY, section_key='wan')
        create_setting_row_ui(wan_section.body(), "I2V High-Noise UNet", ttk.Combobox, self.available_wan_video_models, WAN_I2V_HIGH_NOISE_KEY, section_key='wan')
        create_setting_row_ui(wan_section.body(), "I2V Low-Noise UNet", ttk.Combobox, self.available_wan_video_models, WAN_I2V_LOW_NOISE_KEY, section_key='wan')
        create_setting_row_ui(wan_section.body(), "Default Style", ttk.Combobox, wan_styles, 'default_style_wan', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Default Steps", ttk.Spinbox, var_key_name='wan_steps', section_key='wan', from_=4, to=128, increment=2)
        create_setting_row_ui(wan_section.body(), "Default Guidance", ttk.Spinbox, var_key_name='default_guidance_wan', section_key='wan', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(wan_section.body(), "Default Negative Prompt", scrolledtext.ScrolledText, var_key_name='default_wan_negative_prompt', section_key='wan', is_text_area_field=True)
        wan_clip_options = list(dict.fromkeys(['None'] + self.available_wan_clips))
        wan_vision_options = list(dict.fromkeys(['None'] + self.available_wan_vision))
        create_setting_row_ui(wan_section.body(), "Default WAN CLIP", ttk.Combobox, wan_clip_options, 'default_wan_clip', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Default WAN VAE", ttk.Combobox, self.available_wan_vaes, 'default_wan_vae', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Default Vision Encoder", ttk.Combobox, wan_vision_options, 'default_wan_vision_clip', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Default WAN Shift", ttk.Spinbox, var_key_name='default_wan_shift', section_key='wan', from_=0.0, to=10.0, increment=0.1, format="%.2f")
        create_setting_row_ui(wan_section.body(), "Stage 1 Add Noise", ttk.Combobox, ['enable', 'disable'], 'wan_stage1_add_noise', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 1 Noise Mode", ttk.Combobox, ['randomize', 'fixed'], 'wan_stage1_noise_mode', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 1 Noise Seed", ttk.Entry, var_key_name='wan_stage1_noise_seed', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 1 Seed", ttk.Entry, var_key_name='wan_stage1_seed', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 1 Steps", ttk.Spinbox, var_key_name='wan_stage1_steps', section_key='wan', from_=1, to=256, increment=1)
        create_setting_row_ui(wan_section.body(), "Stage 1 CFG", ttk.Spinbox, var_key_name='wan_stage1_cfg', section_key='wan', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(wan_section.body(), "Stage 1 Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'wan_stage1_sampler', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 1 Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'wan_stage1_scheduler', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 1 Start Step", ttk.Spinbox, var_key_name='wan_stage1_start', section_key='wan', from_=0, to=1000, increment=1)
        create_setting_row_ui(wan_section.body(), "Stage 1 End Step", ttk.Spinbox, var_key_name='wan_stage1_end', section_key='wan', from_=0, to=1000, increment=1)
        create_setting_row_ui(wan_section.body(), "Stage 1 Return Leftover", ttk.Combobox, ['enable', 'disable'], 'wan_stage1_return_with_leftover_noise', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 1 Denoise", ttk.Spinbox, var_key_name='wan_stage1_denoise', section_key='wan', from_=0.0, to=1.0, increment=0.01, format="%.2f")
        create_setting_row_ui(wan_section.body(), "Stage 2 Add Noise", ttk.Combobox, ['enable', 'disable'], 'wan_stage2_add_noise', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 2 Noise Mode", ttk.Combobox, ['randomize', 'fixed'], 'wan_stage2_noise_mode', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 2 Noise Seed", ttk.Entry, var_key_name='wan_stage2_noise_seed', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 2 Seed", ttk.Entry, var_key_name='wan_stage2_seed', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 2 Steps", ttk.Spinbox, var_key_name='wan_stage2_steps', section_key='wan', from_=1, to=256, increment=1)
        create_setting_row_ui(wan_section.body(), "Stage 2 CFG", ttk.Spinbox, var_key_name='wan_stage2_cfg', section_key='wan', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(wan_section.body(), "Stage 2 Sampler", ttk.Combobox, KSAMPLER_SAMPLER_OPTIONS, 'wan_stage2_sampler', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 2 Scheduler", ttk.Combobox, KSAMPLER_SCHEDULER_OPTIONS, 'wan_stage2_scheduler', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 2 Start Step", ttk.Spinbox, var_key_name='wan_stage2_start', section_key='wan', from_=0, to=1000, increment=1)
        create_setting_row_ui(wan_section.body(), "Stage 2 End Step", ttk.Spinbox, var_key_name='wan_stage2_end', section_key='wan', from_=0, to=1000, increment=1)
        create_setting_row_ui(wan_section.body(), "Stage 2 Return Leftover", ttk.Combobox, ['enable', 'disable'], 'wan_stage2_return_with_leftover_noise', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Stage 2 Denoise", ttk.Spinbox, var_key_name='wan_stage2_denoise', section_key='wan', from_=0.0, to=1.0, increment=0.01, format="%.2f")
        create_setting_row_ui(wan_section.body(), "Animation Resolution", ttk.Entry, var_key_name='wan_animation_resolution', section_key='wan')
        create_setting_row_ui(wan_section.body(), "Animation Duration (frames)", ttk.Spinbox, var_key_name='wan_animation_duration', section_key='wan', from_=8, to=480, increment=1)
        create_setting_row_ui(wan_section.body(), "Animation Motion Profile", ttk.Combobox, ['slowmo', 'low', 'medium', 'high'], 'wan_animation_motion_profile', section_key='wan')

        # Kontext Section
        kontext_section = CollapsibleSection(self.kontext_settings_content_frame, "Kontext Defaults", self.color)
        kontext_section.pack(fill=tk.X, padx=4, pady=(0, 6))
        create_setting_row_ui(kontext_section.body(), "Selected Kontext Model", ttk.Combobox, self.available_models, 'selected_kontext_model', section_key='kontext')
        create_setting_row_ui(kontext_section.body(), "Kontext VAE", ttk.Combobox, self.available_vaes, 'selected_vae', section_key='kontext')
        create_setting_row_ui(kontext_section.body(), "Default Steps", ttk.Spinbox, var_key_name='kontext_steps', section_key='kontext', from_=4, to=128, increment=4)
        create_setting_row_ui(kontext_section.body(), "Default Guidance", ttk.Spinbox, var_key_name='kontext_guidance', section_key='kontext', from_=0.0, to=20.0, increment=0.1, format="%.1f")
        create_setting_row_ui(kontext_section.body(), "Default MP Size", ttk.Spinbox, var_key_name='kontext_mp_size', section_key='kontext', from_=0.1, to=8.0, increment=0.05, format="%.2f")

        # LLM Section
        llm_section_container = CollapsibleSection(self.llm_settings_content_frame, "LLM Enhancer", self.color)
        llm_section_container.pack(fill=tk.X, padx=4, pady=(0, 6))
        llm_body = llm_section_container.body()
        create_setting_row_ui(llm_body, "LLM Prompt Enhancer", ttk.Checkbutton, var_key_name='llm_enhancer_enabled', section_key='llm')
        llm_provider_keys = list(self.llm_models_config.get('providers', {}).keys())
        create_setting_row_ui(llm_body, "LLM Provider", ttk.Combobox, llm_provider_keys, 'llm_provider', section_key='llm')
        initial_llm_provider = self.config_manager.settings.get('llm_provider', llm_provider_keys[0] if llm_provider_keys else 'gemini')
        initial_llm_models_for_provider = self.get_ordered_llm_models_for_provider(initial_llm_provider)
        initial_llm_provider_display_name = self.provider_display_map.get(initial_llm_provider, initial_llm_provider.capitalize())
        create_setting_row_ui(
            llm_body,
            f"LLM Model ({initial_llm_provider_display_name})",
            ttk.Combobox,
            initial_llm_models_for_provider,
            'llm_model',
            section_key='llm',
            is_llm_model_selector_field=True
        )
        create_setting_row_ui(llm_body, "Prompt Display Preference", ttk.Combobox, list(self.display_prompt_map.keys()), 'display_prompt_preference', section_key='llm')

        self._apply_settings_search_filter()

        if self.last_focused_setting_key and self.last_focused_setting_key in self.bot_settings_widgets:
            try:
                widget = self.bot_settings_widgets[self.last_focused_setting_key]
                widget.focus_set()
            except tk.TclError:
                pass

        if 'llm_provider' in self.settings_vars:
            self.on_llm_provider_change_for_editor('llm_provider')
    def on_llm_provider_change_for_editor(self, var_key_name_that_changed):
        if var_key_name_that_changed != 'llm_provider':
            return
        provider_var = self.settings_vars.get('llm_provider')
        if provider_var is None:
            return
        selected_provider_display_name = provider_var.get()
        actual_provider_internal_key = next(
            (k_internal for k_internal, v_display in self.provider_display_map.items() if v_display == selected_provider_display_name),
            None
        )
        if not actual_provider_internal_key and selected_provider_display_name:
            actual_provider_internal_key = selected_provider_display_name.lower()
        llm_model_combobox_widget = self.bot_settings_widgets.get('llm_model')
        if not llm_model_combobox_widget:
            return
        new_llm_model_options = self.get_ordered_llm_models_for_provider(actual_provider_internal_key)
        llm_model_combobox_widget['values'] = new_llm_model_options
        model_setting_key_for_new_provider = f"llm_model_{actual_provider_internal_key}" if actual_provider_internal_key else "llm_model"
        current_model_for_new_provider = self.config_manager.settings.get(model_setting_key_for_new_provider, "")
        llm_model_var = self.settings_vars.get('llm_model')
        if llm_model_var is not None:
            if current_model_for_new_provider in new_llm_model_options:
                llm_model_var.set(current_model_for_new_provider)
            elif new_llm_model_options:
                llm_model_var.set(new_llm_model_options[0])
            else:
                llm_model_var.set("")
        llm_model_label_widget = self.bot_settings_widgets.get('llm_model_label')
        if llm_model_label_widget:
            label_base = self.bot_settings_widgets.get('llm_model_label_base', 'LLM Model')
            new_provider_display = self.provider_display_map.get(
                actual_provider_internal_key,
                (actual_provider_internal_key.capitalize() if actual_provider_internal_key else selected_provider_display_name or 'LLM')
            )
            llm_model_label_widget.config(text=f"{label_base} ({new_provider_display}):")

    def load_available_files(self):
        self.available_models = []
        self.available_checkpoints = []
        self.available_qwen_models = []
        self.available_qwen_edit_models = []
        self.available_wan_models = []
        self.available_wan_video_models = []
        self.available_clips_t5 = []
        self.available_clips_l = []
        self.available_qwen_clips = []
        self.available_wan_clips = []
        self.available_wan_vision = []
        self.available_loras = ["None"]
        self.available_upscale_models = ["None"]
        self.available_vaes = ["None"]
        self.available_qwen_vaes = ["None"]
        self.available_wan_vaes = ["None"]

        try:
            if os.path.exists(MODELS_LIST_FILE_NAME):
                with open(MODELS_LIST_FILE_NAME, 'r') as f_ml:
                    models_data = json.load(f_ml)
                if isinstance(models_data, dict):
                    self.available_models = sorted(
                        list(
                            set(
                                m_name
                                for model_type_list in [models_data.get(type_key, []) for type_key in ['safetensors', 'sft', 'gguf']]
                                for m_name in model_type_list
                                if isinstance(m_name, str)
                            )
                        ),
                        key=str.lower,
                    )
        except Exception:
            pass

        try:
            if os.path.exists(CHECKPOINTS_LIST_FILE_NAME):
                with open(CHECKPOINTS_LIST_FILE_NAME, 'r') as f_cp:
                    checkpoints_data = json.load(f_cp)
                if isinstance(checkpoints_data, dict):
                    sdxl_chkpts = checkpoints_data.get('checkpoints', []) if isinstance(checkpoints_data.get('checkpoints'), list) else []
                    if not sdxl_chkpts:
                        for k_cp, v_cp_list in checkpoints_data.items():
                            if isinstance(v_cp_list, list) and k_cp != 'favorites':
                                sdxl_chkpts.extend(c_name for c_name in v_cp_list if isinstance(c_name, str))
                    self.available_checkpoints = sorted(list(set(sdxl_chkpts)), key=str.lower)
        except Exception:
            pass

        try:
            if os.path.exists(QWEN_MODELS_FILE_NAME):
                with open(QWEN_MODELS_FILE_NAME, 'r') as f_qm:
                    qwen_data = json.load(f_qm)
                if isinstance(qwen_data, dict):
                    qwen_models = qwen_data.get('checkpoints', []) if isinstance(qwen_data.get('checkpoints'), list) else []
                    self.available_qwen_models = sorted({m for m in qwen_models if isinstance(m, str)}, key=str.lower)
        except Exception:
            pass

        try:
            if os.path.exists(QWEN_EDIT_MODELS_FILE_NAME):
                with open(QWEN_EDIT_MODELS_FILE_NAME, 'r') as f_qem:
                    qwen_edit_data = json.load(f_qem)
                if isinstance(qwen_edit_data, dict):
                    edit_models = qwen_edit_data.get('checkpoints', []) if isinstance(qwen_edit_data.get('checkpoints'), list) else []
                    self.available_qwen_edit_models = sorted({m for m in edit_models if isinstance(m, str)}, key=str.lower)
        except Exception:
            pass

        if not self.available_qwen_edit_models and self.available_qwen_models:
            self.available_qwen_edit_models = list(self.available_qwen_models)

        try:
            if os.path.exists(WAN_MODELS_FILE_NAME):
                with open(WAN_MODELS_FILE_NAME, 'r') as f_wm:
                    wan_data = json.load(f_wm)
                if isinstance(wan_data, dict):
                    wan_text = wan_data.get('checkpoints', []) if isinstance(wan_data.get('checkpoints'), list) else []
                    wan_video = wan_data.get('video', []) if isinstance(wan_data.get('video'), list) else []
                    self.available_wan_models = sorted({m for m in wan_text if isinstance(m, str)}, key=str.lower)
                    self.available_wan_video_models = sorted({m for m in wan_video if isinstance(m, str)}, key=str.lower)
        except Exception:
            pass

        try:
            if os.path.exists(CLIP_LIST_FILE_NAME):
                with open(CLIP_LIST_FILE_NAME, 'r') as f_cl:
                    clips_data = json.load(f_cl)
                if isinstance(clips_data, dict):
                    self.available_clips_t5 = sorted([c_name for c_name in clips_data.get('t5', []) if isinstance(c_name, str)], key=str.lower)
                    self.available_clips_l = sorted([c_name for c_name in clips_data.get('clip_L', []) if isinstance(c_name, str)], key=str.lower)
                    self.available_qwen_clips = sorted([c_name for c_name in clips_data.get('qwen', []) if isinstance(c_name, str)], key=str.lower)
                    self.available_wan_clips = sorted([c_name for c_name in clips_data.get('wan', []) if isinstance(c_name, str)], key=str.lower)
                    self.available_wan_vision = sorted([c_name for c_name in clips_data.get('vision', []) if isinstance(c_name, str)], key=str.lower)
        except Exception:
            pass

        lora_folder = self.config_manager.config.get('LORAS', {}).get('LORA_FILES', '')
        upscale_folder = self.config_manager.config.get('MODELS', {}).get('UPSCALE_MODELS', '')
        vae_folder = self.config_manager.config.get('MODELS', {}).get('VAE_MODELS', '')

        if lora_folder and os.path.isdir(lora_folder):
            try:
                self.available_loras.extend(
                    sorted(
                        [
                            f_name
                            for f_name in os.listdir(lora_folder)
                            if f_name.lower().endswith(('.safetensors', '.pt', '.ckpt'))
                        ],
                        key=str.lower,
                    )
                )
            except Exception:
                pass

        if upscale_folder and os.path.isdir(upscale_folder):
            try:
                self.available_upscale_models.extend(
                    sorted(
                        [
                            f_name
                            for f_name in os.listdir(upscale_folder)
                            if f_name.lower().endswith(('.pth', '.onnx', '.safetensors', '.pt', '.bin'))
                        ],
                        key=str.lower,
                    )
                )
            except Exception:
                pass

        if vae_folder and os.path.isdir(vae_folder):
            try:
                self.available_vaes.extend(
                    sorted(
                        [
                            f_name
                            for f_name in os.listdir(vae_folder)
                            if f_name.lower().endswith(('.pt', '.safetensors', '.pth', '.ckpt'))
                        ],
                        key=str.lower,
                    )
                )
            except Exception:
                pass

        deduped_vaes = list(dict.fromkeys(self.available_vaes))
        if deduped_vaes:
            self.available_vaes = deduped_vaes
            self.available_qwen_vaes = list(deduped_vaes)
            self.available_wan_vaes = list(deduped_vaes)

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
                    self.show_status_message(f"{task_name_done} complete: {message_details}", level="success")
                    if task_name_done == "Scanning Files":
                        self.load_available_files(); self.populate_bot_settings_tab()
                        if hasattr(self, 'favorites_tab_manager'): self.favorites_tab_manager.populate_all_favorites_sub_tabs()
                else:
                    self.show_status_message(f"{task_name_done} failed: {message_details}", level="error", duration=2200)
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
                    self.show_status_message("Settings reloaded from disk.", level="info")
            if self.master.winfo_exists(): self.master.after(2000, self._check_settings_file_for_changes)
        except FileNotFoundError:
             if self.master.winfo_exists(): self.master.after(2000, self._check_settings_file_for_changes)
        except Exception:
            if self.master.winfo_exists(): self.master.after(5000, self._check_settings_file_for_changes)

    def run_worker_task_on_editor(self, task_function_to_run, task_display_name_str):
        if self.worker_thread and self.worker_thread.is_alive():
            self.show_status_message("Background task already running.", level="warning")
            return
        self.log_queue.put(("info",f"--- Starting {task_display_name_str} ---\n"))
        self.status_banner.show_progress(f"{task_display_name_str} in progress…")
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
            if paths_map["Flux Models"] and os.path.isdir(paths_map["Flux Models"]):
                self.log_queue.put(("worker","Scanning Flux models...\n"))
                model_scanner.update_models_list(CONFIG_FILE_NAME,MODELS_LIST_FILE_NAME)
            if paths_map["CLIP Files"] and os.path.isdir(paths_map["CLIP Files"]):
                self.log_queue.put(("worker","Scanning CLIPs...\n"))
                model_scanner.scan_clip_files(CONFIG_FILE_NAME,CLIP_LIST_FILE_NAME)
            if paths_map["SDXL Checkpoints"] and os.path.isdir(paths_map["SDXL Checkpoints"]):
                self.log_queue.put(("worker","Scanning SDXL checkpoints...\n"))
                model_scanner.update_checkpoints_list(CONFIG_FILE_NAME,CHECKPOINTS_LIST_FILE_NAME)
                self.log_queue.put(("worker","Scanning Qwen models...\n"))
                model_scanner.update_qwen_models_list(CONFIG_FILE_NAME, QWEN_MODELS_FILE_NAME)
                self.log_queue.put(("worker","Scanning WAN models...\n"))
                model_scanner.update_wan_models_list(CONFIG_FILE_NAME, WAN_MODELS_FILE_NAME)
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
                params = {'limit': 100}
                next_after = None
                chat_model_prefixes = ['gpt-4', 'gpt-3.5', 'o1', 'o3', 'o4', 'gpt-5']
                collected_ids = set()

                while True:
                    if next_after:
                        params['after'] = next_after
                    elif 'after' in params:
                        params.pop('after', None)

                    response = requests.get(
                        "https://api.openai.com/v1/models",
                        headers=headers,
                        params=params,
                        timeout=10,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    models = payload.get('data', [])

                    for model in models:
                        model_id = model.get('id')
                        if isinstance(model_id, str) and any(model_id.startswith(p) for p in chat_model_prefixes):
                            collected_ids.add(model_id)

                    if not payload.get('has_more'):
                        break

                    next_after = payload.get('last_id')
                    if not isinstance(next_after, str) or not next_after:
                        break

                openai_model_ids = sorted(collected_ids)

                openai_entry = updated_models_data['providers'].setdefault('openai', {
                    'display_name': 'OpenAI API', 'models': [], 'favorites': []
                })
                if not isinstance(openai_entry, dict):
                    openai_entry = {'display_name': 'OpenAI API', 'models': [], 'favorites': []}
                    updated_models_data['providers']['openai'] = openai_entry
                existing_favorites = [f for f in openai_entry.get('favorites', []) if isinstance(f, str)]
                openai_entry['models'] = openai_model_ids
                openai_entry['favorites'] = [fav for fav in existing_favorites if fav in openai_model_ids]
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
                groq_entry = updated_models_data['providers'].setdefault('groq', {
                    'display_name': 'Groq API', 'models': [], 'favorites': []
                })
                if not isinstance(groq_entry, dict):
                    groq_entry = {'display_name': 'Groq API', 'models': [], 'favorites': []}
                    updated_models_data['providers']['groq'] = groq_entry
                existing_favorites = [f for f in groq_entry.get('favorites', []) if isinstance(f, str)]
                groq_entry['models'] = groq_model_ids
                groq_entry['favorites'] = [fav for fav in existing_favorites if fav in groq_model_ids]
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
                gemini_entry = updated_models_data['providers'].setdefault('gemini', {
                    'display_name': 'Google Gemini API', 'models': [], 'favorites': []
                })
                if not isinstance(gemini_entry, dict):
                    gemini_entry = {'display_name': 'Google Gemini API', 'models': [], 'favorites': []}
                    updated_models_data['providers']['gemini'] = gemini_entry
                existing_favorites = [f for f in gemini_entry.get('favorites', []) if isinstance(f, str)]
                gemini_entry['models'] = gemini_model_ids
                gemini_entry['favorites'] = [fav for fav in existing_favorites if fav in gemini_model_ids]
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
        self.show_status_message(about_message, level="info", duration=2200)

    def save_all_configurations_from_menu(self):
        """Trigger save for all config-related entities."""
        if not silent_askyesno("Confirm Save All", "Save changes in ALL tabs?", parent=self.master): return
        self.config_manager.save_main_config_data()
        self.llm_prompts_tab_manager.save_llm_prompts_data()
        self.lora_styles_tab_manager.save_current_styles_config()
        self.favorites_tab_manager.save_all_favorites_data()
        self.config_manager.save_bot_settings_data()
        self.admin_control_tab_manager._save_blocklist()
        if hasattr(self, 'main_config_status_var'):
            self.main_config_status_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
        if hasattr(self, 'bot_settings_status_var'):
            self.bot_settings_status_var.set(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
        self.show_status_message("All save operations triggered. Check logs for details.", level="success")

    def reset_bot_settings_to_defaults(self):
        """
        Reset all bot settings to their default values defined in the settings template.
        Prompts the user for confirmation before resetting, then refreshes the UI and saves.
        """
        if not silent_askyesno("Confirm Reset", "Are you sure you want to reset all bot settings to their default values?", parent=self.master):
            return
        try:
            default_settings = self.config_manager.settings_template_factory().copy()
            self.config_manager.settings = default_settings
            self.populate_bot_settings_tab()
            self.config_manager.save_bot_settings_data()
            if hasattr(self, 'bot_settings_status_var'):
                self.bot_settings_status_var.set(f"Reset at {datetime.now().strftime('%H:%M:%S')}")
            self.show_status_message("Bot settings reset to defaults.", level="success")
        except Exception as e_reset:
            self.show_status_message(f"Failed to reset settings: {e_reset}", level="error", duration=2200)

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
            if hasattr(self, 'main_config_status_var'):
                self.main_config_status_var.set(f"Exported at {datetime.now().strftime('%H:%M:%S')}")
            self.show_status_message(f"Exported configuration to {os.path.basename(file_path)}", level="success")
        except Exception as e_exp:
            self.show_status_message(f"Failed to export configuration: {e_exp}", level="error", duration=2200)

    def import_config_and_settings(self):
        """Import main config and bot settings from a previously exported JSON file."""
        try:
            file_path = filedialog.askopenfilename(title="Import Config & Settings", filetypes=[("JSON Files","*.json"), ("All Files","*.*")], parent=self.master)
            if not file_path:
                return
            with open(file_path, 'r', encoding='utf-8') as f_in:
                imported_data = json.load(f_in)
            if not isinstance(imported_data, dict):
                self.show_status_message("Invalid import file: expected a JSON object.", level="error", duration=2200)
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
            if hasattr(self, 'main_config_status_var'):
                self.main_config_status_var.set(f"Imported at {datetime.now().strftime('%H:%M:%S')}")
            self.show_status_message(f"Imported configuration from {os.path.basename(file_path)}", level="success")
        except Exception as e_imp:
            self.show_status_message(f"Failed to import configuration: {e_imp}", level="error", duration=2200)
    
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
            self.show_status_message(f"Could not restart the application: {e}", level="error", duration=2200)


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
            self.show_status_message(welcome_message, level="info", duration=2200)

            try:
                with open(flag_file, 'w') as f:
                    f.write(f"First run setup prompt shown on: {datetime.now().isoformat()}")
            except OSError as e:
                self.show_status_message(f"Could not create first-run flag: {e}", level="warning", duration=2200)

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
        print(
            "[ERROR] Fatal Error - Config Editor Application: "
            f"Could not start Config Editor application: {main_app_execution_error}."
        )
# --- END OF FILE config_editor_main.py ---
