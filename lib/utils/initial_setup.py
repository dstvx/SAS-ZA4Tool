from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from lib.steam.steam import get_local_steam_users_with_sas4, get_steam_path, get_save_path, SteamPathNotFound, convert_steamid64_to_userid
from lib.ui.user_interface import OptionType, create_option
from lib.utils.config import ConfigManager
from lib.save_handler import save_manager

def prompt_directory() -> dict:
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    while True:
        sel = filedialog.askdirectory(parent=root, title="Select Steam Installation Folder")
        if not sel: break
        
        path = Path(sel)
        if (path / "steam.exe").exists():
            with ConfigManager() as config: config.data['steam_path'] = str(path)
            break
        print("Invalid directory: steam.exe not found.")
    
    root.destroy()
    return run_auto_setup()

def complete_setup(profile_id: str):
    with ConfigManager() as config: config.data["selected_profile"] = profile_id
    return {"message": f"Setup Complete! Selected {profile_id}.", "command": {"exit": True}}

def set_steam_user_and_continue(uid: int):
    with ConfigManager() as config: config.data["steam_id64"] = uid
    return run_auto_setup()

def run_auto_setup():
    with ConfigManager() as config:
        cm = config.data
        
        # 1. Steam Path
        s_path_str = cm.get("steam_path", "")
        if s_path_str:
            steam_path = Path(s_path_str)
            if not steam_path.exists(): return {"message": "Steam path invalid.", "is_error": True}
        else:
            try:
                steam_path = get_steam_path()
                cm["steam_path"] = str(steam_path)
            except SteamPathNotFound: return {"message": "Auto-detect failed. Set manually.", "is_error": True}
        
        # 2. SteamID64
        sid = cm.get("steam_id64", 0)
        if not sid:
            try:
                users = get_local_steam_users_with_sas4()
                if not users: return {"message": "No Steam users found.", "is_error": True}
                
                if len(users) == 1:
                    sid = users[0][1]
                    cm["steam_id64"] = sid
                else:
                    initial_setup_menu["children"] = []
                    for user in users:
                        name, uid = user
                        initial_setup_menu["children"].append(create_option(name, f"setup_user_{uid}", OptionType.ACTION, action=lambda u=uid: set_steam_user_and_continue(u)))
                    return {"message": "Select Steam account:", "is_error": False}
            except Exception as e: return {"message": f"SteamID error: {e}", "is_error": True}
        
        # 3. Save Path
        try:
            uid = convert_steamid64_to_userid(sid)
            save_path = get_save_path(steam_path, uid)
        except Exception: return {"message": f"Save not found for {sid}.", "is_error": True}

        # 4. Profiles
        try:
            save_data = save_manager.get_data(save_path)
            inventory = save_data.get("Inventory", {})
            active = [k for k, v in inventory.items() if k.startswith("Profile") and v.get("Loaded") is True]
        except Exception as e: return {"message": f"Parse error: {e}", "is_error": True}
            
        if not active: return {"message": "No active profiles found.", "is_error": True}
        cm["active_profiles"] = active
        initial_setup_menu["children"] = []
        for p in active:
            initial_setup_menu["children"].append(create_option(p, f"setup_sel_{p}", OptionType.ACTION, action=lambda p_id=p: complete_setup(p_id)))
            
        return {"message": f"Found {len(active)} profiles in {save_path.name}.", "is_error": False}

initial_setup_menu = create_option('Setup', '1', OptionType.SUBMENU, message='Configure Steam path or SteamID64', children=[
    create_option('Run Auto Setup', '1.1', OptionType.ACTION, action=run_auto_setup),
    create_option('Manually Set SteamID64', '1.2', OptionType.INPUT['number'], config_key='steam_id64', action=run_auto_setup),
    create_option('Manually Set Steam path', '1.3', OptionType.ACTION, action=prompt_directory)
])