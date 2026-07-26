import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from lib.config import config
from lib.ui.ui import console, prompt_str, prompt_confirm, prompt_int
from lib.steam.steam import default_resolver
from lib.steam.sas_za4 import save_path as sas_za4_save_path
from lib.save.editor import Editor
from lib.utils.logger import logger


def parse_steam_users(steam_path: Path) -> List[Dict[str, str]]:
    """Parses loginusers.vdf to find active Steam users on this machine.

    Args:
        steam_path (Path): Path to Steam installation directory.

    Returns:
        List[Dict[str, str]]: List of user dictionaries containing steam_id, persona, and account.
    """
    vdf_path: Path = steam_path / "config" / "loginusers.vdf"
    users: List[Dict[str, str]] = []
    if not vdf_path.exists():
        return users

    try:
        with open(vdf_path, "r", encoding="utf-8") as f:
            content: str = f.read()
        
        matches = re.finditer(r'"(\d{17})"\s*\{([^}]+)\}', content, re.DOTALL)
        for m in matches:
            steam_id: str = m.group(1)
            body: str = m.group(2)
            
            persona_match = re.search(r'"PersonaName"\s+"([^"]+)"', body)
            account_match = re.search(r'"AccountName"\s+"([^"]+)"', body)
            
            users.append({
                "steam_id": steam_id,
                "persona": persona_match.group(1) if persona_match else "Unknown",
                "account": account_match.group(1) if account_match else "Unknown"
            })
    except Exception as e:
        logger.error(f"Failed parsing VDF: {e}")
    return users


def run_setup() -> None:
    """Runs the interactive configuration setup wizard."""
    console.clear()
    console.print("\n[bold yellow]>>> SAS:ZA4Tool Setup Wizard <<<[/]")
    console.print("Let's configure your Steam and SAS:ZA4 game save settings.\n")

    use_steam: bool = prompt_confirm("Do you want to auto-detect Steam settings from this machine?")
    steam_id: str = ""
    save_path: str = ""

    if use_steam:
        try:
            steam_path: Optional[Path] = default_resolver.resolve()
            if not steam_path:
                raise FileNotFoundError("Steam installation path not found in registry.")
            console.print(f"Steam directory found: [green]{steam_path}[/]")
            users: List[Dict[str, str]] = parse_steam_users(steam_path)
            
            if users:
                console.print("\n[bold white]Available Steam Users on this PC:[/]")
                for idx, user in enumerate(users):
                    console.print(f"  [{idx + 1}] [cyan]{user['persona']} ({user['account']})[/] - ID: {user['steam_id']}")
                
                sel: int = prompt_int("Select user profile index", min_val=1, max_val=len(users), clear_screen=False)
                selected_user: Dict[str, str] = users[sel - 1]
                steam_id = selected_user["steam_id"]
                console.print(f"Selected: [green]{selected_user['persona']}[/]")
            else:
                console.print("[yellow]No Steam users detected in loginusers.vdf.[/]")
                steam_id = prompt_str("Please enter your 17-digit Steam ID manually", clear_screen=False)
        except Exception as e:
            console.print(f"[bold red]Failed to resolve Steam path: {e}[/]")
            steam_id = prompt_str("Please enter your 17-digit Steam ID manually", clear_screen=False)
    else:
        while True:
            steam_id = prompt_str("Enter your 17-digit Steam ID", clear_screen=False)
            if steam_id.isdigit() and len(steam_id) == 17:
                break
            console.print("[bold red]Steam ID must be exactly 17 digits.[/]")

    if use_steam and steam_id:
        try:
            save_path = str(sas_za4_save_path.get(steam_id))
            console.print(f"Auto-resolved SAS:ZA4 save path: [green]{save_path}[/]")
            if not Path(save_path).exists():
                console.print("[yellow]Resolved save path does not exist on disk.[/]")
                save_path = ""
        except Exception as e:
            console.print(f"[yellow]Could not automatically resolve SAS:ZA4 save path: {e}[/]")
            save_path = ""

    while not save_path or not Path(save_path).exists():
        save_path = prompt_str("Please paste the absolute path to your Profile.save file", clear_screen=False)
        if Path(save_path).exists() and Path(save_path).name == "Profile.save":
            break
        console.print("[bold red]Invalid path or file name. Must exist and end in 'Profile.save'.[/]")

    config.steam_id = steam_id
    config.save_path = save_path

    try:
        editor: Editor = Editor()
        loaded_profiles: List[str] = editor.get_loaded_profiles()
        config.active_profiles = loaded_profiles

        if len(loaded_profiles) == 1:
            config.current_profile = loaded_profiles[0]
            console.print(f"Only one active profile found. Current profile set to [green]{loaded_profiles[0]}[/].")
        elif len(loaded_profiles) > 1:
            console.print("\n[bold white]Select Default Active Profile:[/]")
            for idx, prof in enumerate(loaded_profiles):
                console.print(f"  [{idx + 1}] {prof}")
            sel = prompt_int("Select profile index", min_val=1, max_val=len(loaded_profiles), clear_screen=False)
            config.current_profile = loaded_profiles[sel - 1]
        else:
            config.current_profile = ""
            console.print("[yellow]No loaded character profiles found in save file.[/]")
    except Exception as e:
        logger.error(f"Setup profile resolution failed: {e}")
        console.print(f"[bold red]Failed to read character profiles from save file: {e}[/]")

    check_updates: bool = prompt_confirm("Do you want to enable automatic update checking on startup?", clear_screen=False)
    config.check_updates = check_updates

    config.setup_done = True
    console.print("\n[bold green]Configuration setup complete![/]")
    input("Press Enter to launch SAS:ZA4Tool...")
