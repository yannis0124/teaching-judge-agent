from __future__ import annotations

import re
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def materials_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "materials"


def outputs_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "outputs"


def sanitize_candidate_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", value.strip())
    return cleaned.upper()


def next_candidate_id(root: Path | None = None) -> str:
    base = materials_dir(root)
    existing = {path.name.upper() for path in base.iterdir() if path.is_dir()} if base.exists() else set()
    index = 1
    while True:
        candidate_id = f"A{index:02d}"
        if candidate_id not in existing:
            return candidate_id
        index += 1


def candidate_material_dir(candidate_id: str, root: Path | None = None) -> Path:
    return materials_dir(root) / candidate_id


def candidate_output_dir(candidate_id: str, root: Path | None = None) -> Path:
    return outputs_dir(root) / candidate_id


def save_uploaded_file(uploaded_file, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        output.write(uploaded_file.getbuffer())


def file_size_label(path: Path) -> str:
    if not path.exists():
        return "-"
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

