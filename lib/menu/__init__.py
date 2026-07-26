import sys
import subprocess
from typing import Optional, List, Final
from lib.config import config
from lib.ui.ui import draw_menu, get_key, prompt_confirm, launch_game, get_option_description
from lib.save.editor import Editor
from lib.menu.settings import handle_settings_menu
from lib.menu.globals import handle_global_menu
from lib.menu.profile import handle_profile_menu
from lib.utils.logger import logger
from lib.exceptions import CancelError


def run_app() -> None:
    """Runs the primary console event loop and navigation routing for the application."""
    editor: Editor = Editor()
    
    try:
        editor.sync()
    except Exception as e:
        logger.error(f"Failed initial sync: {e}")
        
    selected_idx: int = 0
    message: str = ""
    
    while True:
        options: List[str] = [
            f"Profile (Active Profile: {config.current_profile or 'None'})",
            "Global",
            "Settings",
            "Exit"
        ]
        
        draw_menu("Main Menu", options, selected_idx, message, breadcrumb="Main Menu")
        message = ""
        
        try:
            key: str = get_key()
            if not key:
                continue
                
            if key == "up":
                selected_idx = (selected_idx - 1) % len(options)
            elif key == "down":
                selected_idx = (selected_idx + 1) % len(options)
            elif key in ("backspace", "esc", "left"):
                if prompt_confirm("Are you sure you want to exit the application?"):
                    subprocess.run("cls", shell=True)
                    sys.exit(0)
            elif key == "ctrl+c":
                if prompt_confirm("Are you sure you want to exit?"):
                    subprocess.run("cls", shell=True)
                    sys.exit(0)
            elif key == "ctrl+x":
                message = launch_game()
            elif key == "ctrl+i":
                message = get_option_description(options[selected_idx])
            elif key in ("enter", "space", "right") or key.isdigit() or (len(key) == 1 and key.isalpha()):
                idx: int = selected_idx
                if key.isdigit():
                    digit_idx: int = int(key) - 1
                    if 0 <= digit_idx < len(options):
                        idx = digit_idx
                elif len(key) == 1 and key.isalpha():
                    alpha_idx: int = ord(key.upper()) - 65 + 9
                    if 0 <= alpha_idx < len(options):
                        idx = alpha_idx
                        
                if idx == 0:
                    if not config.current_profile:
                        message = "No active profile selected. Switch to one in Settings first."
                    else:
                        err: Optional[str] = handle_profile_menu(editor)
                        if err:
                            message = err
                elif idx == 1:
                    handle_global_menu(editor)
                elif idx == 2:
                    handle_settings_menu(editor)
                elif idx == 3:
                    if prompt_confirm("Are you sure you want to exit the application?"):
                        subprocess.run("cls", shell=True)
                        sys.exit(0)
        except CancelError:
            message = "Action cancelled."
