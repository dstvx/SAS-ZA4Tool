from __future__ import annotations
from typing import Any

from lib.ui.user_interface import OptionType, create_option
from lib.save_handler import save_manager
from lib.save_handler.session import SaveError
from lib.utils.registry import (
    GLOBAL_REVIVE_TOKENS, GLOBAL_NIGHTMARE_TICKETS, GLOBAL_REMOVE_ADS,
    GLOBAL_FACTION, GLOBAL_FW_CREDITS, IAP_CHAR_SLOT_1, IAP_CHAR_SLOT_2,
    IAP_FAIRGROUND_PACK, COLLECTION_WEAPONS, COLLECTION_ARMOUR, 
    COLLECTION_REWARDS, FACTIONS, PLANETS
)

def get_global_property(prop_name: str, default: Any = 0) -> Any:
    try:
        return save_manager.get_session().get(["Global", prop_name], default)
    except SaveError:
        return default

def set_global_property(prop_name: str, node: dict[str, Any]) -> dict[str, Any]:
    try:
        session = save_manager.get_session()
        val = node.get("_last_input", node.get("value"))
        session.set(["Global", prop_name], val)
        session.commit()
        return {"message": f"Updated {prop_name} to {val}", "is_error": False}
    except SaveError as e:
        return {"message": f"Modification failed: {e}", "is_error": True}

