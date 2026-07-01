from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CandidateMaterials:
    candidate_id: str
    candidate_dir: Path
    video_path: Path | None
    ppt_path: Path | None
    srt_path: Path | None
    missing: list[str]
    notes: list[str]
    application_form_path: Path | None = None
    lesson_plan_path: Path | None = None
    ambiguous_documents: dict[str, list[str]] | None = None
    courseware_paths: list[Path] | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["candidate_dir"] = str(self.candidate_dir)
        data["video_path"] = str(self.video_path) if self.video_path else None
        data["ppt_path"] = str(self.ppt_path) if self.ppt_path else None
        data["courseware_paths"] = [str(path) for path in self.courseware_paths or []]
        data["srt_path"] = str(self.srt_path) if self.srt_path else None
        data["application_form_path"] = str(self.application_form_path) if self.application_form_path else None
        data["lesson_plan_path"] = str(self.lesson_plan_path) if self.lesson_plan_path else None
        return data


@dataclass
class SrtEntry:
    index: int
    start: str
    end: str
    start_seconds: float
    end_seconds: float
    text: str
    tags: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KeyframeEvidence:
    timestamp: str
    seconds: float
    image_path: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PptSlideEvidence:
    page: int
    text: str
    tags: list[str]
    image_path: str | None

    def to_dict(self) -> dict:
        return asdict(self)
