import logging
from pathlib import Path
from typing import Final

from lib.config import config

logger: Final[logging.Logger] = logging.getLogger("sas_za4tool")


def setup_logger() -> None:
    """Configures the logger handlers and levels based on settings."""
    logger.handlers.clear()
    
    if getattr(config, "logs_enabled", False):
        from lib.config.config import PROJECT_ROOT
        log_file: Path = PROJECT_ROOT / "sas_za4tool.log"
        handler: logging.FileHandler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    else:
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL)
