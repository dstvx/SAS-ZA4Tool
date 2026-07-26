from typing import Tuple, Final
import urllib.request
import json

VERSION: Final[str] = "1.0.2"


def check_for_updates() -> Tuple[bool, str]:
    """Checks if a newer version of the tool is available.

    Returns:
        Tuple[bool, str]: A tuple where the first element indicates if an update is
            available, and the second element is the latest version string.
    """
    url: str = "https://api.github.com/repos/dstvx/SAS-ZA4Tool/releases/latest"
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            latest_version = data.get("tag_name", "").strip().lstrip("v")
            if latest_version:
                current_parts = [int(x) for x in VERSION.split(".")]
                latest_parts = [int(x) for x in latest_version.split(".")]
                if latest_parts > current_parts:
                    return True, latest_version
    except Exception:
        pass
    return False, VERSION
