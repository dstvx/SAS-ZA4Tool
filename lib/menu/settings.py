import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.table import Table

from lib.config import config
from lib.exceptions import (
    CancelError,
    CryptError,
    ProfileNotFoundError,
    SaveError,
)
from lib.save.editor import Editor
from lib.ui.ui import (
    clear_screen,
    console,
    draw_menu,
    get_key,
    get_option_description,
    launch_game,
    print_header,
    prompt_confirm,
    prompt_str,
    resize_console,
    update_console_title,
)
from lib.utils.backup import create_backup, import_save_file, select_file_dialog
from lib.utils.logger import logger, setup_logger


def _copy_to_clipboard(text: str) -> bool:
    """Copies text to clipboard across platforms."""
    if sys.platform == "win32":
        try:
            subprocess.run("clip", input=text, text=True, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        try:
            subprocess.run(cmd, input=text, text=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            continue
    return False


def handle_item_browser() -> None:
    """Displays a premium interactive side-by-side searchable item database browser."""
    items_path: Path = Path(__file__).resolve().parent.parent / "data" / "items.json"
    try:
        with open(items_path, "r", encoding="utf-8") as f:
            items_data: dict[str, Any] = json.load(f)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to load items database: {e}")
        console.print("[bold red]Failed to load items database.[/]")
        input("Press Enter to go back...")
        return

    flat_items: list[dict[str, Any]] = []
    for cat in ("weapons", "armour"):
        for subcat, variants in items_data.get(cat, {}).items():
            for variant, items in variants.items():
                for item in items:
                    flat_items.append({
                        "name": item.get("Name", "Unknown"),
                        "id": item.get("ID", 0),
                        "type": cat.capitalize()[:-1],
                        "subcat": subcat.capitalize(),
                        "variant": variant.capitalize()
                    })

    search_query: str = ""
    current_page: int = 1
    items_per_page: int = 14
    selected_idx: int = 0
    message: str = ""

    while True:
        filtered: list[dict[str, Any]] = [
            i for i in flat_items
            if not search_query or search_query.lower() in i["name"].lower() or str(i["id"]) == search_query
        ]

        total_items = len(filtered)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        current_page = min(current_page, total_pages)
        current_page = max(current_page, 1)

        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_items = filtered[start_idx:end_idx]

        if page_items:
            if selected_idx >= len(page_items):
                selected_idx = len(page_items) - 1
            selected_idx = max(selected_idx, 0)
        else:
            selected_idx = 0

        update_console_title("Main Menu > Settings > Item Database Browser")
        resize_console(100, 29)

        clear_screen()
        print_header()

        console.print(f"\n  [bold white]Offline Item Database[/] | Search Query: [green]'{search_query or '(All)'}'[/] ({total_items} items found)")
        if message:
            console.print(f"  [bold yellow]Message: {message}[/]")
            message = ""
        else:
            console.print("")

        grid = Table.grid(expand=True)
        grid.add_column(ratio=6)
        grid.add_column(ratio=4)

        list_lines: list[str] = []
        for idx, item in enumerate(page_items):
            item_str = f"{item['name']:<20} (ID: {item['id']:<5}) [{item['type']} - {item['variant']}]"
            if idx == selected_idx:
                list_lines.append(f"  [reverse bold green] > {item_str} [/]")
            else:
                list_lines.append(f"    {item_str}")

        if not list_lines:
            list_lines.append("\n  [dim]No matching items found.[/]")
            list_lines.append("  [dim]Press 'S' to change search query.[/]")

        while len(list_lines) < items_per_page:
            list_lines.append("")

        list_panel = Panel(
            "\n".join(list_lines),
            title="[bold green]Matching Items[/]",
            border_style="green",
            expand=True
        )

        details_lines: list[str] = []
        if page_items and 0 <= selected_idx < len(page_items):
            active_item = page_items[selected_idx]
            details_lines = [
                "",
                f"  [bold white]Name:[/]        [green]{active_item['name']}[/]",
                f"  [bold white]Item ID:[/]     [yellow]{active_item['id']}[/]",
                f"  [bold white]Category:[/]    [cyan]{active_item['type']}[/]",
                f"  [bold white]Subcategory:[/] [cyan]{active_item['subcat']}[/]",
                f"  [bold white]Variant:[/]     [cyan]{active_item['variant']}[/]",
                "",
                "  [dim]Press [bold yellow]C[/] or [bold yellow]Enter[/] to copy ID[/]",
                "  [dim]Press [bold yellow]S[/] to change query[/]",
            ]
        else:
            details_lines = [
                "",
                "  [dim]No item selected.[/]",
                "",
                "  [dim]Press [bold yellow]S[/] to search.[/]"
            ]

        while len(details_lines) < items_per_page:
            details_lines.append("")

        details_panel = Panel(
            "\n".join(details_lines),
            title="[bold cyan]Selected Item Card[/]",
            border_style="cyan",
            expand=True
        )

        grid.add_row(list_panel, details_panel)
        console.print(grid)

        console.print(f"\n  [bold cyan]Page {current_page}/{total_pages}[/]  [dim]|  [Arrows] Navigate/Pages  |  [PgUp/PgDn] Page Jump  |  [S] Search  |  [C/Enter] Copy ID  |  [Esc/Backspace] Back[/]")

        key: str = get_key()
        if not key:
            continue

        if key == "up":
            if page_items:
                selected_idx = (selected_idx - 1) % len(page_items)
        elif key == "down":
            if page_items:
                selected_idx = (selected_idx + 1) % len(page_items)
        elif key == "left":
            if current_page > 1:
                current_page -= 1
                selected_idx = 0
        elif key == "right":
            if current_page < total_pages:
                current_page += 1
                selected_idx = 0
        elif key == "pageup":
            if current_page > 1:
                current_page = max(1, current_page - 5)
                selected_idx = 0
        elif key == "pagedown":
            if current_page < total_pages:
                current_page = min(total_pages, current_page + 5)
                selected_idx = 0
        elif key in ("backspace", "esc"):
            break
        elif key == "S":
            try:
                search_query = prompt_str("Enter item name or ID to search", clear_screen=False).strip()
                current_page = 1
                selected_idx = 0
            except CancelError:
                pass
        elif key in ("C", "enter", "space") and page_items and 0 <= selected_idx < len(page_items):
            active_item = page_items[selected_idx]
            if _copy_to_clipboard(str(active_item["id"])):
                message = f"Copied ID {active_item['id']} ({active_item['name']}) to clipboard!"
            else:
                message = f"Selected ID: {active_item['id']} ({active_item['name']})"


def handle_settings_menu(editor: Editor) -> str | None:
    """Displays and processes choices within the Settings & Tools submenu.

    Args:
        editor (Editor): The save file editor instance.

    Returns:
        Optional[str]: Error message if an operation fails, otherwise None.
    """
    selected_idx: int = 0
    message: str = ""

    while True:
        options: list[str] = [
            f"Select Profile (Active: {config.current_profile or 'None'})",
            "Reload Active Profiles from Save",
            "Import Save File (.save or .json)",
            "Create Backup & Decrypted Export",
            "Search Offline Item Database",
            f"Toggle Logging (Enabled: {config.logs_enabled})",
            f"Change Game Path/URI (Current: {config.game_path})",
            f"Toggle Update Checker (Enabled: {config.check_updates})",
            "Reset Configuration Setup Wizard",
            "Back"
        ]

        draw_menu("Settings & Tools Menu", options, selected_idx, message, breadcrumb="Main Menu > Settings & Tools")
        message = ""

        key: str = get_key()
        if not key:
            continue

        if key == "up":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "down":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("backspace", "esc", "left"):
            return None
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

            try:
                if idx == 0:
                    loaded: list[str] = editor.get_loaded_profiles()
                    if not loaded:
                        message = "No loaded profiles found in save file."
                        continue

                    profile_options: list[str] = loaded + ["Cancel"]
                    prof_idx: int = 0
                    while True:
                        draw_menu("Select Active Profile", profile_options, prof_idx, breadcrumb="Main Menu > Settings > Profile Selection")
                        pk: str = get_key()
                        if pk == "up":
                            prof_idx = (prof_idx - 1) % len(profile_options)
                        elif pk == "down":
                            prof_idx = (prof_idx + 1) % len(profile_options)
                        elif pk in ("backspace", "esc", "left"):
                            break
                        elif pk in ("enter", "space", "right") or pk.isdigit():
                            p_idx: int = prof_idx
                            if pk.isdigit():
                                d_idx = int(pk) - 1
                                if 0 <= d_idx < len(profile_options):
                                    p_idx = d_idx
                            if p_idx == len(loaded):
                                break
                            config.current_profile = loaded[p_idx]
                            message = f"Switched active profile to {loaded[p_idx]}."
                            break
                elif idx == 1:
                    try:
                        synced_list: list[str] = editor.sync()
                        message = f"Synchronized active profiles: {synced_list}"
                    except (SaveError, ProfileNotFoundError, OSError, KeyError, ValueError) as e:
                        logger.error(f"Failed sync profiles: {e}")
                        message = f"Sync failed: {e}"
                elif idx == 2:
                    try:
                        filepath: str = select_file_dialog()
                        if filepath:
                            if prompt_confirm("Replace current save file? (This will auto-create a backup of the old one)"):
                                message = import_save_file(filepath, editor)
                                editor.reload()
                                editor.sync()
                            else:
                                message = "Import cancelled."
                        else:
                            message = "No file selected."
                    except (SaveError, CryptError, OSError, ValueError, json.JSONDecodeError) as e:
                        logger.error(f"Import process failed: {e}")
                        message = f"Import failed: {e}"
                elif idx == 3:
                    message = create_backup(editor)
                elif idx == 4:
                    handle_item_browser()
                elif idx == 5:
                    config.logs_enabled = not config.logs_enabled
                    setup_logger()
                    message = f"Logging set to {config.logs_enabled}."
                elif idx == 6:
                    new_path: str = prompt_str("Enter SAS:ZA4 executable path or steam URI")
                    config.game_path = new_path
                    message = "Game path updated successfully."
                elif idx == 7:
                    config.check_updates = not config.check_updates
                    message = f"Automatic update checker set to {config.check_updates}."
                elif idx == 8:
                    if prompt_confirm("Are you sure you want to reset the configuration and run setup again?"):
                        config.setup_done = False
                        from lib.utils.setup import run_setup
                        run_setup()
                        editor.reload()
                        editor.sync()
                        message = "Configuration setup rerun successfully."
                elif idx == 9:
                    return None
            except CancelError:
                message = "Action cancelled."

