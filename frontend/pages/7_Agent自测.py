from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.file_utils import candidate_output_dir
from frontend.utils.result_loader import list_candidates, read_json
from src.schemas.agent_output_schema import REQUIRED_SCORING_FIELDS
from src.schemas.scoring_schema import load_scoring_schema


LIST_FIELDS = [
    "document_evidence",
    "timestamp_evidence",
    "ppt_page_evidence",
    "keyframe_evidence",
    "strengths",
    "deduction_reasons",
    "manual_review_points",
]


st.set_page_config(page_title="Agent自测", layout="wide")
st.title("Agent自测")

candidates = list_candidates(ROOT)
if not candidates:
    st.info("暂未发现输出结果，请先运行评审。")
    st.stop()

candidate_id = st.selectbox("选择选手", candidates)
base = candidate_output_dir(candidate_id, ROOT)
schema = load_scoring_schema(ROOT / "docs" / "scoring_schema.yaml")


def _json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _is_half_step(value: float) -> bool:
    return abs(value * 2 - round(value * 2)) < 1e-9


def _check_status(errors: list[str], warnings: list[str]) -> str:
    if errors:
        return "失败"
    if warnings:
        return "警告"
    return "通过"


def _score_agent_check(indicator) -> dict[str, Any]:
    data, error = read_json(base / "agents" / indicator.agent_file)
    errors: list[str] = []
    warnings: list[str] = []
    if error:
        errors.append(f"无法读取JSON：{error}")
        return _row(indicator.agent_file, "评分Agent", errors, warnings)

    if data.get("format_error"):
        errors.append("Agent输出格式异常。")
    missing_fields = [field for field in REQUIRED_SCORING_FIELDS if field not in data]
    if missing_fields:
        errors.append(f"缺少字段：{', '.join(missing_fields)}")
    if data.get("section") not in ("", None, indicator.section):
        errors.append(f"section不匹配：期望 {indicator.section}，实际 {data.get('section')}")
    if data.get("indicator_id") not in ("", None, indicator.id):
        errors.append(f"indicator_id不匹配：期望 {indicator.id}，实际 {data.get('indicator_id')}")

    try:
        max_score = float(data.get("max_score"))
        if max_score != float(indicator.max_score):
            errors.append(f"max_score不匹配：期望 {indicator.max_score}，实际 {max_score}")
    except (TypeError, ValueError):
        errors.append("max_score不是数字。")

    score = data.get("suggested_score")
    if score in (None, ""):
        if data.get("status") == "not_scored":
            warnings.append("该Agent标记为未评分。")
        else:
            errors.append("suggested_score为空。")
    else:
        try:
            score_number = float(score)
            if score_number < 0 or score_number > float(indicator.max_score):
                errors.append(f"suggested_score超出范围：{score_number}")
            if not _is_half_step(score_number):
                errors.append(f"suggested_score不是0.5分制：{score_number}")
        except (TypeError, ValueError):
            errors.append("suggested_score不是数字。")

    for field in LIST_FIELDS:
        if field in data and not isinstance(data.get(field), list):
            errors.append(f"{field}应为列表。")
    if data.get("manual_review_points"):
        warnings.append("存在人工复核点。")

    return _row(indicator.agent_file, "评分Agent", errors, warnings)


def _review_agent_check(file_name: str, agent_type: str, required_fields: list[str]) -> dict[str, Any]:
    data, error = read_json(base / "evidence" / file_name)
    errors: list[str] = []
    warnings: list[str] = []
    if error:
        errors.append(f"无法读取JSON：{error}")
        return _row(file_name, agent_type, errors, warnings)

    if data.get("format_error"):
        errors.append("Agent输出格式异常。")
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        errors.append(f"缺少字段：{', '.join(missing_fields)}")
    if not isinstance(data.get("manual_review_points", []), list):
        errors.append("manual_review_points应为列表。")
    elif data.get("manual_review_points"):
        warnings.append("存在人工复核点。")
    return _row(file_name, agent_type, errors, warnings)


