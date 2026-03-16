from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DATA_DIRNAME = "TributaryAreaTool"


def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def user_data_root() -> Path:
    override = os.getenv("TRIBUTARY_APP_DATA")
    if override:
        path = Path(override).expanduser().resolve()
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        path = base / APP_DATA_DIRNAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DATA_DIRNAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        path = base / APP_DATA_DIRNAME

    path.mkdir(parents=True, exist_ok=True)
    return path
