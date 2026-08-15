import os
import re
import select
import subprocess
import sys
from typing import Final

from rich.console import Console

from lib.config import config
from lib.utils.logger import logger

console: Final[Console] = Console()

DESCRIPTIONS: Final[dict[str, str]] = {
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


def clear_screen() -> None:
    """Clears the console screen across platforms."""
    if sys.platform == "win32":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


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


_CURRENT_CONSOLE_SIZE: list[int] = [0, 0]


def resize_console(width: int, height: int) -> None:
    """Resizes the console window and buffer size only when dimensions change."""
    if _CURRENT_CONSOLE_SIZE == [width, height]:
        return
    _CURRENT_CONSOLE_SIZE[0] = width
    _CURRENT_CONSOLE_SIZE[1] = height

    try:
        sys.stdout.write(f"\x1b[8;{height};{width}t")
        sys.stdout.flush()
    except OSError:
        pass

    if sys.platform != "win32":
        return

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel32.GetStdHandle.restype = wintypes.HANDLE
        h_out = kernel32.GetStdHandle(4294967285)
        if h_out in (-1, 0, None):
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
            width = min(width, csbi.dwMaximumWindowSize.X)
            height = min(height, csbi.dwMaximumWindowSize.Y)

        rect = SMALL_RECT(0, 0, 1, 1)
        kernel32.SetConsoleWindowInfo(h_out, True, ctypes.byref(rect))

        buffer_size = COORD(width, height)
        kernel32.SetConsoleScreenBufferSize(h_out, buffer_size)

        rect = SMALL_RECT(0, 0, width - 1, height - 1)
        kernel32.SetConsoleWindowInfo(h_out, True, ctypes.byref(rect))
    except (ImportError, OSError, AttributeError):
        pass


def update_console_title(breadcrumb: str) -> None:
    """Updates the console window title with the application, current profile, and breadcrumb path."""
    profile = getattr(config, "current_profile", "None") or "None"
    title = f"SAS:ZA4Tool by dstvx | {profile} | {breadcrumb}"
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except (ImportError, OSError, AttributeError):
            pass
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()


def draw_menu(title: str, options: list[str], selected_idx: int, message: str = "", breadcrumb: str = "Main Menu") -> None:
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

    clear_screen()
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


def _parse_posix_key_seq(seq: bytes) -> str:
    """Parses raw POSIX stdin bytes into key names."""
    if not seq:
        return ""

    nav_map: Final[dict[bytes, str]] = {
        b"\x1b[A": "up",
        b"\x1bOA": "up",
        b"\x1b[1;2A": "up",
        b"\x1b[1;3A": "up",
        b"\x1b[1;5A": "up",
        b"\x1b[B": "down",
        b"\x1bOB": "down",
        b"\x1b[1;2B": "down",
        b"\x1b[1;3B": "down",
        b"\x1b[1;5B": "down",
        b"\x1b[C": "right",
        b"\x1bOC": "right",
        b"\x1b[1;2C": "right",
        b"\x1b[1;3C": "right",
        b"\x1b[1;5C": "right",
        b"\x1b[D": "left",
        b"\x1bOD": "left",
        b"\x1b[1;2D": "left",
        b"\x1b[1;3D": "left",
        b"\x1b[1;5D": "left",
        b"\x1b[H": "home",
        b"\x1bOH": "home",
        b"\x1b[1~": "home",
        b"\x1b[7~": "home",
        b"\x1b[F": "end",
        b"\x1bOF": "end",
        b"\x1b[4~": "end",
        b"\x1b[8~": "end",
        b"\x1b[5~": "pageup",
        b"\x1b[5;2~": "pageup",
        b"\x1b[5;5~": "pageup",
        b"\x1b[6~": "pagedown",
        b"\x1b[6;2~": "pagedown",
        b"\x1b[6;5~": "pagedown",
    }
    if seq in nav_map:
        return nav_map[seq]

    if seq == b"\x1b":
        return "esc"
    if seq in (b"\r", b"\n"):
        return "enter"
    if seq == b" ":
        return "space"
    if seq in (b"\x7f", b"\x08"):
        return "backspace"
    if seq == b"\x03":
        return "ctrl+c"
    if seq == b"\x18":
        return "ctrl+x"
    if seq == b"\t":
        return "ctrl+i"

    try:
        decoded = seq.decode("utf-8")
        if len(decoded) == 1 and decoded.isalnum():
            return decoded.upper()
    except UnicodeDecodeError:
        pass

    return ""


def _get_key_windows() -> str:
    """Reads a keypress on Windows using msvcrt."""
    if sys.platform != "win32":
        return ""

    import msvcrt
    getch_fn = getattr(msvcrt, "getch", None)
    if getch_fn is None:
        return ""

    ch: bytes = getch_fn()
    if ch in (b"\xe0", b"\x00"):
        ch2: bytes = getch_fn()
        nav_map = {
            b"H": "up",
            b"P": "down",
            b"K": "left",
            b"M": "right",
            b"I": "pageup",
            b"Q": "pagedown",
            b"G": "home",
            b"O": "end",
        }
        return nav_map.get(ch2, "")

    if ch == b"\x1b":
        kbhit_fn = getattr(msvcrt, "kbhit", None)
        if kbhit_fn and kbhit_fn():
            ch2 = getch_fn()
            if ch2 in (b"[", b"O"):
                ch3 = getch_fn()
                vt_map = {
                    b"A": "up",
                    b"B": "down",
                    b"C": "right",
                    b"D": "left",
                    b"H": "home",
                    b"F": "end",
                }
                return vt_map.get(ch3, "esc")
        return "esc"

    key_map = {
        b"\r": "enter",
        b"\n": "enter",
        b" ": "space",
        b"\x08": "backspace",
        b"\x7f": "backspace",
        b"\x03": "ctrl+c",
        b"\x18": "ctrl+x",
        b"\t": "ctrl+i",
    }
    if ch in key_map:
        return key_map[ch]

    try:
        char = ch.decode("utf-8").upper()
        return char if char.isalnum() else ""
    except UnicodeDecodeError:
        return ""


def _get_key_posix() -> str:
    """Reads a keypress on POSIX/Linux using termios and raw os.read."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    if not os.isatty(fd):
        line = sys.stdin.readline()
        return line.strip().upper() if line else "esc"

    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        b = os.read(fd, 1)
        if b == b"\x1b":
            rlist, _, _ = select.select([fd], [], [], 0.05)
            if rlist:
                rest = os.read(fd, 31)
                seq = b + rest
            else:
                seq = b
        else:
            seq = b
        return _parse_posix_key_seq(seq)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_key() -> str:
    """Reads a keystroke press across platforms.

    Returns:
        str: Text name of key pressed (e.g. 'up', 'down', 'A', '1').
    """
    if sys.platform == "win32":
        return _get_key_windows()
    return _get_key_posix()


def prompt_input(prompt_text: str, clear_screen_first: bool = True) -> str:
    """Reads a text input string, optionally clearing the terminal and adding visual hints.

    Args:
        prompt_text (str): Prompt text description.
        clear_screen_first (bool): Whether to clear the screen on run.

    Returns:
        str: User input value string.
    """
    from lib.exceptions import CancelError
    if clear_screen_first:
        clear_screen()
        print_header()

        prompt_str_line: str = f"  [bold cyan][>][/] {prompt_text}: "
        console.print(f"\n{prompt_str_line}")
        console.print("\n  [dim]Press Enter to confirm, Ctrl+C to cancel.[/]")

        plain_prompt: str = f"  [>] {prompt_text}: "
        prompt_len: int = len(plain_prompt)

        sys.stdout.write(f"\033[3A\r\033[{prompt_len}C")
        sys.stdout.flush()

        try:
            return input()
        except (KeyboardInterrupt, EOFError) as e:
            logger.info(f"Prompt '{prompt_text}' cancelled by user.")
            raise CancelError() from e

    prompt_str_line_inline: str = f"\n  [bold cyan][>][/] {prompt_text}: "
    try:
        return console.input(prompt_str_line_inline)
    except (KeyboardInterrupt, EOFError) as e:
        logger.info(f"Prompt '{prompt_text}' cancelled by user.")
        raise CancelError() from e


def prompt_int(prompt_text: str, min_val: int | None = None, max_val: int | None = None, clear_screen: bool = True) -> int:
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
            val_str: str = prompt_input(prompt_text, clear_screen_first=clear_screen)
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
        val: str = prompt_input(prompt_text, clear_screen_first=clear_screen).strip()
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
        val: str = prompt_input(f"{prompt_text} (Y/n)", clear_screen_first=clear_screen).strip().lower()
        if val in ("", "y", "yes"):
            return True
        if val in ("n", "no"):
            return False


def launch_game() -> str:
    """Launches SAS:ZA4 using configured executable path or URI across platforms.

    Returns:
        str: Result feedback notice string.
    """
    game_path: str = getattr(config, "game_path", "steam://run/678800") or "steam://run/678800"
    logger.info(f"Launching game from path/URI: {game_path}")
    try:
        if sys.platform == "win32":
            if game_path.startswith("steam://") or os.path.exists(game_path):
                subprocess.Popen(["cmd", "/c", "start", "", game_path], shell=True)
                return "Game launched successfully!"
            return f"Game path '{game_path}' not found."

        if game_path.startswith("steam://"):
            launchers = [
                ["xdg-open", game_path],
                ["steam", game_path],
                ["steam", "-applaunch", "678800"],
                ["flatpak", "run", "com.valvesoftware.Steam", game_path],
            ]
            for cmd in launchers:
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.info(f"Launched game via {cmd[0]}")
                    return "Game launched successfully!"
                except (OSError, FileNotFoundError):
                    continue
            return "Failed to launch Steam (no compatible launcher found)."

        if os.path.exists(game_path):
            subprocess.Popen([game_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Game launched successfully!"

        return f"Game path '{game_path}' not found."
    except OSError as e:
        logger.error(f"Failed to launch game: {e}")
        return f"Failed to launch game: {e}"

