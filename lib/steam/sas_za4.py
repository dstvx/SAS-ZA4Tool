import re
from pathlib import Path
from typing import Optional, Final

from lib.steam.steam import Resolver, default_resolver, to_account_id

SAS_ZA4_APP_ID: Final[int] = 678800
HEX_FOLDER_REGEX: Final[re.Pattern[str]] = re.compile(r"^[0-9a-fA-F]+$")


from lib.exceptions import ResolveError, GameNotFoundError, SaveNotFoundError


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
        steam_path: Optional[Path] = self._steam_resolver.resolve()
        if not steam_path:
            raise GameNotFoundError("Steam installation path could not be resolved.")

        account_id: int = to_account_id(steam_id)
        
        userdata_app_path: Path = steam_path / "userdata" / str(account_id) / str(SAS_ZA4_APP_ID)
        
        if not userdata_app_path.exists():
            is_game_installed: bool = (steam_path / "steamapps" / f"appmanifest_{SAS_ZA4_APP_ID}.acf").exists()
            if not is_game_installed:
                lib_vdf: Path = steam_path / "steamapps" / "libraryfolders.vdf"
                if lib_vdf.exists():
                    try:
                        with open(lib_vdf, "r", encoding="utf-8", errors="ignore") as f:
                            content: str = f.read()
                        paths: list[str] = re.findall(r'"path"\s+"([^"]+)"', content)
                        for p in paths:
                            p_path: Path = Path(p.replace("\\\\", "\\")) / "steamapps" / f"appmanifest_{SAS_ZA4_APP_ID}.acf"
                            if p_path.exists():
                                is_game_installed = True
                                break
                    except Exception:
                        pass
            
            if not is_game_installed:
                raise GameNotFoundError(
                    f"SAS:ZA4 is not installed on this computer (Steam App ID {SAS_ZA4_APP_ID} missing)."
                )
            else:
                raise SaveNotFoundError(
                    f"SAS:ZA4 is installed, but no save data folder exists for Steam account {steam_id}. "
                    "Please launch the game at least once on this account to generate save files."
                )

        docs_path: Path = userdata_app_path / "local" / "Data" / "Docs"

        if not docs_path.exists() or not docs_path.is_dir():
            raise SaveNotFoundError(
                f"SAS:ZA4 userdata Docs directory not found at: {docs_path}. "
                "Please launch the game at least once on this account."
            )

        profile_save_direct: Path = docs_path / "Profile.save"
        if profile_save_direct.is_file():
            return profile_save_direct

        try:
            candidates = (
                d / "Profile.save"
                for d in docs_path.iterdir()
                if d.is_dir() and HEX_FOLDER_REGEX.match(d.name)
            )
            for candidate in candidates:
                if candidate.is_file():
                    return candidate
        except OSError as e:
            raise ResolveError(f"Failed to read directory {docs_path}: {e}") from e

        raise SaveNotFoundError(
            f"Profile.save file not found in {docs_path} or any of its hex-named subdirectories."
        )


save_path: Final[SaveResolver] = SaveResolver()
