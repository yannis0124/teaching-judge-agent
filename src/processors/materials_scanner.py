from __future__ import annotations

from pathlib import Path

from src.schemas.evidence_schema import CandidateMaterials


APPLICATION_FORM_NAMES = [
    "application_form.docx",
    "application_form.pdf",
    "application.docx",
    "application.pdf",
    "case_design.docx",
    "case_design.pdf",
    "申报表.docx",
    "申报表.pdf",
    "案例整体设计.docx",
    "案例整体设计.pdf",
    "参赛申报表.docx",
    "参赛申报表.pdf",
]

LESSON_PLAN_NAMES = [
    "lesson_plan.docx",
    "lesson_plan.pdf",
    "teaching_plan.docx",
    "teaching_plan.pdf",
    "教案.docx",
    "教案.pdf",
    "教学设计.docx",
    "教学设计.pdf",
]

COURSEWARE_NAMES = [
    "slides.pptx",
    "slides.html",
    "slides.htm",
]


def scan_materials(materials_dir: Path, candidate: str | None = None) -> list[CandidateMaterials]:
    if not materials_dir.exists():
        raise FileNotFoundError(f"材料目录不存在：{materials_dir}")

    candidate_dirs = [materials_dir / candidate] if candidate else [
        path for path in sorted(materials_dir.iterdir()) if path.is_dir()
    ]
    results: list[CandidateMaterials] = []
    for candidate_dir in candidate_dirs:
        if not candidate_dir.exists() or not candidate_dir.is_dir():
            results.append(
                CandidateMaterials(
                    candidate_id=candidate_dir.name,
                    candidate_dir=candidate_dir,
                    video_path=None,
                    ppt_path=None,
                    srt_path=None,
                    application_form_path=None,
                    lesson_plan_path=None,
                    ambiguous_documents={},
                    missing=["video", "courseware", "transcript.srt"],
                    notes=[f"选手目录不存在：{candidate_dir}"],
                    courseware_paths=[],
                )
            )
            continue

        video_path = _find_video(candidate_dir)
        courseware_paths = _find_coursewares(candidate_dir)
        ppt_path = courseware_paths[0] if courseware_paths else None
        srt_path = candidate_dir / "transcript.srt"
        application_form_path, application_ambiguous = _find_document(candidate_dir, APPLICATION_FORM_NAMES)
        lesson_plan_path, lesson_ambiguous = _find_document(candidate_dir, LESSON_PLAN_NAMES)
        missing: list[str] = []
        notes: list[str] = []
        ambiguous_documents: dict[str, list[str]] = {}
        if video_path is None:
            missing.append("video")
            notes.append("缺少video.mp4或videos.mp4，不能生成正式现场展示评分。")
        if ppt_path is None:
            missing.append("courseware")
            notes.append("缺少slides.pptx或slides.html，课件页码证据不足。")
        if not srt_path.exists():
            srt_path = None
            missing.append("transcript.srt")
            notes.append("缺少transcript.srt，无法进行完整评审。")
        if application_form_path is None:
            missing.append("application_form")
            notes.append("缺少申报表/案例整体设计材料，不评价案例整体设计20分。")
        if lesson_plan_path is None:
            missing.append("lesson_plan")
            notes.append("缺少教案材料，不评价教案20分。")
        if application_ambiguous:
            ambiguous_documents["application_form"] = [str(path) for path in application_ambiguous]
            notes.append("检测到多个申报表候选文件，已按优先级选择，建议人工确认。")
        if lesson_ambiguous:
            ambiguous_documents["lesson_plan"] = [str(path) for path in lesson_ambiguous]
            notes.append("检测到多个教案候选文件，已按优先级选择，建议人工确认。")

        results.append(
            CandidateMaterials(
                candidate_id=candidate_dir.name,
                candidate_dir=candidate_dir,
                video_path=video_path,
                ppt_path=ppt_path,
                srt_path=srt_path,
                application_form_path=application_form_path,
                lesson_plan_path=lesson_plan_path,
                ambiguous_documents=ambiguous_documents,
                courseware_paths=courseware_paths,
                missing=missing,
                notes=notes,
            )
        )
    return results


def _find_video(candidate_dir: Path) -> Path | None:
    for name in ("video.mp4", "videos.mp4"):
        path = candidate_dir / name
        if path.exists():
            return path
    return None


def _find_coursewares(candidate_dir: Path) -> list[Path]:
    existing = {path.name.lower(): path for path in candidate_dir.iterdir() if path.is_file()}
    selected: list[Path] = []
    seen: set[Path] = set()
    for name in COURSEWARE_NAMES:
        path = existing.get(name.lower())
        if path is not None:
            selected.append(path)
            seen.add(path)
    for path in sorted(candidate_dir.glob("slides_*")):
        if path.is_file() and path.suffix.lower() in {".pptx", ".html", ".htm"} and path not in seen:
            selected.append(path)
    return selected


def _find_document(candidate_dir: Path, preferred_names: list[str]) -> tuple[Path | None, list[Path]]:
    existing = {path.name.lower(): path for path in candidate_dir.iterdir() if path.is_file()}
    matches: list[Path] = []
    for name in preferred_names:
        path = existing.get(name.lower())
        if path is not None:
            matches.append(path)
    selected = matches[0] if matches else None
    ambiguous = matches[1:] if len(matches) > 1 else []
    return selected, ambiguous
