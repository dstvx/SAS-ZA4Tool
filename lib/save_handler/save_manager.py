"""
Global Save Manager.
Provides a singleton-like interface to the active SaveSession.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from .session import SaveSession, SaveError

# Global internal session
_session: SaveSession | None = None

def get_session(force_reload: bool = False) -> SaveSession:
    """Gets the active SaveSession, creating it if it doesn't exist."""
    global _session
    
    active_path = SaveSession.resolve_active_path()
    if not active_path:
        raise SaveError("No active save path configured.")

    if _session is None or _session.path != active_path or force_reload:
        _session = SaveSession.open_active()
    
    return _session

def get_data(file_path: str | Path, force_reload: bool = False) -> dict[str, Any]:
    """Compatibility wrapper for retrieving raw save data."""
    # We ignore file_path if it matches the active path for efficiency, 
    # but use it if requested for a specific file.
    path = Path(file_path)
    active_path = SaveSession.resolve_active_path()
    
    if path == active_path:
        return get_session(force_reload).data
    
    # Otherwise, open a temporary session for that specific file
    return SaveSession.from_file(path).data

def save_recorded_data(file_path: str | Path, data: dict[str, Any] | None = None) -> None:
    """Compatibility wrapper for saving data."""
    path = Path(file_path)
    active_path = SaveSession.resolve_active_path()
    
    if path == active_path and data is None:
        get_session().commit()
        return

    # If data is provided manually, we perform a manual encode
    from .dgdata import encode_to_file
    import json
    
    target = data if data is not None else get_session().data
    compact = json.dumps(target, separators=(",", ":"))
    encode_to_file(compact, str(path))
    
    # If the file being saved is the active one, refresh the session
    if path == active_path:
        get_session(force_reload=True)

def resolve_active_save_path() -> Path | None:
    """Exposes the path resolution logic."""
    return SaveSession.resolve_active_path()

def invalidate_cache() -> None:
    """Clears the global session."""
    global _session
    _session = None
