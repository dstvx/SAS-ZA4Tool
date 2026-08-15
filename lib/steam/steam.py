import sys
from pathlib import Path
from typing import Final

STEAM_ID64_BASE: Final[int] = 76561197960265728

LINUX_STEAM_PATHS: Final[tuple[Path, ...]] = (
    Path.home() / ".local/share/Steam",
    Path.home() / ".steam/steam",
    Path.home() / ".steam/root",
    Path.home() / ".var/app/com.valvesoftware.Steam/.steam/steam",
    Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    Path.home() / "snap/steam/common/.steam/steam",
    Path.home() / "snap/steam/common/.local/share/Steam",
)


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


def _query_registry_path(hkey: int, subkey: str, value_name: str) -> Path | None:
    """Queries registry key for Steam installation path value on Windows.

    Args:
        hkey (int): Registry hive key (HKEY_CURRENT_USER/HKEY_LOCAL_MACHINE).
        subkey (str): Registry path name.
        value_name (str): Registry value name to extract.

    Returns:
        Path | None: Resolved directory Path or None.
    """
    if sys.platform != "win32":
        return None

    import winreg
    try:
        with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
            path_str, _ = winreg.QueryValueEx(key, value_name)
            return Path(str(path_str)).resolve() if path_str else None
    except OSError:
        return None


def _resolve_windows() -> Path | None:
    """Resolves Steam path on Windows via registry lookups."""
    if sys.platform != "win32":
        return None

    import winreg
    lookups: tuple[tuple[int, str, str], ...] = (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Valve\Steam", "InstallPath"),
    )
    for hkey, subkey, value_name in lookups:
        path = _query_registry_path(hkey, subkey, value_name)
        if path and path.is_dir():
            return path
    return None


def _resolve_posix() -> Path | None:
    """Resolves Steam path on POSIX/Linux via standard directories."""
    for candidate in LINUX_STEAM_PATHS:
        resolved = candidate.resolve()
        if resolved.is_dir():
            return resolved
    return None


class Resolver:
    """Steam path resolver locating installation directory across platforms."""

    def __init__(self) -> None:
        """Initializes Resolver instance."""
        self._cached_path: Path | None = None
        self._resolved: bool = False

    def resolve(self) -> Path | None:
        """Resolves the Steam path and caches it.

        Returns:
            Path | None: Resolved path directory, or None.
        """
        if self._resolved:
            return self._cached_path

        if sys.platform == "win32":
            self._cached_path = _resolve_windows()
        else:
            self._cached_path = _resolve_posix()

        self._resolved = True
        return self._cached_path


default_resolver: Final[Resolver] = Resolver()

