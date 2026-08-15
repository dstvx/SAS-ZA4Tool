import json
import random
from pathlib import Path
from typing import Any

from lib.config import config
from lib.crypt import decode_from_file, encode_to_file
from lib.exceptions import CryptError, ProfileNotFoundError, SaveError
from lib.utils.logger import logger

XP_THRESHOLDS = [
    0, 1071, 1288, 1655, 2176, 2855, 3696, 4704, 5883, 7237,
    8770, 10486, 12390, 14486, 16778, 19270, 21966, 24871, 27989, 31324,
    34880, 38661, 42672, 46917, 51400, 56125, 91145, 98978, 107193, 115797,
    124795, 134195, 144002, 154222, 164863, 175930, 187430, 199368, 211752, 224587,
    237880, 251637, 265865, 280569, 295756, 311433, 327605, 344279, 361461, 379158,
    397375, 416120, 435398, 455215, 475579, 496495, 517970, 540009, 562620, 585808,
    609580, 844923, 878201, 912282, 947176, 982890, 1019433, 1056813, 1095038, 1134118,
    1174060, 1214873, 1256565, 1299144, 1342620, 1387000, 1432293, 1478507, 1525650, 1573732,
    1622760, 1672743, 1723689, 1775606, 1828504, 1882390, 1937273, 1993161, 2050062, 2107986,
    2166940, 3339899, 3431459, 3524603, 3619342, 3715690, 3813659, 3913262, 4014512, 4117420
]