def _final_agent_check() -> dict[str, Any]:
    final, error = read_json(base / "agents" / "final_judgement.json")
    errors: list[str] = []
    warnings: list[str] = []
    if error:
        errors.append(f"无法读取JSON：{error}")
        return _row("final_judgement.json", "总控Agent", errors, warnings)

    if final.get("status") in {"missing_api_key", "material_missing"}:
        errors.append(f"总控Agent未完成正式评审：{final.get('status')}")
        return _row("final_judgement.json", "总控Agent", errors, warnings)

    required_fields = [
        "summary",
        "main_strengths",
        "main_problems",
        "missing_sections",
        "manual_review_points",
        "notes",
        "case_design_score_20",
        "lesson_plan_score_20",
        "live_teaching_score_60",
        "available_total_score",
        "available_max_score",
        "full_total_score_100",
        "can_score_total_100",
    ]
    missing_fields = [field for field in required_fields if field not in final]
    if missing_fields:
        errors.append(f"缺少字段：{', '.join(missing_fields)}")

    for field in ["main_strengths", "main_problems", "missing_sections", "manual_review_points"]:
        if field in final and not isinstance(final.get(field), list):
            errors.append(f"{field}应为列表。")

    section_scores = {
        "case_design": _sum_section("case_design"),
        "lesson_plan": _sum_section("lesson_plan"),
        "live_teaching": _sum_section("live_teaching"),
    }
    expected_available = sum(score for score in section_scores.values() if score is not None)
    actual_available = _as_float(final.get("available_total_score"))
    if actual_available is None:
        errors.append("available_total_score不是数字。")
    elif abs(actual_available - expected_available) > 1e-9:
        errors.append(f"available_total_score与分项合计不一致：期望 {expected_available}，实际 {actual_available}")

    _check_section_total(final, "case_design_score_20", section_scores["case_design"], errors)
    _check_section_total(final, "lesson_plan_score_20", section_scores["lesson_plan"], errors)
    _check_section_total(final, "live_teaching_score_60", section_scores["live_teaching"], errors)

    can_total = bool(final.get("can_score_total_100"))
    full_total = final.get("full_total_score_100")
    if can_total and _as_float(full_total) != actual_available:
        errors.append("可形成100分总评时，full_total_score_100应等于available_total_score。")
    if not can_total and full_total not in (None, ""):
        errors.append("材料不足时，full_total_score_100应为空。")
    if final.get("manual_review_points"):
        warnings.append("总控Agent提出人工复核点。")

    return _row("final_judgement.json", "总控Agent", errors, warnings)


def _sum_section(section: str) -> float | None:
    scores: list[float] = []
    for indicator in schema.indicators:
        if indicator.section != section:
            continue
        data, error = read_json(base / "agents" / indicator.agent_file)
        if error:
            return None
        score = data.get("suggested_score")
        if score in (None, ""):
            return None
        parsed = _as_float(score)
        if parsed is None:
            return None
        scores.append(parsed)
    return round(sum(scores) * 2) / 2


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check_section_total(final: dict, field: str, expected: float | None, errors: list[str]) -> None:
    actual = final.get(field)
    if expected is None:
        if actual not in (None, ""):
            errors.append(f"{field}应为空。")
        return
    actual_float = _as_float(actual)
    if actual_float is None or abs(actual_float - expected) > 1e-9:
        errors.append(f"{field}与分项合计不一致：期望 {expected}，实际 {actual}")


def _row(agent: str, agent_type: str, errors: list[str], warnings: list[str]) -> dict[str, str]:
    return {
        "Agent": agent,
        "类型": agent_type,
        "状态": _check_status(errors, warnings),
        "问题": "；".join(errors),
        "提醒": "；".join(warnings),
    }


rows = [_score_agent_check(indicator) for indicator in schema.indicators]
rows.append(_review_agent_check("consistency_review.json", "一致性复核Agent", ["summary", "consistency_issues", "score_adjustment_suggestions", "manual_review_points"]))
rows.append(_review_agent_check("bias_review.json", "偏差审查Agent", ["summary", "bias_risks", "score_adjustment_suggestions", "manual_review_points"]))
rows.append(_final_agent_check())

df = pd.DataFrame(rows)
fail_count = int((df["状态"] == "失败").sum())
warning_count = int((df["状态"] == "警告").sum())
pass_count = int((df["状态"] == "通过").sum())

col1, col2, col3 = st.columns(3)
col1.metric("通过", pass_count)
col2.metric("警告", warning_count)
col3.metric("失败", fail_count)

if fail_count:
    st.error("存在失败项，请优先查看总控Agent和缺失/格式异常的Agent。")
elif warning_count:
    st.warning("Agent结构正常，但存在人工复核点或未评分项。")
else:
    st.success("所有Agent自测通过。")

status_filter = st.radio("显示范围", ["全部", "失败", "警告", "通过"], horizontal=True)
view_df = df if status_filter == "全部" else df[df["状态"] == status_filter]
st.dataframe(view_df, use_container_width=True, hide_index=True)

with st.expander("总控Agent原始输出", expanded=False):
    final_data, final_error = read_json(base / "agents" / "final_judgement.json")
    if final_error:
        st.warning(final_error)
    else:
        st.json(final_data)

