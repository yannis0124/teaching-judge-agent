from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from frontend.utils.file_utils import outputs_dir


AGENT_FILES = [
    "case_goal_agent.json",
    "case_overview_implementation_agent.json",
    "case_feature_innovation_agent.json",
    "case_material_norm_agent.json",
    "lesson_elements_agent.json",
    "lesson_ideology_culture_agent.json",
    "lesson_student_objectives_agent.json",
    "lesson_content_strategy_agent.json",
    "lesson_evaluation_reflection_agent.json",
    "moral_culture.json",
    "vocational_feature.json",
    "aesthetic_education.json",
    "teaching_quality.json",
    "ai_application.json",
    "teacher_quality.json",
    "final_judgement.json",
    "overall_review.json",
]


def list_candidates(root: Path | None = None) -> list[str]:
    base = outputs_dir(root)
    if not base.exists():
        return []
    return sorted(path.name for path in base.iterdir() if path.is_dir())


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "文件不存在"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def read_excel(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    if not path.exists():
        return None, "文件不存在"
    try:
        return pd.read_excel(path), None
    except Exception as exc:
        return None, str(exc)


def read_workbook_sheets(path: Path) -> tuple[dict[str, pd.DataFrame], str | None]:
    if not path.exists():
        return {}, "文件不存在"
    try:
        return pd.read_excel(path, sheet_name=None), None
    except Exception as exc:
        return {}, str(exc)


def load_summary(root: Path | None = None) -> tuple[pd.DataFrame | None, str | None]:
    return read_excel(outputs_dir(root) / "summary_ranking.xlsx")


def load_agent_outputs(candidate_id: str, root: Path | None = None) -> dict[str, tuple[dict | None, str | None]]:
    base = outputs_dir(root) / candidate_id / "agents"
    return {name: read_json(base / name) for name in AGENT_FILES}


def status_from_row(row: dict) -> str:
    total = row.get("available_total_score", row.get("现场展示60分建议", row.get("total_score", "")))
    manual_count = row.get("manual_review_count", row.get("需要人工复核数量", 0))
    try:
        manual_count_number = int(manual_count)
    except Exception:
        manual_count_number = 0
    if total in ("", None) or pd.isna(total):
        return "unscored"
    if manual_count_number > 0:
        return "needs_review"
    return "scored"


def normalize_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    normalized = df.copy()
    normalized["状态"] = [status_from_row(row) for row in normalized.to_dict("records")]
    return normalized