class ProfileProxy:
    """Namespace proxy for profile-specific operations (SOLID SRP)."""

    def __init__(self, editor: "Editor", profile_key: str) -> None:
        self._editor = editor
        self._profile_key = profile_key

    def set(self, key_path: str | list[str], value: Any) -> None:
        """Sets a value inside this profile."""
        self._editor.set_profile_value(self._profile_key, key_path, value)

    def get(self, key_path: str | list[str], default: Any = None) -> Any:
        """Gets a value from this profile."""
        return self._editor.get_profile_value(self._profile_key, key_path, default)

                                                                  
    @property
    def name(self) -> str:
        """Gets the profile name."""
        return self.get("Name", "")

    @name.setter
    def name(self, value: str) -> None:
        """Sets the profile name."""
        self.set("Name", value)

    @property
    def money(self) -> int:
        """Gets the profile money."""
        return self.get("Money", 0)

    @money.setter
    def money(self, value: int) -> None:
        """Sets the profile money."""
        if value < 0:
            raise ValueError("Money must be a non-negative integer.")
        self.set("Money", value)

    @property
    def black_keys(self) -> int:
        """Gets the profile available black keys count."""
        return self.get(["Skills", "AvailableBlackKeys"], 0)

    @black_keys.setter
    def black_keys(self, value: int) -> None:
        """Sets the profile available black keys count."""
        if value < 0:
            raise ValueError("Black keys count must be a non-negative integer.")
        self.set(["Skills", "AvailableBlackKeys"], value)

    @property
    def augment_cores(self) -> int:
        """Gets the profile available elite augment cores count."""
        return self.get(["Skills", "AvailableEliteAugmentCores"], 0)

    @augment_cores.setter
    def augment_cores(self, value: int) -> None:
        """Sets the profile available elite augment cores count."""
        if value < 0:
            raise ValueError("Augment cores count must be a non-negative integer.")
        self.set(["Skills", "AvailableEliteAugmentCores"], value)

    @property
    def skill_reset(self) -> bool:
        """Gets whether free skill reset is available."""
        return self.get("FreeSkillsReset", False)

    @skill_reset.setter
    def skill_reset(self, value: bool) -> None:
        """Sets whether free skill reset is available."""
        self.set("FreeSkillsReset", value)

    @property
    def ammo_frag(self) -> int:
        """Gets the profile frag grenades count."""
        return self.get(["Ammo", "grenades_frag"], 0)

    @ammo_frag.setter
    def ammo_frag(self, value: int) -> None:
        """Sets the profile frag grenades count."""
        if value < 0:
            raise ValueError("Grenade count must be a non-negative integer.")
        self.set(["Ammo", "grenades_frag"], value)

    @property
    def ammo_cryo(self) -> int:
        """Gets the profile cryo grenades count."""
        return self.get(["Ammo", "grenades_cryo"], 0)

    @ammo_cryo.setter
    def ammo_cryo(self, value: int) -> None:
        """Sets the profile cryo grenades count."""
        if value < 0:
            raise ValueError("Grenade count must be a non-negative integer.")
        self.set(["Ammo", "grenades_cryo"], value)

                                      
    def get_available_turrets(self) -> list[dict[str, Any]]:
        """Returns the list of available turrets based on player level tier."""
        level = self.level
        items_path = Path(__file__).resolve().parent.parent / "data" / "items.json"
        try:
            with open(items_path, "r", encoding="utf-8") as f:
                items_data = json.load(f)
            category = "normal" if level <= 30 else "red"
            return items_data.get("turret", {}).get(category, [])
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return []

    def set_turret_count(self, turret_id: int, count: int) -> None:
        """Sets the quantity of a specific turret type."""
        if count < 0:
            raise ValueError("Turret count must be a non-negative integer.")

        data = self._editor._load()
        turrets = data.setdefault("Inventory", {}).setdefault(self._profile_key, {}).setdefault("Turrets", [])

                                                     
        match = next((item for item in turrets if item.get("TurretId") == turret_id), None)
        if match is not None:
            match["TurretCount"] = count
        else:
            turrets.append({"TurretId": turret_id, "TurretCount": count})

        self._editor._save(data)

                                    
    @property
    def level(self) -> int:
        """Gets the profile player level."""
        return self.get(["Skills", "PlayerLevel"], 1)

    @level.setter
    def level(self, val: int) -> None:
        """Sets player level and calculates/syncs corresponding cumulative XP."""
        if not (1 <= val <= 100):
            raise ValueError("Player level must be between 1 and 100.")

                                                         
        total_xp = sum(XP_THRESHOLDS[:val])
        self.set(["Skills", "PlayerLevel"], val)
        self.set(["Skills", "PlayerTotalXp"], total_xp)

    @property
    def xp(self) -> int:
        """Gets the profile player total experience points."""
        return self.get(["Skills", "PlayerTotalXp"], 0)

    @xp.setter
    def xp(self, val: int) -> None:
        """Sets player total experience points."""
        if val < 0:
            raise ValueError("XP must be a non-negative integer.")
        self.set(["Skills", "PlayerTotalXp"], val)

                                                     
    def remove_item(self, category: str, list_index: int) -> None:
        """Pops an item from the category list and re-assigns InventoryIndex sequentially."""
        if category not in ("Weapons", "Equipment"):
            raise ValueError("Category must be 'Weapons' or 'Equipment'.")

        data = self._editor._load()
        inventory = data.setdefault("Inventory", {}).setdefault(self._profile_key, {})
        item_list = inventory.setdefault(category, [])

        if not (0 <= list_index < len(item_list)):
            raise IndexError("Item index out of range.")

        removed_item = item_list.pop(list_index)

                                                       
        for idx, item in enumerate(item_list):
            item["InventoryIndex"] = idx

                                  
        if category == "Weapons":
            removed_id = removed_item.get("ID")
            premium_map = self._editor._get_premium_weapons()
            if removed_id in premium_map:
                still_exists = any(item.get("ID") == removed_id for item in item_list)
                if not still_exists:
                    iap_id = premium_map[removed_id]
                    iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
                    match = next((item for item in iap_array if item.get("Identifier") == iap_id), None)
                    if match is not None:
                        match["Value"] = False

        self._editor._save(data)

                                    
    def set_masteries(self, level: int, xp: int) -> None:
        """Sets the Mastery level and XP for all weapon/armour masteries."""
        data = self._editor._load()
        mastery_key = f"Mastery{self._profile_key}"
        mastery_list = data.setdefault("MasteryProgress", {}).setdefault(mastery_key, [])
        for item in mastery_list:
            item["MasteryLvl"] = level
            item["MasteryXp"] = xp
        self._editor._save(data)

    def max_masteries(self) -> None:
        """Maxes out mastery level (level 5) and mastery XP (542,400) for all items."""
        self.set_masteries(5, 542400)

    def clear_masteries(self) -> None:
        """Resets mastery level and mastery XP to 0 for all items."""
        self.set_masteries(0, 0)

                                     
    def inject_item(
        self,
        is_weapon: bool,
        item_id: int,
        version: int = 0,
        grade: int = 0,
        slot: int = -1,
        augs: int = 0,
        bonus: int = 0,
    ) -> None:
        """Appends a 4-element item payload to the claimed strongboxes queue."""
        if not (0 <= version <= 3):
            raise ValueError("Version must be in [0, 3].")
        if not (0 <= grade <= 12):
            raise ValueError("Grade must be in [0, 12].")
        if not (0 <= bonus <= 10):
            raise ValueError("Bonus stats level must be in [0, 10].")

        max_augs = 4 if is_weapon else 3
        if not (0 <= augs <= max_augs):
            raise ValueError(f"Augment slots must be in [0, {max_augs}].")

        if is_weapon:
            item_dict: dict[str, Any] = {
                "ID": item_id,
                "EquipVersion": version,
                "Grade": grade,
                "EquippedSlot": slot if slot >= 0 else -1,
                "AugmentSlots": augs,
                "InventoryIndex": 0,
                "Seen": True,
                "BonusStatsLevel": bonus,
            }
        else:
            equip_type = slot if slot >= 0 else self._editor._get_armour_slot(item_id)
            item_dict = {
                "ID": item_id,
                "EquipVersion": version,
                "Grade": grade,
                "EquippedSlot": equip_type,
                "AugmentSlots": augs,
                "InventoryIndex": equip_type,
                "Seen": True,
                "BonusStatsLevel": bonus,
                "Equipped": False,
            }

        data = self._editor._load()
        claimed = (
            data.setdefault("Inventory", {})
            .setdefault(self._profile_key, {})
            .setdefault("Strongboxes", {})
            .setdefault("Claimed", [])
        )

        claimed.append(0 if is_weapon else 1)
        claimed.append(item_dict)
        claimed.append(8)
        claimed.append(2)

        if is_weapon:
            premium_map = self._editor._get_premium_weapons()
            if item_id in premium_map:
                iap_id = premium_map[item_id]
                iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
                match = next((item for item in iap_array if item.get("Identifier") == iap_id), None)
                if match is not None:
                    match["Value"] = True
                else:
                    iap_array.append({"Identifier": iap_id, "Value": True})

        self._editor._save(data)

    def inject_to_inventory(
        self,
        is_weapon: bool,
        item_id: int,
        version: int = 0,
        grade: int = 0,
        slot: int = -1,
        augs: int = 0,
        bonus: int = 0,
    ) -> None:
        """Appends an item directly to the active profile's weapons or equipment inventory list."""
        if not (0 <= version <= 3):
            raise ValueError("Version must be in [0, 3].")
        if not (0 <= grade <= 12):
            raise ValueError("Grade must be in [0, 12].")
        if not (0 <= bonus <= 10):
            raise ValueError("Bonus stats level must be in [0, 10].")

        max_augs: int = 4 if is_weapon else 3
        if not (0 <= augs <= max_augs):
            raise ValueError(f"Augment slots must be in [0, {max_augs}].")

        data = self._editor._load()
        inventory = data.setdefault("Inventory", {}).setdefault(self._profile_key, {})
        category: str = "Weapons" if is_weapon else "Equipment"
        item_list: list[dict[str, Any]] = inventory.setdefault(category, [])

        if is_weapon:
            item_dict: dict[str, Any] = {
                "ID": item_id,
                "EquipVersion": version,
                "Grade": grade,
                "EquippedSlot": slot if slot >= 0 else -1,
                "AugmentSlots": augs,
                "InventoryIndex": len(item_list),
                "Seen": True,
                "BonusStatsLevel": bonus,
            }
        else:
            equip_type = slot if slot >= 0 else self._editor._get_armour_slot(item_id)
            item_dict = {
                "ID": item_id,
                "EquipVersion": version,
                "Grade": grade,
                "EquippedSlot": equip_type,
                "AugmentSlots": augs,
                "InventoryIndex": len(item_list),
                "Seen": True,
                "BonusStatsLevel": bonus,
                "Equipped": False,
            }

        item_list.append(item_dict)

        if is_weapon:
            premium_map = self._editor._get_premium_weapons()
            if item_id in premium_map:
                iap_id = premium_map[item_id]
                iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
                match = next((item for item in iap_array if item.get("Identifier") == iap_id), None)
                if match is not None:
                    match["Value"] = True
                else:
                    iap_array.append({"Identifier": iap_id, "Value": True})

        self._editor._save(data)


                                       
    def get_mp_stat(self, stat_key: str, default: int = 0) -> int:
        """Gets a multiplayer stat value by key (e.g. games_lost)."""
        stats = self.get("StatsData", [])
        match = next((item for item in stats if item.get("key") == stat_key), None)
        return match.get("val", default) if match else default

    def set_mp_stat(self, stat_key: str, value: int) -> None:
        """Sets a multiplayer stat value by key (e.g. games_lost)."""
        data = self._editor._load()
        stats = data.setdefault("Inventory", {}).setdefault(self._profile_key, {}).setdefault("StatsData", [])

                                               
        match = next((item for item in stats if item.get("key") == stat_key), None)
        if match is not None:
            match["val"] = value
        else:
            stats.append({"key": stat_key, "val": value})

        self._editor._save(data)

                                                      
    def clear_strongbox_queues(self) -> None:
        """Resets both the normal strongbox claim queue and available black boxes list."""
        self.set(["Strongboxes", "Claimed"], [])
        self.set(["Skills", "AvailableBlackStrongboxes"], [])

    def set_black_boxes(self, count_or_seeds: int | list[int]) -> None:
        """Overwrites the available black strongbox array with random seeds or a direct list of seeds."""
        if isinstance(count_or_seeds, int):
            if count_or_seeds < 0:
                raise ValueError("Count must be a non-negative integer.")
            new_seeds = [random.randint(100000, 9999999999) for _ in range(count_or_seeds)]
        elif isinstance(count_or_seeds, list):
            new_seeds = count_or_seeds
        else:
            raise TypeError("Expected int or List[int].")

        self.set(["Skills", "AvailableBlackStrongboxes"], new_seeds)

    def add_black_boxes(self, count_or_seeds: int | list[int]) -> None:
        """Appends new random black box seeds or a direct list of seeds to the character's available black box array."""
        if isinstance(count_or_seeds, int):
            if count_or_seeds < 0:
                raise ValueError("Count must be a non-negative integer.")
            new_seeds = [random.randint(100000, 9999999999) for _ in range(count_or_seeds)]
        elif isinstance(count_or_seeds, list):
            new_seeds = count_or_seeds
        else:
            raise TypeError("Expected int or List[int].")

        current_boxes = self.get(["Skills", "AvailableBlackStrongboxes"], [])
        if not isinstance(current_boxes, list):
            current_boxes = []

        self.set(["Skills", "AvailableBlackStrongboxes"], current_boxes + new_seeds)

    def get_claimed_strongboxes(self) -> list[dict[str, Any]]:
        """Returns the list of pending items in the claimed strongboxes queue."""
        data = self._editor._load()
        claimed = (
            data.setdefault("Inventory", {})
            .setdefault(self._profile_key, {})
            .setdefault("Strongboxes", {})
            .setdefault("Claimed", [])
        )
        items: list[dict[str, Any]] = []
        for i in range(0, len(claimed), 4):
            if i + 1 < len(claimed):
                item_data = claimed[i + 1]
                is_weapon = (claimed[i] == 0)
                items.append({
                    "is_weapon": is_weapon,
                    "data": item_data
                })
        return items

    def remove_claimed_strongbox(self, index: int) -> None:
        """Removes a specific item from the claimed strongboxes queue by index."""
        data = self._editor._load()
        claimed = (
            data.setdefault("Inventory", {})
            .setdefault(self._profile_key, {})
            .setdefault("Strongboxes", {})
            .setdefault("Claimed", [])
        )
        start_idx = index * 4
        if start_idx + 3 < len(claimed):
            del claimed[start_idx : start_idx + 4]
        self._editor._save(data)

    def transport_item(self, category: str, list_index: int, dest_profile_key: str) -> None:
        """Pops an item from the category list and appends it to the destination profile's category list."""
        if category not in ("Weapons", "Equipment"):
            raise ValueError("Category must be 'Weapons' or 'Equipment'.")

        data = self._editor._load()
        if dest_profile_key not in data.get("Inventory", {}):
            raise ValueError(f"Destination profile {dest_profile_key} not found.")

        src_inventory = data.setdefault("Inventory", {}).setdefault(self._profile_key, {})
        src_list = src_inventory.setdefault(category, [])

        if not (0 <= list_index < len(src_list)):
            raise IndexError("Item index out of range.")

        item = src_list.pop(list_index)
        item["EquippedSlot"] = -1
        if "Equipped" in item:
            item["Equipped"] = False

        for idx, it in enumerate(src_list):
            it["InventoryIndex"] = idx

        dest_inventory = data["Inventory"][dest_profile_key]
        dest_list = dest_inventory.setdefault(category, [])
        item["InventoryIndex"] = len(dest_list)
        dest_list.append(item)

        self._editor._save(data)

    def update_item_stats(self, category: str, list_index: int, grade: int, augs: int, bonus: int) -> None:
        """Updates the grade, augment slots, and bonus stats level of an item in inventory."""
        if category not in ("Weapons", "Equipment"):
            raise ValueError("Category must be 'Weapons' or 'Equipment'.")

        if not (0 <= grade <= 12):
            raise ValueError("Grade must be in [0, 12].")
        if not (0 <= bonus <= 10):
            raise ValueError("Bonus stats level must be in [0, 10].")
        max_augs: int = 4 if category == "Weapons" else 3
        if not (0 <= augs <= max_augs):
            raise ValueError(f"Augment slots must be in [0, {max_augs}].")

        data = self._editor._load()
        inventory = data.setdefault("Inventory", {}).setdefault(self._profile_key, {})
        item_list = inventory.setdefault(category, [])

        if not (0 <= list_index < len(item_list)):
            raise IndexError("Item index out of range.")

        item: dict[str, Any] = item_list[list_index]
        item["Grade"] = grade
        item["AugmentSlots"] = augs
        item["BonusStatsLevel"] = bonus

        self._editor._save(data)

    def update_claimed_strongbox_stats(self, index: int, grade: int, augs: int, bonus: int) -> None:
        """Updates the grade, augment slots, and bonus stats level of an item in the claim queue."""
        if not (0 <= grade <= 12):
            raise ValueError("Grade must be in [0, 12].")
        if not (0 <= bonus <= 10):
            raise ValueError("Bonus stats level must be in [0, 10].")

        data = self._editor._load()
        claimed = (
            data.setdefault("Inventory", {})
            .setdefault(self._profile_key, {})
            .setdefault("Strongboxes", {})
            .setdefault("Claimed", [])
        )
        start_idx = index * 4
        if start_idx + 1 < len(claimed):
            item = claimed[start_idx + 1]
            item["Grade"] = grade
            item["AugmentSlots"] = augs
            item["BonusStatsLevel"] = bonus

            is_weapon = (claimed[start_idx] == 0)
            max_augs = 4 if is_weapon else 3
            if not (0 <= augs <= max_augs):
                raise ValueError(f"Augment slots must be in [0, {max_augs}].")

            self._editor._save(data)

    def transport_claimed_strongbox(self, index: int, dest_profile_key: str) -> None:
        """Pops a claimed strongbox item payload and appends it to the destination profile's queue."""
        data = self._editor._load()
        if dest_profile_key not in data.get("Inventory", {}):
            raise ValueError(f"Destination profile {dest_profile_key} not found.")

        src_inventory = data.setdefault("Inventory", {}).setdefault(self._profile_key, {})
        src_claimed = src_inventory.setdefault("Strongboxes", {}).setdefault("Claimed", [])

        start_idx = index * 4
        if not (0 <= start_idx < len(src_claimed)):
            raise IndexError("Claimed item index out of range.")

        item_type = src_claimed.pop(start_idx)
        item_dict = src_claimed.pop(start_idx)
        val_8 = src_claimed.pop(start_idx)
        val_2 = src_claimed.pop(start_idx)

        dest_inventory = data["Inventory"][dest_profile_key]
        dest_claimed = dest_inventory.setdefault("Strongboxes", {}).setdefault("Claimed", [])

        dest_claimed.append(item_type)
        dest_claimed.append(item_dict)
        dest_claimed.append(val_8)
        dest_claimed.append(val_2)

        self._editor._save(data)


