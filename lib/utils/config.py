from pathlib import Path
from typing import TypedDict
import json

class ConfigData(TypedDict):
    steam_id64: int
    steam_path: str
    active_profiles: list[str]
    selected_profile: str


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path if path else Path.cwd() / "config.json"
        self._cached_data: ConfigData | None = None
        self.default: ConfigData = {
            "steam_id64": 0,
            "steam_path": "",
            "active_profiles": [""],
            "selected_profile": ""
        }

    def load(self) -> ConfigData:
        if not self.path.exists():
            return self.default
        
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.save(self.default)
            return self.default
    
    def save(self, config: ConfigData) -> None:
        with open(self.path, "w") as f:
            json.dump(config, f, indent=4)
    
    def reset(self) -> None:
        self.save(self.default)
    
    @property
    def data(self) -> ConfigData:
        if self._cached_data is None:
            self._cached_data = self.load()
        return self._cached_data
    
    @data.setter
    def data(self, config: ConfigData) -> None:
        self._cached_data = config
        self.save(config)

    def __enter__(self) -> "ConfigManager":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._cached_data is not None:
            self.save(self._cached_data)

    def __repr__(self) -> str:
        return f"ConfigManager({self.path.name})"

__all__ = [
    "ConfigManager",
    "ConfigData"
]