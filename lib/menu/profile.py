import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from lib.config import config
from lib.exceptions import (
    CancelError,
    ProfileNotFoundError,
    SAS_ZA4ToolError,
    SaveError,
)
from lib.save.editor import Editor
from lib.ui.ui import (
    draw_menu as _draw_menu,
)
from lib.ui.ui import (
    get_key,
    get_option_description,
    launch_game,
    prompt_confirm,
    prompt_int,
    prompt_str,
)
from lib.utils.logger import logger


def draw_menu(
    title: str,
    options: list[str],
    selected_idx: int,
    message: str = "",
    breadcrumb: str = "",
) -> None:
    """Draws a menu screen wrapper customized for profile editor submenus.

    Args:
        title (str): Submenu title.
        options (List[str]): List of choices.
        selected_idx (int): Current highlighted selection.
        message (str): Optional result feedback message to display.
        breadcrumb (str): Page history directory hierarchy.
    """
    if not breadcrumb:
        profile_key: str = config.current_profile or "Profile"
        breadcrumb = f"Main Menu > Profile Editor ({profile_key}) > {title}"
    _draw_menu(title, options, selected_idx, message, breadcrumb)


def build_weapon_name_map(items_data: dict[str, Any]) -> Mapping[int, str]:
    """Generates a fast lookup dictionary mapping weapon IDs to human-readable names.

    Args:
        items_data (Dict[str, Any]): Parsed items JSON catalog.

    Returns:
        Mapping[int, str]: Dictionary mapping weapon ID integer to descriptive name.
    """
    name_map: dict[int, str] = {}
    for variants in items_data.get("weapons", {}).values():
        for variant, items in variants.items():
            for item in items:
                name_map[item["ID"]] = f"{item['Name']} ({variant.capitalize()})"
    return name_map


def build_armour_name_map(items_data: dict[str, Any]) -> Mapping[int, str]:
    """Generates a fast lookup dictionary mapping armour/equipment IDs to human-readable names.

    Args:
        items_data (Dict[str, Any]): Parsed items JSON catalog.

    Returns:
        Mapping[int, str]: Dictionary mapping armour ID integer to descriptive name.
    """
    name_map: dict[int, str] = {}
    for variants in items_data.get("armour", {}).values():
        for variant, items in variants.items():
            for item in items:
                name_map[item["ID"]] = f"{item['Name']} ({variant.capitalize()})"
    return name_map


def format_display_name(raw_name: str) -> str:
    """Formats raw internal database category names into readable display labels.

    Args:
        raw_name (str): Raw string identifier.

    Returns:
        str: Formatted clean display name string.
    """
    mapping: Final[dict[str, str]] = {
        "smg": "SMG",
        "lmgs": "LMGs",
        "assault_rifles": "Assault Rifles",
        "sniper_rifles": "Sniper Rifles",
        "rocket_launchers": "Rocket Launchers",
        "flame_throwers": "Flame Throwers",
        "disk_throwers": "Disk Throwers",
    }
    return mapping.get(raw_name.lower(), raw_name.capitalize().replace("_", " "))


