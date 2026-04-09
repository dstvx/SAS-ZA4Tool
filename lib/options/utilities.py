import json
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

from lib.ui.user_interface import OptionType, create_option
from lib.utils.config import ConfigManager
from lib.steam.steam import get_save_path, convert_steamid64_to_userid
from lib.save_handler import save_manager


def _get_active_save_path() -> Path | None:
    """Helper to fetch the current active Profile.save path based on Config."""
    with ConfigManager() as config:
        cm = config.data
        steam_path_str = cm.get("steam_path", "")
        steamid64 = cm.get("steam_id64", 0)
        
        if not steam_path_str or not steamid64:
            return None
        
        steam_path = Path(steam_path_str)
        user_id = convert_steamid64_to_userid(steamid64)
        try:
            return get_save_path(steam_path, user_id)
        except Exception:
            return None

def _prompt_file(title: str, filetypes: list[tuple[str, str]]) -> Path | None:
    """Helper to prompt the user for a file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    selected_path = filedialog.askopenfilename(
        parent=root,
        title=title,
        filetypes=filetypes
    )
    
    root.destroy()
    if selected_path:
        return Path(selected_path)
    return None

def _create_timestamped_folder(base_folder: str) -> Path:
    """Creates and returns a Path to a timestamped folder inside the given base_folder."""
    # Format: YYYY-MM-DD_HH-MM-SS
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_path = Path.cwd() / base_folder / timestamp
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path

def backup_profile() -> dict:
    """Backs up the current Profile.save into a Backup/timestamp directory."""
    save_path = _get_active_save_path()
    if not save_path or not save_path.exists():
        return {"message": "Could not locate active Profile.save to backup.", "is_error": True}
        
    try:
        backup_dir = _create_timestamped_folder("Backup")
        dest = backup_dir / "Profile.save"
        shutil.copy2(save_path, dest)
        # Invalidating cache isn't strictly necessary for a backup read, 
        # but safe if we want to ensure next read is fresh.
        save_manager.invalidate_cache() 
        return {"message": f"Successfully backed up to {backup_dir.name}/Profile.save", "is_error": False}
    except Exception as e:
        return {"message": f"Failed to backup profile: {e}", "is_error": True}

def decode_profile() -> dict:
    """Decodes Profile.save into a Decoded/timestamp/Profile.json file."""
    save_path = _get_active_save_path()
    if not save_path or not save_path.exists():
        return {"message": "Could not locate active Profile.save to decode.", "is_error": True}
        
    try:
        save_data = save_manager.get_data(save_path)
        formatted_json = json.dumps(save_data, indent=4)
        
        decode_dir = _create_timestamped_folder("Decoded")
        dest = decode_dir / "Profile.json"
        
        with open(dest, "w", encoding="utf-8") as f:
            f.write(formatted_json)
            
        return {"message": f"Successfully decoded to {decode_dir.name}/Profile.json", "is_error": False}
    except Exception as e:
        return {"message": f"Failed to decode profile: {e}", "is_error": True}

def encode_profile() -> dict:
    """Prompts for a Profile.json and encodes it into the active Profile.save (makes a backup)."""
    save_path = _get_active_save_path()
    if not save_path:
        return {"message": "Could not locate active Profile.save destination.", "is_error": True}
        
    json_path = _prompt_file("Select Profile.json to Encode", [("JSON Files", "*.json")])
    if not json_path:
        return {"message": "Encoding cancelled.", "is_error": True}
        
    try:
        # 1. Take a Backup First
        backup_result = backup_profile()
        if backup_result["is_error"]:
            return {"message": f"Aborting encode. Auto-backup failed: {backup_result['message']}", "is_error": True}
            
        # 2. Read the JSON string
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            
        # 3. Encode back over the active save and refresh cache
        save_manager.save_recorded_data(save_path, json_data)
        
        backup_dir_name = backup_result["message"].split('to ')[1].split('/')[0]
        return {
            "message": f"Successfully encoded to Profile.save! (Backup saved in {backup_dir_name})", 
            "is_error": False
        }
    except Exception as e:
        return {"message": f"Failed to encode profile: {e}", "is_error": True}

def replace_profile() -> dict:
    """Prompts for an external Profile.save and replaces the active one (makes a backup)."""
    save_path = _get_active_save_path()
    if not save_path:
        return {"message": "Could not locate active Profile.save destination.", "is_error": True}
        
    replacement_path = _prompt_file("Select Replacement Profile.save", [("Save Files", "*.save")])
    if not replacement_path:
        return {"message": "Replacement cancelled.", "is_error": True}
        
    try:
        # 1. Take a Backup First
        backup_result = backup_profile()
        if backup_result["is_error"]:
            return {"message": f"Aborting replacement. Auto-backup failed: {backup_result['message']}", "is_error": True}
            
        # 2. Replace the save
        shutil.copy2(replacement_path, save_path)
        save_manager.invalidate_cache()
        
        backup_dir_name = backup_result["message"].split('to ')[1].split('/')[0]
        return {
            "message": f"Successfully replaced Profile.save! (Backup saved in {backup_dir_name})", 
            "is_error": False
        }
    except Exception as e:
        return {"message": f"Failed to replace profile: {e}", "is_error": True}


def generate_utilities_menu() -> dict:
    """Generates the Utilities menu node dynamically."""
    
    # We use SUBMENU here to hold all the utilities
    utilities_menu = create_option(
        label='Utilities',
        option_id='1.3',
        option_type=OptionType.SUBMENU,
        children=[
            create_option(
                label='Decode Profile.save (extract to JSON)',
                option_id='1.3.1',
                option_type=OptionType.ACTION,
                action=decode_profile
            ),
            create_option(
                label='Backup Profile.save',
                option_id='1.3.2',
                option_type=OptionType.ACTION,
                action=backup_profile
            ),
            create_option(
                label='Encode JSON into Profile.save (WARNING: OVERWRITES)',
                option_id='1.3.3',
                option_type=OptionType.INPUT['confirm'],
                action=encode_profile
            ),
            create_option(
                label='Replace Profile.save with another (WARNING: OVERWRITES)',
                option_id='1.3.4',
                option_type=OptionType.INPUT['confirm'],
                action=replace_profile
            ),
        ]
    )
    
    return utilities_menu
