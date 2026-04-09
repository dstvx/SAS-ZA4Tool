import json
from pathlib import Path

from lib.ui.user_interface import OptionType, create_option
from lib.utils.config import ConfigManager
from lib.steam.steam import get_save_path, convert_steamid64_to_userid
from lib.save_handler import save_manager

def select_profile(profile_name: str) -> dict:
    """Action to change the currently activated profile in the config."""
    with ConfigManager() as config:
        config.data['selected_profile'] = profile_name
    return {
        "message": f"Successfully changed active profile to '{profile_name}'.",
        "is_error": False
    }

def scan_for_profiles(change_profile_node: dict) -> dict:
    """Scans the Profile.save for newly added character profiles."""
    with ConfigManager() as config:
        cm = config.data
        steam_path_str = cm.get("steam_path", "")
        steamid64 = cm.get("steam_id64", 0)
        
        if not steam_path_str or not steamid64:
            return {"message": "Setup incomplete. Expected Steam path and SteamID.", "is_error": True}
        
        try:
            steam_path = Path(steam_path_str)
            user_id = convert_steamid64_to_userid(steamid64)
            save_path = get_save_path(steam_path, user_id)
            
            save_data = save_manager.get_data(save_path)
            
            inventory = save_data.get("Inventory", {})
            active_profiles = []
            
            for profile_key, profile_data in inventory.items():
                if profile_key.startswith("Profile") and isinstance(profile_data, dict):
                    if profile_data.get("Loaded") is True:
                        active_profiles.append(profile_key)
            
            if not active_profiles:
                return {"message": "No active profiles found in your save file.", "is_error": True}
                
            cm["active_profiles"] = active_profiles
            
            # Dynamically update the Change Profile submenu options
            if change_profile_node is not None:
                change_profile_node['children'] = []
                for profile in active_profiles:
                    change_profile_node['children'].append(
                        create_option(
                            label=f"{profile}",
                            option_id=f"opt_sel_{profile}",
                            option_type=OptionType.ACTION,
                            action=lambda p=profile: select_profile(p)
                        )
                    )
            
            return {"message": f"Scan Complete! Found {len(active_profiles)} active profile(s).", "is_error": False}
            
        except Exception as e:
            return {"message": f"Failed to scan profiles: {e}", "is_error": True}

def generate_options_menu() -> dict:
    """Generates the Options menu node dynamically."""
    with ConfigManager() as config:
        active_profiles = config.data.get("active_profiles", [])
    
    change_profile_submenu = create_option(
        label='Change Profile',
        option_id='1.4.1',
        option_type=OptionType.SUBMENU,
        children=[]
    )
    
    # Pre-populate the profile submenu with the items found during setup
    for profile in active_profiles:
        change_profile_submenu['children'].append(
            create_option(
                label=f"{profile}",
                option_id=f"opt_sel_{profile}",
                option_type=OptionType.ACTION,
                action=lambda p=profile: select_profile(p)
            )
        )
        
    options_menu = create_option(
        label='Options',
        option_id='1.4',
        option_type=OptionType.SUBMENU,
        children=[
            change_profile_submenu,
            create_option(
                label='Scan for Updated Profiles',
                option_id='1.4.2',
                option_type=OptionType.ACTION,
                action=lambda: scan_for_profiles(change_profile_submenu)
            )
        ]
    )
    
    return options_menu
