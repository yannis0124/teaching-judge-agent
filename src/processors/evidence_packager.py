from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.schemas.evidence_schema import CandidateMaterials


def build_evidence_package(
    materials: CandidateMaterials,
    application_form: dict,
    lesson_plan: dict,
    speech: dict,
    visual: dict,
    ppt: dict,
    output_dir: Path,
    transcription_status: dict | None = None,
) -> dict:
    evidence_dir = output_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    package = {
        "candidate_id": materials.candidate_id,
        "scoring_scope": "支持案例整体设计20分、教案20分、现场教学展示60分；材料缺失模块不评分、不计0分。",
        "materials": materials.to_dict(),
        "material_integrity": _legacy_material_integrity(materials),
        "material_completeness": _material_completeness(materials, application_form, lesson_plan, transcription_status),
        "application_form_evidence": application_form,
        "lesson_plan_evidence": lesson_plan,
        "transcription_status": transcription_status or {
            "auto_transcribe_enabled": False,
            "transcript_exists_before_run": materials.srt_path is not None,
            "transcript_generated": False,
            "transcript_path": str(materials.candidate_dir / "transcript.srt"),
            "model": None,
            "error": None,
            "message": "已发现 transcript.srt，直接读取现有字幕稿。" if materials.srt_path is not None else "未提供 transcript.srt，无法进行完整评审。",
        },
        "live_teaching_evidence": {
            "speech_evidence": speech,
            "visual_evidence": visual,
            "ppt_evidence": ppt,
            "transcription_status": transcription_status or {},
        },
        "speech_evidence": speech,
        "visual_evidence": visual,
        "ppt_evidence": ppt,
        "evidence_rules": {
            "keyframe_boundary": "视频关键帧只作为画面辅助证据，不得用单帧推断整堂课整体状态。",
            "missing_srt": "缺少transcript.srt时，不得虚构语音证据，现场展示模块不得评分。",
            "missing_ppt": "缺少slides.pptx或slides.html时，不得虚构课件页码证据。",
            "ppt_image_failure": "课件页面截图未生成时，视觉证据不足，需要人工复核。",
        },
    }
    write_json(evidence_dir / "evidence_package.json", package)
    _write_evidence_workbooks(evidence_dir, package)
    return package


def _legacy_material_integrity(materials: CandidateMaterials) -> dict:
    return {
        "has_application_form": materials.application_form_path is not None,
        "has_lesson_plan": materials.lesson_plan_path is not None,
        "has_video": materials.video_path is not None,
        "has_srt": materials.srt_path is not None,
        "has_ppt": bool(materials.courseware_paths or materials.ppt_path),
        "missing": materials.missing,
        "notes": materials.notes,
        "ambiguous_documents": materials.ambiguous_documents or {},
    }


def _material_completeness(
    materials: CandidateMaterials,
    application_form: dict,
    lesson_plan: dict,
    transcription_status: dict | None,
) -> dict:
    app_status = _document_material_status(application_form)
    lesson_status = _document_material_status(lesson_plan)
    video_status = "present" if materials.video_path else "missing"
    ppt_status = "present" if materials.courseware_paths or materials.ppt_path else "missing"
    transcript_status = "present" if materials.srt_path else "missing"
    can_case = app_status == "present"
    can_lesson = lesson_status == "present"
    can_live = video_status == "present" and transcript_status == "present"
    available = (20 if can_case else 0) + (20 if can_lesson else 0) + (60 if can_live else 0)
    return {
        "application_form": app_status,
        "lesson_plan": lesson_status,
        "video": video_status,
        "ppt": ppt_status,
        "transcript": transcript_status,
        "can_score_case_design_20": can_case,
        "can_score_lesson_plan_20": can_lesson,
        "can_score_live_teaching_60": can_live,
        "can_score_total_100": can_case and can_lesson and can_live,
        "available_max_score": available,
    }


