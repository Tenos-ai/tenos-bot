import tkinter as tk
from tkinter import ttk
import json
import os
import traceback
from editor_utils import silent_showinfo, silent_showerror, save_json_config, load_llm_models_config_util
from editor_constants import (
    MODELS_LIST_FILE_NAME, CHECKPOINTS_LIST_FILE_NAME, CLIP_LIST_FILE_NAME, LLM_MODELS_FILE_NAME,
    QWEN_MODELS_FILE_NAME, WAN_MODELS_FILE_NAME,
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
        self.fav_qwen_models_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_qwen_assets_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_wan_models_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_wan_assets_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_llm_models_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_clip_t5_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_clip_l_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")
        self.fav_styles_sub_tab = ttk.Frame(self.fav_sub_notebook, padding="5", style="Tenos.TFrame")

        self.fav_sub_notebook.add(self.fav_flux_models_sub_tab, text=" Flux Models ")
        self.fav_sub_notebook.add(self.fav_sdxl_checkpoints_sub_tab, text=" SDXL Checkpoints ")
        self.fav_sub_notebook.add(self.fav_qwen_models_sub_tab, text=" Qwen Models ")
        self.fav_sub_notebook.add(self.fav_qwen_assets_sub_tab, text=" Qwen Assets ")
        self.fav_sub_notebook.add(self.fav_wan_models_sub_tab, text=" WAN Models ")
        self.fav_sub_notebook.add(self.fav_wan_assets_sub_tab, text=" WAN Assets ")
        self.fav_sub_notebook.add(self.fav_llm_models_sub_tab, text=" LLM Models ")
        self.fav_sub_notebook.add(self.fav_clip_t5_sub_tab, text=" T5 Clips ")
        self.fav_sub_notebook.add(self.fav_clip_l_sub_tab, text=" Other Encoders ")
        self.fav_sub_notebook.add(self.fav_styles_sub_tab, text=" Styles ")

        ttk.Button(self.favorites_tab_frame, text="Save All Favorites", command=self.save_all_favorites_data).pack(side="bottom", pady=10)

        self.flux_model_favorite_vars = {}
        self.sdxl_checkpoint_favorite_vars = {}
        self.qwen_model_favorite_vars = {}
        self.qwen_vae_favorite_vars = {}
        self.wan_model_favorite_vars = {}
        self.wan_video_favorite_vars = {}
        self.wan_vae_favorite_vars = {}
        self.llm_model_favorite_vars = {}
        self.clip_favorite_vars = {'t5': {}, 'clip_L': {}, 'qwen': {}, 'wan': {}, 'vision': {}}
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
        scrollbar_widget.pack(side="right", fill="y")
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


        clips_data = {}
        clip_t5_fav = []
        clip_l_fav = []
        clip_qwen_fav = []
        clip_wan_fav = []
        clip_vision_fav = []
        self.clip_favorite_vars = {'t5': {}, 'clip_L': {}, 'qwen': {}, 'wan': {}, 'vision': {}}
        try:
            if os.path.exists(CLIP_LIST_FILE_NAME):
                with open(CLIP_LIST_FILE_NAME, 'r') as f:
                    clips_data = json.load(f)
            if isinstance(clips_data, dict):
                favorites_section = clips_data.setdefault('favorites', {})
                if not isinstance(favorites_section, dict):
                    favorites_section = {}
                clip_t5_fav = favorites_section.get('t5', []) if isinstance(favorites_section.get('t5'), list) else []
                favorites_section['t5'] = clip_t5_fav
                clip_l_fav = favorites_section.get('clip_L', []) if isinstance(favorites_section.get('clip_L'), list) else []
                favorites_section['clip_L'] = clip_l_fav
                clip_qwen_fav = favorites_section.get('qwen', []) if isinstance(favorites_section.get('qwen'), list) else []
                favorites_section['qwen'] = clip_qwen_fav
                clip_wan_fav = favorites_section.get('wan', []) if isinstance(favorites_section.get('wan'), list) else []
                favorites_section['wan'] = clip_wan_fav
                clip_vision_fav = favorites_section.get('vision', []) if isinstance(favorites_section.get('vision'), list) else []
                favorites_section['vision'] = clip_vision_fav
                clips_data['favorites'] = favorites_section
            else:
                clips_data = {'t5': [], 'clip_L': [], 'qwen': [], 'wan': [], 'vision': [], 'favorites': {'t5': [], 'clip_L': [], 'qwen': [], 'wan': [], 'vision': []}}
        except Exception as e:
            print(f"EditorFavorites: Error loading {CLIP_LIST_FILE_NAME}: {e}")
            clips_data = {'t5': [], 'clip_L': [], 'qwen': [], 'wan': [], 'vision': [], 'favorites': {'t5': [], 'clip_L': [], 'qwen': [], 'wan': [], 'vision': []}}

        qwen_frame = self._create_scrollable_sub_tab_frame(self.fav_qwen_models_sub_tab)
        qwen_assets_frame = self._create_scrollable_sub_tab_frame(self.fav_qwen_assets_sub_tab)
        self.qwen_model_favorite_vars = {}
        self.qwen_vae_favorite_vars = {}
        qwen_data = {}; qwen_favorites = []; qwen_vae_favorites = []
        try:
            if os.path.exists(QWEN_MODELS_FILE_NAME):
                with open(QWEN_MODELS_FILE_NAME, 'r') as f: qwen_data = json.load(f)
            if isinstance(qwen_data, dict):
                raw_favs = qwen_data.get('favorites', [])
                if isinstance(raw_favs, list):
                    qwen_favorites = [str(item) for item in raw_favs if isinstance(item, str)]
                raw_vae_favs = qwen_data.get('vae_favorites', [])
                if isinstance(raw_vae_favs, list):
                    qwen_vae_favorites = [str(item) for item in raw_vae_favs if isinstance(item, str)]
        except Exception as e:
            print(f"EditorFavorites: Error loading {QWEN_MODELS_FILE_NAME}: {e}")
            qwen_data = {}
        qwen_list = qwen_data.get('checkpoints', []) if isinstance(qwen_data, dict) else []
        qwen_list = sorted([m for m in qwen_list if isinstance(m, str)], key=str.lower)
        row = 0
        for model_name in qwen_list:
            var = tk.BooleanVar(value=(model_name in qwen_favorites))
            chk = tk.Checkbutton(qwen_frame, text=model_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                 selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                 activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
            chk.grid(row=row, column=0, sticky="w", padx=5)
            self.qwen_model_favorite_vars[model_name] = var
            row += 1
        if qwen_frame.winfo_exists(): qwen_frame.event_generate("<Configure>")

        qwen_assets_row = 0
        qwen_vaes = sorted([v for v in self.editor_app.available_qwen_vaes if isinstance(v, str)], key=str.lower)
        if qwen_vaes:
            ttk.Label(qwen_assets_frame, text="VAEs", style=BOLD_TLABEL_STYLE).grid(row=qwen_assets_row, column=0, sticky='w', padx=5, pady=(5, 2))
            qwen_assets_row += 1
            for vae_name in qwen_vaes:
                var = tk.BooleanVar(value=(vae_name in qwen_vae_favorites))
                chk = tk.Checkbutton(qwen_assets_frame, text=vae_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=qwen_assets_row, column=0, sticky="w", padx=15)
                self.qwen_vae_favorite_vars[vae_name] = var
                qwen_assets_row += 1
        qwen_encoders = sorted([c for c in clips_data.get('qwen', []) if isinstance(c, str)], key=str.lower)
        if qwen_encoders:
            ttk.Label(qwen_assets_frame, text="Text Encoders", style=BOLD_TLABEL_STYLE).grid(row=qwen_assets_row, column=0, sticky='w', padx=5, pady=(10, 2))
            qwen_assets_row += 1
            for clip_name in qwen_encoders:
                var = tk.BooleanVar(value=(clip_name in clip_qwen_fav))
                chk = tk.Checkbutton(qwen_assets_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=qwen_assets_row, column=0, sticky="w", padx=15)
                self.clip_favorite_vars['qwen'][clip_name] = var
                qwen_assets_row += 1
        if qwen_assets_frame.winfo_exists(): qwen_assets_frame.event_generate("<Configure>")


        wan_frame = self._create_scrollable_sub_tab_frame(self.fav_wan_models_sub_tab)
        wan_assets_frame = self._create_scrollable_sub_tab_frame(self.fav_wan_assets_sub_tab)
        self.wan_model_favorite_vars = {}
        self.wan_video_favorite_vars = {}
        self.wan_vae_favorite_vars = {}
        wan_data = {}; wan_favorites = []; wan_video_favorites = []; wan_vae_favorites = []
        try:
            if os.path.exists(WAN_MODELS_FILE_NAME):
                with open(WAN_MODELS_FILE_NAME, 'r') as f: wan_data = json.load(f)
            if isinstance(wan_data, dict):
                raw_favs = wan_data.get('favorites', [])
                if isinstance(raw_favs, list):
                    wan_favorites = [str(item) for item in raw_favs if isinstance(item, str)]
                raw_video_favs = wan_data.get('video_favorites', [])
                if isinstance(raw_video_favs, list):
                    wan_video_favorites = [str(item) for item in raw_video_favs if isinstance(item, str)]
                raw_vae_favs = wan_data.get('vae_favorites', [])
                if isinstance(raw_vae_favs, list):
                    wan_vae_favorites = [str(item) for item in raw_vae_favs if isinstance(item, str)]
        except Exception as e:
            print(f"EditorFavorites: Error loading {WAN_MODELS_FILE_NAME}: {e}")
            wan_data = {}
        wan_models = wan_data.get('checkpoints', []) if isinstance(wan_data, dict) else []
        wan_models = [m for m in wan_models if isinstance(m, str)]
        wan_video_models = wan_data.get('video', []) if isinstance(wan_data, dict) else []
        wan_video_models = sorted([m for m in wan_video_models if isinstance(m, str)], key=str.lower)
        if wan_video_models:
            video_model_set = {name.lower() for name in wan_video_models}
            wan_models = [m for m in wan_models if m.lower() not in video_model_set]
        wan_models = sorted(wan_models, key=str.lower)
        row = 0
        for model_name in wan_models:
            var = tk.BooleanVar(value=(model_name in wan_favorites))
            chk = tk.Checkbutton(wan_frame, text=model_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                 selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                 activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
            chk.grid(row=row, column=0, sticky="w", padx=5)
            self.wan_model_favorite_vars[model_name] = var
            row += 1
        if wan_frame.winfo_exists(): wan_frame.event_generate("<Configure>")

        wan_assets_row = 0
        if wan_video_models:
            ttk.Label(wan_assets_frame, text="Video Models", style=BOLD_TLABEL_STYLE).grid(row=wan_assets_row, column=0, sticky='w', padx=5, pady=(5, 2))
            wan_assets_row += 1
            for model_name in wan_video_models:
                var = tk.BooleanVar(value=(model_name in wan_video_favorites))
                chk = tk.Checkbutton(wan_assets_frame, text=model_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=wan_assets_row, column=0, sticky="w", padx=15)
                self.wan_video_favorite_vars[model_name] = var
                wan_assets_row += 1
        wan_vaes = sorted([v for v in self.editor_app.available_wan_vaes if isinstance(v, str)], key=str.lower)
        if wan_vaes:
            ttk.Label(wan_assets_frame, text="VAEs", style=BOLD_TLABEL_STYLE).grid(row=wan_assets_row, column=0, sticky='w', padx=5, pady=(10, 2))
            wan_assets_row += 1
            for vae_name in wan_vaes:
                var = tk.BooleanVar(value=(vae_name in wan_vae_favorites))
                chk = tk.Checkbutton(wan_assets_frame, text=vae_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=wan_assets_row, column=0, sticky="w", padx=15)
                self.wan_vae_favorite_vars[vae_name] = var
                wan_assets_row += 1
        wan_text_encoders = sorted([c for c in clips_data.get('wan', []) if isinstance(c, str)], key=str.lower)
        if wan_text_encoders:
            ttk.Label(wan_assets_frame, text="Text Encoders", style=BOLD_TLABEL_STYLE).grid(row=wan_assets_row, column=0, sticky='w', padx=5, pady=(10, 2))
            wan_assets_row += 1
            for clip_name in wan_text_encoders:
                var = tk.BooleanVar(value=(clip_name in clip_wan_fav))
                chk = tk.Checkbutton(wan_assets_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=wan_assets_row, column=0, sticky="w", padx=15)
                self.clip_favorite_vars['wan'][clip_name] = var
                wan_assets_row += 1

        vision_encoders = sorted([c for c in clips_data.get('vision', []) if isinstance(c, str)], key=str.lower)
        if vision_encoders:
            ttk.Label(wan_assets_frame, text="Vision Encoders", style=BOLD_TLABEL_STYLE).grid(row=wan_assets_row, column=0, sticky='w', padx=5, pady=(10, 2))
            wan_assets_row += 1
            for clip_name in vision_encoders:
                var = tk.BooleanVar(value=(clip_name in clip_vision_fav))
                chk = tk.Checkbutton(wan_assets_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=wan_assets_row, column=0, sticky="w", padx=15)
                self.clip_favorite_vars['vision'][clip_name] = var
                wan_assets_row += 1

        if wan_assets_frame.winfo_exists(): wan_assets_frame.event_generate("<Configure>")


        llm_frame = self._create_scrollable_sub_tab_frame(self.fav_llm_models_sub_tab)
        self.llm_model_favorite_vars = {}
        llm_models_data = {}
        try:
            if os.path.exists(LLM_MODELS_FILE_NAME):
                with open(LLM_MODELS_FILE_NAME, 'r') as f: llm_models_data = json.load(f)
            if not isinstance(llm_models_data, dict): llm_models_data = {}
        except Exception as e:
            print(f"EditorFavorites: Error loading {LLM_MODELS_FILE_NAME}: {e}")
            llm_models_data = {}

        providers_data = llm_models_data.get('providers', {}) if isinstance(llm_models_data.get('providers'), dict) else {}
        row = 0
        if not providers_data:
            ttk.Label(llm_frame, text="No LLM providers configured.", style=BOLD_TLABEL_STYLE).grid(row=row, column=0, sticky='w', padx=5, pady=(5, 2))
            row += 1
        for provider_key in sorted(providers_data.keys(), key=str.lower):
            provider_entry = providers_data.get(provider_key, {}) if isinstance(providers_data.get(provider_key), dict) else {}
            display_name = provider_entry.get('display_name', provider_key.capitalize())
            models_list = [m.strip() for m in provider_entry.get('models', []) if isinstance(m, str)]
            favorites_list = [m.strip() for m in provider_entry.get('favorites', []) if isinstance(m, str)]
            ttk.Label(llm_frame, text=f"{display_name} ({provider_key})", style=BOLD_TLABEL_STYLE).grid(row=row, column=0, sticky='w', padx=5, pady=(10 if row else 5, 2))
            row += 1
            self.llm_model_favorite_vars[provider_key] = {}
            if not models_list:
                ttk.Label(llm_frame, text="No models available.", style="Tenos.TLabel").grid(row=row, column=0, sticky='w', padx=15)
                row += 1
                continue
            for model_name in sorted(set(models_list), key=str.lower):
                var = tk.BooleanVar(value=(model_name in favorites_list))
                chk = tk.Checkbutton(
                    llm_frame,
                    text=model_name,
                    variable=var,
                    bg=FRAME_BG_COLOR,
                    fg=TEXT_COLOR_NORMAL,
                    selectcolor=ENTRY_BG_COLOR,
                    activebackground=FRAME_BG_COLOR,
                    activeforeground=TEXT_COLOR_NORMAL,
                    highlightthickness=0,
                    borderwidth=0
                )
                chk.grid(row=row, column=0, sticky="w", padx=15)
                self.llm_model_favorite_vars[provider_key][model_name] = var
                row += 1
        if llm_frame.winfo_exists(): llm_frame.event_generate("<Configure>")


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

        qwen_encoders = sorted([c for c in clips_data.get('qwen', []) if isinstance(c, str)], key=str.lower)
        if qwen_encoders:
            ttk.Label(l_frame, text="Qwen Encoders", style=BOLD_TLABEL_STYLE).grid(row=row, column=0, sticky='w', padx=5, pady=(10, 2))
            row += 1
            for clip_name in qwen_encoders:
                var = tk.BooleanVar(value=(clip_name in clip_qwen_fav))
                chk = tk.Checkbutton(l_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=row, column=0, sticky="w", padx=15)
                self.clip_favorite_vars['qwen'][clip_name] = var
                row += 1

        wan_encoders = sorted([c for c in clips_data.get('wan', []) if isinstance(c, str)], key=str.lower)
        if wan_encoders:
            ttk.Label(l_frame, text="WAN Encoders", style=BOLD_TLABEL_STYLE).grid(row=row, column=0, sticky='w', padx=5, pady=(10, 2))
            row += 1
            for clip_name in wan_encoders:
                var = tk.BooleanVar(value=(clip_name in clip_wan_fav))
                chk = tk.Checkbutton(l_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=row, column=0, sticky="w", padx=15)
                self.clip_favorite_vars['wan'][clip_name] = var
                row += 1

        vision_encoders = sorted([c for c in clips_data.get('vision', []) if isinstance(c, str)], key=str.lower)
        if vision_encoders:
            ttk.Label(l_frame, text="WAN Vision Encoders", style=BOLD_TLABEL_STYLE).grid(row=row, column=0, sticky='w', padx=5, pady=(10, 2))
            row += 1
            for clip_name in vision_encoders:
                var = tk.BooleanVar(value=(clip_name in clip_vision_fav))
                chk = tk.Checkbutton(l_frame, text=clip_name, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL,
                                     selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR,
                                     activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
                chk.grid(row=row, column=0, sticky="w", padx=15)
                self.clip_favorite_vars['vision'][clip_name] = var
                row += 1
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
            qwen_data = {}
            if os.path.exists(QWEN_MODELS_FILE_NAME):
                with open(QWEN_MODELS_FILE_NAME, 'r') as f: qwen_data = json.load(f)
            if not isinstance(qwen_data, dict): qwen_data = {}
            qwen_data.setdefault('checkpoints', [])
            qwen_data['favorites'] = [model for model, var in self.qwen_model_favorite_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
            qwen_data['vae_favorites'] = [vae for vae, var in self.qwen_vae_favorite_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
            if save_json_config(QWEN_MODELS_FILE_NAME, qwen_data, "Qwen model favorites"): saved_files_count +=1
        except Exception as e: errors_list.append(f"{QWEN_MODELS_FILE_NAME}: {e}"); traceback.print_exc()
        try:
            wan_data = {}
            if os.path.exists(WAN_MODELS_FILE_NAME):
                with open(WAN_MODELS_FILE_NAME, 'r') as f: wan_data = json.load(f)
            if not isinstance(wan_data, dict): wan_data = {}
            wan_data.setdefault('checkpoints', [])
            wan_data.setdefault('video', [])
            wan_data['favorites'] = [model for model, var in self.wan_model_favorite_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
            wan_data['video_favorites'] = [video for video, var in self.wan_video_favorite_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
            wan_data['vae_favorites'] = [vae for vae, var in self.wan_vae_favorite_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
            if save_json_config(WAN_MODELS_FILE_NAME, wan_data, "WAN model favorites"): saved_files_count +=1
        except Exception as e: errors_list.append(f"{WAN_MODELS_FILE_NAME}: {e}"); traceback.print_exc()
        try:
            llm_models_data = {}
            if os.path.exists(LLM_MODELS_FILE_NAME):
                with open(LLM_MODELS_FILE_NAME, 'r') as f: llm_models_data = json.load(f)
            if not isinstance(llm_models_data, dict): llm_models_data = {}
            providers_data = llm_models_data.setdefault('providers', {})
            if not isinstance(providers_data, dict):
                providers_data = {}
                llm_models_data['providers'] = providers_data
            for provider_key, model_vars in self.llm_model_favorite_vars.items():
                provider_entry = providers_data.get(provider_key)
                if not isinstance(provider_entry, dict):
                    provider_entry = {"display_name": provider_key.capitalize(), "models": [], "favorites": []}
                favorites_list = [model_name for model_name, var in model_vars.items() if isinstance(var, tk.BooleanVar) and var.get()]
                provider_entry['favorites'] = favorites_list
                providers_data[provider_key] = provider_entry
            if save_json_config(LLM_MODELS_FILE_NAME, llm_models_data, "LLM model favorites"): saved_files_count +=1
        except Exception as e: errors_list.append(f"{LLM_MODELS_FILE_NAME}: {e}"); traceback.print_exc()
        try:
            clips_data = {}
            if os.path.exists(CLIP_LIST_FILE_NAME):
                with open(CLIP_LIST_FILE_NAME, 'r') as f: clips_data = json.load(f)
            if not isinstance(clips_data, dict): clips_data = {}
            clips_data.setdefault('t5', []); clips_data.setdefault('clip_L', []);
            clips_data.setdefault('qwen', []); clips_data.setdefault('wan', []); clips_data.setdefault('vision', []);
            clips_data.setdefault('favorites', {})
            if not isinstance(clips_data['favorites'], dict): clips_data['favorites'] = {}
            clips_data['favorites']['t5'] = [clip for clip, var in self.clip_favorite_vars.get('t5', {}).items() if isinstance(var, tk.BooleanVar) and var.get()]
            clips_data['favorites']['clip_L'] = [clip for clip, var in self.clip_favorite_vars.get('clip_L', {}).items() if isinstance(var, tk.BooleanVar) and var.get()]
            clips_data['favorites']['qwen'] = [clip for clip, var in self.clip_favorite_vars.get('qwen', {}).items() if isinstance(var, tk.BooleanVar) and var.get()]
            clips_data['favorites']['wan'] = [clip for clip, var in self.clip_favorite_vars.get('wan', {}).items() if isinstance(var, tk.BooleanVar) and var.get()]
            clips_data['favorites']['vision'] = [clip for clip, var in self.clip_favorite_vars.get('vision', {}).items() if isinstance(var, tk.BooleanVar) and var.get()]
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
        self.editor_app.llm_models_config = load_llm_models_config_util()
        self.editor_app.provider_display_map = {
            k: v.get("display_name", k.capitalize())
            for k, v in self.editor_app.llm_models_config.get("providers", {}).items()
        }
        self.editor_app.config_manager.load_bot_settings_data(self.editor_app.llm_models_config)
        self.editor_app.populate_bot_settings_tab()
        if hasattr(self.editor_app, 'lora_styles_tab_manager'):
            self.editor_app.lora_styles_tab_manager.populate_lora_styles_tab()
        
        self.populate_all_favorites_sub_tabs()
