from __future__ import annotations

import argparse
import os
import runpy
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from app.runtime_paths import bundle_root, user_data_root


def worker_subprocess_command(script_name: str, workspace: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        return [
            sys.executable,
            "--worker-script",
            script_name,
            "--workspace",
            str(workspace),
        ]

    runtime_script = bundle_root() / "desktop_app.py"
    return [
        sys.executable,
        "-u",
        str(runtime_script),
        "--worker-script",
        script_name,
        "--workspace",
        str(workspace),
    ]


def run_worker_script(script_name: str, workspace: Path) -> int:
    script_path = bundle_root() / "app" / "engine" / "legacy" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Worker script not found: {script_path}")

    prior_cwd = Path.cwd()
    added_paths: list[str] = []
    try:
        os.chdir(workspace)
        for candidate in (str(script_path.parent), str(bundle_root())):
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
                added_paths.append(candidate)
        runpy.run_path(str(script_path), run_name="__main__")
        return 0
    finally:
        os.chdir(prior_cwd)
        for candidate in added_paths:
            if candidate in sys.path:
                sys.path.remove(candidate)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def configured_port() -> int:
    raw_value = os.getenv("TRIBUTARY_APP_PORT", "").strip()
    if not raw_value:
        return find_free_port()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"Invalid TRIBUTARY_APP_PORT: {raw_value}") from exc


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0):
                return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.25)
    return False


def launch_desktop_app() -> int:
    import tkinter as tk
    from tkinter import ttk

    import uvicorn

    from app.main import app

    port = configured_port()
    auto_open_browser = os.getenv("TRIBUTARY_APP_NO_BROWSER", "").strip().lower() not in {"1", "true", "yes"}
    url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, name="desktop-server", daemon=True)
    server_thread.start()

    if not wait_for_server(url):
        print("Desktop app failed to start local server.", file=sys.stderr)
        return 1

    root = tk.Tk()
    root.title("Two-Way Slab Tributary Area")
    root.geometry("520x250")
    root.minsize(460, 220)

    status_var = tk.StringVar(value="Desktop app running")
    url_var = tk.StringVar(value=url)
    data_dir_var = tk.StringVar(value=str(user_data_root()))

    frame = ttk.Frame(root, padding=18)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Two-Way Slab Tributary Area", font=("", 16, "bold")).pack(anchor="w")
    ttk.Label(
        frame,
        text="The tool is running locally. Keep this window open while employees use the app.",
        wraplength=460,
        justify="left",
    ).pack(anchor="w", pady=(10, 6))

    ttk.Label(frame, textvariable=status_var).pack(anchor="w")
    ttk.Label(frame, text="App URL:").pack(anchor="w", pady=(12, 0))
    ttk.Label(frame, textvariable=url_var).pack(anchor="w")
    ttk.Label(frame, text="Local data folder:").pack(anchor="w", pady=(12, 0))
    ttk.Label(frame, textvariable=data_dir_var, wraplength=460, justify="left").pack(anchor="w")

    button_row = ttk.Frame(frame)
    button_row.pack(anchor="w", pady=(18, 0))

    def open_app() -> None:
        webbrowser.open(url)

    def close_app() -> None:
        status_var.set("Shutting down...")
        server.should_exit = True
        root.after(150, root.destroy)

    ttk.Button(button_row, text="Open App", command=open_app).pack(side="left")
    ttk.Button(button_row, text="Quit", command=close_app).pack(side="left", padx=(10, 0))

    root.protocol("WM_DELETE_WINDOW", close_app)
    if auto_open_browser:
        root.after(250, open_app)
    root.mainloop()

    server.should_exit = True
    server_thread.join(timeout=10.0)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-script")
    parser.add_argument("--workspace")
    args = parser.parse_args(argv)

    if args.worker_script:
        if not args.workspace:
            parser.error("--workspace is required with --worker-script")
        try:
            return run_worker_script(args.worker_script, Path(args.workspace))
        except Exception:
            traceback.print_exc()
            return 1

    return launch_desktop_app()


if __name__ == "__main__":
    raise SystemExit(main())
