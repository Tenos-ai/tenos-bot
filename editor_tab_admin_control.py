import tkinter as tk
from tkinter import ttk, simpledialog
import traceback
import json
import os
import requests
import threading
import time
import re

from editor_utils import silent_showinfo, silent_showerror, silent_askyesno, silent_askstring, save_json_config
from editor_constants import (
    FRAME_BG_COLOR, TEXT_COLOR_NORMAL, LISTBOX_BG, LISTBOX_FG,
    LISTBOX_SELECT_BG, LISTBOX_SELECT_FG, ENTRY_BG_COLOR,
    BOLD_TLABEL_STYLE, TENOS_LIGHT_BLUE_ACCENT2, TENOS_DARK_BLUE_BG
)

BLOCKLIST_FILE = "blocklist.json"
USER_CACHE_FILE = "user_cache.json"

class AdminControlTab:
    """Manages the Admin, Allowed Users, Blocklist, and Live Bot Explorer."""

    def __init__(self, editor_app_ref, parent_notebook):
        self.editor_app = editor_app_ref
        self.notebook = parent_notebook
        self.admin_control_tab_frame = ttk.Frame(self.notebook, padding="10", style="Tenos.TFrame")
        self.notebook.add(self.admin_control_tab_frame, text=' Admin ')

        self.admin_username_var = tk.StringVar()
        self.admin_user_id_var = tk.StringVar()
        self.permission_vars = {}
        self.blocked_user_ids = set()
        self.user_cache = {}
        self.api_base_url = ""
        self.last_api_check_time = 0
        self.is_bot_api_online = False
        self.dm_data = {}
        self.admin_save_debounce_id = None
        self.available_permissions = {
            "can_gen": "Can use /gen command",
            "can_manage_bot": "Can use admin commands like /clear, /sheet",
            "can_use_actions": "Can use action buttons (Upscale, Vary, Rerun, etc.)",
            "can_delete_jobs": "Can delete own jobs with 🗑️ or --delete"
        }

        self._load_user_cache()
        self._create_widgets()
        self.populate_admin_tab()
        self.editor_app.master.after(2000, self.periodic_api_check)

    def _load_user_cache(self):
        if os.path.exists(USER_CACHE_FILE):
            try:
                with open(USER_CACHE_FILE, 'r') as f:
                    self.user_cache = json.load(f)
                if not isinstance(self.user_cache, dict): self.user_cache = {}
            except (json.JSONDecodeError, TypeError): self.user_cache = {}
        else: self.user_cache = {}

    def save_user_cache_on_exit(self):
        
        self._save_main_config()
        try:
            with open(USER_CACHE_FILE, 'w') as f:
                json.dump(self.user_cache, f, indent=2)
        except Exception as e:
            print(f"AdminTab Error: Could not save user cache on exit: {e}")

    def _create_widgets(self):
        self.admin_notebook = ttk.Notebook(self.admin_control_tab_frame, style="Tenos.TNotebook")
        self.admin_notebook.pack(expand=True, fill="both", padx=0, pady=0)
        user_management_tab = ttk.Frame(self.admin_notebook, padding="10", style="Tenos.TFrame")
        live_manager_tab = ttk.Frame(self.admin_notebook, padding="10", style="Tenos.TFrame")
        self.admin_notebook.add(user_management_tab, text=" User Management ")
        self.admin_notebook.add(live_manager_tab, text=" Live Manager ")
        self._create_user_management_widgets(user_management_tab)
        self._create_live_manager_widgets(live_manager_tab)

    def _create_user_management_widgets(self, parent_frame):
        parent_frame.rowconfigure(1, weight=1); parent_frame.columnconfigure(0, weight=1)
        
        admin_frame = ttk.LabelFrame(parent_frame, text="Main Bot Admin", style="Tenos.TLabelframe")
        admin_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        admin_frame.columnconfigure(1, weight=1); admin_frame.columnconfigure(3, weight=1)
        ttk.Label(admin_frame, text="Username:", style="Tenos.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        admin_user_entry = ttk.Entry(admin_frame, textvariable=self.admin_username_var, width=30, style="Tenos.TEntry")
        admin_user_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(admin_frame, text="User ID:", style="Tenos.TLabel").grid(row=0, column=2, sticky="w", padx=(10,5), pady=2)
        admin_id_entry = ttk.Entry(admin_frame, textvariable=self.admin_user_id_var, width=30, style="Tenos.TEntry")
        admin_id_entry.grid(row=0, column=3, sticky="ew", padx=5, pady=2)
        admin_user_entry.bind("<KeyRelease>", self._on_admin_change_debounced)
        admin_id_entry.bind("<KeyRelease>", self._on_admin_change_debounced)

        users_permissions_container = ttk.Frame(parent_frame, style="Tenos.TFrame")
        users_permissions_container.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        users_permissions_container.columnconfigure(1, weight=1); users_permissions_container.rowconfigure(0, weight=1)
        list_frame = ttk.Frame(users_permissions_container, style="Tenos.TFrame")
        list_frame.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ttk.Label(list_frame, text="Allowed Users:", style="Bold.TLabel").pack(anchor='w', pady=(0, 2))
        self.user_listbox = tk.Listbox(list_frame, width=35, bg=LISTBOX_BG, fg=LISTBOX_FG, selectbackground=LISTBOX_SELECT_BG, selectforeground=LISTBOX_SELECT_FG, highlightthickness=0, borderwidth=1, relief="sunken", font=('Arial', 9), exportselection=False)
        self.user_listbox.pack(pady=(0, 5), fill=tk.Y, expand=True)
        self.user_listbox.bind('<<ListboxSelect>>', self._on_user_selected)
        list_buttons_frame = ttk.Frame(list_frame, style="Tenos.TFrame")
        list_buttons_frame.pack(fill=tk.X)
        ttk.Button(list_buttons_frame, text="Add User (by ID)", command=self._add_user_prompt).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_buttons_frame, text="Remove User", command=self._remove_user).pack(side=tk.LEFT, padx=2)
        self.permissions_frame = ttk.LabelFrame(users_permissions_container, text="Permissions for Selected User", style="Tenos.TLabelframe")
        self.permissions_frame.grid(row=0, column=1, sticky="nsew")

        blocklist_pane = ttk.LabelFrame(parent_frame, text="User Blocklist", style="Tenos.TLabelframe")
        blocklist_pane.grid(row=2, column=0, sticky="nsew")
        blocklist_pane.columnconfigure(0, weight=1); blocklist_pane.rowconfigure(0, weight=1)
        self.block_listbox = tk.Listbox(blocklist_pane, height=6, bg=LISTBOX_BG, fg=LISTBOX_FG, selectbackground=LISTBOX_SELECT_BG, selectforeground=LISTBOX_SELECT_FG, highlightthickness=0, borderwidth=1, relief="sunken")
        self.block_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        block_buttons_frame = ttk.Frame(blocklist_pane, style="Tenos.TFrame")
        block_buttons_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        ttk.Button(block_buttons_frame, text="Block User (by ID)", command=self._add_blocked_user_prompt).pack(side=tk.LEFT, padx=2)
        ttk.Button(block_buttons_frame, text="Unblock Selected", command=self._remove_blocked_user).pack(side=tk.LEFT, padx=2)

    def _create_live_manager_widgets(self, parent_frame):
        top_live_frame = ttk.Frame(parent_frame, style="Tenos.TFrame")
        top_live_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_label = ttk.Label(top_live_frame, text="Bot API Status: OFFLINE", style="Bold.TLabel", foreground=TENOS_DARK_BLUE_BG)
        self.status_label.pack(side=tk.LEFT, padx=(0, 20))
        live_content_frame = ttk.Frame(parent_frame, style="Tenos.TFrame")
        live_content_frame.pack(fill=tk.BOTH, expand=True)
        live_content_frame.columnconfigure(0, weight=2); live_content_frame.columnconfigure(1, weight=3)
        live_content_frame.rowconfigure(0, weight=1); live_content_frame.rowconfigure(1, weight=1)
        server_pane = ttk.LabelFrame(live_content_frame, text="Servers", padding=5)
        server_pane.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        server_pane.rowconfigure(0, weight=1); server_pane.columnconfigure(0, weight=1)
        self.server_listbox = tk.Listbox(server_pane, bg=LISTBOX_BG, fg=LISTBOX_FG, selectbackground=LISTBOX_SELECT_BG, selectforeground=LISTBOX_SELECT_FG, exportselection=False)
        self.server_listbox.grid(row=0, column=0, sticky="nsew")
        self.server_listbox.bind("<<ListboxSelect>>", self.on_server_select)
        ttk.Button(server_pane, text="Leave Selected Server", command=self.leave_selected_server).grid(row=1, column=0, sticky="ew", pady=(5,0))
        member_pane = ttk.LabelFrame(live_content_frame, text="Members in Selected Server", padding=5)
        member_pane.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        member_pane.columnconfigure(0, weight=1); member_pane.rowconfigure(0, weight=1)
        self.member_listbox = tk.Listbox(member_pane, bg=LISTBOX_BG, fg=LISTBOX_FG, selectbackground=LISTBOX_SELECT_BG, selectforeground=LISTBOX_SELECT_FG, exportselection=False)
        self.member_listbox.grid(row=0, column=0, sticky="nsew")
        member_buttons = ttk.Frame(member_pane, style="Tenos.TFrame")
        member_buttons.grid(row=1, column=0, sticky="ew", pady=(5,0))
        ttk.Button(member_buttons, text="Add to Allowed Users", command=lambda: self.manage_selected_member("allow")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(member_buttons, text="Add to Blocklist", command=lambda: self.manage_selected_member("block")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        dm_pane = ttk.LabelFrame(live_content_frame, text="Recent Direct Messages", padding=5)
        dm_pane.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        dm_pane.columnconfigure(0, weight=1); dm_pane.rowconfigure(0, weight=1)
        self.dm_listbox = tk.Listbox(dm_pane, bg=LISTBOX_BG, fg=LISTBOX_FG, selectbackground=LISTBOX_SELECT_BG, selectforeground=LISTBOX_SELECT_FG, exportselection=False)
        self.dm_listbox.grid(row=0, column=0, sticky="nsew")
        self.dm_listbox.bind("<<ListboxSelect>>", self.on_dm_select)
        self.dm_content = tk.Text(dm_pane, height=5, state="disabled", wrap="word", background="#f0f0f0", fg="black")
        self.dm_content.grid(row=1, column=0, sticky="ew", pady=5)

    def _save_main_config(self): self.editor_app.config_manager.save_main_config_data(show_success_message=False)
    def _save_blocklist(self): save_json_config(BLOCKLIST_FILE, sorted(list(self.blocked_user_ids)), "blocklist")

    def populate_admin_tab(self):
        main_config = self.editor_app.config_manager.config; admin_user = main_config.get("ADMIN", {})
        self.admin_username_var.set(admin_user.get("USERNAME", "")); self.admin_user_id_var.set(admin_user.get("ID", ""))
        self.user_listbox.delete(0, tk.END)
        allowed_users = main_config.get("ALLOWED_USERS", {})
        sorted_user_ids = sorted(allowed_users.keys(), key=lambda uid: self.user_cache.get(uid, uid).lower())
        for user_id in sorted_user_ids:
            user_name = self.user_cache.get(user_id, "Unknown User")
            self.user_listbox.insert(tk.END, f"{user_name} ({user_id})")
        self._clear_permissions_frame()
        if self.user_listbox.size() > 0: self.user_listbox.selection_set(0); self._on_user_selected()
        else: ttk.Label(self.permissions_frame, text="Select a user to view permissions.", style="Tenos.TLabel").pack(padx=10, pady=10)
        self.load_and_populate_blocklist()

    def _on_user_selected(self, event=None):
        selection_indices = self.user_listbox.curselection()
        if not selection_indices:
            self._clear_permissions_frame(); ttk.Label(self.permissions_frame, text="Select a user to view permissions.", style="Tenos.TLabel").pack(padx=10, pady=10); return
        selection_text = self.user_listbox.get(selection_indices[0])
        user_id_match = re.search(r'\((\d+)\)', selection_text)
        if user_id_match: self._display_permissions_for_user(user_id_match.group(1))

    def _clear_permissions_frame(self):
        for widget in self.permissions_frame.winfo_children(): widget.destroy()

    def _display_permissions_for_user(self, user_id):
        self._clear_permissions_frame()
        user_id_str = str(user_id)
        main_config = self.editor_app.config_manager.config
        user_perms = main_config.get("ALLOWED_USERS", {}).get(user_id_str, {})
        user_name = self.user_cache.get(user_id_str, "Unknown User")
        self.permission_vars[user_id_str] = {}
        ttk.Label(self.permissions_frame, text=f"Editing: {user_name} ({user_id_str})", style="Bold.TLabel").pack(anchor='w', padx=5, pady=(5, 10))
        for perm_key, perm_desc in self.available_permissions.items():
            var = tk.BooleanVar(value=user_perms.get(perm_key, False))
            chk = tk.Checkbutton(self.permissions_frame, text=perm_desc, variable=var, bg=FRAME_BG_COLOR, fg=TEXT_COLOR_NORMAL, selectcolor=ENTRY_BG_COLOR, activebackground=FRAME_BG_COLOR, activeforeground=TEXT_COLOR_NORMAL, highlightthickness=0, borderwidth=0)
            chk.pack(anchor='w', padx=10, pady=2)
            chk.config(command=lambda uid=user_id_str, p=perm_key: self._on_permission_change(uid, p))
            self.permission_vars[user_id_str][perm_key] = var

    def _on_admin_change_debounced(self, event=None):
        if self.admin_save_debounce_id: self.editor_app.master.after_cancel(self.admin_save_debounce_id)
        self.admin_save_debounce_id = self.editor_app.master.after(2000, self._perform_admin_save)

    def _perform_admin_save(self):
        main_config = self.editor_app.config_manager.config
        if "ADMIN" not in main_config: main_config["ADMIN"] = {}
        main_config["ADMIN"]["USERNAME"] = self.admin_username_var.get().strip()
        main_config["ADMIN"]["ID"] = self.admin_user_id_var.get().strip()
        self._save_main_config()

    def _on_permission_change(self, user_id, perm_key):
        user_id_str = str(user_id)
        main_config = self.editor_app.config_manager.config
        if "ALLOWED_USERS" not in main_config: main_config["ALLOWED_USERS"] = {}
        if user_id_str not in main_config["ALLOWED_USERS"]: main_config["ALLOWED_USERS"][user_id_str] = {}
        var = self.permission_vars.get(user_id_str, {}).get(perm_key)
        if var:
            
            main_config["ALLOWED_USERS"][user_id_str][perm_key] = var.get()

    def _add_user_prompt(self):
        id_str = silent_askstring("Add User by ID", "Enter the Discord User ID of the user to allow:", parent=self.editor_app.master)
        if id_str and id_str.strip().isdigit():
            new_user_id = id_str.strip()
            if self.is_bot_api_online:
                threading.Thread(target=self._fetch_user_and_add, args=(new_user_id, "allow"), daemon=True).start()
            else: self._add_user_to_config(new_user_id, "Unknown User")
        elif id_str: silent_showerror("Invalid ID", "Please enter a valid numeric Discord User ID.", parent=self.editor_app.master)

    def _fetch_user_and_add(self, user_id, add_type):
        user_name = "Unknown User"
        try:
            response = requests.get(f"{self.api_base_url}/user/{user_id}", timeout=3)
            if response.status_code == 200: user_name = response.json().get("name", "Unknown User")
        except Exception: pass
        if add_type == "allow": self.editor_app.master.after(0, self._add_user_to_config, user_id, user_name)
        elif add_type == "block": self.editor_app.master.after(0, self._add_blocked_user_to_config, int(user_id), user_name)

    def _add_user_to_config(self, user_id, user_name="Unknown User"):
        main_config = self.editor_app.config_manager.config
        if user_id in main_config.get("ALLOWED_USERS", {}):
            silent_showerror("User Exists", f"User ID '{user_id}' is already in the allowed list.", parent=self.editor_app.master); return
        if "ALLOWED_USERS" not in main_config: main_config["ALLOWED_USERS"] = {}
        main_config["ALLOWED_USERS"][user_id] = {key: False for key in self.available_permissions}
        self.user_cache[user_id] = user_name
        self._save_main_config(); self.populate_admin_tab()
        try:
            all_users_in_list = [re.search(r'\((\d+)\)', item).group(1) for item in self.user_listbox.get(0, tk.END) if re.search(r'\((\d+)\)', item)]
            if user_id in all_users_in_list:
                self.user_listbox.selection_clear(0, tk.END)
                self.user_listbox.selection_set(all_users_in_list.index(user_id)); self._on_user_selected()
        except (AttributeError, tk.TclError): pass

    def _remove_user(self):
        selection_indices = self.user_listbox.curselection()
        if not selection_indices: silent_showwarning("No Selection", "Please select a user to remove.", parent=self.editor_app.master); return
        selection_text = self.user_listbox.get(selection_indices[0])
        user_id_match = re.search(r'\((\d+)\)', selection_text)
        if not user_id_match: return
        user_id_to_remove = user_id_match.group(1)
        main_config = self.editor_app.config_manager.config
        if silent_askyesno("Confirm Removal", f"Are you sure you want to remove user {selection_text}?", parent=self.editor_app.master):
            if user_id_to_remove in main_config.get("ALLOWED_USERS", {}):
                del main_config["ALLOWED_USERS"][user_id_to_remove]
                if user_id_to_remove in self.permission_vars: del self.permission_vars[user_id_to_remove]
                self._save_main_config(); self.populate_admin_tab()
                silent_showinfo("User Removed", f"User {selection_text} has been removed.", parent=self.editor_app.master)

    def load_and_populate_blocklist(self):
        if os.path.exists(BLOCKLIST_FILE):
            try:
                with open(BLOCKLIST_FILE, 'r') as f: self.blocked_user_ids = set(json.load(f))
            except (json.JSONDecodeError, TypeError): self.blocked_user_ids = set()
        else: self.blocked_user_ids = set()
        self.block_listbox.delete(0, tk.END)
        for user_id in sorted(list(self.blocked_user_ids)):
            user_name = self.user_cache.get(str(user_id), "Unknown User")
            self.block_listbox.insert(tk.END, f"{user_name} ({user_id})")

    def _add_blocked_user_prompt(self):
        id_str = silent_askstring("Block User by ID", "Enter the Discord User ID to block:", parent=self.editor_app.master)
        if id_str and id_str.strip().isdigit():
            new_user_id = int(id_str.strip())
            if self.is_bot_api_online:
                threading.Thread(target=self._fetch_user_and_add, args=(str(new_user_id), "block"), daemon=True).start()
            else: self._add_blocked_user_to_config(new_user_id, "Unknown User")
        elif id_str: silent_showerror("Invalid ID", "Please enter a valid numeric Discord User ID.", parent=self.editor_app.master)

    def _add_blocked_user_to_config(self, user_id, user_name="Unknown User"):
        if user_id in self.blocked_user_ids:
            silent_showerror("Already Blocked", f"User ID {user_id} is already blocked.", parent=self.editor_app.master); return
        self.blocked_user_ids.add(user_id)
        self.user_cache[str(user_id)] = user_name
        self._save_blocklist(); self.load_and_populate_blocklist()
        silent_showinfo("User Blocked", f"User {user_name} ({user_id}) added to blocklist.", parent=self.editor_app.master)

    def _remove_blocked_user(self):
        selection_indices = self.block_listbox.curselection()
        if not selection_indices: silent_showwarning("No Selection", "Please select a User ID to unblock.", parent=self.editor_app.master); return
        selection_text = self.block_listbox.get(selection_indices[0])
        user_id_match = re.search(r'\((\d+)\)', selection_text)
        if not user_id_match: silent_showerror("Parse Error", "Could not extract User ID from selected item.", parent=self.editor_app.master); return
        user_id_to_remove = int(user_id_match.group(1))
        if user_id_to_remove in self.blocked_user_ids:
            self.blocked_user_ids.remove(user_id_to_remove)
            self._save_blocklist()
            self.load_and_populate_blocklist()
        else: silent_showerror("Error", "User ID not found in the current blocklist.", parent=self.editor_app.master)

    def periodic_api_check(self):
        is_bot_running = self.editor_app.bot_control_tab_manager.is_bot_script_running()
        if is_bot_running: self.refresh_all_live_data()
        elif self.is_bot_api_online: self.set_api_status(False)
        self.editor_app.master.after(3000, self.periodic_api_check)

    def set_api_status(self, is_online):
        if is_online != self.is_bot_api_online:
            self.is_bot_api_online = is_online
            if is_online: self.status_label.config(text="Bot API Status: ONLINE", foreground=TENOS_LIGHT_BLUE_ACCENT2)
            else:
                self.status_label.config(text="Bot API Status: OFFLINE", foreground=TENOS_DARK_BLUE_BG)
                self.server_listbox.delete(0, tk.END); self.member_listbox.delete(0, tk.END); self.dm_listbox.delete(0, tk.END)
                self.dm_content.config(state="normal"); self.dm_content.delete("1.0", tk.END); self.dm_content.config(state="disabled")

    def _get_api_url(self):
        cfg = self.editor_app.config_manager.config
        host = cfg.get("BOT_INTERNAL_API", {}).get("HOST", "127.0.0.1")
        port = cfg.get("BOT_INTERNAL_API", {}).get("PORT", 8189)
        return f"http://{host}:{port}/api"

    def refresh_all_live_data(self):
        self.api_base_url = self._get_api_url(); self.last_api_check_time = time.time()
        threading.Thread(target=self._fetch_all_data_thread, daemon=True).start()

    def _fetch_all_data_thread(self):
        try:
            guilds_response = requests.get(f"{self.api_base_url}/guilds", timeout=2)
            if guilds_response.status_code != 200: self.editor_app.master.after(0, self.set_api_status, False); return
            guilds_data = guilds_response.json()
            dms_response = requests.get(f"{self.api_base_url}/dms", timeout=2)
            dms_data = dms_response.json() if dms_response.status_code == 200 else []
            self.editor_app.master.after(0, self._update_gui_with_fetched_data, guilds_data, dms_data)
        except (requests.ConnectionError, requests.Timeout): self.editor_app.master.after(0, self.set_api_status, False)
        except Exception: self.editor_app.master.after(0, self.set_api_status, False)

    def _update_gui_with_fetched_data(self, guilds_data, dms_data):
        self.set_api_status(True); cache_updated = False
        selected_server_id = None
        if self.server_listbox.curselection(): selected_server_id = self.server_listbox.get(self.server_listbox.curselection()[0]).split(' | ')[-1]
        current_server_ids = {item.split(' | ')[-1] for item in self.server_listbox.get(0, tk.END)}
        new_server_ids = {guild['id'] for guild in guilds_data}
        if current_server_ids != new_server_ids:
            self.server_listbox.delete(0, tk.END)
            for guild in guilds_data: self.server_listbox.insert(tk.END, f"{guild['name']} | {guild['id']}")
            if selected_server_id:
                for i, item in enumerate(self.server_listbox.get(0, tk.END)):
                    if item.endswith(f" | {selected_server_id}"): self.server_listbox.selection_set(i); break
        selected_dm_id = None
        if self.dm_listbox.curselection():
            id_match = re.search(r'\((\d+)\)', self.dm_listbox.get(self.dm_listbox.curselection()[0]))
            if id_match: selected_dm_id = id_match.group(1)
        self.dm_data = {dm['author_id']: dm for dm in dms_data}
        for dm in dms_data:
            if str(dm['author_id']) not in self.user_cache or self.user_cache[str(dm['author_id'])] != dm['author_name']:
                self.user_cache[str(dm['author_id'])] = dm['author_name']; cache_updated = True
        new_dm_ids = set(self.dm_data.keys()); current_dm_ids = {re.search(r'\((\d+)\)', item).group(1) for item in self.dm_listbox.get(0, tk.END) if re.search(r'\((\d+)\)', item)}
        if new_dm_ids != current_dm_ids:
            self.dm_listbox.delete(0, tk.END)
            for dm in dms_data: self.dm_listbox.insert(tk.END, f"{dm['author_name']} ({dm['author_id']})")
            if selected_dm_id:
                for i, item in enumerate(self.dm_listbox.get(0, tk.END)):
                    if item.endswith(f"({selected_dm_id})"): self.dm_listbox.selection_set(i); break
        if cache_updated: self.populate_admin_tab()
        
    def on_server_select(self, event=None):
        selection = self.server_listbox.curselection()
        if not selection or not self.is_bot_api_online: return
        guild_id = self.server_listbox.get(selection[0]).split(' | ')[-1]
        threading.Thread(target=self._fetch_members_thread, args=(guild_id,), daemon=True).start()

    def _fetch_members_thread(self, guild_id):
        try:
            response = requests.get(f"{self.api_base_url}/guilds/{guild_id}/members", timeout=5)
            if response.status_code == 200: self.editor_app.master.after(0, self._update_members_list, response.json())
        except Exception: pass

    def _update_members_list(self, members_data):
        self.member_listbox.delete(0, tk.END); cache_updated = False
        for member in members_data:
            user_id_str = str(member['id'])
            if user_id_str not in self.user_cache or self.user_cache[user_id_str] != member['name']:
                self.user_cache[user_id_str] = member['name']; cache_updated = True
            user_type = " [BOT]" if member.get('is_bot') else ""
            display_name = f"{member['display_name']} ({member['name']}#{member['discriminator']}){user_type}"
            self.member_listbox.insert(tk.END, f"{display_name} | {member['id']}")
        if cache_updated: self.populate_admin_tab()

    def on_dm_select(self, event=None):
        selection = self.dm_listbox.curselection()
        if not selection: return
        id_match = re.search(r'\((\d+)\)', self.dm_listbox.get(selection[0]))
        if not id_match: return
        user_id = id_match.group(1)
        dm = self.dm_data.get(user_id)
        if dm:
            self.dm_content.config(state="normal"); self.dm_content.delete("1.0", tk.END)
            self.dm_content.insert(tk.END, f"Time: {dm['timestamp']}\n\n{dm['content']}"); self.dm_content.config(state="disabled")

    def leave_selected_server(self):
        selection = self.server_listbox.curselection()
        if not selection or not self.is_bot_api_online: return
        guild_name, guild_id = self.server_listbox.get(selection[0]).split(' | ')
        if silent_askyesno("Confirm Leave", f"Are you sure the bot should leave '{guild_name}'?", parent=self.editor_app.master):
             threading.Thread(target=self._leave_guild_thread, args=(guild_id,), daemon=True).start()

    def _leave_guild_thread(self, guild_id):
        try:
            response = requests.post(f"{self.api_base_url}/guilds/{guild_id}/leave", timeout=5)
            if response.status_code == 200: self.editor_app.master.after(0, self.refresh_all_live_data)
            else: self.editor_app.master.after(0, silent_showerror, "API Error", f"Failed to leave guild: {response.text}", self.editor_app.master)
        except Exception as e: self.editor_app.master.after(0, silent_showerror, "Connection Error", f"Could not contact bot API: {e}", self.editor_app.master)

    def manage_selected_member(self, action):
        selection = self.member_listbox.curselection()
        if not selection: silent_showwarning("No Selection", "Please select a member from the list.", parent=self.editor_app.master); return
        user_info_str = self.member_listbox.get(selection[0])
        user_name, user_id_str = user_info_str.rsplit(' | ', 1)
        user_id = int(user_id_str)
        username_simple_match = re.search(r'\(([^#]+)', user_name)
        username_simple = username_simple_match.group(1) if username_simple_match else user_name.split(' ')[0]
        if action == "allow":
            if silent_askyesno("Confirm Allow", f"Add '{username_simple} ({user_id_str})' to the Allowed Users list?", parent=self.editor_app.master):
                self._add_user_to_config(user_id_str, username_simple)
        elif action == "block":
            if silent_askyesno("Confirm Block", f"Add User ID {user_id} to the blocklist?", parent=self.editor_app.master):
                self._add_blocked_user_to_config(user_id, username_simple)
