class SAS_ZA4ToolError(Exception):
    """Base exception for the SAS:ZA4Tool application."""


class CryptError(SAS_ZA4ToolError):
    """Raised for cryptography and decoding failures."""


class ResolveError(SAS_ZA4ToolError):
    """Base exception for save path resolution errors."""


class GameNotFoundError(ResolveError):
    """Raised when the game installation or Steam path cannot be resolved."""


class SaveNotFoundError(ResolveError):
    """Raised when the Profile.save file cannot be found."""


class SaveError(SAS_ZA4ToolError):
    """Base exception for save file editing and parsing errors."""


class ProfileNotFoundError(SaveError):
    """Raised when a character profile does not exist or is not loaded."""


class CancelError(SAS_ZA4ToolError):
    """Raised when the user cancels an input prompt."""