class GlobalProxy:
    """Namespace proxy for global save operations (SOLID SRP)."""

    def __init__(self, editor: "Editor") -> None:
        self._editor = editor

                                                                       
    @property
    def revive_tokens(self) -> int:
        """Gets the global revive tokens count."""
        return self._editor.get_global_property("ReviveTokens", 0)

    @revive_tokens.setter
    def revive_tokens(self, value: int) -> None:
        """Sets the global revive tokens count."""
        self._editor.set_global_property("ReviveTokens", value)

    @property
    def nightmare_tickets(self) -> int:
        """Gets the global Nightmare Tickets count."""
        return self._editor.get_global_property("AvailablePremiumTickets", 0)

    @nightmare_tickets.setter
    def nightmare_tickets(self, value: int) -> None:
        """Sets the global Nightmare Tickets count."""
        self._editor.set_global_property("AvailablePremiumTickets", value)

    @property
    def remove_ads(self) -> bool:
        """Gets whether ads are globally removed."""
        return self._editor.get_global_property("ForceRemoveAds", False)

    @remove_ads.setter
    def remove_ads(self, value: bool) -> None:
        """Sets whether ads are globally removed."""
        self._editor.set_global_property("ForceRemoveAds", value)

                                            
    def set_collection_state(self, unlocked: bool) -> None:
        """Sets the unlocked state for all weapons, armours, and rewards collections."""
        data = self._editor._load()

        for item in data.setdefault("CollectionArrayWeapon", []):
            item["CollectionUnlocked"] = unlocked

        for item in data.setdefault("CollectionArrayArmour", []):
            item["CollectionUnlocked"] = unlocked

        rewards = data.setdefault("CollectionRewards", {})
        for key in rewards:
            rewards[key] = unlocked

        self._editor._save(data)

    def set_weapons_collection_state(self, unlocked: bool) -> None:
        """Sets the unlocked state for weapons collections."""
        data = self._editor._load()
        for item in data.setdefault("CollectionArrayWeapon", []):
            item["CollectionUnlocked"] = unlocked
        self._editor._save(data)

    def set_armour_collection_state(self, unlocked: bool) -> None:
        """Sets the unlocked state for armours collections."""
        data = self._editor._load()
        for item in data.setdefault("CollectionArrayArmour", []):
            item["CollectionUnlocked"] = unlocked
        self._editor._save(data)

    def set_rewards_collection_state(self, unlocked: bool) -> None:
        """Sets the unlocked state for collection rewards."""
        data = self._editor._load()
        rewards = data.setdefault("CollectionRewards", {})
        for key in rewards:
            rewards[key] = unlocked
        self._editor._save(data)

    def wipe_collection_stats(self) -> None:
        """Resets all weapon and armour usage/kill stats to 0."""
        data = self._editor._load()

        target_keys = {
            "CollectionSPKills",
            "CollectionMPKills",
            "CollectionBossKills",
            "CollectionTotalDamage",
            "CollectionMaxDamage",
            "CollectionTimesUsed",
        }

                                                        
        for category in ("CollectionArrayWeapon", "CollectionArrayArmour"):
            for item in data.setdefault(category, []):
                for key in target_keys:
                    if key in item:
                        item[key] = 0

        self._editor._save(data)

                                           
    def get_iap_status(self, identifier: str) -> bool:
        """Returns True if the specified IAP is purchased/unlocked."""
        data = self._editor._load()
        iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
        return any(item.get("Identifier") == identifier and item.get("Value") is True for item in iap_array)

    def toggle_iap(self, identifier: str) -> None:
        """Toggles the state of a specific In-App Purchase/DLC."""
        data = self._editor._load()
        iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])

                                               
        match = next((item for item in iap_array if item.get("Identifier") == identifier), None)
        if match is not None:
            match["Value"] = not match.get("Value", False)
        else:
            iap_array.append({"Identifier": identifier, "Value": True})

        self._editor._save(data)

    def unlock_profiles(self) -> None:
        """Unlocks paywalled character slots (Profile4 and Profile5)."""
        self._editor.unlock_profiles()

    def unlock_all_premium_guns(self) -> None:
        """Globally unlocks/purchases all premium DLC weapons in the PurchasedIAP list."""
        self._editor.unlock_all_premium_guns()

    def unlock_fairground_pack(self) -> None:
        """Unlocks the Fairground premium map pack DLC."""
        data = self._editor._load()
        iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])

                                    
        while len(iap_array) < 17:
            iap_array.append({"Identifier": "unknown", "Value": False})

        iap_array[15] = {"Identifier": "sas4_fairgroundpack_1", "Value": True}
        iap_array[16] = {"Identifier": "sas4_fairgroundpack_2", "Value": True}

        self._editor._save(data)

                         
    def set_faction(self, faction_name: str) -> None:
        """Joins the specified faction, or leaves if already in it."""
        data = self._editor._load()
        current = data.get("CurrentFactionWarFaction", "")

                                       
        data["CurrentFactionWarFaction"] = "" if current == faction_name else faction_name
        self._editor._save(data)

    def set_faction_war_credits(self, pid: str, amt: int) -> None:
        """Sets faction credits globally, for all planets, or a specific planet."""
        data = self._editor._load()

        if pid == "Faction War":
            data["FactionWarCredits"] = amt
        elif pid == "All":
            data["FactionWarCredits"] = amt
            for planet in data.setdefault("FactionWarPlanetArray", []):
                planet["Currency"] = amt
        else:
            planets = data.setdefault("FactionWarPlanetArray", [])
            match = next((p for p in planets if p.get("Planet") == pid), None)
            if match is not None:
                match["Currency"] = amt
            else:
                planets.append({"Planet": pid, "Currency": amt})

        self._editor._save(data)


