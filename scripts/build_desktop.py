from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build" / "pyinstaller"
APP_NAME = "Tributary Area Tool"


def data_spec(source: Path, target: str) -> str:
    separator = ";" if sys.platform == "win32" else ":"
    return f"{source}{separator}{target}"


def main() -> int:
    try:
        import PyInstaller.__main__
    except ImportError as exc:
        raise SystemExit("Install build dependencies first: pip install -r requirements-build.txt") from exc

    shutil.rmtree(DIST_DIR / APP_NAME, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    args = [
        str(ROOT_DIR / "desktop_app.py"),
        "--name",
        APP_NAME,
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
        "--add-data",
        data_spec(ROOT_DIR / "app" / "templates", "app/templates"),
        "--add-data",
        data_spec(ROOT_DIR / "app" / "static", "app/static"),
        "--add-data",
        data_spec(ROOT_DIR / "app" / "engine" / "legacy", "app/engine/legacy"),
        "--add-data",
        data_spec(ROOT_DIR / "demo", "demo"),
        "--collect-all",
        "openpyxl",
        "--collect-all",
        "pandas",
        "--collect-all",
        "numpy",
        "--collect-all",
        "matplotlib",
        "--collect-all",
        "shapely",
        "--collect-all",
        "ezdxf",
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.lifespan.on",
    ]

    PyInstaller.__main__.run(args)
    print(f"Desktop bundle created at: {DIST_DIR / APP_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
