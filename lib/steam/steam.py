import sys
from pathlib import Path
from typing import Optional, Final

if sys.platform != "win32":
    raise RuntimeError("Resolver is only supported on Windows platform.")

import winreg

STEAM_ID64_BASE: Final[int] = 76561197960265728


def to_account_id(steam_id: int | str) -> int:
    """Converts a 64-bit SteamID to a 32-bit account ID.

    Args:
        steam_id (int | str): The 64-bit or 32-bit Steam ID.

    Returns:
        int: The 32-bit Steam account ID.

    Raises:
        ValueError: If steam_id format is invalid.
    """
    try:
        val = int(steam_id)
    except ValueError as e:
        raise ValueError(f"Invalid Steam ID format: {steam_id}") from e

    if val >= STEAM_ID64_BASE:
        return val - STEAM_ID64_BASE
    return val


def _query_registry_path(hkey: int, subkey: str, value_name: str) -> Optional[Path]:
    """Queries registry key for Steam installation path value.

    Args:
        hkey (int): Registry hive key (HKEY_CURRENT_USER/HKEY_LOCAL_MACHINE).
        subkey (str): Registry path name.
        value_name (str): Registry value name to extract.

    Returns:
        Optional[Path]: Resolved directory Path or None.
    """
    try:
        with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
            path_str, _ = winreg.QueryValueEx(key, value_name)
            return Path(str(path_str)).resolve() if path_str else None
    except OSError:
        return None


class Resolver:
    """Steam path resolver locating installation directory using windows registry."""
    
    REGISTRY_LOOKUPS: Final[tuple[tuple[int, str, str], ...]] = (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Valve\Steam", "InstallPath"),
    )

    def __init__(self) -> None:
        """Initializes Resolver instance."""
        self._cached_path: Optional[Path] = None
        self._resolved: bool = False

    def resolve(self) -> Optional[Path]:
        """Resolves the Steam path from registry lookups and caches it.

        Returns:
            Optional[Path]: Resolved path directory, or None.
        """
        if not self._resolved:
            for hkey, subkey, value_name in self.REGISTRY_LOOKUPS:
                path = _query_registry_path(hkey, subkey, value_name)
                if path and path.is_dir():
                    self._cached_path = path
                    break
            self._resolved = True
        return self._cached_path


default_resolver: Final[Resolver] = Resolver()