class Editor:
    """Coordinates reading, writing, and providing namespace proxies to edit save data (SOLID SRP)."""

    def __init__(self, filepath: str | Path = "") -> None:
        self._filepath: Path | None = Path(filepath) if filepath else None
        self._data: dict[str, Any] | None = None
        # Auto-load decoded copy into memory if valid save file exists
        try:
            if self._has_valid_filepath():
                self._data = self._load()
        except (SaveError, CryptError, OSError, json.JSONDecodeError, KeyError, ValueError):
            self._data = None

    def _has_valid_filepath(self) -> bool:
        """Checks if a valid save file path is currently configured."""
        try:
            path = self._filepath or Path(config.save_path)
            return bool(path and str(path) != "." and path.is_file())
        except (OSError, ValueError, TypeError):
            return False

    def _get_filepath(self) -> Path:
        """Resolves the current filepath, falling back to config if not provided."""
        path = self._filepath or Path(config.save_path)
        if not path or str(path) == "." or not path.exists():
            raise SaveError(f"Save file path '{path}' is invalid or does not exist.")
        return path

    @property
    def data(self) -> dict[str, Any]:
        """Gets the internal decoded working copy of the save file."""
        return self._load()

    def get_data(self) -> dict[str, Any]:
        """Returns the internal decoded working copy of the save data."""
        return self._load()

    def reload(self) -> dict[str, Any]:
        """Forces reloading and decrypting the save file from disk into memory."""
        self._data = None
        return self._load()

    def export_json(self, export_path: str | Path, indent: int = 4) -> Path:
        """Exports the in-memory decoded save copy directly to a JSON file.

        Args:
            export_path (str | Path): Destination JSON filepath.
            indent (int): JSON indentation spaces.

        Returns:
            Path: Path object of exported JSON file.
        """
        dest = Path(export_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(self._load(), f, indent=indent)
        logger.info(f"Exported decoded save data to {dest}")
        return dest

    def _load(self) -> dict[str, Any]:
        """Loads and decrypts save file data into the working copy."""
        if self._data is not None:
            return self._data

        filepath = self._get_filepath()
        try:
            decoded_str = decode_from_file(str(filepath))
            decoded_json: dict[str, Any] = json.loads(decoded_str)
            self._data = decoded_json
            logger.info(f"Loaded and decrypted save file from disk: {filepath}")
            return decoded_json
        except Exception as e:
            logger.error(f"Failed to load or decrypt save file: {e}")
            raise SaveError(f"Failed to load or decrypt save file: {e}") from e

    def _save(self, data: dict[str, Any]) -> None:
        """Encrypts and writes save file data back to disk while keeping in-memory copy synced."""
        self._data = data
        filepath = self._get_filepath()
        try:
            json_str = json.dumps(data, separators=(",", ":"))
            encode_to_file(json_str, str(filepath))
            logger.info(f"Encrypted and wrote save file changes to disk: {filepath}")
        except Exception as e:
            logger.error(f"Failed to encrypt or write save file: {e}")
            raise SaveError(f"Failed to encrypt or write save file: {e}") from e

    @property
    def globals(self) -> GlobalProxy:
        """Access global save file attributes and operations."""
        return GlobalProxy(self)

    def profile(self, key: str) -> ProfileProxy:
        """Access profile-specific attributes and operations."""
        inventory = self._load().get("Inventory", {})
        if key not in inventory or not inventory[key].get("Loaded"):
            raise ProfileNotFoundError(f"Profile '{key}' is not active or loaded.")
        logger.info(f"Initialized ProfileProxy for {key}")
        return ProfileProxy(self, key)

    def get_loaded_profiles(self) -> list[str]:
        """Returns list of profile keys (e.g. Profile0) that are currently loaded."""
        data = self._load()
        inventory = data.get("Inventory", {})

        loaded_profiles = []
        for i in range(6):
            profile_key = f"Profile{i}"
            profile = inventory.get(profile_key)
            if profile and profile.get("Loaded"):
                loaded_profiles.append(profile_key)

        return loaded_profiles

    def sync(self) -> list[str]:
        """Synchronizes active profiles list with config without forcing disk re-decode."""
        loaded = self.get_loaded_profiles()
        config.active_profiles = loaded
        return loaded


                                                              

    def get_global_property(self, key: str, default: Any = None) -> Any:
        """Gets a property value from the nested 'Global' dictionary."""
        try:
            return self._load().get("Global", {}).get(key, default)
        except (SaveError, CryptError, KeyError, TypeError, OSError):
            return default

    def set_global_property(self, key: str, value: Any) -> None:
        """Sets a property value inside the nested 'Global' dictionary."""
        data = self._load()
        global_dict = data.setdefault("Global", {})
        global_dict[key] = value
        self._save(data)

    def get_global(self, key: str, default: Any = None) -> Any:
        """Gets a global root value from the save file."""
        return self._load().get(key, default)

    def set_global(self, key: str, value: Any) -> None:
        """Sets a global root value in the save file."""
        data = self._load()
        data[key] = value
        self._save(data)

    def unlock_profiles(self) -> None:
        """Unlocks paywalled character slots (Profile4 and Profile5)."""
        data = self._load()
        iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])
        target_ids = {"SAS4_CharacterSlot1", "SAS4_CharacterSlot2"}
        for item in iap_array:
            if item.get("Identifier") in target_ids:
                item["Value"] = True
        self._save(data)

    def unlock_all_premium_guns(self) -> None:
        """Globally unlocks/purchases all premium DLC weapons in the PurchasedIAP list."""
        premium_guns = [
            "sas4_ahab", "sas4_banshee", "sas4_bayonet", "sas4_calamity",
            "sas4_cm000kelvin", "sas4_cm352quasar", "sas4_cm369starfury",
            "sas4_cm467", "sas4_cm505alphaltdedition", "sas4_cmlaserdrill",
            "sas4_cmprotonarc", "sas4_contagion", "sas4_donderbus",
            "sas4_handkanone", "sas4_hiks888caw", "sas4_hiksa10",
            "sas4_hikss4000", "sas4_planetstormerltdedition", "sas4_ria15se",
            "sas4_ria75", "sas4_ria8a", "sas4_ricochet", "sas4_ronson5x5",
            "sas4_ronsonwpxincinerator"
        ]
        data = self._load()
        iap_array = data.setdefault("PurchasedIAP", {}).setdefault("PurchasedIAPArray", [])

        for identifier in premium_guns:
            match = next((item for item in iap_array if item.get("Identifier") == identifier), None)
            if match is not None:
                match["Value"] = True
            else:
                iap_array.append({"Identifier": identifier, "Value": True})

        self._save(data)

    def _get_premium_weapons(self) -> dict[int, str]:
        """Returns mapping of premium weapon ID to its IAP identifier."""
        items_path = Path(__file__).resolve().parent.parent / "data" / "items.json"
        try:
            with open(items_path, "r", encoding="utf-8") as f:
                items_data = json.load(f)

            premium_map = {}
            for category_data in items_data.get("weapons", {}).values():
                for item in category_data.get("premium", []):
                    item_id = item.get("ID")
                    item_name = item.get("Name", "")
                    if item_id and item_name:
                        iap_id = f"sas4_{item_name.lower().replace('.', '').replace(' ', '')}"
                        premium_map[item_id] = iap_id
            return premium_map
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return {}

    def _get_armour_slot(self, item_id: int) -> int:
        """Returns the equipment slot (0=helmet, 1=vest, 2=gloves, 3=pants, 4=boots) for an armour item ID."""
        slot_map: dict[str, int] = {
            "helmet": 0,
            "vest": 1,
            "gloves": 2,
            "pants": 3,
            "boots": 4,
        }
        items_path = Path(__file__).resolve().parent.parent / "data" / "items.json"
        try:
            with open(items_path, "r", encoding="utf-8") as f:
                items_data = json.load(f)
            for subcat, variants in items_data.get("armour", {}).items():
                slot_idx = slot_map.get(subcat.lower(), 0)
                for variant_items in variants.values():
                    for item in variant_items:
                        if item.get("ID") == item_id:
                            return slot_idx
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            pass
        return 0

                                        

    def set_profile_value(self, profile_key: str, key_path: str | list[str], value: Any) -> None:
        """Sets a value inside a specific loaded profile, supporting nested key paths."""
        data = self._load()
        profile = data.get("Inventory", {}).get(profile_key)

        if not profile or not profile.get("Loaded"):
            raise ProfileNotFoundError(f"Profile '{profile_key}' is not active or loaded.")

        if isinstance(key_path, str):
            profile[key_path] = value
        else:
                                  
                                           
            current = profile
            for step in key_path[:-1]:
                current = current.setdefault(step, {})
            current[key_path[-1]] = value

        self._save(data)

    def get_profile_value(self, profile_key: str, key_path: str | list[str], default: Any = None) -> Any:
        """Gets a value from a specific loaded profile, supporting nested key paths."""
        data = self._load()
        profile = data.get("Inventory", {}).get(profile_key)

        if not profile or not profile.get("Loaded"):
            raise ProfileNotFoundError(f"Profile '{profile_key}' is not active or loaded.")

        if isinstance(key_path, str):
            return profile.get(key_path, default)

                              
                                       
        current = profile
        for step in key_path[:-1]:
            current = current.setdefault(step, {})
        return current.get(key_path[-1], default)
