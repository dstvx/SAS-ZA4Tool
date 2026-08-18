import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.config import config
from lib.crypt import decode_from_file, encode_to_file
from lib.utils.logger import logger


def select_file_dialog() -> str:
    """Opens a file picker dialog or falls back to console prompt if GUI unavailable.

    Returns:
        str: Selected absolute filepath, or empty string if cancelled.
    """
    try:
        from tkinter import TclError, Tk, filedialog

        root: Tk = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath: str = filedialog.askopenfilename(
            title="Select SAS:ZA4 Save or JSON File",
            filetypes=[("Save / JSON Files", "*.save;*.json"), ("All Files", "*.*")],
        )
        root.destroy()
        if filepath:
            return filepath
    except (ImportError, RuntimeError, AttributeError, OSError, TclError) as e:
        logger.info(f"GUI file picker unavailable ({e}), prompting via console.")

    from lib.exceptions import CancelError
    from lib.ui.ui import prompt_str

    try:
        return prompt_str(
            "Enter path to SAS:ZA4 .save or .json file", clear_screen=False
        )
    except CancelError:
        return ""


def create_backup(editor: Any = None) -> str:
    """Creates a timestamped copy of Profile.save and exports a decrypted Profile.json.

    Args:
        editor (Optional[Editor]): Optional editor instance holding decoded data.

    Returns:
        str: Message describing the result of the backup operation.
    """
    try:
        save_path: Path = Path(config.save_path)
        if not save_path.exists():
            return "Active save file does not exist."

        timestamp: str = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

        backup_dir: Path = (
            Path(__file__).resolve().parent.parent.parent / "backups" / timestamp
        )
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path: Path = backup_dir / "Profile.save"
        shutil.copy2(save_path, backup_path)

        export_dir: Path = (
            Path(__file__).resolve().parent.parent.parent / "exports" / timestamp
        )
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path: Path = export_dir / "Profile.json"

        # Use internal decoded copy from editor if available to avoid decoding overhead
        if editor is not None and hasattr(editor, "data"):
            data: Any = editor.data
        else:
            decoded_str: str = decode_from_file(str(save_path))
            data = json.loads(decoded_str)

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        logger.info(f"Created backup at {backup_path} and export at {export_path}")
        return f"Backup created in backups/{timestamp}/"
    except OSError as e:
        logger.error(f"Backup failed: {e}")
        return f"Backup failed: {e}"


def import_save_file(filepath: str, editor: Any = None) -> str:
    """Imports save data from a .save or .json file, validating it and backing up first.

    Args:
        filepath (str): Filepath of save or JSON file to import.
        editor (Optional[Editor]): Optional active Editor instance to update.

    Returns:
        str: Message describing the result of the import operation.
    """
    try:
        path: Path = Path(filepath)
        if not path.exists():
            return "Selected file does not exist."

        data: Any | None = None
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif path.suffix.lower() == ".save":
            decoded: str = decode_from_file(str(path))
            data = json.loads(decoded)
        else:
            return "Unsupported file extension. Must be .save or .json"

        if not isinstance(data, dict) or "Inventory" not in data:
            return "Invalid save file structure (missing 'Inventory' key)."

        backup_msg: str = create_backup(editor)
        if "failed" in backup_msg.lower():
            return f"Import aborted: Backup of old save failed. {backup_msg}"

        target_save_path: Path = Path(config.save_path)
        if editor is not None and hasattr(editor, "_save"):
            editor._save(data)
        elif path.suffix.lower() == ".save":
            shutil.copy2(path, target_save_path)
        else:
            json_str: str = json.dumps(data, separators=(",", ":"))
            encode_to_file(json_str, str(target_save_path))

        logger.info(f"Successfully imported save from {path}")
        return f"Save imported successfully! ({backup_msg})"
    except OSError as e:
        logger.error(f"Import failed: {e}")
        return f"Import failed: {e}"
