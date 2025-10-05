import tkinter as tk
from tkinter import ttk
import json
import os
import traceback
from editor_utils import silent_showinfo, silent_showerror, save_json_config
from editor_constants import (
    MODELS_LIST_FILE_NAME, CHECKPOINTS_LIST_FILE_NAME, CLIP_LIST_FILE_NAME,
    STYLES_CONFIG_FILE_NAME, CANVAS_BG_COLOR, FRAME_BG_COLOR, TEXT_COLOR_NORMAL,
    ENTRY_BG_COLOR, LISTBOX_BG, LISTBOX_FG, LISTBOX_SELECT_BG, LISTBOX_SELECT_FG, BOLD_TLABEL_STYLE
)

class FavoritesTab:
    def __init__(self, editor_app_ref, parent_notebook):
        self.editor_app = editor_app_ref
        self.notebook = parent_notebook

        self.favorites_tab_frame = ttk.Frame(self.notebook, padding="10", style="Tenos.TFrame")
        self.notebook.add(self.favorites_tab_frame, text=' Favorites ')

        self.fav_sub_notebook = ttk.Notebook(self.favorites_tab_frame, style="Tenos.TNotebook")
        self.fav_sub_notebook.pack(expand=True, fill="both")

        self.fav_flux_models_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_sdxl_checkpoints_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_clip_t5_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_clip_l_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_styles_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")

        self.fav_sub_notebook.add(self.fav_flux_models_sub_tab, text=" Flux Models ")
        self.fav_sub_notebook.add(self.fav_sdxl_checkpoints_sub_tab, text=" SDXL Checkpoints ")
        self.fav_sub_notebook.add(self.fav_clip_t5_sub_tab, text=" T5 Clips ")
        self.fav_sub_notebook.add(self.fav_clip_l_sub_tab, text=" Clip-L ")
        self.fav_sub_notebook.add(self.fav_styles_sub_tab, text=" Styles ")

        ttk.Button(self.favorites_tab_frame, text="Save All Favorites", command=self.save_all_favorites_data).pack(side="bottom", pady=10)

        self.flux_model_favorite_vars = {}
        self.sdxl_checkpoint_favorite_vars = {}
        self.clip_favorite_vars = {'t5': {}, 'clip_L': {}}
        self.style_favorite_vars = {}

        self.populate_all_favorites_sub_tabs()


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
            "<Configure>", lambda event, c=canvas_widget: self.editor_app._debounce_canvas_configure(c, event)
        )
        canvas_widget.create_window((0, 0), window=scrollable_content_frame, anchor="nw")
        canvas_widget.configure(yscrollcommand=scrollbar_widget.set)
        canvas_widget.pack(side="left", fill="both", expand=True)
        return scrollable_content_frame

    def populate_all_favorites_sub_tabs(self):
        
        flux_frame = self._create_scrollable_sub_tab_frame(self.fav_flux_models_sub_tab)
        self.flux_model_favorite_vars = {}
        models_data = {}; flux_favorites = []
        try:
            if os.path.exists(MODELS_LIST_FILE_NAME):
                with open(MODELS_LIST_FILE_NAME, 'r') as f: models_data = json.load(f)
            if isinstance(models_data, dict) and isinstance(models_data.get('favorites'), list):
                flux_favorites = models_data['favorites']
            elif isinstance(models_data, dict): models_data['favorites'] = []
        except Exception as e: print(f"EditorFavorites: Error loading {MODELS_LIST_FILE_NAME}: {e}")
        row = 0
        for model_type in ['safetensors', 'sft', 'gguf']:
            ttk.Label(flux_frame, text=model_type.upper() + " Models", style=BOLD_TLABEL_STYLE).grid(row=row, column=0, sticky='w', pady=(5,2), padx=5); row+=1 # Use BOLD_TLABEL_STYLE
            for model_name in sorted(models_data.get(model_type, []), key=str.lower):
                 if not isinstance(model_name, str): continue
                 var = tk.BooleanVar(value=(model_name in flux_favorites))
                 chk = tk.Checkbutton(flux_frame, text=model_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL, selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR, activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                 chk.grid(row=row, column=0, sticky="w", padx=15)
                 self.flux_model_favorite_vars[model_name] = var; row += 1
        if flux_frame.winfo_exists(): flux_frame.event_generate("<Configure>")


        
        sdxl_frame = self._create_scrollable_sub_tab_frame(self.fav_sdxl_checkpoints_sub_tab)
        self.sdxl_checkpoint_favorite_vars = {}
        checkpoints_data = {}; sdxl_favorites = []
        try:
            if os.path.exists(CHECKPOINTS_LIST_FILE_NAME):
                with open(CHECKPOINTS_LIST_FILE_NAME, 'r') as f: checkpoints_data = json.load(f)
            if isinstance(checkpoints_data, dict) and isinstance(checkpoints_data.get('favorites'), list):
                sdxl_favorites = checkpoints_data['favorites']
            elif isinstance(checkpoints_data, dict): checkpoints_data['favorites'] = []
        except Exception as e: print(f"EditorFavorites: Error loading {CHECKPOINTS_LIST_FILE_NAME}: {e}")
        row = 0
        all_sdxl_from_file = []
        if isinstance(checkpoints_data.get('checkpoints'), list):
            all_sdxl_from_file = checkpoints_data['checkpoints']
        elif isinstance(checkpoints_data, dict):
            for key, value in checkpoints_data.items():
                if isinstance(value, list) and key != 'favorites':
                    all_sdxl_from_file.extend(c for c in value if isinstance(c, str))
        all_sdxl_from_file = sorted(list(set(all_sdxl_from_file)), key=str.lower)
        for checkpoint_name in all_sdxl_from_file:
             var = tk.BooleanVar(value=(checkpoint_name in sdxl_favorites))
             chk = tk.Checkbutton(sdxl_frame, text=checkpoint_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL, selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR, activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
             chk.grid(row=row, column=0, sticky="w", padx=5)
             self.sdxl_checkpoint_favorite_vars[checkpoint_name] = var; row += 1
        if sdxl_frame.winfo_exists(): sdxl_frame.event_generate("<Configure>")


        
        clips_data = {}; clip_t5_fav = []; clip_l_fav = []
        self.clip_favorite_vars = {'t5': {}, 'clip_L': {}}
        try:
            if os.path.exists(CLIP_LIST_FILE_NAME):
                with open(CLIP_LIST_FILE_NAME, 'r') as f: clips_data = json.load(f)
            if isinstance(clips_data, dict):
                 fav_dict = clips_data.setdefault('favorites', {})
                 if not isinstance(fav_dict, dict): fav_dict = {}
                 clip_t5_fav = fav_dict.get('t5', [])
                 if not isinstance(clip_t5_fav, list): clip_t5_fav = []
                 fav_dict['t5'] = clip_t5_fav
                 clip_l_fav = fav_dict.get('clip_L', [])
                 if not isinstance(clip_l_fav, list): clip_l_fav = []
                 fav_dict['clip_L'] = clip_l_fav
                 clips_data['favorites'] = fav_dict
        except Exception as e: print(f"EditorFavorites: Error loading {CLIP_LIST_FILE_NAME}: {e}")
        t5_frame = self._create_scrollable_sub_tab_frame(self.fav_clip_t5_sub_tab)
        row = 0
        for clip_name in sorted(clips_data.get('t5', []), key=str.lower):
            if not isinstance(clip_name, str): continue
            var = tk.BooleanVar(value=(clip_name in clip_t5_fav))
            chk = tk.Checkbutton(t5_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL, selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR, activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
            chk.grid(row=row, column=0, sticky="w", padx=5)
            self.clip_favorite_vars['t5'][clip_name] = var; row += 1
        if t5_frame.winfo_exists(): t5_frame.event_generate("<Configure>")

        l_frame = self._create_scrollable_sub_tab_frame(self.fav_clip_l_sub_tab)
        row = 0
        for clip_name in sorted(clips_data.get('clip_L',[]), key=str.lower):
            if not isinstance(clip_name, str): continue
            var = tk.BooleanVar(value=(clip_name in clip_l_fav))
            chk = tk.Checkbutton(l_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL, selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR, activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
            chk.grid(row=row, column=0, sticky="w", padx=5)
            self.clip_favorite_vars['clip_L'][clip_name] = var; row += 1
        if l_frame.winfo_exists(): l_frame.event_generate("<Configure>")

        
        style_fav_frame = self._create_scrollable_sub_tab_frame(self.fav_styles_sub_tab)
        self.style_favorite_vars = {}
        row = 0
        
        for style_name_key in sorted([str(k) for k in self.editor_app.styles_config.keys()]):
            if style_name_key == "off": continue
            style_data_entry = self.editor_app.styles_config[style_name_key]
            is_favorite = isinstance(style_data_entry, dict) and style_data_entry.get('favorite', False)
            var = tk.BooleanVar(value=is_favorite)
            chk = tk.Checkbutton(style_fav_frame, text=style_name_key, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL, selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR, activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
            chk.grid(row=row, column=0, sticky="w", padx=5)
            self.style_favorite_vars[style_name_key] = var; row += 1
        if style_fav_frame.winfo_exists(): style_fav_frame.event_generate("<Configure>")


    def save_all_favorites_data(self):
        saved_files_count = 0; errors_list = []
        try:
            models_data = {}
            if os.path.exists(MODELS_LIST_FILE_NAME):
                with open(MODELS_LIST_FILE_NAME, 'r') as f: models_data = json.load(f)
            if not isinstance(models_data, dict): models_data = {}
            for mtype in ['safetensors', 'sft', 'gguf', 'favorites']: models_data.setdefault(mtype, [])
            models_data['favorites'] = [model for model, var in self.flux_model_favorite_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
            if save_json_config(MODELS_LIST_FILE_NAME, models_data, "Flux model favorites"): saved_files_count +=1
        except Exception as e: errors_list.append(f"{MODELS_LIST_FILE_NAME}: {e}"); traceback.print_exc()
        try:
            checkpoints_data = {}
            if os.path.exists(CHECKPOINTS_LIST_FILE_NAME):
                with open(CHECKPOINTS_LIST_FILE_NAME, 'r') as f: checkpoints_data = json.load(f)
            if not isinstance(checkpoints_data, dict): checkpoints_data = {}
            checkpoints_data.setdefault('checkpoints', []); checkpoints_data.setdefault('favorites', [])
            checkpoints_data['favorites'] = [chkpt for chkpt, var in self.sdxl_checkpoint_favorite_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
            if save_json_config(CHECKPOINTS_LIST_FILE_NAME, checkpoints_data, "SDXL checkpoint favorites"): saved_files_count +=1
        except Exception as e: errors_list.append(f"{CHECKPOINTS_LIST_FILE_NAME}: {e}"); traceback.print_exc()
        try:
            clips_data = {}
            if os.path.exists(CLIP_LIST_FILE_NAME):
                with open(CLIP_LIST_FILE_NAME, 'r') as f: clips_data = json.load(f)
            if not isinstance(clips_data, dict): clips_data = {}
            clips_data.setdefault('t5', []); clips_data.setdefault('clip_L', []); clips_data.setdefault('favorites', {})
            if not isinstance(clips_data['favorites'], dict): clips_data['favorites'] = {}
            clips_data['favorites']['t5'] = [clip for clip, var in self.clip_favorite_vars.get('t5', {}).items() if isinstance(var, tk.BooleanVar) and var.get()]
            clips_data['favorites']['clip_L'] = [clip for clip, var in self.clip_favorite_vars.get('clip_L', {}).items() if isinstance(var, tk.BooleanVar) and var.get()]
            if save_json_config(CLIP_LIST_FILE_NAME, clips_data, "CLIP favorites"): saved_files_count +=1
        except Exception as e: errors_list.append(f"{CLIP_LIST_FILE_NAME}: {e}"); traceback.print_exc()
        try:
            
            for style_name, var_fav in self.style_favorite_vars.items():
                if style_name in self.editor_app.styles_config and isinstance(self.editor_app.styles_config[style_name], dict):
                    if isinstance(var_fav, tk.BooleanVar): self.editor_app.styles_config[style_name]['favorite'] = var_fav.get()
                elif style_name != "off": self.editor_app.styles_config[style_name] = {'favorite': var_fav.get() if isinstance(var_fav, tk.BooleanVar) else False}
            if 'off' in self.editor_app.styles_config and isinstance(self.editor_app.styles_config['off'], dict): self.editor_app.styles_config['off']['favorite'] = False
            else: self.editor_app.styles_config['off'] = {"favorite": False}
            if save_json_config(STYLES_CONFIG_FILE_NAME, self.editor_app.styles_config, "style favorites"): saved_files_count +=1
            
        except Exception as e: errors_list.append(f"{STYLES_CONFIG_FILE_NAME}: {e}"); traceback.print_exc()

        if not errors_list:
            silent_showinfo("Success", "All favorites updated successfully!", parent=self.editor_app.master)
        else:
            silent_showerror("Error Saving Favorites", f"Failed to save some favorites settings:\n\n" + "\n".join(errors_list), parent=self.editor_app.master)

        
        self.editor_app.load_available_files()
        self.editor_app.config_manager.load_bot_settings_data(self.editor_app.llm_models_config)
        self.editor_app.populate_bot_settings_tab()
        if hasattr(self.editor_app, 'lora_styles_tab_manager'):
            self.editor_app.lora_styles_tab_manager.populate_lora_styles_tab()
        
        self.populate_all_favorites_sub_tabs()
