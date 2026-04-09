"""
Profile-Specific Options.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, TypeVar

from lib.ui.user_interface import OptionType, create_option
from lib.save_handler import save_manager
from lib.save_handler.session import SaveError
from lib.utils.registry import (
    PROF_MONEY, PROF_LEVEL, PROF_XP, PROF_STATS, PROF_BLACK_KEYS, PROF_BLACK_BOXES, 
    PROF_AUG_CORES, PROF_SKILL_RESET, AMMO_FRAG, AMMO_CRYO, XP_THRESHOLDS
)

T = TypeVar("T")
ITEMS_JSON_PATH = Path(__file__).parent.parent / "data" / "items.json"
_ITEM_DATA_CACHE: dict[str, Any] | None = None

def get_items_database() -> dict[str, Any]:
    global _ITEM_DATA_CACHE
    if _ITEM_DATA_CACHE is None:
        try:
            with open(ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
                _ITEM_DATA_CACHE = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _ITEM_DATA_CACHE = {"weapons": {}, "armour": {}, "premium": {}, "turret": {}}
    return _ITEM_DATA_CACHE

def _get_selected_profile_key() -> str | None:
    from lib.utils.config import ConfigManager
    with ConfigManager() as config:
        return config.data.get("selected_profile")

def get_item_name(item_id: int, preferred_category: str | None = None) -> str:
    db = get_items_database()
    
    # Priority search in preferred category
    if preferred_category:
        cat_data = db.get(preferred_category, {})
        if preferred_category in ["weapons", "armour"]:
            for subcat in cat_data.values():
                for version in subcat.values():
                    for item in version:
                        if item["ID"] == item_id: return item["Name"]
        else: # premium or turret
            for item_list in cat_data.values():
                for item in item_list:
                    if item["ID"] == item_id: return item["Name"]

    # Global fallback search
    for cat_name, cat_data in db.items():
        if cat_name in ["weapons", "armour"]:
            for subcat in cat_data.values():
                for version in subcat.values():
                    for item in version:
                        if item["ID"] == item_id: return item["Name"]
        else:
            for item_list in cat_data.values():
                for item in item_list:
                    if item["ID"] == item_id: return item["Name"]
                
    return f"Unknown Item ({item_id})"
    
def _get_iap_identifier(item_id: int) -> str | None:
    db = get_items_database()
    for cat_list in db.get("premium", {}).values():
        for wpn in cat_list:
            if wpn["ID"] == item_id:
                return f"sas4_{wpn['Name'].lower().replace('.', '').replace(' ', '')}"
    return None

def _set_iap_value(identifier: str, value: bool):
    session = save_manager.get_session()
    iap_path = ["PurchasedIAP", "PurchasedIAPArray"]
    iaps = session.get(iap_path, [])
    found = False
    for iap in iaps:
        if iap.get("Identifier") == identifier:
            iap["Value"] = value
            found = True
            break
    if not found and value:
        iaps.append({"Identifier": identifier, "Value": True})
    session.set(iap_path, iaps)

def remove_item_at_index(list_index: int, category: str) -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        
        path_name = "Weapons" if category == "weapon" else "Equipment"
        path = ["Inventory", str(profile_key), path_name]
        items = session.get(path, [])
        
        if 0 <= list_index < len(items):
            removed = items.pop(list_index)
            # Re-index to keep inventory clean
            for i, item in enumerate(items):
                item["InventoryIndex"] = i
                
            session.set(path, items)
            
            # Handle IAP for premium guns
            if category == "weapon":
                ident = _get_iap_identifier(removed.get("ID", 0))
                if ident:
                    # Check if any of THIS gun still exists
                    has_more = any(w.get("ID") == removed.get("ID") for w in items)
                    if not has_more:
                        _set_iap_value(ident, False)

            session.commit()
            return {"message": f"Successfully removed {get_item_name(removed.get('ID'))}!", "is_error": False}
        return {"message": "Invalid item index.", "is_error": True}
    except SaveError as e:
        return {"message": f"Removal failed: {e}", "is_error": True}

def get_profile_property(prop_path: list[str], default: Any = 0) -> Any:
    try:
        profile_key = _get_selected_profile_key()
        if not profile_key: return default
        
        session = save_manager.get_session()
        full_path = ["Inventory", str(profile_key)] + prop_path
        return session.get(full_path, default)
    except SaveError:
        return default

def set_profile_property(prop_path: list[str], node: dict[str, Any]) -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        if not profile_key: return {"message": "No profile selected.", "is_error": True}
        
        session = save_manager.get_session()
        full_path = ["Inventory", str(profile_key)] + prop_path
        val = node.get("_last_input", node.get("value"))
        
        session.set(full_path, val)
        session.commit()
        return {"message": f"Updated {prop_path[-1]} to {val}!", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed to modify profile: {e}", "is_error": True}

def set_player_level(node: dict[str, Any]) -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        if not profile_key: return {"message": "No profile selected.", "is_error": True}
        
        level = int(node.get("_last_input", node.get("value", 1)))
        total_xp = sum(XP_THRESHOLDS[:level])
        
        session = save_manager.get_session()
        session.set(["Inventory", str(profile_key)] + PROF_LEVEL, level)
        session.set(["Inventory", str(profile_key)] + PROF_XP, total_xp)
        session.commit()
        
        return {"message": f"Set level to {level} (XP: {total_xp:,})", "is_error": False}
    except Exception as e:
        return {"message": f"Failed to sync level: {e}", "is_error": True}

def add_random_black_strongboxes(node: dict[str, Any]) -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        count = int(node.get("_last_input", node.get("value", 0)))
        if count <= 0: return {"message": "Count must be positive.", "is_error": True}
        
        seeds = [random.randint(100000, 9999999999) for _ in range(count)]
        
        session = save_manager.get_session()
        session.set(["Inventory", str(profile_key)] + PROF_BLACK_BOXES, seeds)
        session.commit()
        
        return {"message": f"Added {count} Black Strongboxes", "is_error": False}
    except Exception as e:
        return {"message": f"Failed to add boxes: {e}", "is_error": True}

def get_mp_stat(stat_key: str) -> int:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        stats = session.get(["Inventory", str(profile_key)] + PROF_STATS, [])
        for entry in stats:
            if entry.get("key") == stat_key:
                return entry.get("val", 0)
    except Exception: pass
    return 0

def set_mp_stat(stat_key: str, node: dict[str, Any]) -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        path = ["Inventory", str(profile_key)] + PROF_STATS
        stats = session.get(path, [])
        val = int(node.get("_last_input", node.get("value", 0)))
        
        found = False
        for entry in stats:
            if entry.get("key") == stat_key:
                entry["val"] = val
                found = True
                break
        
        if not found: stats.append({"key": stat_key, "val": val})
            
        session.set(path, stats)
        session.commit()
        return {"message": f"Updated {stat_key} to {val}", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed to update MP stat: {e}", "is_error": True}

def get_turret_count(turret_id: int) -> int:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        turrets = session.get(["Inventory", str(profile_key), "Turrets"], [])
        for t in turrets:
            if t.get("TurretId") == turret_id:
                return t.get("TurretCount", 0)
    except Exception: pass
    return 0

def set_turret_count(turret_id: int, node: dict[str, Any]) -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        path = ["Inventory", str(profile_key), "Turrets"]
        turrets = session.get(path, [])
        val = int(node.get("_last_input", node.get("value", 0)))
        
        found = False
        for t in turrets:
            if t.get("TurretId") == turret_id:
                t["TurretCount"] = val
                found = True
                break
        if not found: turrets.append({"TurretId": turret_id, "TurretCount": val})
            
        session.set(path, turrets)
        session.commit()
        return {"message": f"Set Turret {turret_id} to {val}", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed to set turret: {e}", "is_error": True}

def max_out_masteries() -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        masteries = session.get(["MasteryProgress", f"Mastery{profile_key}"], [])
        for m in masteries:
            m["MasteryXp"] = 542400
            m["MasteryLvl"] = 5
        
        session.set(["MasteryProgress", f"Mastery{profile_key}"], masteries)
        session.commit()
        return {"message": "Masteries maxed out!", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed to update Masteries: {e}", "is_error": True}
        
def clear_masteries() -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        masteries = session.get(["MasteryProgress", f"Mastery{profile_key}"], [])
        for m in masteries:
            m["MasteryXp"] = 0
            m["MasteryLvl"] = 0
        
        session.set(["MasteryProgress", f"Mastery{profile_key}"], masteries)
        session.commit()
        return {"message": "Masteries cleared!", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed to clear Masteries: {e}", "is_error": True}

def god_roll_equipped() -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        
        for category in ["Weapons", "Equipment"]:
            path = ["Inventory", str(profile_key), category]
            items = session.get(path, [])
            for item in items:
                if item.get("EquippedSlot", -1) != -1 or item.get("Equipped") is True:
                    item["Grade"] = 12
                    item["BonusStatsLevel"] = 10
                    item["AugmentSlots"] = 4 if category == "Weapons" else 3
            session.set(path, items)
            
        session.commit()
        return {"message": "Equipped items God-Rolled (12/10)", "is_error": False}
    except SaveError as e:
        return {"message": f"God-roll failed: {e}", "is_error": True}

def clean_new_badges() -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        for category in ["Weapons", "Equipment"]:
            path = ["Inventory", str(profile_key), category]
            items = session.get(path, [])
            for item in items: item["Seen"] = True
            session.set(path, items)
            
        session.commit()
        return {"message": "Inventory notifications cleared", "is_error": False}
    except SaveError as e:
        return {"message": f"Clear failed: {e}", "is_error": True}

def clear_strongbox_queue() -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        session.set(["Inventory", str(profile_key), "Strongboxes", "Claimed"], [])
        session.commit()
        return {"message": "Claim queue cleared", "is_error": False}
    except SaveError as e:
        return {"message": f"Clear failed: {e}", "is_error": True}

def clear_black_box_queue() -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        session.set(["Inventory", str(profile_key)] + PROF_BLACK_BOXES, [])
        session.commit()
        return {"message": "Black Box queue cleared", "is_error": False}
    except SaveError as e:
        return {"message": f"Clear failed: {e}", "is_error": True}

def purge_premium_guns() -> dict[str, Any]:
    try:
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        db = get_items_database()
        
        premium_ids = set()
        iap_identifiers = set()
        for w_list in db.get("premium", {}).values():
            for wpn in w_list:
                premium_ids.add(wpn["ID"])
                ident = f"sas4_{wpn['Name'].lower().replace('.', '').replace(' ', '')}"
                iap_identifiers.add(ident)
        
        w_path = ["Inventory", str(profile_key), "Weapons"]
        weapons = session.get(w_path, [])
        session.set(w_path, [w for w in weapons if w.get("ID") not in premium_ids])
        
        iap_path = ["PurchasedIAP", "PurchasedIAPArray"]
        iaps = session.get(iap_path, [])
        for iap in iaps:
            if iap.get("Identifier") in iap_identifiers: iap["Value"] = False
        session.set(iap_path, iaps)
        
        session.commit()
        return {"message": "Premium weapons purged and revoked.", "is_error": False}
    except SaveError as e:
        return {"message": f"Purge failed: {e}", "is_error": True}
        
def _ask_for_number(prompt: str, r_min: int, r_max: int) -> int:
    while True:
        try:
            line = input(f"{prompt} [{r_min}-{r_max}]: ").strip()
            if not line: return -1
            num = int(line)
            if r_min <= num <= r_max: return num
            print(f"Error: Range {r_min}-{r_max}")
        except ValueError:
            print("Error: Invalid number")

def inject_item(category: str, item_id: int, version: str, slot: int) -> dict[str, Any]:
    try:
        bonus = _ask_for_number("Bonus Stats Level", 0, 10)
        if bonus == -1: return {"message": "Cancelled", "is_error": True}
        
        max_augs = 4 if category == "weapon" else 3
        augs = _ask_for_number(f"Augment Slots", 0, max_augs)
        if augs == -1: return {"message": "Cancelled", "is_error": True}
        grade = _ask_for_number("Item Grade (0-12)", 0, 12)
        if grade == -1: return {"message": "Cancelled", "is_error": True}

        ver_map = {"normal": 0, "red": 1, "black": 2, "factions": 3}
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        
        claim_path = ["Inventory", str(profile_key), "Strongboxes", "Claimed"]
        strongboxes = session.get(claim_path, [])
        
        item_prefix = 0 if category == "weapon" else 1
        item_obj = {
            "ID": item_id, "EquipVersion": ver_map.get(version, 0), "Grade": grade,
            "EquippedSlot": slot, "AugmentSlots": augs, "InventoryIndex": 0,
            "Seen": False, "BonusStatsLevel": bonus, "ContainsKey": False,
            "ContainsAugmentCore": False, "BlackStrongboxSeed": 0, "UseDefaultOpenLogic": True
        }
        if category == "armour": item_obj["Equipped"] = False
        
        strongboxes.extend([item_prefix, item_obj, 8, 2])
        session.set(claim_path, strongboxes)
        
        # Handle IAP for premium guns
        if category == "weapon":
            ident = _get_iap_identifier(item_id)
            if ident: _set_iap_value(ident, True)

        session.commit()
        return {"message": "Item injected into queue!", "is_error": False}
    except SaveError as e:
        return {"message": f"Inject failed: {e}", "is_error": True}

def _build_ammo_menu() -> dict[str, Any]:
    frag = create_option("Frag Grenades", "1.2.7.1", OptionType.INPUT["number"], range_min=0, value=lambda: get_profile_property(AMMO_FRAG))
    frag["action"] = lambda n=frag: set_profile_property(AMMO_FRAG, n)
    cryo = create_option("Cryo Grenades", "1.2.7.2", OptionType.INPUT["number"], range_min=0, value=lambda: get_profile_property(AMMO_CRYO))
    cryo["action"] = lambda n=cryo: set_profile_property(AMMO_CRYO, n)
    return create_option("Set Grenades", "1.2.7", OptionType.SUBMENU, children=[frag, cryo])

def _build_turrets_menu() -> dict[str, Any]:
    def get_turret_nodes():
        db = get_items_database()
        level = get_profile_property(PROF_LEVEL, 1)
        turret_cat = "normal" if level <= 30 else "red"
        turrets = db.get("turret", {}).get(turret_cat, [])
        
        nodes = []
        for t in turrets:
            t_id = t["ID"]
            node = create_option(f"{t['Name']} ({turret_cat})", f"1.2.8.{t_id}", OptionType.INPUT["number"], range_min=0, value=lambda tid=t_id: get_turret_count(tid))
            node["action"] = lambda tid=t_id, n=node: set_turret_count(tid, n)
            nodes.append(node)
        return nodes
    return create_option("Set Turrets", "1.2.8", OptionType.SUBMENU, children=get_turret_nodes)

def _build_injection_menus() -> dict[str, Any]:
    db = get_items_database()
    
    std_wpns = create_option("Standard Weapons", "1.2.6.1", OptionType.SUBMENU, children=[])
    for w_idx, (w_type, versions) in enumerate(db.get("weapons", {}).items(), 1):
        type_menu = create_option(w_type.replace("_", " ").title(), f"1.2.6.1.{w_idx}", OptionType.SUBMENU, children=[])
        for v_idx, (v_str, wpn_list) in enumerate(versions.items(), 1):
            ver_menu = create_option(v_str.title(), f"1.2.6.1.{w_idx}.{v_idx}", OptionType.SUBMENU, children=[])
            for i, wpn in enumerate(wpn_list, 1):
                node = create_option(wpn["Name"], f"1.2.6.1.{w_idx}.{v_idx}.{i}", OptionType.ACTION)
                node["action"] = lambda i_id=wpn["ID"], v=v_str: inject_item("weapon", i_id, v, -1)
                ver_menu["children"].append(node)
            type_menu["children"].append(ver_menu)
        std_wpns["children"].append(type_menu)

    premium = create_option("Premium Weapons", "1.2.6.2", OptionType.SUBMENU, children=[])
    for p_idx, (p_type, wpn_list) in enumerate(db.get("premium", {}).items(), 1):
        type_menu = create_option(p_type.replace("_", " ").title(), f"1.2.6.2.{p_idx}", OptionType.SUBMENU, children=[])
        for i, wpn in enumerate(wpn_list, 1):
            node = create_option(wpn["Name"], f"1.2.6.2.{p_idx}.{i}", OptionType.ACTION)
            node["action"] = lambda i_id=wpn["ID"]: inject_item("weapon", i_id, "normal", -1)
            type_menu["children"].append(node)
        premium["children"].append(type_menu)

    equipment = create_option("Equipment", "1.2.6.3", OptionType.SUBMENU, children=[])
    slots = {"helmet": 1, "vest": 2, "gloves": 3, "boots": 4, "pants": 5}
    for a_idx, (a_type, versions) in enumerate(db.get("armour", {}).items(), 1):
        type_menu = create_option(a_type.title(), f"1.2.6.3.{a_idx}", OptionType.SUBMENU, children=[])
        for v_idx, (v_str, a_list) in enumerate(versions.items(), 1):
            ver_menu = create_option(v_str.title(), f"1.2.6.3.{a_idx}.{v_idx}", OptionType.SUBMENU, children=[])
            for i, armr in enumerate(a_list, 1):
                node = create_option(armr["Name"], f"1.2.6.3.{a_idx}.{v_idx}.{i}", OptionType.ACTION)
                s_id = slots.get(a_type.lower(), 0)
                node["action"] = lambda i_id=armr["ID"], v=v_str, s=s_id: inject_item("armour", i_id, v, s)
                ver_menu["children"].append(node)
            type_menu["children"].append(ver_menu)
        equipment["children"].append(type_menu)

    return create_option("Inject Items", "1.2.6", OptionType.SUBMENU, children=[std_wpns, premium, equipment])

def _build_removal_menu() -> dict[str, Any]:
    def get_weapon_nodes():
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        wpns = session.get(["Inventory", str(profile_key), "Weapons"], [])
        nodes = []
        for idx, wpn in enumerate(wpns):
            name = get_item_name(wpn.get("ID", 0), "weapons")
            grade = wpn.get("Grade", 0)
            ver = wpn.get("EquipVersion", 0)
            ver_str = ["Norm", "Red", "Blk", "Fact"][ver] if ver < 4 else f"V{ver}"
            node = create_option(f"[{idx}] {name} ({ver_str}) G{grade}", f"1.2.11.1.{idx}", OptionType.ACTION)
            node["action"] = lambda i=idx: remove_item_at_index(i, "weapon")
            nodes.append(node)
        return nodes

    def get_armour_nodes():
        profile_key = _get_selected_profile_key()
        session = save_manager.get_session()
        armr = session.get(["Inventory", str(profile_key), "Equipment"], [])
        nodes = []
        for idx, item in enumerate(armr):
            name = get_item_name(item.get("ID", 0), "armour")
            grade = item.get("Grade", 0)
            node = create_option(f"[{idx}] {name} G{grade}", f"1.2.11.2.{idx}", OptionType.ACTION)
            node["action"] = lambda i=idx: remove_item_at_index(i, "armour")
            nodes.append(node)
        return nodes

    wpns = create_option("Remove Weapons", "1.2.11.1", OptionType.SUBMENU, children=get_weapon_nodes)
    armr = create_option("Remove Equipment", "1.2.11.2", OptionType.SUBMENU, children=get_armour_nodes)
    return create_option("Remove Items", "1.2.11", OptionType.SUBMENU, children=[wpns, armr])

def _build_mp_stats_menu() -> dict[str, Any]:
    stats_config = [("Kills", "multi_kills"), ("Deaths", "multi_deaths"), ("Won", "multi_games_won"), ("Lost", "multi_games_lost")]
    children = []
    for i, (label, key) in enumerate(stats_config, 1):
        def create_node(l=label, k=key, idx=i):
            node = create_option(l, f"1.2.10.{idx}", OptionType.INPUT["number"], range_min=0, value=lambda: get_mp_stat(k))
            node["action"] = lambda n=node, sk=k: set_mp_stat(sk, n)
            return node
        children.append(create_node())
    return create_option("Multiplayer Stats", "1.2.10", OptionType.SUBMENU, children=children)

def generate_profile_menu() -> dict[str, Any]:
    money = create_option("Set Money", "1.2.1", OptionType.INPUT["number"], value=lambda: get_profile_property(PROF_MONEY), action=lambda: set_profile_property(PROF_MONEY, money))
    level = create_option("Set Level", "1.2.2", OptionType.INPUT["number"], value=lambda: get_profile_property(PROF_LEVEL), range_min=1, range_max=100, action=lambda: set_player_level(level))
    keys = create_option("Set Black Keys", "1.2.3", OptionType.INPUT["number"], value=lambda: get_profile_property(PROF_BLACK_KEYS), action=lambda: set_profile_property(PROF_BLACK_KEYS, keys))
    boxes = create_option("Set Black Strongboxes", "1.2.3.1", OptionType.INPUT["number"], range_min=0, value=lambda: len(get_profile_property(PROF_BLACK_BOXES, [])), action=lambda: add_random_black_strongboxes(boxes))
    cores = create_option("Set Augment Cores", "1.2.4", OptionType.INPUT["number"], value=lambda: get_profile_property(PROF_AUG_CORES), action=lambda: set_profile_property(PROF_AUG_CORES, cores))
    reset = create_option("Toggle Skill Reset", "1.2.5", OptionType.TOGGLE, value=lambda: bool(get_profile_property(PROF_SKILL_RESET, False)), action=lambda: set_profile_property(PROF_SKILL_RESET, reset))
    
    return create_option("Profile", "1.2", OptionType.SUBMENU, children=[
        money, level, keys, boxes, cores, reset, _build_ammo_menu(), _build_turrets_menu(),
        _build_mp_stats_menu(),
        create_option("Mass God-Roll (Equipped)", "1.2.9", OptionType.ACTION, action=god_roll_equipped),
        create_option("Max Out Masteries", "1.2.9.1", OptionType.ACTION, action=max_out_masteries),
        create_option("Clear Masteries", "1.2.9.2", OptionType.ACTION, action=clear_masteries),
        create_option("Clear 'New' Notifs", "1.2.9.3", OptionType.ACTION, action=clean_new_badges),
        create_option("Purge Premium Weapons", "1.2.9.4", OptionType.ACTION, action=purge_premium_guns),
        create_option("Wipe Strongbox Queue", "1.2.9.5", OptionType.ACTION, action=clear_strongbox_queue),
        create_option("Wipe Black Strongbox Queue", "1.2.9.6", OptionType.ACTION, action=clear_black_box_queue),
        _build_injection_menus(),
        _build_removal_menu()
    ])