def set_collection_state(unlocked: bool) -> dict[str, Any]:
    try:
        session = save_manager.get_session()
        
        for key in (COLLECTION_WEAPONS, COLLECTION_ARMOUR):
            items = session.get([key], [])
            for item in items: item["CollectionUnlocked"] = unlocked
            session.set([key], items)
            
        rewards = session.get([COLLECTION_REWARDS], {})
        for key in rewards: rewards[key] = unlocked
        session.set([COLLECTION_REWARDS], rewards)
        
        session.commit()
        state = "Unlocked" if unlocked else "Locked/Reset"
        return {"message": f"Collections {state}", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed: {e}", "is_error": True}

def wipe_collection_stats() -> dict[str, Any]:
    try:
        session = save_manager.get_session()
        stat_keys = [
            "CollectionSPKills", "CollectionMPKills", "CollectionBossKills",
            "CollectionTotalDamage", "CollectionMaxDamage", "CollectionTimesUsed"
        ]
        
        for key in (COLLECTION_WEAPONS, COLLECTION_ARMOUR):
            items = session.get([key], [])
            for item in items:
                for sk in stat_keys:
                    if sk in item: item[sk] = 0
            session.set([key], items)
            
        session.commit()
        return {"message": "Collection stats wiped", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed: {e}", "is_error": True}

def unlock_fairground_pack() -> dict[str, Any]:
    try:
        session = save_manager.get_session()
        iaps = session.get(["PurchasedIAP", "PurchasedIAPArray"], [])
        
        for idx in [15, 16]:
            while len(iaps) <= idx: iaps.append({"Identifier": "unknown", "Value": False})
            iaps[idx]["Value"] = True
            if idx == 15: iaps[idx]["Identifier"] = IAP_FAIRGROUND_PACK[0]
            if idx == 16: iaps[idx]["Identifier"] = IAP_FAIRGROUND_PACK[1]
            
        session.set(["PurchasedIAP", "PurchasedIAPArray"], iaps)
        session.commit()
        return {"message": "Fairground Pack Unlocked", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed: {e}", "is_error": True}

def get_iap_status(identifier: str) -> bool:
    try:
        session = save_manager.get_session()
        iaps = session.get(["PurchasedIAP", "PurchasedIAPArray"], [])
        return any(iap.get("Identifier") == identifier and iap.get("Value") for iap in iaps)
    except SaveError: return False

def toggle_iap(identifier: str) -> dict[str, Any]:
    try:
        session = save_manager.get_session()
        iaps = session.get(["PurchasedIAP", "PurchasedIAPArray"], [])
        
        state = True
        found = False
        for iap in iaps:
            if iap.get("Identifier") == identifier:
                state = not iap.get("Value", False)
                iap["Value"] = state
                found = True
                break
        
        if not found: iaps.append({"Identifier": identifier, "Value": True})
            
        session.set(["PurchasedIAP", "PurchasedIAPArray"], iaps)
        session.commit()
        return {"message": f"Set {identifier} to {state}", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed: {e}", "is_error": True}

def set_faction_war_faction(name: str, sub_node: dict[str, Any]) -> dict[str, Any]:
    try:
        session = save_manager.get_session()
        cur = session.get([GLOBAL_FACTION], "")
        new = "" if cur == name else name
        
        session.set([GLOBAL_FACTION], new)
        session.commit()
        
        if sub_node:
            for child in sub_node.get("children", []):
                base = child["id"].split("_")[1]
                child["label"] = f"[ACTIVE] {base}" if base == new else base
        
        return {"message": f"Faction set to {new if new else 'None'}", "is_error": False}
    except SaveError as e:
        return {"message": f"Failed: {e}", "is_error": True}

def set_faction_war_credits(pid: int | str, node: dict[str, Any], parent: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        amt = int(node.get("_last_input", node.get("value", 0)))
        session = save_manager.get_session()
        
        if pid == "Faction War":
            session.set([GLOBAL_FW_CREDITS], amt)
            msg = f"Set Credits to {amt}"
        else:
            planets = session.get(["FactionWarPlanetArray"], [])
            if pid == "All":
                for p in planets: p["Currency"] = amt
                msg = f"Set all planets to {amt}"
                if parent:
                    for child in parent.get("children", []):
                        if child.get("option_id", "").startswith("1.1.2.101_"):
                            child["value"] = amt
            else:
                found = False
                for p in planets:
                    if p.get("Planet") == pid:
                        p["Currency"] = amt
                        found = True
                        break
                if not found: planets.append({"Planet": pid, "Currency": amt})
                msg = f"Set Planet {pid} to {amt}"
            session.set(["FactionWarPlanetArray"], planets)
            
        session.commit()
        return {"message": msg, "is_error": False}
    except Exception as e:
        return {"message": f"Failed: {e}", "is_error": True}

def _build_iap_menu() -> dict[str, Any]:
    return create_option("IAP & Packs", "1.1.1", OptionType.SUBMENU,
        children=[
            create_option("Unlock Slot 4", "1.1.1.1", OptionType.TOGGLE, value=get_iap_status(IAP_CHAR_SLOT_1), action=lambda: toggle_iap(IAP_CHAR_SLOT_1)),
            create_option("Unlock Slot 5", "1.1.1.2", OptionType.TOGGLE, value=get_iap_status(IAP_CHAR_SLOT_2), action=lambda: toggle_iap(IAP_CHAR_SLOT_2)),
            create_option("Unlock Fairground Pack", "1.1.1.3", OptionType.ACTION, action=unlock_fairground_pack)
        ]
    )

def _build_collections_menu() -> dict[str, Any]:
    return create_option("Collection Management", "1.1.5", OptionType.SUBMENU,
        children=[
            create_option("Unlock ALL", "1.1.5.1", OptionType.ACTION, action=lambda: set_collection_state(True)),
            create_option("Reset ALL", "1.1.5.2", OptionType.ACTION, action=lambda: set_collection_state(False)),
            create_option("Wipe Stats (Kills/Dmg)", "1.1.5.3", OptionType.ACTION, action=wipe_collection_stats)
        ]
    )

def _build_fw_menu() -> dict[str, Any]:
    session = save_manager.get_session()
    cur_f = session.get([GLOBAL_FACTION], "")
    
    sel = create_option("Change Faction", "1.1.5.1", OptionType.SUBMENU, children=[])
    for f in FACTIONS:
        lbl = f"[ACTIVE] {f}" if f == cur_f else f
        sel["children"].append(create_option(lbl, f"fw_{f}", OptionType.ACTION, action=lambda f_n=f: set_faction_war_faction(f_n, sel)))

    creds = create_option("Set Credits", "1.1.5.2", OptionType.SUBMENU, children=[])
    main_c = create_option("Set Main Credits", "1.1.5.2.Main", OptionType.INPUT["number"], range_min=0, value=lambda: session.get([GLOBAL_FW_CREDITS], 0))
    main_c["action"] = lambda n=main_c: set_faction_war_credits("Faction War", n)
    
    all_p = create_option("Set ALL Planet Credits", "1.1.5.2.All", OptionType.INPUT["number"], range_min=0, value=lambda: 0, action=lambda: set_faction_war_credits("All", all_p, creds))
    creds["children"].extend([main_c, all_p])
    
    p_raw = session.get(["FactionWarPlanetArray"], [])
    p_map = {p.get("Planet", 0): p.get("Currency", 0) for p in p_raw}
    for i, (name, pid) in enumerate(PLANETS, 1):
        node = create_option(name, f"1.1.5.2.{i}", OptionType.INPUT["number"], range_min=0, value=lambda p=pid: p_map.get(p, 0))
        node["action"] = lambda p=pid, n=node: set_faction_war_credits(p, n)
        creds["children"].append(node)
        
    return create_option("Faction War", "1.1.6", OptionType.SUBMENU, children=[sel, creds])

def generate_global_menu() -> dict[str, Any]:
    revive = create_option("Revive Tokens", "1.1.2", OptionType.INPUT["number"], range_min=0, value=lambda: get_global_property(GLOBAL_REVIVE_TOKENS), action=lambda: set_global_property(GLOBAL_REVIVE_TOKENS, revive))
    tickets = create_option("Nightmare Tickets", "1.1.3", OptionType.INPUT["number"], range_min=0, value=lambda: get_global_property(GLOBAL_NIGHTMARE_TICKETS), action=lambda: set_global_property(GLOBAL_NIGHTMARE_TICKETS, tickets))
    ads = create_option("Toggle Ads (Mobile)", "1.1.4", OptionType.TOGGLE, value=lambda: bool(get_global_property(GLOBAL_REMOVE_ADS, False)), action=lambda: set_global_property(GLOBAL_REMOVE_ADS, ads))
    
    return create_option("Global", "1.1", OptionType.SUBMENU, children=[_build_iap_menu(), revive, tickets, ads, _build_collections_menu(), _build_fw_menu()])
