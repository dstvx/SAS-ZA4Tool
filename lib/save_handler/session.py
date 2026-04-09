"""
Save Handler Session Module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar, Iterable

from .dgdata import decode_from_file, encode_to_file
from lib.utils.config import ConfigManager
from lib.steam.steam import get_save_path, convert_steamid64_to_userid

T = TypeVar("T")

class SaveError(Exception):
    pass

class SaveNotFoundError(SaveError):
    pass

@dataclass
class SaveSession:
    """Manages a session with a SAS4 Profile.save file."""
    path: Path
    data: dict[str, Any] = field(default_factory=dict)
    _is_dirty: bool = False

    @classmethod
    def open_active(cls) -> SaveSession:
        path = cls.resolve_active_path()
        if not path or not path.exists():
            raise SaveNotFoundError("Could not resolve or find the active Profile.save.")
        
        return cls.from_file(path)

    @classmethod
    def resolve_active_path(cls) -> Path | None:
        with ConfigManager() as config:
            cm = config.data
            steam_path_str = cm.get("steam_path", "")
            steamid64 = cm.get("steam_id64", 0)
            
            if not steam_path_str or not steamid64:
                return None
            
            steam_path = Path(steam_path_str)
            user_id = convert_steamid64_to_userid(steamid64)
            try:
                return get_save_path(steam_path, user_id)
            except Exception:
                return None

    @classmethod
    def from_file(cls, path: Path | str) -> SaveSession:
        path = Path(path)
        try:
            decoded_str = decode_from_file(str(path))
            data = json.loads(decoded_str)
            return cls(path=path, data=data)
        except Exception as e:
            raise SaveError(f"Failed to load save file: {e}") from e

    def get(self, path: Iterable[str], default: Any = None) -> Any:
        current = self.data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    def set(self, path: Iterable[str], value: Any) -> None:
        path_list = list(path)
        if not path_list:
            return

        current = self.data
        for key in path_list[:-1]:
            current = current.setdefault(key, {})
        
        target_key = path_list[-1]
        existing = current.get(target_key)
        
        # Mark dirty if value changed or if mutable object is modified in-place
        if existing != value or (isinstance(value, (list, dict)) and existing is value):
            current[target_key] = value
            self._is_dirty = True

    def commit(self) -> None:
        if not self._is_dirty:
            return
            
        try:
            compact_json = json.dumps(self.data, separators=(",", ":"))
            encode_to_file(compact_json, str(self.path))
            self._is_dirty = False
        except Exception as e:
            raise SaveError(f"Failed to commit changes to disk: {e}") from e

    def rollback(self) -> None:
        new_session = self.from_file(self.path)
        self.data = new_session.data
        self._is_dirty = False