def _document_material_status(document: dict) -> str:
    if not document.get("exists"):
        return "missing"
    if document.get("extraction_status") != "success":
        return "parse_failed"
    return "present"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_evidence_workbooks(evidence_dir: Path, package: dict) -> None:
    _write_xlsx(
        evidence_dir / "speech_evidence.xlsx",
        ["index", "start", "end", "tags", "text"],
        [
            {
                "index": item.get("index"),
                "start": item.get("start"),
                "end": item.get("end"),
                "tags": ",".join(item.get("tags", [])),
                "text": item.get("text"),
            }
            for item in package["speech_evidence"].get("entries", [])
        ],
        empty_note=package["speech_evidence"].get("status", "无语音证据。"),
    )
    _write_xlsx(
        evidence_dir / "visual_evidence.xlsx",
        ["timestamp", "seconds", "reason", "image_path"],
        package["visual_evidence"].get("frames", []),
        empty_note=package["visual_evidence"].get("status", "无画面证据。"),
    )
    _write_xlsx(
        evidence_dir / "ppt_evidence.xlsx",
        ["page", "tags", "text", "image_path"],
        [
            {
                "page": item.get("page"),
                "tags": ",".join(item.get("tags", [])),
                "text": item.get("text"),
                "image_path": item.get("image_path"),
            }
            for item in package["ppt_evidence"].get("slides", [])
        ],
        empty_note=package["ppt_evidence"].get("status", "无PPT证据。"),
    )
    _write_document_evidence_xlsx(
        evidence_dir / "application_form_evidence.xlsx",
        package["application_form_evidence"],
    )
    _write_document_evidence_xlsx(
        evidence_dir / "lesson_plan_evidence.xlsx",
        package["lesson_plan_evidence"],
    )
    timeline_rows = []
    for item in package["speech_evidence"].get("entries", []):
        timeline_rows.append(
            {
                "type": "speech",
                "time": item.get("start"),
                "source": "SRT",
                "summary": item.get("text"),
            }
        )
    for item in package["visual_evidence"].get("frames", []):
        timeline_rows.append(
            {
                "type": "keyframe",
                "time": item.get("timestamp"),
                "source": item.get("image_path"),
                "summary": item.get("reason"),
            }
        )
    _write_xlsx(
        evidence_dir / "timeline_evidence.xlsx",
        ["type", "time", "source", "summary"],
        sorted(timeline_rows, key=lambda row: row.get("time") or ""),
        empty_note="无时间轴证据。",
    )


def _write_document_evidence_xlsx(path: Path, document: dict) -> None:
    rows = []
    sections = document.get("section_candidates", {}) or {}
    for section, excerpts in sections.items():
        for excerpt in excerpts:
            rows.append(
                {
                    "document_type": document.get("document_type"),
                    "file_name": document.get("file_name"),
                    "section": section,
                    "excerpt": excerpt,
                    "extraction_status": document.get("extraction_status"),
                    "evidence_sufficiency": document.get("evidence_sufficiency"),
                }
            )
    if not rows and document.get("exists"):
        rows.append(
            {
                "document_type": document.get("document_type"),
                "file_name": document.get("file_name"),
                "section": "",
                "excerpt": (document.get("extracted_text") or document.get("tables_text") or "")[:1000],
                "extraction_status": document.get("extraction_status"),
                "evidence_sufficiency": document.get("evidence_sufficiency"),
            }
        )
    _write_xlsx(
        path,
        ["document_type", "file_name", "section", "excerpt", "extraction_status", "evidence_sufficiency"],
        rows,
        empty_note="文档材料缺失或无可提取证据。",
    )


def _write_xlsx(path: Path, headers: list[str], rows: list[dict], empty_note: str) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError as exc:
        raise RuntimeError("缺少openpyxl依赖，请先安装requirements.txt。") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "evidence"
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    if rows:
        for row in rows:
            sheet.append([_safe_excel_value(row.get(header, "")) for header in headers])
    else:
        sheet.append([_safe_excel_value(empty_note)] + [""] * (len(headers) - 1))
    for column_cells in sheet.columns:
        max_len = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 60)
        for cell in column_cells:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _safe_excel_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]", "", value)
    return value
