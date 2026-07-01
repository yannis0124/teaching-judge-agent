from __future__ import annotations

from pathlib import Path


def write_score_workbook(
    output_path: Path,
    candidate_id: str,
    agent_results: dict | None,
    material_note: str | None = None,
    evidence_package: dict | None = None,
) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError as exc:
        raise RuntimeError("缺少openpyxl依赖，请先安装requirements.txt。") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "score"
    headers = [
        "candidate_id",
        "section",
        "indicator_name",
        "max_score",
        "suggested_score",
        "evidence_sufficiency",
        "document_evidence",
        "timestamp_evidence",
        "ppt_page_evidence",
        "keyframe_evidence",
        "strengths",
        "deduction_reasons",
        "manual_review_points",
    ]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    if not agent_results:
        sheet.append([candidate_id, "", "材料不足", "", "", "不足", "", "", "", "", "", material_note or "", material_note or ""])
    else:
        for item in agent_results.get("scoring_results", {}).values():
            sheet.append(
                [
                    candidate_id,
                    item.get("section", ""),
                    item.get("indicator_name", ""),
                    item.get("max_score", ""),
                    item.get("suggested_score", ""),
                    item.get("evidence_sufficiency", ""),
                    _join(item.get("document_evidence", [])),
                    _join(item.get("timestamp_evidence", [])),
                    _join(item.get("ppt_page_evidence", [])),
                    _join(item.get("keyframe_evidence", [])),
                    _join(item.get("strengths", [])),
                    _join(item.get("deduction_reasons", [])),
                    _join(item.get("manual_review_points", [])),
                ]
            )
    if evidence_package is not None:
        _add_material_status_sheet(workbook, evidence_package)
    _fit_sheet(sheet)
    for extra_sheet in workbook.worksheets[1:]:
        _fit_sheet(extra_sheet)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def _add_material_status_sheet(workbook, evidence_package: dict) -> None:
    sheet = workbook.create_sheet("material_status")
    completeness = evidence_package.get("material_completeness", {})
    transcription = evidence_package.get("transcription_status", {})
    rows = [
        ("application_form", completeness.get("application_form")),
        ("lesson_plan", completeness.get("lesson_plan")),
        ("video", completeness.get("video")),
        ("ppt", completeness.get("ppt")),
        ("transcript", completeness.get("transcript")),
        ("can_score_case_design_20", completeness.get("can_score_case_design_20")),
        ("can_score_lesson_plan_20", completeness.get("can_score_lesson_plan_20")),
        ("can_score_live_teaching_60", completeness.get("can_score_live_teaching_60")),
        ("can_score_total_100", completeness.get("can_score_total_100")),
        ("available_max_score", completeness.get("available_max_score")),
        ("transcript_path", transcription.get("transcript_path")),
        ("transcript_message", transcription.get("message")),
    ]
    sheet.append(["字段", "值"])
    for key, value in rows:
        sheet.append([key, "" if value is None else str(value)])


def _fit_sheet(sheet) -> None:
    from openpyxl.styles import Alignment

    for column_cells in sheet.columns:
        max_len = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 12), 55)
        for cell in column_cells:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def _join(value: list | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return "\n".join(_format_item(item) for item in value)


def _format_item(item) -> str:
    if isinstance(item, dict):
        return "；".join(f"{key}: {value}" for key, value in item.items())
    return str(item)
