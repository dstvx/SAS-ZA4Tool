import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lib.config import config
from lib.crypt import decode_from_file, encode_to_file
from lib.save.editor import Editor


class TestSaveEditorFeatures(unittest.TestCase):
    """Unit test suite for save editor enhancements."""

    def setUp(self) -> None:
        """Sets up a temporary encrypted SAS:ZA4 save file."""
        self.initial_data: dict[str, Any] = {
            "Inventory": {
                "Profile0": {
                    "Name": "TestChar1",
                    "Money": 1000,
                    "Loaded": True,
                    "FreeSkillsReset": False,
                    "Skills": {
                        "AvailableBlackKeys": 5,
                        "AvailableEliteAugmentCores": 3,
                        "AvailableBlackStrongboxes": [99999]
                    },
                    "Weapons": [
                        {
                            "ID": 101,
                            "InventoryIndex": 0,
                            "Grade": 2,
                            "AugmentSlots": 2,
                            "BonusStatsLevel": 1,
                            "EquippedSlot": -1
                        }
                    ],
                    "Equipment": [],
                    "Strongboxes": {
                        "Claimed": [
                            0,
                            {
                                "ID": 201,
                                "EquipVersion": 1,
                                "Grade": 4,
                                "AugmentSlots": 3,
                                "BonusStatsLevel": 2,
                                "EquippedSlot": -1
                            },
                            8,
                            2
                        ]
                    }
                },
                "Profile1": {
                    "Name": "TestChar2",
                    "Money": 200,
                    "Loaded": True,
                    "Weapons": [],
                    "Equipment": []
                }
            },
            "CollectionArrayWeapon": [
                {"CollectionUnlocked": False}
            ],
            "CollectionArrayArmour": [
                {"CollectionUnlocked": False}
            ],
            "CollectionRewards": {
                "reward_1": False
            }
        }

        fd, path_str = tempfile.mkstemp(suffix=".save")
        os.close(fd)
        self.temp_save_path = Path(path_str)
        
        json_str = json.dumps(self.initial_data, separators=(",", ":"))
        encode_to_file(json_str, str(self.temp_save_path))

    def tearDown(self) -> None:
        """Cleans up the temporary save file."""
        if self.temp_save_path.exists():
            os.remove(self.temp_save_path)

    def test_granular_collections(self) -> None:
        """Tests granular collection unlocking methods."""
        editor = Editor(self.temp_save_path)
        
        editor.globals.set_weapons_collection_state(True)
        raw = json.loads(decode_from_file(str(self.temp_save_path)))
        self.assertTrue(raw["CollectionArrayWeapon"][0]["CollectionUnlocked"])
        self.assertFalse(raw["CollectionArrayArmour"][0]["CollectionUnlocked"])

        editor.globals.set_armour_collection_state(True)
        raw = json.loads(decode_from_file(str(self.temp_save_path)))
        self.assertTrue(raw["CollectionArrayArmour"][0]["CollectionUnlocked"])

        editor.globals.set_rewards_collection_state(True)
        raw = json.loads(decode_from_file(str(self.temp_save_path)))
        self.assertTrue(raw["CollectionRewards"]["reward_1"])

    def test_claim_queue_viewer(self) -> None:
        """Tests reading and deleting items from the strongbox claim queue."""
        editor = Editor(self.temp_save_path)
        p0 = editor.profile("Profile0")
        
        claimed = p0.get_claimed_strongboxes()
        self.assertEqual(len(claimed), 1)
        self.assertTrue(claimed[0]["is_weapon"])
        self.assertEqual(claimed[0]["data"]["ID"], 201)

        p0.remove_claimed_strongbox(0)
        claimed_after = p0.get_claimed_strongboxes()
        self.assertEqual(len(claimed_after), 0)

    def test_shared_inventory_transporter(self) -> None:
        """Tests transporting items between profiles."""
        editor = Editor(self.temp_save_path)
        p0 = editor.profile("Profile0")
        p1 = editor.profile("Profile1")
        
        self.assertEqual(len(p0.get("Weapons", [])), 1)
        self.assertEqual(len(p1.get("Weapons", [])), 0)

        p0.transport_item("Weapons", 0, "Profile1")
        
        self.assertEqual(len(p0.get("Weapons", [])), 0)
        self.assertEqual(len(p1.get("Weapons", [])), 1)
        self.assertEqual(p1.get("Weapons", [])[0]["ID"], 101)

    def test_stat_editor(self) -> None:
        """Tests editing stats on equipped inventory items."""
        editor = Editor(self.temp_save_path)
        p0 = editor.profile("Profile0")
        
        weapon = p0.get("Weapons", [])[0]
        self.assertEqual(weapon["Grade"], 2)
        self.assertEqual(weapon["AugmentSlots"], 2)
        self.assertEqual(weapon["BonusStatsLevel"], 1)

        p0.update_item_stats("Weapons", 0, 10, 4, 8)
        
        updated_weapon = p0.get("Weapons", [])[0]
        self.assertEqual(updated_weapon["Grade"], 10)
        self.assertEqual(updated_weapon["AugmentSlots"], 4)
        self.assertEqual(updated_weapon["BonusStatsLevel"], 8)

    def test_inject_to_inventory(self) -> None:
        """Tests injecting an item directly to the active profile's inventory."""
        editor = Editor(self.temp_save_path)
        p0 = editor.profile("Profile0")
        
        self.assertEqual(len(p0.get("Weapons", [])), 1)
        p0.inject_to_inventory(is_weapon=True, item_id=202, version=0, grade=10, slot=-1, augs=4, bonus=5)
        
        weapons = p0.get("Weapons", [])
        self.assertEqual(len(weapons), 2)
        self.assertEqual(weapons[1]["ID"], 202)
        self.assertEqual(weapons[1]["Grade"], 10)
        self.assertEqual(weapons[1]["AugmentSlots"], 4)
        self.assertEqual(weapons[1]["BonusStatsLevel"], 5)
        self.assertEqual(weapons[1]["EquippedSlot"], -1)

        # Inject equipment (Vest - ID 101, slot 1)
        p0.inject_to_inventory(is_weapon=False, item_id=101, version=0, grade=8, slot=1, augs=3, bonus=6)
        equipment = p0.get("Equipment", [])
        self.assertGreaterEqual(len(equipment), 1)
        last_equip = equipment[-1]
        self.assertEqual(last_equip["ID"], 101)
        self.assertEqual(last_equip["EquippedSlot"], 1)
        self.assertEqual(last_equip["AugmentSlots"], 3)
        self.assertEqual(last_equip["BonusStatsLevel"], 6)
        self.assertFalse(last_equip["Equipped"])

    def test_inject_equipment_to_claimed_strongbox(self) -> None:
        """Tests injecting equipment to claimed strongbox with auto-resolved slot."""
        editor = Editor(self.temp_save_path)
        p0 = editor.profile("Profile0")

        # Inject Boots (ID 214 -> boots = slot 4)
        p0.inject_item(is_weapon=False, item_id=214, version=1, grade=10, slot=4, augs=3, bonus=7)
        claimed = p0.get_claimed_strongboxes()
        newest = claimed[-1]
        self.assertFalse(newest["is_weapon"])
        self.assertEqual(newest["data"]["ID"], 214)
        self.assertEqual(newest["data"]["EquippedSlot"], 4)
        self.assertEqual(newest["data"]["InventoryIndex"], 4)
        self.assertEqual(newest["data"]["AugmentSlots"], 3)
        self.assertEqual(newest["data"]["BonusStatsLevel"], 7)
        self.assertFalse(newest["data"]["Equipped"])

    def test_claimed_strongbox_stats_and_transport(self) -> None:
        """Tests editing stats and transporting items inside the claimed strongbox queue."""
        editor = Editor(self.temp_save_path)
        p0 = editor.profile("Profile0")
        p1 = editor.profile("Profile1")
        
        claimed_p0 = p0.get_claimed_strongboxes()
        self.assertEqual(len(claimed_p0), 1)
        self.assertEqual(claimed_p0[0]["data"]["Grade"], 4)
        
        p0.update_claimed_strongbox_stats(0, grade=12, augs=4, bonus=10)
        claimed_p0_updated = p0.get_claimed_strongboxes()
        self.assertEqual(claimed_p0_updated[0]["data"]["Grade"], 12)
        self.assertEqual(claimed_p0_updated[0]["data"]["AugmentSlots"], 4)
        self.assertEqual(claimed_p0_updated[0]["data"]["BonusStatsLevel"], 10)
        
        p0.transport_claimed_strongbox(0, "Profile1")
        self.assertEqual(len(p0.get_claimed_strongboxes()), 0)
        
        claimed_p1 = p1.get_claimed_strongboxes()
        self.assertEqual(len(claimed_p1), 1)
        self.assertEqual(claimed_p1[0]["data"]["ID"], 201)
        self.assertEqual(claimed_p1[0]["data"]["Grade"], 12)

    def test_config_check_updates(self) -> None:
        """Tests config properties for check_updates."""
        original_val = config.check_updates
        try:
            config.check_updates = False
            self.assertFalse(config.check_updates)
            config.check_updates = True
            self.assertTrue(config.check_updates)
        finally:
            config.check_updates = original_val

    def test_live_update_checking(self) -> None:
        """Tests check_for_updates functionality using unittest.mock."""
        from unittest.mock import MagicMock, patch

        from lib.utils.updates import check_for_updates
        
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v9.9.9"}'
        mock_response.__enter__.return_value = mock_response
        
        with patch("urllib.request.urlopen", return_value=mock_response):
            has_update, latest = check_for_updates()
            self.assertTrue(has_update)
            self.assertEqual(latest, "9.9.9")

        mock_response_older = MagicMock()
        mock_response_older.read.return_value = b'{"tag_name": "v1.0.1"}'
        mock_response_older.__enter__.return_value = mock_response_older
        
        with patch("urllib.request.urlopen", return_value=mock_response_older):
            has_update, latest = check_for_updates()
            self.assertFalse(has_update)

    def test_config_validation(self) -> None:
        """Tests configuration validation warnings and errors."""
        orig_save = config.save_path
        orig_steam = config.steam_id
        orig_steam_path = config.steam_path
        orig_profile = config.current_profile
        orig_active = config.active_profiles
        
        try:
            config.save_path = ""
            errors = config.validate()
            self.assertTrue(any("Critical: Save path" in e for e in errors))
            
            config.save_path = "C:\\non_existent_save_file.save"
            errors = config.validate()
            self.assertTrue(any("Critical: Save path does not exist" in e for e in errors))
            
            config.save_path = str(self.temp_save_path)
            config.steam_id = "abc"
            errors = config.validate()
            self.assertTrue(any("Critical: Steam ID ('steam_id') must be a numeric string" in e for e in errors))
            
            config.steam_id = ""
            errors = config.validate()
            self.assertTrue(any("Critical: Steam ID ('steam_id') is empty" in e for e in errors))
            
            config.steam_id = "12345"
            config.current_profile = "Profile99"
            config.active_profiles = ["Profile0"]
            errors = config.validate()
            self.assertTrue(any("Warning: Selected profile 'Profile99' is not in active profiles list" in e for e in errors))
            
            config.current_profile = "Profile0"
            config.steam_path = ""
            errors = config.validate()
            self.assertEqual(len(errors), 0)
        finally:
            config.save_path = orig_save
            config.steam_id = orig_steam
            config.steam_path = orig_steam_path
            config.current_profile = orig_profile
            config.active_profiles = orig_active

    def test_in_memory_decoded_copy(self) -> None:
        """Tests accessing, mutating, and exporting the in-memory decoded copy."""
        editor = Editor(self.temp_save_path)
        data = editor.data
        self.assertIn("Inventory", data)
        self.assertEqual(data["Inventory"]["Profile0"]["Name"], "TestChar1")

        # Mutate in-memory and verify disk persistence
        p0 = editor.profile("Profile0")
        p0.money = 50000
        self.assertEqual(editor.data["Inventory"]["Profile0"]["Money"], 50000)

        # Export JSON directly from in-memory copy
        export_fd, export_path_str = tempfile.mkstemp(suffix=".json")
        os.close(export_fd)
        export_path = Path(export_path_str)
        try:
            editor.export_json(export_path)
            with open(export_path, "r", encoding="utf-8") as f:
                exported_data = json.load(f)
            self.assertEqual(exported_data["Inventory"]["Profile0"]["Money"], 50000)
        finally:
            if export_path.exists():
                os.remove(export_path)

    def test_in_memory_crypt(self) -> None:
        """Tests in-memory encoding and decoding without file roundtrips."""
        from lib.crypt import decode_bytes, encode_bytes
        sample_text = json.dumps({"test_key": 12345, "name": "SAS4_Hero"})
        encoded = encode_bytes(sample_text)
        self.assertTrue(encoded.startswith(b"DGDATA"))
        decoded = decode_bytes(encoded)
        self.assertEqual(decoded, sample_text)

    def test_steam_resolver_cross_platform(self) -> None:
        """Tests that Steam resolver does not crash and resolves paths on Linux/Windows."""
        from lib.steam.steam import Resolver, to_account_id
        resolver = Resolver()
        resolved = resolver.resolve()
        # Should not raise exception
        if resolved is not None:
            self.assertTrue(resolved.is_dir())

        # Test Steam ID 64 to 32 conversion
        self.assertEqual(to_account_id(76561198984674273), 1024408545)
        self.assertEqual(to_account_id(1024408545), 1024408545)


if __name__ == "__main__":
    unittest.main()

