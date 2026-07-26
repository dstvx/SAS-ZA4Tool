import msvcrt
import os
import subprocess
import re
import sys
from typing import Any, List, Optional, Final, Dict
from rich.console import Console
from lib.config import config
from lib.utils.logger import logger

console: Final[Console] = Console()

DESCRIPTIONS: Final[Dict[str, str]] = {
    "Character Editor": "Configure character name, money, keys, stats, sentries, items, and inventory.",
    "Account / Global Save Editor": "Edit global revive tokens, nightmare tickets, collection states, and premium DLCs.",
    "Settings & Tools Menu": "Manage profile configurations, save imports, backups, game path, and logging.",
    "Exit": "Safely exit the application.",
    "Revive Tokens": "Edit the number of Revive Tokens available on your account.",
    "Nightmare Tickets": "Edit the quantity of Nightmare Tickets for playing Nightmare mode.",
    "Remove Ads Toggle": "Enable or disable in-game ads removal.",
    "Unlock All Collections": "Instantly unlock all weapons, armor, and rewards collections.",
    "Wipe Collection Stats": "Reset all collection metrics including kills and damage stats.",
    "Unlock Character Slots": "Enable or disable premium Character Slots 4 and 5.",
    "Unlock Fairground Pack DLC": "Enable or disable the premium Fairground map pack DLC.",
    "Unlock All Premium Guns globally": "Purchase and unlock all premium IAP weapons globally.",
    "Join Faction": "Choose and join a Faction War faction.",
    "Set Faction War Credits": "Set Faction War planetary or general credits.",
    "Add Item": "Inject a custom weapon or armor piece into your Strongbox Claim Queue.",
    "Remove Item": "Delete a selected weapon or armor piece from your profile inventory.",
    "Change Username": "Modify the display name of your character.",
    "Set Cash/Money": "Modify the cash reserves on this profile.",
    "Set Black Keys Count": "Change the number of Black Keys available on this profile.",
    "Set Augment Cores Count": "Change the number of Elite Augment Cores available on this profile.",
    "Toggle Skill Reset": "Enable or disable free skill reset availability.",
    "Set Frag Grenades": "Change the number of Frag Grenades on this profile.",
    "Set Cryo Grenades": "Change the number of Cryo Grenades on this profile.",
    "Set Player Level": "Change player level (1-100) and synchronize experience points.",
    "Max Out Masteries": "Maximize all weapon and class masteries.",
    "Clear / Reset Masteries": "Reset all masteries to level 0.",
    "Set Multiplayer Stats": "Change multiplayer games, kills, deaths, wins, and losses.",
    "Manage Sentry Turrets": "Change quantities of sentry turrets in your inventory.",
    "Manage Available Black Boxes": "Add or overwrite available Black Boxes in your inventory.",
    "Clear All Strongbox and Black Box Claim Queues": "Wipe all pending normal and black strongbox claims.",
    "Select Profile": "Switch the active character profile to edit.",
    "Reload Active Profiles from Save": "Re-read and synchronize active profiles from the save file.",
    "Import Save File": "Import a save file (.save) or decrypted json (.json).",
    "Create Backup & Decrypted Export": "Save a backup copy and export decrypted data as Profile.json.",
    "Toggle Logging": "Enable or disable logging application logs to sas_za4tool.log.",
    "Change Game Path/URI": "Configure the Steam executable path or launch URI.",
    "Reset Configuration Setup Wizard": "Reset all configuration settings and run the initial setup wizard again."
}


def get_option_description(text: str) -> str:
    """Finds and returns the option description string matching the given text.

    Args:
        text (str): Option menu name.

    Returns:
        str: Description string, or default notice if not found.
    """
    cleaned: str = re.sub(r"\s*\(Current:.*?\)", "", text)
    cleaned = re.sub(r"\s*\(Active.*?\)", "", cleaned)
    cleaned = re.sub(r"\s*\(Enabled:.*?\)", "", cleaned)
    cleaned = cleaned.strip()
    
    for key, desc in DESCRIPTIONS.items():
        if cleaned.lower().startswith(key.lower()) or key.lower().startswith(cleaned.lower()):
            return desc
    return "No description available for this option."


def print_header() -> None:
    """Prints the application ASCII art title banner and selected profile name."""
    from lib.utils.updates import VERSION
    profile: str = config.current_profile or "None"
    header: str = (
        r"[red]        _______   _____ ____  ___  __________          __" + "\n"
        r"       / __/ _ | / __(_)_  / / _ |/ / /_  __/__  ___  / /" + "\n"
        r"      _\ \/ __ |_\ \_   / /_/ __ /_  _// / / _ \/ _ \/ / " + "\n"
        r"     /___/_/ |_/___(_) /___/_/ |_|/_/ /_/  \___/\___/_/  [/]" + "\n"
        r"                    [cyan]by[/][white]:[/] [green]dstvx[/][cyan] ver[/][white]:[/] [green]{}[/]" + "\n"
        r"                 [cyan]Selected Profile: [/][green]{}[/]"
    ).format(VERSION, profile)
    console.print(header)


