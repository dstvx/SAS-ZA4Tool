class SAS_ZA4ToolError(Exception):
    """Base exception for the SAS:ZA4Tool application."""
    pass


class CryptError(SAS_ZA4ToolError):
    """Raised for cryptography and decoding failures."""
    pass


class ResolveError(SAS_ZA4ToolError):
    """Base exception for save path resolution errors."""
    pass


class GameNotFoundError(ResolveError):
    """Raised when the game installation or Steam path cannot be resolved."""
    pass


class SaveNotFoundError(ResolveError):
    """Raised when the Profile.save file cannot be found."""
    pass


class SaveError(SAS_ZA4ToolError):
    """Base exception for save file editing and parsing errors."""
    pass


class ProfileNotFoundError(SaveError):
    """Raised when a character profile does not exist or is not loaded."""
    pass


class CancelError(SAS_ZA4ToolError):
    """Raised when the user cancels an input prompt."""
    pass
