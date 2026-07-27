import tomllib
import logging
from pathlib import Path
from typing import Any, Dict, List, Final

logger: Final[logging.Logger] = logging.getLogger("sas_za4tool")


def _serialize_value(value: Any) -> str:
    """Serializes a Python value into a TOML-compatible string.

    Args:
        value (Any): Input value to serialize.

    Returns:
        str: TOML serialized string value.

    Raises:
        TypeError: If value type is unsupported.
    """
    if isinstance(value, str):
        escaped: str = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        serialized_items: list[str] = [_serialize_value(item) for item in value]
        return f"[{', '.join(serialized_items)}]"
    raise TypeError(f"Unsupported configuration type: {type(value)}")


class Config:
    """Stores, loads, and manages configuration parameters in a TOML file."""
    
    DEFAULT_CONFIG: Final[Dict[str, Any]] = {
        "steam_id": "",
        "steam_path": "",
        "save_path": "",
        "active_profiles": [],
        "current_profile": "",
        "setup_done": False,
        "game_path": "steam://run/678800",
        "logs_enabled": False,
        "check_updates": True,
    }

    def __init__(self, filepath: Path) -> None:
        """Initializes the Config instance.

        Args:
            filepath (Path): Filepath to the TOML configuration file.
        """
        super().__setattr__("_filepath", filepath)
        super().__setattr__("_data", self._load_file())

    def _load_file(self) -> Dict[str, Any]:
        """Loads and parses the TOML configuration file.

        Returns:
            Dict[str, Any]: Parsed flat configuration dictionary.
        """
        if not self._filepath.exists():
            logger.info("Config file not found. Using defaults.")
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self._filepath, "rb") as f:
                data: Dict[str, Any] = tomllib.load(f)
            flat_data: Dict[str, Any] = {}
            def flatten(d: dict[str, Any]) -> None:
                for k, v in d.items():
                    if isinstance(v, dict):
                        flatten(v)
                    else:
                        flat_data[k] = v
            flatten(data)
            logger.info(f"Loaded config from {self._filepath}")
            return {**self.DEFAULT_CONFIG, **flat_data}
        except (OSError, tomllib.TOMLDecodeError) as e:
            logger.error(f"Error loading config TOML: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _save_file(self) -> None:
        """Saves the active configuration state back to the TOML file."""
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        sections: Dict[str, List[str]] = {
            "steam": ["steam_id", "steam_path"],
            "game": ["save_path", "game_path"],
            "tool": ["active_profiles", "current_profile", "setup_done", "logs_enabled", "check_updates"]
        }
        
        known_keys: set[str] = set(sections["steam"] + sections["game"] + sections["tool"])
        for k in self._data.keys():
            if k not in known_keys:
                sections["tool"].append(k)
                
        lines: List[str] = []
        for section, keys in sections.items():
            lines.append(f"[{section}]")
            for k in keys:
                if k in self._data:
                    lines.append(f"{k} = {_serialize_value(self._data[k])}")
            lines.append("")
            
        try:
            with open(self._filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            logger.info(f"Saved config updates to {self._filepath}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def _update_value(self, name: str, value: Any) -> None:
        """Updates a configuration setting and saves changes.

        Args:
            name (str): Parameter key name.
            value (Any): Parameter value.
        """
        self._data[name] = value
        self._save_file()
        logger.info(f"Config parameter updated: {name} = {value}")

    @property
    def steam_id(self) -> Any:
        return self._data.get("steam_id", "")

    @steam_id.setter
    def steam_id(self, value: Any) -> None:
        self._update_value("steam_id", value)

    @property
    def steam_path(self) -> str:
        return self._data.get("steam_path", "")

    @steam_path.setter
    def steam_path(self, value: str) -> None:
        self._update_value("steam_path", value)

    @property
    def save_path(self) -> str:
        return self._data.get("save_path", "")

    @save_path.setter
    def save_path(self, value: str) -> None:
        self._update_value("save_path", value)

    @property
    def active_profiles(self) -> List[str]:
        return self._data.get("active_profiles", [])

    @active_profiles.setter
    def active_profiles(self, value: List[str]) -> None:
        self._update_value("active_profiles", value)

    @property
    def current_profile(self) -> str:
        return self._data.get("current_profile", "")

    @current_profile.setter
    def current_profile(self, value: str) -> None:
        self._update_value("current_profile", value)

    @property
    def setup_done(self) -> bool:
        return self._data.get("setup_done", False)

    @setup_done.setter
    def setup_done(self, value: bool) -> None:
        self._update_value("setup_done", value)

    @property
    def check_updates(self) -> bool:
        return self._data.get("check_updates", True)

    @check_updates.setter
    def check_updates(self, value: bool) -> None:
        self._update_value("check_updates", value)

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Config has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._update_value(name, value)

    def __delattr__(self, name: str) -> None:
        if name in self._data:
            del self._data[name]
            self._save_file()
            logger.info(f"Deleted config parameter: {name}")
        else:
            raise AttributeError(f"Config has no attribute '{name}'")

    def update(self, **kwargs: Any) -> None:
        """Performs a bulk update of multiple keys and writes once.

        Args:
            **kwargs (Any): Key-value pairs to update.
        """
        self._data.update(kwargs)
        self._save_file()
        logger.info(f"Bulk config updated: {kwargs}")

    def delete(self, key: str) -> None:
        """Deletes a key from the configuration file.

        Args:
            key (str): Parameter key name to remove.
        """
        if key in self._data:
            del self._data[key]
            self._save_file()
            logger.info(f"Deleted config key: {key}")

    def validate(self) -> List[str]:
        """Validates critical and secondary configuration parameters.

        Returns:
            List[str]: A list of warning/error messages. Empty if validation passes.
        """
        errors: List[str] = []

        save_path_str: str = self._data.get("save_path", "")
        if not save_path_str:
            errors.append("Critical: Save path ('save_path') is empty.")
        else:
            p = Path(save_path_str)
            if not p.exists():
                errors.append(f"Critical: Save path does not exist: {save_path_str}")
            elif not p.is_file():
                errors.append(f"Critical: Save path is not a file: {save_path_str}")

        steam_id_str: str = str(self._data.get("steam_id", ""))
        if not steam_id_str:
            errors.append("Critical: Steam ID ('steam_id') is empty.")
        elif not steam_id_str.isdigit():
            errors.append(f"Critical: Steam ID ('steam_id') must be a numeric string, got: '{steam_id_str}'")

        steam_path_str: str = self._data.get("steam_path", "")
        if steam_path_str:
            sp = Path(steam_path_str)
            if not sp.exists():
                errors.append(f"Warning: Steam path does not exist: {steam_path_str}")

        current_profile: str = self._data.get("current_profile", "")
        active_profiles: list[str] = self._data.get("active_profiles", [])
        if current_profile and current_profile not in active_profiles:
            errors.append(f"Warning: Selected profile '{current_profile}' is not in active profiles list: {active_profiles}")

        return errors


def _get_project_root() -> Path:
    import sys
    is_compiled = False
    if hasattr(sys, "frozen") or getattr(sys, "readcompiled", False) or "__compiled__" in globals():
        is_compiled = True
    else:
        try:
            import builtins
            is_compiled = hasattr(builtins, "__compiled__")
        except ImportError:
            pass
    if is_compiled:
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT: Final[Path] = _get_project_root()
DEFAULT_TOML_PATH: Final[Path] = PROJECT_ROOT / "config.toml"

config: Final[Config] = Config(DEFAULT_TOML_PATH)