def resize_console(width: int, height: int) -> None:
    """Resizes the console window and buffer size on Windows to match the required dimensions."""
    try:
        sys.stdout.write(f"\x1b[8;{height};{width}t")
        sys.stdout.flush()
    except Exception:
        pass

    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.windll.kernel32
        
        kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel32.GetStdHandle.restype = wintypes.HANDLE
        
        h_out = kernel32.GetStdHandle(4294967285)
        if h_out == -1 or h_out == 0 or h_out is None:
            return

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short),
                ("Top", ctypes.c_short),
                ("Right", ctypes.c_short),
                ("Bottom", ctypes.c_short)
            ]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [
                ("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", ctypes.c_ushort),
                ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD)
            ]

        kernel32.GetConsoleScreenBufferInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        kernel32.GetConsoleScreenBufferInfo.restype = wintypes.BOOL
        
        kernel32.SetConsoleWindowInfo.argtypes = [wintypes.HANDLE, wintypes.BOOL, ctypes.c_void_p]
        kernel32.SetConsoleWindowInfo.restype = wintypes.BOOL
        
        kernel32.SetConsoleScreenBufferSize.argtypes = [wintypes.HANDLE, COORD]
        kernel32.SetConsoleScreenBufferSize.restype = wintypes.BOOL

        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        if kernel32.GetConsoleScreenBufferInfo(h_out, ctypes.byref(csbi)):
            max_width = csbi.dwMaximumWindowSize.X
            max_height = csbi.dwMaximumWindowSize.Y
            width = min(width, max_width)
            height = min(height, max_height)

        rect = SMALL_RECT(0, 0, 1, 1)
        kernel32.SetConsoleWindowInfo(h_out, True, ctypes.byref(rect))

        buffer_size = COORD(width, height)
        kernel32.SetConsoleScreenBufferSize(h_out, buffer_size)

        rect = SMALL_RECT(0, 0, width - 1, height - 1)
        kernel32.SetConsoleWindowInfo(h_out, True, ctypes.byref(rect))
    except Exception:
        pass


def update_console_title(breadcrumb: str) -> None:
    """Updates the console window title with the application, current profile, and breadcrumb path."""
    if sys.platform != "win32":
        return
    import ctypes
    profile = getattr(config, "current_profile", "None") or "None"
    title = f"SAS:ZA4Tool by dstvx | {profile} | {breadcrumb}"
    ctypes.windll.kernel32.SetConsoleTitleW(title)


def draw_menu(title: str, options: List[str], selected_idx: int, message: str = "", breadcrumb: str = "Main Menu") -> None:
    """Renders the menu options list with titles and navigation help tips.

    Args:
        title (str): Submenu title.
        options (List[str]): List of choices string.
        selected_idx (int): Selected element index.
        message (str): Optional result feedback message to display.
        breadcrumb (str): Page history directory hierarchy.
    """
    update_console_title(breadcrumb)
    
    max_opt_len = max(len(opt) for opt in options) if options else 0
    width = max(95, max_opt_len + 12)
    height = 6 + 3 + len(options) + (2 if message else 1) + 3 + 8
    resize_console(width, height)

    subprocess.run("cls", shell=True)
    print_header()
    
    console.print(f"\n[dim]{breadcrumb}[/]")
    console.print(f"[bold white]>>> {title} <<<[/]\n")
    
    for idx, opt in enumerate(options):
        shortcut: str = str(idx + 1) if idx < 9 else chr(65 + idx - 9)
        if idx == selected_idx:
            console.print(f"  [reverse bold green] ({shortcut}) {opt} [/]")
        else:
            console.print(f"   [cyan]({shortcut})[/] {opt}")
            
    if message:
        console.print(f"\n[bold yellow]Message: {message}[/]")
    else:
        console.print("\n")
        
    console.print("\n[dim]Use Up/Down Arrow to navigate, Space/Enter/Right to select, Backspace/Esc/Left to go back[/]")
    console.print("[dim]Press 1-9 or A-Z to select instantly, Ctrl+X to launch game, Ctrl+C to exit, Tab / Ctrl+I for description[/]")


