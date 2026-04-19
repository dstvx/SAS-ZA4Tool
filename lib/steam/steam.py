from pathlib import Path
import winreg
import vdf

class SteamPathNotFound(Exception):
    def __init__(self, message: str = "Steam installation path not found."):
        super().__init__(message)

class SteamUserParsingError(Exception):
    def __init__(self, message: str = "Steam user data cannot be parsed."):
        super().__init__(message)

def get_steam_path() -> Path:
    """Gets the Steam installation path via registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        return Path(steam_path)
    except FileNotFoundError:
        raise SteamPathNotFound()

def convert_steamid64_to_userid(steamid64: int) -> int:
    return steamid64 - 76561197960265728

def get_save_path(steam_path: Path, user_id: int) -> Path:
    """Locates Profile.save by mapping SteamID64 to local userdata."""
    base_path = steam_path / "userdata" / str(user_id) / "678800" / "local" / "Data" / "Docs"

    # Check for direct save (Legacy/Sync)
    direct_profile_path = base_path / "Profile.save"
    if direct_profile_path.is_file():
        return direct_profile_path

    # Check hash-named subdirectories (Cloud/Modern)
    if base_path.exists():
        for sub_dir in base_path.iterdir():
            if sub_dir.is_dir() and len(sub_dir.name) == 24:
                hashed_profile_path = sub_dir / "Profile.save"
                if hashed_profile_path.is_file():
                    return hashed_profile_path

    raise FileNotFoundError(f"SAS4 Profile.save not found for user {user_id} in {base_path}")

def get_local_steam_users() -> list[tuple[str, int]]:
    """Lists local Steam users from loginusers.vdf."""
    steam_path = get_steam_path()
    loginusers_path = steam_path / "config" / "loginusers.vdf"

    if not loginusers_path.is_file():
        raise FileNotFoundError(f"loginusers.vdf not found at {loginusers_path}")

    with open(loginusers_path, 'r', encoding='utf-8') as f:
        data = vdf.load(f)

    local_users: list[tuple[str, int]] = []
    users = data.get("users", {})

    for steamid_str, user_data in users.items():
        try:
            local_users.append((user_data.get("PersonaName", "Unknown"), int(steamid_str)))
        except ValueError:
            continue

    return local_users

def get_local_steam_users_with_sas4() -> list[tuple[str, int]]:
    """Filters local users who have an existing SAS4 save folder."""
    steam_path = get_steam_path()
    all_users = get_local_steam_users()
    
    sas4_users = []
    for username, steam_id64 in all_users:
        try:
            user_id = convert_steamid64_to_userid(steam_id64)
            get_save_path(steam_path, user_id)
            sas4_users.append((username, steam_id64))
        except FileNotFoundError:
            continue
    
    return sas4_users

__all__ = [
    "SteamPathNotFound",
    "SteamUserParsingError",
    "convert_steamid64_to_userid",
    "get_steam_path",
    "get_save_path",
    "get_local_steam_users",
    "get_local_steam_users_with_sas4",
]