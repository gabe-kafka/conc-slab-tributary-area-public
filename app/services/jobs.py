from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from app.desktop_runtime import worker_subprocess_command


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    id: str
    session_id: str
    draft_id: str
    input_filename: str
    source_units: str
    layer_mapping: Dict[str, list[str]]
    status: str = "queued"
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    workspace: str = ""
    warnings: list[str] = field(default_factory=list)
    error_message: str = ""
    logs: list[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


class JobManager:
    def __init__(self, base_dir: Path, engine_dir: Path):
        self.base_dir = base_dir
        self.engine_dir = engine_dir
        self.drafts_dir = base_dir / "drafts"
        self.jobs_dir = base_dir / "jobs"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._drafts: Dict[str, Dict] = {}
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run_worker, name="job-worker", daemon=True)
        self._worker.start()

    def register_draft(self, draft) -> None:
        with self._lock:
            self._drafts[draft.id] = draft

    def get_draft(self, draft_id: str):
        with self._lock:
            return self._drafts.get(draft_id)

    def create_job(self, session_id: str, draft_id: str, source_units: str, layer_mapping: Dict[str, list[str]]) -> JobRecord:
        with self._lock:
            draft = self._drafts[draft_id]
            job_id = uuid.uuid4().hex
            workspace = self.jobs_dir / job_id
            workspace.mkdir(parents=True, exist_ok=True)

            record = JobRecord(
                id=job_id,
                session_id=session_id,
                draft_id=draft_id,
                input_filename=draft.filename,
                source_units=source_units,
                layer_mapping=layer_mapping,
                workspace=str(workspace),
            )
            self._jobs[job_id] = record
            self._queue.put(job_id)
            return record

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def _set_job(self, job_id: str, **changes) -> None:
        with self._lock:
            record = self._jobs[job_id]
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = _utc_now()

    def _append_logs(self, job_id: str, text: str) -> None:
        if not text:
            return
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        with self._lock:
            self._jobs[job_id].logs.extend(lines)
            self._jobs[job_id].updated_at = _utc_now()

    def _run_script(self, job_id: str, script_path: Path, workspace: Path) -> int:
        self._append_logs(job_id, f"[stage] starting {script_path.name}")
        command = worker_subprocess_command(script_path.name, workspace)
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        process = subprocess.Popen(
            command,
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            self._append_logs(job_id, line)

        return process.wait()

    def _run_worker(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._process(job_id)
            finally:
                self._queue.task_done()

    def _process(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            draft = self._drafts[record.draft_id]
        self._set_job(job_id, status="running")

        workspace = Path(record.workspace)
        input_path = workspace / "INPUT.DXF"
        shutil.copy2(draft.path, input_path)

        config = {"layers": record.layer_mapping, "source_units": record.source_units}
        (workspace / "job_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

        scripts = ["extract_dxf_data.py", "tributary.py"]
        for script_name in scripts:
            script_path = self.engine_dir / script_name
            returncode = self._run_script(job_id, script_path, workspace)
            if returncode != 0:
                combined = "\n".join(self.get_job(job_id).logs)
                status = "needs_review" if "NeedsReviewError" in combined else "failed"
                self._set_job(job_id, status=status, error_message=combined.strip()[-4000:])
                return

        artifacts = {}
        dxf_artifact = workspace / "tributary_output_fixed.dxf"
        xlsx_artifact = workspace / "column_load_takedown.xlsx"
        geometry_artifact = workspace / "geometry.json"
        if dxf_artifact.exists():
            artifacts["tributary_output.dxf"] = str(dxf_artifact)
        if xlsx_artifact.exists():
            artifacts["column_load_takedown.xlsx"] = str(xlsx_artifact)
        if geometry_artifact.exists():
            artifacts["geometry.json"] = str(geometry_artifact)

        warnings = [line for line in self.get_job(job_id).logs if "warning" in line.lower()]
        self._set_job(job_id, status="completed", artifacts=artifacts, warnings=warnings)
