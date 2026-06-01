from __future__ import annotations

import argparse
import os
import sys
from http.server import HTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"
API_DIR = WEB_DIR / "api"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def build_handler():
    sys.path.insert(0, str(API_DIR))

    from process import handler as ProcessHandler
    from upload import handler as UploadHandler

    class Dispatcher(UploadHandler, ProcessHandler):
        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/upload":
                return UploadHandler.do_POST(self)
            if path == "/api/process":
                return ProcessHandler.do_POST(self)
            return self._json_response(404, {"detail": f"Unknown API route: {path}"})

    return Dispatcher


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Vercel Python API handlers.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()

    load_env_file(WEB_DIR / ".env.local")
    handler = build_handler()
    server = HTTPServer((args.host, args.port), handler)
    print(f"API dispatcher ready at http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