def handle_profile_menu(editor: Editor) -> str | None:
    """Manages selections, navigation loops and edits in the Profile Editor.

    Args:
        editor (Editor): The save file editor instance.

    Returns:
        Optional[str]: Error message if validation or read fails, otherwise None.
    """
    selected_idx: int = 0
    message: str = ""

    items_path: Path = Path(__file__).resolve().parent.parent / "data" / "items.json"
    try:
        with open(items_path, "r", encoding="utf-8") as f:
            items_data: dict[str, Any] = json.load(f)
        weapon_names: Mapping[int, str] = build_weapon_name_map(items_data)
        armour_names: Mapping[int, str] = build_armour_name_map(items_data)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to load items database: {e}")
        items_data = {}
        weapon_names = {}
        armour_names = {}

    while True:
        profile_key: str = config.current_profile
        if not profile_key:
            return "No active profile selected. Please select one in Settings."

        try:
            p = editor.profile(profile_key)
            name: str = p.name
            money: int = p.money
            keys: int = p.black_keys
            cores: int = p.augment_cores
            reset: bool = p.skill_reset
            frag: int = p.ammo_frag
            cryo: int = p.ammo_cryo
            level: int = p.level
            xp: int = p.xp
            black_box_count: int = len(
                p.get(["Skills", "AvailableBlackStrongboxes"], [])
            )
        except (ProfileNotFoundError, SaveError, KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to load profile data: {e}")
            return f"Failed to load profile data: {e}"

        options: list[str] = [
            "Add Item",
            "Remove Item",
            "Edit Item Stats",
            "Transport Item to Profile",
            "Manage Strongbox Claim Queue",
            f"Change Username (Current: {name})",
            f"Set Cash/Money (Current: {money})",
            f"Set Black Keys Count (Current: {keys})",
            f"Set Augment Cores Count (Current: {cores})",
            f"Toggle Skill Reset (Current: {reset})",
            f"Set Frag Grenades (Current: {frag})",
            f"Set Cryo Grenades (Current: {cryo})",
            f"Set Player Level (Current: {level}, XP: {xp})",
            "Max Out Masteries",
            "Clear / Reset Masteries",
            "Set Multiplayer Stats",
            "Manage Sentry Turrets",
            f"Manage Available Black Boxes (Current count: {black_box_count})",
            "Clear All Strongbox and Black Box Claim Queues",
            "Back",
        ]

        draw_menu(
            f"Profile Editor - {profile_key}",
            options,
            selected_idx,
            message,
            breadcrumb=f"Main Menu > Profile Editor ({profile_key})",
        )
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
        elif (
            key in ("enter", "space", "right")
            or key.isdigit()
            or (len(key) == 1 and key.isalpha())
        ):
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
                    cats: list[str] = ["Weapon", "Equipment", "Cancel"]
                    cat_idx: int = 0
                    while True:
                        draw_menu("Select Category to Inject", cats, cat_idx)
                        ck: str = get_key()
                        if ck == "up":
                            cat_idx = (cat_idx - 1) % len(cats)
                        elif ck == "down":
                            cat_idx = (cat_idx + 1) % len(cats)
                        elif ck in ("backspace", "esc", "left"):
                            break
                        elif ck in ("enter", "space", "right") or ck.isdigit():
                            c_sel: int = cat_idx
                            if ck.isdigit():
                                d_idx = int(ck) - 1
                                if 0 <= d_idx < len(cats):
                                    c_sel = d_idx
                            if c_sel == 2:
                                break

                            is_weapon: bool = c_sel == 0
                            db_key: str = "weapons" if is_weapon else "armour"
                            raw_subcats: list[str] = list(
                                items_data.get(db_key, {}).keys()
                            )
                            subcats: list[str] = [
                                format_display_name(s) for s in raw_subcats
                            ] + ["Cancel"]

                            sub_idx: int = 0
                            while True:
                                draw_menu("Select Subcategory", subcats, sub_idx)
                                sk: str = get_key()
                                if sk == "up":
                                    sub_idx = (sub_idx - 1) % len(subcats)
                                elif sk == "down":
                                    sub_idx = (sub_idx + 1) % len(subcats)
                                elif sk in ("backspace", "esc", "left"):
                                    break
                                elif sk in ("enter", "space", "right") or sk.isdigit():
                                    s_sel: int = sub_idx
                                    if sk.isdigit():
                                        d_idx = int(sk) - 1
                                        if 0 <= d_idx < len(subcats):
                                            s_sel = d_idx
                                    if s_sel == len(subcats) - 1:
                                        break

                                    subcat_name: str = raw_subcats[s_sel]
                                    variants: list[str] = [
                                        format_display_name(v)
                                        for v in items_data.get(db_key, {}).get(
                                            subcat_name, {}
                                        )
                                    ] + ["Cancel"]
                                    raw_variants: list[str] = list(
                                        items_data.get(db_key, {})
                                        .get(subcat_name, {})
                                        .keys()
                                    )

                                    var_idx: int = 0
                                    while True:
                                        draw_menu("Select Variant", variants, var_idx)
                                        vk: str = get_key()
                                        if vk == "up":
                                            var_idx = (var_idx - 1) % len(variants)
                                        elif vk == "down":
                                            var_idx = (var_idx + 1) % len(variants)
                                        elif vk in ("backspace", "esc", "left"):
                                            break
                                        elif (
                                            vk in ("enter", "space", "right")
                                            or vk.isdigit()
                                        ):
                                            v_sel: int = var_idx
                                            if vk.isdigit():
                                                d_idx = int(vk) - 1
                                                if 0 <= d_idx < len(variants):
                                                    v_sel = d_idx
                                            if v_sel == len(variants) - 1:
                                                break

                                            variant_name: str = raw_variants[v_sel]
                                            items_list: list[dict[str, Any]] = (
                                                items_data.get(db_key, {})
                                                .get(subcat_name, {})
                                                .get(variant_name, [])
                                            )

                                            if not items_list:
                                                message = "No items found for this subcategory and variant."
                                                break

                                            item_options: list[str] = [
                                                i.get("Name", "Unknown")
                                                for i in items_list
                                            ] + ["Cancel"]
                                            it_idx: int = 0
                                            while True:
                                                draw_menu(
                                                    "Select Item to Inject",
                                                    item_options,
                                                    it_idx,
                                                )
                                                itk: str = get_key()
                                                if itk == "up":
                                                    it_idx = (it_idx - 1) % len(
                                                        item_options
                                                    )
                                                elif itk == "down":
                                                    it_idx = (it_idx + 1) % len(
                                                        item_options
                                                    )
                                                elif itk in (
                                                    "backspace",
                                                    "esc",
                                                    "left",
                                                ):
                                                    break
                                                elif (
                                                    itk in ("enter", "space", "right")
                                                    or itk.isdigit()
                                                    or (len(itk) == 1 and itk.isalpha())
                                                ):
                                                    it_sel: int = it_idx
                                                    if itk.isdigit():
                                                        d_idx = int(itk) - 1
                                                        if (
                                                            0
                                                            <= d_idx
                                                            < len(item_options)
                                                        ):
                                                            it_sel = d_idx
                                                    elif (
                                                        len(itk) == 1 and itk.isalpha()
                                                    ):
                                                        a_idx: int = (
                                                            ord(itk.upper()) - 65 + 9
                                                        )
                                                        if (
                                                            0
                                                            <= a_idx
                                                            < len(item_options)
                                                        ):
                                                            it_sel = a_idx

                                                    if it_sel == len(items_list):
                                                        break

                                                    target_item: dict[str, Any] = (
                                                        items_list[it_sel]
                                                    )
                                                    item_id: int = target_item["ID"]

                                                    v_map: Final[dict[str, int]] = {
                                                        "normal": 0,
                                                        "red": 1,
                                                        "black": 2,
                                                        "factions": 3,
                                                        "premium": 0,
                                                    }
                                                    ver_val: int = v_map.get(
                                                        variant_name, 0
                                                    )

                                                    grade: int = prompt_int(
                                                        "Enter item grade (0-12)", 0, 12
                                                    )
                                                    max_augs: int = (
                                                        4 if is_weapon else 3
                                                    )
                                                    augs: int = prompt_int(
                                                        f"Enter augment slots count (0-{max_augs})",
                                                        0,
                                                        max_augs,
                                                    )
                                                    bonus: int = prompt_int(
                                                        "Enter bonus stats level (0-10)",
                                                        0,
                                                        10,
                                                    )

                                                    p.inject_item(
                                                        is_weapon,
                                                        item_id,
                                                        ver_val,
                                                        grade,
                                                        -1,
                                                        augs,
                                                        bonus,
                                                    )
                                                    message = f"Injected {target_item.get('Name')} into Claimed Strongbox queue."
                                                    break
                elif idx == 1:
                    cats = ["Weapons", "Equipment", "Cancel"]
                    cat_idx = 0
                    while True:
                        draw_menu("Select Item Category to Remove", cats, cat_idx)
                        ck = get_key()
                        if ck == "up":
                            cat_idx = (cat_idx - 1) % len(cats)
                        elif ck == "down":
                            cat_idx = (cat_idx + 1) % len(cats)
                        elif ck in ("backspace", "esc", "left"):
                            break
                        elif ck in ("enter", "space", "right") or ck.isdigit():
                            c_sel = cat_idx
                            if ck.isdigit():
                                d_idx = int(ck) - 1
                                if 0 <= d_idx < len(cats):
                                    c_sel = d_idx
                            if c_sel == 2:
                                break

                            category_key: str = cats[c_sel]
                            it_idx = 0
                            while True:
                                p_items: list[dict[str, Any]] = p.get(category_key, [])
                                if not p_items:
                                    message = f"No items found in {category_key} list."
                                    break

                                item_options = []
                                for item in p_items:
                                    item_id = item.get("ID")
                                    is_weapon = category_key == "Weapons"
                                    names_dict = (
                                        weapon_names if is_weapon else armour_names
                                    )
                                    name_label: str = names_dict.get(
                                        item_id, f"Unknown Item (ID {item_id})"
                                    )
                                    details: str = f"[Grade {item.get('Grade')}, Augs {item.get('AugmentSlots')}, Bonus {item.get('BonusStatsLevel')}]"
                                    item_options.append(f"{name_label} {details}")

                                item_options.append("Cancel")
                                draw_menu("Select Item to Remove", item_options, it_idx)
                                itk = get_key()
                                if itk == "up":
                                    it_idx = (it_idx - 1) % len(item_options)
                                elif itk == "down":
                                    it_idx = (it_idx + 1) % len(item_options)
                                elif itk in ("backspace", "esc", "left"):
                                    break
                                elif (
                                    itk in ("enter", "space", "right")
                                    or itk.isdigit()
                                    or (len(itk) == 1 and itk.isalpha())
                                ):
                                    it_sel = it_idx
                                    if itk.isdigit():
                                        d_idx = int(itk) - 1
                                        if 0 <= d_idx < len(item_options):
                                            it_sel = d_idx
                                    elif len(itk) == 1 and itk.isalpha():
                                        a_idx = ord(itk.upper()) - 65 + 9
                                        if 0 <= a_idx < len(item_options):
                                            it_sel = a_idx

                                    if it_sel == len(p_items):
                                        break

                                    if prompt_confirm(
                                        f"Are you sure you want to remove item {it_sel}?"
                                    ):
                                        p.remove_item(category_key, it_sel)
                                        message = "Item removed successfully."
                                    break
                elif idx == 2:
                    sources: list[str] = [
                        "Active Inventory",
                        "Strongbox Claim Queue",
                        "Cancel",
                    ]
                    src_idx: int = 0
                    while True:
                        draw_menu("Select Item Source to Edit", sources, src_idx)
                        sk = get_key()
                        if sk == "up":
                            src_idx = (src_idx - 1) % len(sources)
                        elif sk == "down":
                            src_idx = (src_idx + 1) % len(sources)
                        elif sk in ("backspace", "esc", "left"):
                            break
                        elif sk in ("enter", "space", "right") or sk.isdigit():
                            s_sel: int = src_idx
                            if sk.isdigit():
                                d_idx = int(sk) - 1
                                if 0 <= d_idx < len(sources):
                                    s_sel = d_idx
                            if s_sel == 2:
                                break

                            if s_sel == 0:
                                cats = ["Weapons", "Equipment", "Cancel"]
                                cat_idx = 0
                                while True:
                                    draw_menu(
                                        "Select Item Category to Edit", cats, cat_idx
                                    )
                                    ck = get_key()
                                    if ck == "up":
                                        cat_idx = (cat_idx - 1) % len(cats)
                                    elif ck == "down":
                                        cat_idx = (cat_idx + 1) % len(cats)
                                    elif ck in ("backspace", "esc", "left"):
                                        break
                                    elif (
                                        ck in ("enter", "space", "right")
                                        or ck.isdigit()
                                    ):
                                        c_sel = cat_idx
                                        if ck.isdigit():
                                            d_idx = int(ck) - 1
                                            if 0 <= d_idx < len(cats):
                                                c_sel = d_idx
                                        if c_sel == 2:
                                            break

                                        category_key = cats[c_sel]
                                        it_idx = 0
                                        while True:
                                            p_items = p.get(category_key, [])
                                            if not p_items:
                                                message = f"No items found in {category_key} list."
                                                break

                                            item_options = []
                                            for item in p_items:
                                                item_id = item.get("ID")
                                                is_weapon = category_key == "Weapons"
                                                names_dict = (
                                                    weapon_names
                                                    if is_weapon
                                                    else armour_names
                                                )
                                                name_label = names_dict.get(
                                                    item_id,
                                                    f"Unknown Item (ID {item_id})",
                                                )
                                                details = f"[Grade {item.get('Grade')}, Augs {item.get('AugmentSlots')}, Bonus {item.get('BonusStatsLevel')}]"
                                                item_options.append(
                                                    f"{name_label} {details}"
                                                )

                                            item_options.append("Cancel")
                                            draw_menu(
                                                "Select Item to Edit Stats",
                                                item_options,
                                                it_idx,
                                            )
                                            itk = get_key()
                                            if itk == "up":
                                                it_idx = (it_idx - 1) % len(
                                                    item_options
                                                )
                                            elif itk == "down":
                                                it_idx = (it_idx + 1) % len(
                                                    item_options
                                                )
                                            elif itk in ("backspace", "esc", "left"):
                                                break
                                            elif (
                                                itk in ("enter", "space", "right")
                                                or itk.isdigit()
                                                or (len(itk) == 1 and itk.isalpha())
                                            ):
                                                it_sel = it_idx
                                                if itk.isdigit():
                                                    d_idx = int(itk) - 1
                                                    if 0 <= d_idx < len(item_options):
                                                        it_sel = d_idx
                                                elif len(itk) == 1 and itk.isalpha():
                                                    a_idx = ord(itk.upper()) - 65 + 9
                                                    if 0 <= a_idx < len(item_options):
                                                        it_sel = a_idx

                                                if it_sel == len(p_items):
                                                    break

                                                grade = prompt_int(
                                                    "Enter new item grade (0-12)", 0, 12
                                                )
                                                max_augs = (
                                                    4
                                                    if category_key == "Weapons"
                                                    else 3
                                                )
                                                augs = prompt_int(
                                                    f"Enter new augment slots count (0-{max_augs})",
                                                    0,
                                                    max_augs,
                                                )
                                                bonus = prompt_int(
                                                    "Enter new bonus stats level (0-10)",
                                                    0,
                                                    10,
                                                )

                                                p.update_item_stats(
                                                    category_key,
                                                    it_sel,
                                                    grade,
                                                    augs,
                                                    bonus,
                                                )
                                                message = (
                                                    "Item stats updated successfully."
                                                )
                                                break
                                        break
                            elif s_sel == 1:
                                it_idx = 0
                                while True:
                                    claimed_items: list[dict[str, Any]] = (
                                        p.get_claimed_strongboxes()
                                    )
                                    if not claimed_items:
                                        message = (
                                            "No items found in Strongbox Claim Queue."
                                        )
                                        break
                                    item_options = []
                                    for item in claimed_items:
                                        item_id = item["data"].get("ID")
                                        names_dict = (
                                            weapon_names
                                            if item["is_weapon"]
                                            else armour_names
                                        )
                                        name_label = names_dict.get(
                                            item_id, f"Unknown Item (ID {item_id})"
                                        )
                                        variant_type = (
                                            "Weapon"
                                            if item["is_weapon"]
                                            else "Equipment"
                                        )
                                        details = f"[Grade {item['data'].get('Grade')}, Augs {item['data'].get('AugmentSlots')}, Bonus {item['data'].get('BonusStatsLevel')}]"
                                        item_options.append(
                                            f"[{variant_type}] {name_label} {details}"
                                        )

                                    item_options.append("Cancel")
                                    draw_menu(
                                        "Select Queue Item to Edit Stats",
                                        item_options,
                                        it_idx,
                                    )
                                    itk = get_key()
                                    if itk == "up":
                                        it_idx = (it_idx - 1) % len(item_options)
                                    elif itk == "down":
                                        it_idx = (it_idx + 1) % len(item_options)
                                    elif itk in ("backspace", "esc", "left"):
                                        break
                                    elif (
                                        itk in ("enter", "space", "right")
                                        or itk.isdigit()
                                    ):
                                        it_sel = it_idx
                                        if itk.isdigit():
                                            d_idx = int(itk) - 1
                                            if 0 <= d_idx < len(item_options):
                                                it_sel = d_idx
                                        if it_sel == len(claimed_items):
                                            break

                                        target_q_item: dict[str, Any] = claimed_items[
                                            it_sel
                                        ]
                                        grade = prompt_int(
                                            "Enter new item grade (0-12)", 0, 12
                                        )
                                        max_augs = (
                                            4 if target_q_item["is_weapon"] else 3
                                        )
                                        augs = prompt_int(
                                            f"Enter new augment slots count (0-{max_augs})",
                                            0,
                                            max_augs,
                                        )
                                        bonus = prompt_int(
                                            "Enter new bonus stats level (0-10)", 0, 10
                                        )

                                        p.update_claimed_strongbox_stats(
                                            it_sel, grade, augs, bonus
                                        )
                                        message = (
                                            "Queue item stats updated successfully."
                                        )
                                        break
                elif idx == 3:
                    sources = ["Active Inventory", "Strongbox Claim Queue", "Cancel"]
                    src_idx = 0
                    while True:
                        draw_menu("Select Item Source to Transport", sources, src_idx)
                        sk = get_key()
                        if sk == "up":
                            src_idx = (src_idx - 1) % len(sources)
                        elif sk == "down":
                            src_idx = (src_idx + 1) % len(sources)
                        elif sk in ("backspace", "esc", "left"):
                            break
                        elif sk in ("enter", "space", "right") or sk.isdigit():
                            s_sel = src_idx
                            if sk.isdigit():
                                d_idx = int(sk) - 1
                                if 0 <= d_idx < len(sources):
                                    s_sel = d_idx
                            if s_sel == 2:
                                break

                            if s_sel == 0:
                                cats = ["Weapons", "Equipment", "Cancel"]
                                cat_idx = 0
                                while True:
                                    draw_menu(
                                        "Select Item Category to Transport",
                                        cats,
                                        cat_idx,
                                    )
                                    ck = get_key()
                                    if ck == "up":
                                        cat_idx = (cat_idx - 1) % len(cats)
                                    elif ck == "down":
                                        cat_idx = (cat_idx + 1) % len(cats)
                                    elif ck in ("backspace", "esc", "left"):
                                        break
                                    elif (
                                        ck in ("enter", "space", "right")
                                        or ck.isdigit()
                                    ):
                                        c_sel = cat_idx
                                        if ck.isdigit():
                                            d_idx = int(ck) - 1
                                            if 0 <= d_idx < len(cats):
                                                c_sel = d_idx
                                        if c_sel == 2:
                                            break

                                        category_key = cats[c_sel]
                                        it_idx = 0
                                        while True:
                                            p_items = p.get(category_key, [])
                                            if not p_items:
                                                message = f"No items found in {category_key} list."
                                                break

                                            item_options = []
                                            for item in p_items:
                                                item_id = item.get("ID")
                                                name_label = (
                                                    weapon_names
                                                    if category_key == "Weapons"
                                                    else armour_names
                                                ).get(
                                                    item_id,
                                                    f"Unknown Item (ID {item_id})",
                                                )
                                                details = f"[Grade {item.get('Grade')}, Augs {item.get('AugmentSlots')}, Bonus {item.get('BonusStatsLevel')}]"
                                                item_options.append(
                                                    f"{name_label} {details}"
                                                )

                                            item_options.append("Cancel")
                                            draw_menu(
                                                "Select Item to Transport",
                                                item_options,
                                                it_idx,
                                            )
                                            itk = get_key()
                                            if itk == "up":
                                                it_idx = (it_idx - 1) % len(
                                                    item_options
                                                )
                                            elif itk == "down":
                                                it_idx = (it_idx + 1) % len(
                                                    item_options
                                                )
                                            elif itk in ("backspace", "esc", "left"):
                                                break
                                            elif (
                                                itk in ("enter", "space", "right")
                                                or itk.isdigit()
                                                or (len(itk) == 1 and itk.isalpha())
                                            ):
                                                it_sel = it_idx
                                                if itk.isdigit():
                                                    d_idx = int(itk) - 1
                                                    if 0 <= d_idx < len(item_options):
                                                        it_sel = d_idx
                                                elif len(itk) == 1 and itk.isalpha():
                                                    a_idx = ord(itk.upper()) - 65 + 9
                                                    if 0 <= a_idx < len(item_options):
                                                        it_sel = a_idx

                                                if it_sel == len(p_items):
                                                    break

                                                loaded_profiles = (
                                                    editor.get_loaded_profiles()
                                                )
                                                other_profiles = [
                                                    prof
                                                    for prof in loaded_profiles
                                                    if prof != profile_key
                                                ]
                                                if not other_profiles:
                                                    message = "No other active profiles available to transport to."
                                                    break

                                                prof_options = other_profiles + [
                                                    "Cancel"
                                                ]
                                                prof_idx = 0
                                                target_prof = ""
                                                while True:
                                                    draw_menu(
                                                        "Select Destination Profile",
                                                        prof_options,
                                                        prof_idx,
                                                    )
                                                    pk = get_key()
                                                    if pk == "up":
                                                        prof_idx = (prof_idx - 1) % len(
                                                            prof_options
                                                        )
                                                    elif pk == "down":
                                                        prof_idx = (prof_idx + 1) % len(
                                                            prof_options
                                                        )
                                                    elif pk in (
                                                        "backspace",
                                                        "esc",
                                                        "left",
                                                    ):
                                                        break
                                                    elif (
                                                        pk
                                                        in ("enter", "space", "right")
                                                        or pk.isdigit()
                                                    ):
                                                        p_idx = prof_idx
                                                        if pk.isdigit():
                                                            d_idx = int(pk) - 1
                                                            if (
                                                                0
                                                                <= d_idx
                                                                < len(prof_options)
                                                            ):
                                                                p_idx = d_idx
                                                        if p_idx == len(other_profiles):
                                                            break
                                                        target_prof = other_profiles[
                                                            p_idx
                                                        ]
                                                        break

                                                if target_prof:
                                                    p.transport_item(
                                                        category_key,
                                                        it_sel,
                                                        target_prof,
                                                    )
                                                    message = f"Transported item to {target_prof} successfully."
                                                break
                                        break
                            elif s_sel == 1:
                                it_idx = 0
                                while True:
                                    claimed_items = p.get_claimed_strongboxes()
                                    if not claimed_items:
                                        message = (
                                            "No items found in Strongbox Claim Queue."
                                        )
                                        break
                                    item_options = []
                                    for item in claimed_items:
                                        item_id = item["data"].get("ID")
                                        names_dict = (
                                            weapon_names
                                            if item["is_weapon"]
                                            else armour_names
                                        )
                                        name_label = names_dict.get(
                                            item_id, f"Unknown Item (ID {item_id})"
                                        )
                                        variant_type = (
                                            "Weapon"
                                            if item["is_weapon"]
                                            else "Equipment"
                                        )
                                        details = f"[Grade {item['data'].get('Grade')}, Augs {item['data'].get('AugmentSlots')}, Bonus {item['data'].get('BonusStatsLevel')}]"
                                        item_options.append(
                                            f"[{variant_type}] {name_label} {details}"
                                        )

                                    item_options.append("Cancel")
                                    draw_menu(
                                        "Select Queue Item to Transport",
                                        item_options,
                                        it_idx,
                                    )
                                    itk = get_key()
                                    if itk == "up":
                                        it_idx = (it_idx - 1) % len(item_options)
                                    elif itk == "down":
                                        it_idx = (it_idx + 1) % len(item_options)
                                    elif itk in ("backspace", "esc", "left"):
                                        break
                                    elif (
                                        itk in ("enter", "space", "right")
                                        or itk.isdigit()
                                    ):
                                        it_sel = it_idx
                                        if itk.isdigit():
                                            d_idx = int(itk) - 1
                                            if 0 <= d_idx < len(item_options):
                                                it_sel = d_idx
                                        if it_sel == len(claimed_items):
                                            break

                                        loaded_profiles = editor.get_loaded_profiles()
                                        other_profiles = [
                                            prof
                                            for prof in loaded_profiles
                                            if prof != profile_key
                                        ]
                                        if not other_profiles:
                                            message = "No other active profiles available to transport to."
                                            break

                                        prof_options = other_profiles + ["Cancel"]
                                        prof_idx = 0
                                        target_prof = ""
                                        while True:
                                            draw_menu(
                                                "Select Destination Profile",
                                                prof_options,
                                                prof_idx,
                                            )
                                            pk = get_key()
                                            if pk == "up":
                                                prof_idx = (prof_idx - 1) % len(
                                                    prof_options
                                                )
                                            elif pk == "down":
                                                prof_idx = (prof_idx + 1) % len(
                                                    prof_options
                                                )
                                            elif pk in ("backspace", "esc", "left"):
                                                break
                                            elif (
                                                pk in ("enter", "space", "right")
                                                or pk.isdigit()
                                            ):
                                                p_idx = prof_idx
                                                if pk.isdigit():
                                                    d_idx = int(pk) - 1
                                                    if 0 <= d_idx < len(prof_options):
                                                        p_idx = d_idx
                                                if p_idx == len(other_profiles):
                                                    break
                                                target_prof = other_profiles[p_idx]
                                                break

                                        if target_prof:
                                            p.transport_claimed_strongbox(
                                                it_sel, target_prof
                                            )
                                            message = f"Transported queue item to {target_prof} successfully."
                                            break
                elif idx == 4:
                    it_idx = 0
                    while True:
                        claimed_items = p.get_claimed_strongboxes()
                        item_options = []
                        for i, item in enumerate(claimed_items):
                            item_id = item["data"].get("ID")
                            name_label = (
                                weapon_names if item["is_weapon"] else armour_names
                            ).get(item_id, f"Unknown Item (ID {item_id})")
                            variant_type = (
                                "Weapon" if item["is_weapon"] else "Equipment"
                            )
                            item_options.append(f"[{variant_type}] {name_label}")

                        item_options.append("Clear Entire Queue")
                        item_options.append("Cancel")

                        draw_menu("Manage Strongbox Claim Queue", item_options, it_idx)
                        itk = get_key()
                        if itk == "up":
                            it_idx = (it_idx - 1) % len(item_options)
                        elif itk == "down":
                            it_idx = (it_idx + 1) % len(item_options)
                        elif itk in ("backspace", "esc", "left"):
                            break
                        elif (
                            itk in ("enter", "space", "right")
                            or itk.isdigit()
                            or (len(itk) == 1 and itk.isalpha())
                        ):
                            it_sel = it_idx
                            if itk.isdigit():
                                d_idx = int(itk) - 1
                                if 0 <= d_idx < len(item_options):
                                    it_sel = d_idx
                            elif len(itk) == 1 and itk.isalpha():
                                a_idx = ord(itk.upper()) - 65 + 9
                                if 0 <= a_idx < len(item_options):
                                    it_sel = a_idx

                            if it_sel == len(item_options) - 1:
                                break
                            elif it_sel == len(item_options) - 2:
                                if prompt_confirm("Clear the entire claim queue?"):
                                    p.set(["Strongboxes", "Claimed"], [])
                                    message = "Claim queue cleared successfully."
                                break
                            else:
                                if prompt_confirm(
                                    f"Remove item {it_sel} from claim queue?"
                                ):
                                    p.remove_claimed_strongbox(it_sel)
                                    message = "Item removed from claim queue."
                                break
                elif idx == 5:
                    val_username: str = prompt_str("Enter new Username")
                    p.name = val_username
                    message = "Username updated successfully."
                elif idx == 6:
                    val_money: int = prompt_int("Enter Money amount", min_val=0)
                    p.money = val_money
                    message = "Money updated successfully."
                elif idx == 7:
                    val_keys: int = prompt_int("Enter Black Keys count", min_val=0)
                    p.black_keys = val_keys
                    message = "Black Keys count updated successfully."
                elif idx == 8:
                    val_cores: int = prompt_int(
                        "Enter Elite Augment Cores count", min_val=0
                    )
                    p.augment_cores = val_cores
                    message = "Augment Cores count updated successfully."
                elif idx == 9:
                    p.skill_reset = not reset
                    message = f"Skill Reset set to {not reset}."
                elif idx == 10:
                    val_frag: int = prompt_int("Enter Frag Grenades count", min_val=0)
                    p.ammo_frag = val_frag
                    message = "Frag Grenades updated successfully."
                elif idx == 11:
                    val_cryo: int = prompt_int("Enter Cryo Grenades count", min_val=0)
                    p.ammo_cryo = val_cryo
                    message = "Cryo Grenades updated successfully."
                elif idx == 12:
                    val_level: int = prompt_int(
                        "Enter Player Level (1-100)", min_val=1, max_val=100
                    )
                    p.level = val_level
                    message = f"Level set to {val_level} and experience points synced."
                elif idx == 13:
                    p.max_masteries()
                    message = "All masteries maxed out."
                elif idx == 14:
                    p.clear_masteries()
                    message = "All masteries reset to 0."
                elif idx == 15:
                    stats: list[str] = [
                        "multi_kills",
                        "multi_deaths",
                        "multi_games_won",
                        "multi_games_lost",
                    ]
                    s_idx: int = 0
                    while True:
                        stat_options: list[str] = [
                            f"{s} (Current: {p.get_mp_stat(s)})" for s in stats
                        ] + ["Cancel"]
                        draw_menu(
                            "Select Multiplayer Stat to Modify", stat_options, s_idx
                        )
                        sk = get_key()
                        if sk == "up":
                            s_idx = (s_idx - 1) % len(stat_options)
                        elif sk == "down":
                            s_idx = (s_idx + 1) % len(stat_options)
                        elif sk in ("backspace", "esc", "left"):
                            break
                        elif sk in ("enter", "space", "right") or sk.isdigit():
                            target_s: int = s_idx
                            if sk.isdigit():
                                d_idx = int(sk) - 1
                                if 0 <= d_idx < len(stat_options):
                                    target_s = d_idx
                            if target_s == len(stats):
                                break
                            stat_key: str = stats[target_s]
                            val_stat: int = prompt_int(
                                f"Enter new value for {stat_key}", min_val=0
                            )
                            p.set_mp_stat(stat_key, val_stat)
                            message = f"{stat_key} updated to {val_stat}."
                            break
                elif idx == 16:
                    turrets: list[dict[str, Any]] = p.get_available_turrets()
                    if not turrets:
                        message = (
                            "No available turrets found in database for current level."
                        )
                        continue

                    t_idx: int = 0
                    while True:
                        raw_save: dict[str, Any] = editor._load()
                        current_turrets: list[dict[str, Any]] = (
                            raw_save.get("Inventory", {})
                            .get(profile_key, {})
                            .get("Turrets", [])
                        )
                        current_counts: dict[int, int] = {
                            t.get("TurretId", 0): t.get("TurretCount", 0)
                            for t in current_turrets
                        }
                        t_options: list[str] = [
                            f"{t.get('Name')} (ID {t.get('ID')}) - Current: {current_counts.get(t.get('ID', 0), 0)}"
                            for t in turrets
                        ] + ["Cancel"]

                        draw_menu("Select Sentry Turret Type", t_options, t_idx)
                        tk = get_key()
                        if tk == "up":
                            t_idx = (t_idx - 1) % len(t_options)
                        elif tk == "down":
                            t_idx = (t_idx + 1) % len(t_options)
                        elif tk in ("backspace", "esc", "left"):
                            break
                        elif (
                            tk in ("enter", "space", "right")
                            or tk.isdigit()
                            or (len(tk) == 1 and tk.isalpha())
                        ):
                            target_t: int = t_idx
                            if tk.isdigit():
                                d_idx = int(tk) - 1
                                if 0 <= d_idx < len(t_options):
                                    target_t = d_idx
                            elif len(tk) == 1 and tk.isalpha():
                                a_idx = ord(tk.upper()) - 65 + 9
                                if 0 <= a_idx < len(t_options):
                                    target_t = a_idx

                            if target_t == len(turrets):
                                break

                            turret_id: int = int(turrets[target_t]["ID"])
                            val_t: int = prompt_int(
                                f"Enter quantity for {turrets[target_t].get('Name')}",
                                min_val=0,
                            )
                            p.set_turret_count(turret_id, val_t)
                            message = f"{turrets[target_t].get('Name')} quantity updated to {val_t}."
                elif idx == 17:
                    actions: list[str] = [
                        "Set Black Boxes count (overwrites)",
                        "Add Black Boxes count (appends)",
                        "Cancel",
                    ]
                    act_idx: int = 0
                    while True:
                        draw_menu("Manage Black Boxes", actions, act_idx)
                        ak = get_key()
                        if ak == "up":
                            act_idx = (act_idx - 1) % len(actions)
                        elif ak == "down":
                            act_idx = (act_idx + 1) % len(actions)
                        elif ak in ("backspace", "esc", "left"):
                            break
                        elif ak in ("enter", "space", "right") or ak.isdigit():
                            sel: int = act_idx
                            if ak.isdigit():
                                d_idx = int(ak) - 1
                                if 0 <= d_idx < len(actions):
                                    sel = d_idx
                            if sel == 2:
                                break

                            val_box: int = prompt_int(
                                "Enter count of black boxes", min_val=0
                            )
                            if sel == 0:
                                p.set_black_boxes(val_box)
                                message = f"Black boxes count set to {val_box}."
                            else:
                                p.add_black_boxes(val_box)
                                message = f"Appended {val_box} black boxes."
                            break
                elif idx == 18:
                    if prompt_confirm(
                        "Clear both normal Strongbox Claim Queue and Black Strongboxes queue?"
                    ):
                        p.clear_strongbox_queues()
                        message = "Strongbox queues cleared successfully."
                elif idx == 19:
                    return None
            except CancelError:
                message = "Action cancelled."
            except (
                SAS_ZA4ToolError,
                OSError,
                ValueError,
                KeyError,
                IndexError,
                TypeError,
            ) as e:
                logger.error(f"Profile option failed: {e}")
                message = f"Error: {e}"
