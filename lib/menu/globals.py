from typing import Any, Final

from lib.exceptions import CancelError, CryptError, SAS_ZA4ToolError, SaveError
from lib.save.editor import Editor
from lib.ui.ui import (
    draw_menu,
    get_key,
    get_option_description,
    launch_game,
    prompt_confirm,
    prompt_int,
)
from lib.utils.logger import logger


def handle_global_menu(editor: Editor) -> str | None:
    """Displays and processes choices within the Global & Account Save Editor.

    Args:
        editor (Editor): The save file editor instance.

    Returns:
        Optional[str]: Error message if an operation fails, otherwise None.
    """
    selected_idx: int = 0
    message: str = ""
    
    premium_guns: Final[list[str]] = [
        "sas4_ahab", "sas4_banshee", "sas4_bayonet", "sas4_calamity",
        "sas4_cm000kelvin", "sas4_cm352quasar", "sas4_cm369starfury",
        "sas4_cm467", "sas4_cm505alphaltdedition", "sas4_cmlaserdrill",
        "sas4_cmprotonarc", "sas4_contagion", "sas4_donderbus",
        "sas4_handkanone", "sas4_hiks888caw", "sas4_hiksa10",
        "sas4_hikss4000", "sas4_planetstormerltdedition", "sas4_ria15se",
        "sas4_ria75", "sas4_ria8a", "sas4_ricochet", "sas4_ronson5x5",
        "sas4_ronsonwpxincinerator"
    ]

    while True:
        try:
            tokens: int = editor.globals.revive_tokens
            tickets: int = editor.globals.nightmare_tickets
            ads: bool = editor.globals.remove_ads
            faction: str = editor.get_global("CurrentFactionWarFaction", "None")
            fw_credits: int = editor.get_global("FactionWarCredits", 0)

            raw_save: dict[str, Any] = editor._load()
            iap_array: list[dict[str, Any]] = raw_save.get("PurchasedIAP", {}).get("PurchasedIAPArray", [])

            s1: dict[str, Any] | None = next((x for x in iap_array if x.get("Identifier") == "SAS4_CharacterSlot1"), None)
            s2: dict[str, Any] | None = next((x for x in iap_array if x.get("Identifier") == "SAS4_CharacterSlot2"), None)
            slots_active: bool = bool(s1 and s1.get("Value") and s2 and s2.get("Value"))

            fg1: Any = len(iap_array) > 15 and iap_array[15].get("Identifier") == "sas4_fairgroundpack_1" and iap_array[15].get("Value")
            fg2: Any = len(iap_array) > 16 and iap_array[16].get("Identifier") == "sas4_fairgroundpack_2" and iap_array[16].get("Value")
            fg_active: bool = bool(fg1 and fg2)

            guns_unlocked: int = sum(
                1 for g in premium_guns
                if any(x.get("Identifier") == g and x.get("Value") for x in iap_array)
            )
            guns_active: bool = (guns_unlocked == len(premium_guns))
        except (SaveError, KeyError, ValueError, TypeError, IndexError) as e:
            logger.error(f"Failed to read globals: {e}")
            tokens, tickets, ads, faction, fw_credits = 0, 0, False, "None", 0
            slots_active, fg_active, guns_active, guns_unlocked = False, False, False, 0

        options: list[str] = [
            f"Revive Tokens (Current: {tokens})",
            f"Nightmare Tickets (Current: {tickets})",
            f"Remove Ads Toggle (Current: {ads})",
            "Unlock Collections (Granular/All)",
            "Wipe Collection Stats (Kills/Damage)",
            f"Unlock Character Slots (Profile4 & Profile5) (Current: {'Active' if slots_active else 'Inactive'})",
            f"Unlock Fairground Pack DLC (Current: {'Active' if fg_active else 'Inactive'})",
            f"Unlock All Premium Guns globally (Current: {'Active' if guns_active else f'{guns_unlocked}/{len(premium_guns)}'})",
            f"Join Faction (Current: {faction or 'None'})",
            f"Set Faction War Credits (Main Faction War: {fw_credits})",
            "Back"
        ]
        
        draw_menu("Global / Account Editor", options, selected_idx, message, breadcrumb="Main Menu > Global & Account Editor")
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
                    val: int = prompt_int("Enter new Revive Tokens amount", min_val=0)
                    editor.globals.revive_tokens = val
                    message = "Revive Tokens updated successfully."
                elif idx == 1:
                    val = prompt_int("Enter new Nightmare Tickets amount", min_val=0)
                    editor.globals.nightmare_tickets = val
                    message = "Nightmare Tickets updated successfully."
                elif idx == 2:
                    editor.globals.remove_ads = not ads
                    message = f"Ads removal status set to {not ads}."
                elif idx == 3:
                    sub_opts: list[str] = ["Unlock Weapons Only", "Unlock Armor Only", "Unlock Rewards Only", "Unlock All Collections", "Cancel"]
                    sub_sel: int = 0
                    while True:
                        draw_menu("Granular Collection Unlocks", sub_opts, sub_sel, breadcrumb="Main Menu > Global Editor > Collections")
                        sk: str = get_key()
                        if sk == "up":
                            sub_sel = (sub_sel - 1) % len(sub_opts)
                        elif sk == "down":
                            sub_sel = (sub_sel + 1) % len(sub_opts)
                        elif sk in ("backspace", "esc", "left"):
                            break
                        elif sk in ("enter", "space", "right") or sk.isdigit():
                            target_sub: int = sub_sel
                            if sk.isdigit():
                                d_idx = int(sk) - 1
                                if 0 <= d_idx < len(sub_opts):
                                    target_sub = d_idx
                            if target_sub == 4:
                                break
                            elif target_sub == 0:
                                editor.globals.set_weapons_collection_state(True)
                                message = "Weapons collections unlocked."
                                break
                            elif target_sub == 1:
                                editor.globals.set_armour_collection_state(True)
                                message = "Armour collections unlocked."
                                break
                            elif target_sub == 2:
                                editor.globals.set_rewards_collection_state(True)
                                message = "Collection rewards unlocked."
                                break
                            elif target_sub == 3:
                                editor.globals.set_collection_state(True)
                                message = "All collections unlocked."
                                break
                elif idx == 4:
                    if prompt_confirm("Wipe all collections kills/damage stats?"):
                        editor.globals.wipe_collection_stats()
                        message = "Collection stats wiped successfully."
                elif idx == 5:
                    if slots_active:
                        raw_save = editor._load()
                        iap_array = raw_save.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
                        for item in iap_array:
                            if item.get("Identifier") in ("SAS4_CharacterSlot1", "SAS4_CharacterSlot2"):
                                item["Value"] = False
                        editor._save(raw_save)
                        message = "Character Slots 4 and 5 locked."
                    else:
                        editor.globals.unlock_profiles()
                        message = "Character Slots 4 and 5 unlocked."
                elif idx == 6:
                    if fg_active:
                        raw_save = editor._load()
                        iap_array = raw_save.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
                        if len(iap_array) > 16:
                            iap_array[15] = {"Identifier": "sas4_fairgroundpack_1", "Value": False}
                            iap_array[16] = {"Identifier": "sas4_fairgroundpack_2", "Value": False}
                        editor._save(raw_save)
                        message = "Fairground Map Pack DLC locked."
                    else:
                        editor.globals.unlock_fairground_pack()
                        message = "Fairground Map Pack DLC unlocked."
                elif idx == 7:
                    if guns_active:
                        raw_save = editor._load()
                        iap_array = raw_save.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
                        for g in premium_guns:
                            match: dict[str, Any] | None = next((item for item in iap_array if item.get("Identifier") == g), None)
                            if match:
                                match["Value"] = False
                        editor._save(raw_save)
                        message = "All premium weapons locked globally."
                    else:
                        editor.globals.unlock_all_premium_guns()
                        message = "All premium weapons unlocked globally."
                elif idx == 8:
                    factions: list[str] = ["CENTURIONS", "CORSAIRS", "GUARDIANS", "NOMADS", "OUTLAWS", "RANGERS", "SPARTANS", "VANGUARD"]
                    fac_idx: int = 0
                    while True:
                        draw_menu("Select Faction to Join", factions + ["Leave Faction", "Cancel"], fac_idx, breadcrumb="Main Menu > Global Editor > Faction Join")
                        fk: str = get_key()
                        if fk == "up":
                            fac_idx = (fac_idx - 1) % (len(factions) + 2)
                        elif fk == "down":
                            fac_idx = (fac_idx + 1) % (len(factions) + 2)
                        elif fk in ("backspace", "esc", "left"):
                            break
                        elif fk in ("enter", "space", "right") or fk.isdigit():
                            target_idx: int = fac_idx
                            if fk.isdigit():
                                d_idx: int = int(fk) - 1
                                if 0 <= d_idx < len(factions) + 2:
                                    target_idx = d_idx
                            if target_idx == len(factions) + 1:
                                break
                            elif target_idx == len(factions):
                                editor.set_global("CurrentFactionWarFaction", "")
                                message = "Left current faction."
                                break
                            else:
                                editor.globals.set_faction(factions[target_idx])
                                message = f"Joined faction: {factions[target_idx]}."
                                break
                elif idx == 9:
                    planets: list[str] = ["ZETA", "EPSILON", "SIGMA", "XI", "OMICRON", "Faction War", "All", "Cancel"]
                    plan_idx: int = 0
                    while True:
                        draw_menu("Select Faction Credits Target", planets, plan_idx, breadcrumb="Main Menu > Global Editor > Faction Credits")
                        pk: str = get_key()
                        if pk == "up":
                            plan_idx = (plan_idx - 1) % len(planets)
                        elif pk == "down":
                            plan_idx = (plan_idx + 1) % len(planets)
                        elif pk in ("backspace", "esc", "left"):
                            break
                        elif pk in ("enter", "space", "right") or pk.isdigit():
                            target_idx: int = plan_idx
                            if pk.isdigit():
                                d_idx = int(pk) - 1
                                if 0 <= d_idx < len(planets):
                                    target_idx = d_idx
                            if target_idx == len(planets) - 1:
                                break
                            target_name: str = planets[target_idx]
                            amt: int = prompt_int(f"Enter Faction credits for {target_name}", min_val=0)
                            editor.globals.set_faction_war_credits(target_name, amt)
                            message = f"Credits for {target_name} set to {amt}."
                            break
                elif idx == 10:
                    return None
            except CancelError:
                message = "Action cancelled."
            except (SaveError, CryptError, SAS_ZA4ToolError, OSError, ValueError, KeyError, TypeError, IndexError) as e:
                logger.error(f"Global operation failed: {e}")
                message = f"Error: {e}"

