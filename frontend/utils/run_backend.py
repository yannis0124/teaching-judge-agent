from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run_candidate(candidate_id: str, root: Path) -> tuple[int, str]:
    command = [sys.executable, "app.py", "--candidate", candidate_id]
    env = os.environ.copy()
    process = subprocess.Popen(
        command,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        lines.append(line.rstrip())
    return_code = process.wait()
    return return_code, "\n".join(lines)