def get_key() -> str:
    """Reads a keystroke press from the Windows standard input buffer.

    Returns:
        str: Text name of key pressed (e.g. 'up', 'down', 'A', '1').
    """
    ch: bytes = msvcrt.getch()
    if ch in (b"\xe0", b"\x00"):
        ch2: bytes = msvcrt.getch()
        if ch2 == b"H": return "up"
        if ch2 == b"P": return "down"
        if ch2 == b"K": return "left"
        if ch2 == b"M": return "right"
        if ch2 == b"I": return "pageup"
        if ch2 == b"Q": return "pagedown"
        
    if ch == b"\r": return "enter"
    if ch == b" ": return "space"
    if ch == b"\x08": return "backspace"
    if ch == b"\x1b": return "esc"
    if ch == b"\x03": return "ctrl+c"
    if ch == b"\x18": return "ctrl+x"
    if ch in (b"\t", b"\x09"): return "ctrl+i"
    
    try:
        char: str = ch.decode("utf-8").upper()
        if char.isalnum():
            return char
    except UnicodeDecodeError:
        pass
    return ""


def prompt_input(prompt_text: str, clear_screen: bool = True) -> str:
    """Reads a text input string, optionally clearing the terminal and adding visual hints.

    Args:
        prompt_text (str): Prompt text description.
        clear_screen (bool): Whether to clear the screen on run.

    Returns:
        str: User input value string.
    """
    from lib.exceptions import CancelError
    if clear_screen:
        subprocess.run("cls", shell=True)
        print_header()
        
        prompt_str_line: str = f"  [bold cyan][>][/] {prompt_text}: "
        console.print(f"\n{prompt_str_line}")
        console.print("\n  [dim]Press Enter to confirm, Ctrl+C to cancel.[/]")
        
        plain_prompt: str = f"  [>] {prompt_text}: "
        prompt_len: int = len(plain_prompt)
        
        sys.stdout.write(f"\033[3A\r\033[{prompt_len}C")
        sys.stdout.flush()
        
        try:
            val: str = input()
            return val
        except (KeyboardInterrupt, EOFError):
            logger.info(f"Prompt '{prompt_text}' cancelled by user.")
            raise CancelError()
    else:
        prompt_str_line_inline: str = f"\n  [bold cyan][>][/] {prompt_text}: "
        try:
            val_inline: str = console.input(prompt_str_line_inline)
            return val_inline
        except (KeyboardInterrupt, EOFError):
            logger.info(f"Prompt '{prompt_text}' cancelled by user.")
            raise CancelError()


def prompt_int(prompt_text: str, min_val: Optional[int] = None, max_val: Optional[int] = None, clear_screen: bool = True) -> int:
    """Prompts the user for an integer, validating it stays within boundaries.

    Args:
        prompt_text (str): Prompt description.
        min_val (Optional[int]): Minimum allowed value.
        max_val (Optional[int]): Maximum allowed value.
        clear_screen (bool): Whether to clear screen first.

    Returns:
        int: Verified integer input value.
    """
    while True:
        try:
            val_str: str = prompt_input(prompt_text, clear_screen=clear_screen)
            val: int = int(val_str)
            if min_val is not None and val < min_val:
                continue
            if max_val is not None and val > max_val:
                continue
            return val
        except ValueError:
            pass


def prompt_str(prompt_text: str, clear_screen: bool = True) -> str:
    """Prompts the user for a non-empty string.

    Args:
        prompt_text (str): Prompt description.
        clear_screen (bool): Whether to clear screen first.

    Returns:
        str: Cleared non-empty string input value.
    """
    while True:
        val: str = prompt_input(prompt_text, clear_screen=clear_screen).strip()
        if val:
            return val


def prompt_confirm(prompt_text: str, clear_screen: bool = True) -> bool:
    """Prompts the user for a yes/no confirmation.

    Args:
        prompt_text (str): Prompt confirmation description.
        clear_screen (bool): Whether to clear screen first.

    Returns:
        bool: True for yes, False for no.
    """
    while True:
        val: str = prompt_input(f"{prompt_text} (Y/n)", clear_screen=clear_screen).strip().lower()
        if val == "" or val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False


def launch_game() -> str:
    """Launches SAS:ZA4 using configured executable path or URI.

    Returns:
        str: Result feedback notice string.
    """
    game_path: str = getattr(config, "game_path", "steam://run/678800")
    logger.info(f"Launching game from path/URI: {game_path}")
    try:
        if game_path.startswith("steam://") or os.path.exists(game_path):
            os.startfile(game_path)
            return "Game launched successfully!"
        else:
            return f"Game path '{game_path}' not found."
    except Exception as e:
        logger.error(f"Failed to launch game: {e}")
        return f"Failed to launch game: {e}"
