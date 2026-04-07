"""Vercel Python Function: Synchronous DXF tributary area processing.

Downloads DXF from Blob, runs the full engine pipeline (extract → tributary),
uploads artifacts to Blob, returns geometry + artifact URLs.
"""

from __future__ import annotations

import io
import json
import os
import runpy
import shutil
import sys
import traceback
import uuid
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Add engine directory to Python path
ENGINE_DIR = str(Path(__file__).parent / "_engine")
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

from blob_utils import blob_delete, blob_download, blob_put  # noqa: E402

SCRIPTS = ["extract_dxf_data.py", "tributary.py"]


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(content_length)
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            body = json.loads(raw)

            blob_url = body["blob_url"]
            source_units = body.get("source_units", "in")
            layer_mapping = body["layer_mapping"]

            result = _process(blob_url, source_units, layer_mapping)
            self._json_response(200, result)

        except KeyError as e:
            self._json_response(400, {"status": "failed", "error_message": f"Missing field: {e}"})
        except Exception as e:
            self._json_response(500, {"status": "failed", "error_message": str(e)})

    def _json_response(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def _run_script(script_name: str, workspace: Path) -> tuple[list[str], str | None]:
    """Execute an engine script in-process using runpy, capturing stdout."""
    import multiprocessing

    script_path = os.path.join(ENGINE_DIR, script_name)
    saved_cwd = os.getcwd()
    captured = io.StringIO()

    # Redirect stdout to capture logs
    saved_stdout = sys.stdout
    sys.stdout = captured

    # Force single-threaded execution — ProcessPoolExecutor with fork
    # doesn't work inside Vercel Functions
    original_cpu_count = multiprocessing.cpu_count
    multiprocessing.cpu_count = lambda: 1

    try:
        os.chdir(workspace)
        runpy.run_path(script_path, run_name="__main__")
        logs = [line.rstrip() for line in captured.getvalue().splitlines() if line.strip()]
        return logs, None
    except Exception as e:
        logs = [line.rstrip() for line in captured.getvalue().splitlines() if line.strip()]
        error = f"{e}\n{traceback.format_exc()}"
        return logs, error
    finally:
        multiprocessing.cpu_count = original_cpu_count
        sys.stdout = saved_stdout
        os.chdir(saved_cwd)


def _process(blob_url: str, source_units: str, layer_mapping: dict) -> dict:
    """Run the full engine pipeline synchronously."""
    workspace = Path(f"/tmp/tributary-{uuid.uuid4().hex}")
    workspace.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Download DXF from Blob
        dxf_bytes = blob_download(blob_url)
        (workspace / "INPUT.DXF").write_bytes(dxf_bytes)

        # 2. Write job config
        config = {"layers": layer_mapping, "source_units": source_units}
        (workspace / "job_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

        # 3. Run engine scripts in-process
        all_logs: list[str] = []

        for script_name in SCRIPTS:
            logs, error = _run_script(script_name, workspace)
            all_logs.extend(logs)

            if error is not None:
                status = "needs_review" if "NeedsReviewError" in error else "failed"
                return {
                    "status": status,
                    "geometry": None,
                    "artifacts": {"dxf_url": None, "xlsx_url": None},
                    "logs": all_logs,
                    "warnings": [],
                    "error_message": error[-4000:],
                }

        # 4. Read geometry JSON (inline in response)
        geometry = None
        geometry_path = workspace / "geometry.json"
        if geometry_path.exists():
            geometry = json.loads(geometry_path.read_text(encoding="utf-8"))

        # 5. Upload artifacts to Blob
        artifacts = {"dxf_url": None, "xlsx_url": None}

        dxf_output = workspace / "tributary_output_fixed.dxf"
        if dxf_output.exists():
            blob_result = blob_put(
                "artifacts/tributary_output.dxf",
                dxf_output.read_bytes(),
                access="private",
                content_type="application/dxf",
            )
            artifacts["dxf_url"] = blob_result.get("downloadUrl") or blob_result["url"]

        xlsx_output = workspace / "column_load_takedown.xlsx"
        if xlsx_output.exists():
            blob_result = blob_put(
                "artifacts/column_load_takedown.xlsx",
                xlsx_output.read_bytes(),
                access="private",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            artifacts["xlsx_url"] = blob_result.get("downloadUrl") or blob_result["url"]

        # 6. Clean up input DXF blob
        try:
            blob_delete(blob_url)
        except Exception:
            pass  # Non-critical — blob cleanup failure is acceptable

        # 7. Extract warnings from logs
        warnings = [line for line in all_logs if "warning" in line.lower()]

        return {
            "status": "completed",
            "geometry": geometry,
            "artifacts": artifacts,
            "logs": all_logs,
            "warnings": warnings,
        }

    finally:
        shutil.rmtree(workspace, ignore_errors=True)
