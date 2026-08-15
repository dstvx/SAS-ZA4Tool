import re
from pathlib import Path
from typing import Final

from lib.exceptions import GameNotFoundError, ResolveError, SaveNotFoundError
from lib.steam.steam import Resolver, default_resolver, to_account_id

SAS_ZA4_APP_ID: Final[int] = 678800
HEX_FOLDER_REGEX: Final[re.Pattern[str]] = re.compile(r"^[0-9a-fA-F]+$")
SAVE_FILE_NAMES: Final[tuple[str, ...]] = ("Profile.save", "profile.save")


def _find_save_in_dir(directory: Path) -> Path | None:
    """Checks for Profile.save or profile.save in directory."""
    for filename in SAVE_FILE_NAMES:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


class SaveResolver:
    """Resolves the SAS:ZA4 Profile.save path using a SteamPathResolver."""

    def __init__(self, steam_resolver: Resolver = default_resolver) -> None:
        """Initializes SaveResolver.

        Args:
            steam_resolver (Resolver): Steam directory resolver instance.
        """
        self._steam_resolver: Resolver = steam_resolver

    def get(self, steam_id: int | str) -> Path:
        """Resolves and returns the path to the game's Profile.save file.

        Args:
            steam_id (int | str): Steam account ID (64-bit or 32-bit).

        Returns:
            Path: Resolved Profile.save file Path object.

        Raises:
            GameNotFoundError: If Steam path or SAS:ZA4 installation is not found.
            SaveNotFoundError: If save directory or Profile.save file is not found.
            ResolveError: If directory list query fails.
        """
        steam_path: Path | None = self._steam_resolver.resolve()
        if not steam_path:
            raise GameNotFoundError("Steam installation path could not be resolved.")

        account_id: int = to_account_id(steam_id)
        userdata_app_path: Path = steam_path / "userdata" / str(account_id) / str(SAS_ZA4_APP_ID)

        if not userdata_app_path.exists():
            is_installed = self._check_game_installed(steam_path)
            if not is_installed:
                raise GameNotFoundError(
                    f"SAS:ZA4 is not installed on this computer (Steam App ID {SAS_ZA4_APP_ID} missing)."
                )
            raise SaveNotFoundError(
                f"SAS:ZA4 is installed, but no save data folder exists for Steam account {steam_id}. "
                "Please launch the game at least once on this account to generate save files."
            )

        docs_path: Path = userdata_app_path / "local" / "Data" / "Docs"
        if not docs_path.is_dir():
            raise SaveNotFoundError(
                f"SAS:ZA4 userdata Docs directory not found at: {docs_path}. "
                "Please launch the game at least once on this account."
            )

        direct_save = _find_save_in_dir(docs_path)
        if direct_save:
            return direct_save

        try:
            for sub_dir in docs_path.iterdir():
                if not sub_dir.is_dir() or not HEX_FOLDER_REGEX.match(sub_dir.name):
                    continue
                nested_save = _find_save_in_dir(sub_dir)
                if nested_save:
                    return nested_save
        except OSError as e:
            raise ResolveError(f"Failed to read directory {docs_path}: {e}") from e

        raise SaveNotFoundError(
            f"Profile.save file not found in {docs_path} or any of its hex-named subdirectories."
        )

    def _check_game_installed(self, steam_path: Path) -> bool:
        """Checks if SAS:ZA4 app manifest exists in steam apps or library folders."""
        manifest_name = f"appmanifest_{SAS_ZA4_APP_ID}.acf"
        if (steam_path / "steamapps" / manifest_name).exists():
            return True

        lib_vdf = steam_path / "steamapps" / "libraryfolders.vdf"
        if not lib_vdf.exists():
            return False

        try:
            with open(lib_vdf, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for p in paths:
                normalized = Path(p.replace("\\\\", "/"))
                if (normalized / "steamapps" / manifest_name).exists():
                    return True
        except OSError:
            pass

        return False


save_path: Final[SaveResolver] = SaveResolver()

