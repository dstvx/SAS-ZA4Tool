import sys

from lib.config import config
from lib.exceptions import CancelError, ProfileNotFoundError, SaveError
from lib.menu.globals import handle_global_menu
from lib.menu.profile import handle_profile_menu
from lib.menu.settings import handle_settings_menu
from lib.save.editor import Editor
from lib.ui.ui import (
    clear_screen,
    draw_menu,
    get_key,
    get_option_description,
    launch_game,
    prompt_confirm,
)
from lib.utils.logger import logger


def run_app() -> None:
    """Runs the primary console event loop and navigation routing for the application."""
    editor: Editor = Editor()

    try:
        editor.sync()
    except (SaveError, ProfileNotFoundError, OSError, KeyError, ValueError) as e:
        logger.error(f"Failed initial sync: {e}")

    selected_idx: int = 0
    message: str = ""

    while True:
        options: list[str] = [
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
            elif key in ("backspace", "esc", "left", "ctrl+c"):
                if prompt_confirm("Are you sure you want to exit the application?"):
                    clear_screen()
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
                        err: str | None = handle_profile_menu(editor)
                        if err:
                            message = err
                elif idx == 1:
                    handle_global_menu(editor)
                elif idx == 2:
                    handle_settings_menu(editor)
                elif idx == 3 and prompt_confirm("Are you sure you want to exit the application?"):
                    clear_screen()
                    sys.exit(0)
        except CancelError:
            message = "Action cancelled."

