from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.file_utils import candidate_output_dir, file_size_label
from frontend.utils.result_loader import list_candidates, read_json, read_workbook_sheets


def _render_dimension(
    title: str,
    data: dict[str, Any],
    extra_fields: list[tuple[str, str]] | None = None,
    list_fields: list[tuple[str, str]] | None = None,
) -> None:
    st.markdown(f"### {title}")
    if not data:
        st.caption("暂无结构化内容。")
        return
    for label, field in extra_fields or []:
        st.markdown(f"**{label}**：{data.get(field, '')}")
    if data.get("summary"):
        st.write(data.get("summary"))
    fields = list_fields or [
        ("主要优势", "strengths"),
        ("主要不足", "weaknesses"),
        ("关键证据", "evidence"),
        ("优化建议", "improvement_suggestions"),
        ("人工复核点", "manual_review_points"),
    ]
    for label, field in fields:
        values = data.get(field, [])
        st.markdown(f"**{label}**")
        if not values:
            st.caption("暂无。")
            continue
        for value in values:
            st.markdown(f"- {_format_value(value)}")


def _format_value(value: Any) -> str:
    if isinstance(value, dict):
        return "；".join(f"{key}: {_format_value(item)}" for key, item in value.items())
    if isinstance(value, list):
        return "；".join(_format_value(item) for item in value)
    return str(value)


st.set_page_config(page_title="选手详情", layout="wide")
st.title("选手详情")

candidates = list_candidates(ROOT)
if not candidates:
    st.info("暂未发现 outputs/{candidate_id}/，请先运行评审。")
    st.stop()

candidate_id = st.selectbox("选择选手", candidates)
base = candidate_output_dir(candidate_id, ROOT)

evidence, evidence_error = read_json(base / "evidence" / "evidence_package.json")
final, final_error = read_json(base / "agents" / "final_judgement.json")
overall, overall_error = read_json(base / "agents" / "overall_review.json")
score_sheets, score_error = read_workbook_sheets(base / "score.xlsx")
score_df = score_sheets.get("score") if score_sheets else None

overview_tab, overall_tab, items_tab, files_tab = st.tabs(["总览", "整体性评价", "分项评价", "文件下载"])

with overview_tab:
    st.subheader("材料完整性")
    if evidence_error:
        st.warning(f"无法读取 evidence_package.json：{evidence_error}")
    else:
        integrity = evidence.get("material_integrity", {})
        transcription = evidence.get("transcription_status", {})
        ppt = evidence.get("ppt_evidence", {})
        visual = evidence.get("visual_evidence", {})
        cols = st.columns(5)
        completeness = evidence.get("material_completeness", {})
        cols[0].metric("申报表", completeness.get("application_form", "-"))
        cols[1].metric("教案", completeness.get("lesson_plan", "-"))
        cols[2].metric("现场视频", completeness.get("video", "-"))
        cols[3].metric("关键帧", "已生成" if visual.get("available") else "不足")
        cols[4].metric("可评审满分", completeness.get("available_max_score", 0))
        st.write("字幕状态：", transcription.get("message", ""))
        st.write("PPT截图：", ppt.get("image_status", ""))
        if integrity.get("notes"):
            st.warning("；".join(integrity.get("notes", [])))

    st.subheader("评分汇总")
    if final_error:
        st.warning(f"无法读取 final_judgement.json：{final_error}")
    else:
        cols = st.columns(5)
        cols[0].metric("案例20", final.get("case_design_score_20"))
        cols[1].metric("教案20", final.get("lesson_plan_score_20"))
        cols[2].metric("现场60", final.get("live_teaching_score_60"))
        cols[3].metric("已评/可评", f"{final.get('available_total_score', '')}/{final.get('available_max_score', '')}")
        cols[4].metric("100分总评", final.get("full_total_score_100") if final.get("can_score_total_100") else "材料不足")
        with st.expander("总控Agent JSON", expanded=False):
            st.json(final)

    if score_error:
        st.warning(f"无法读取 score.xlsx：{score_error}")
    elif score_df is not None:
        st.dataframe(score_df, use_container_width=True, hide_index=True)

with overall_tab:
    if overall_error:
        st.info(f"暂未读取到整体性评价：{overall_error}")
    else:
        st.subheader("整体摘要")
        st.write(overall.get("overall_summary", ""))
        dimensions = overall.get("dimensions", {})
        _render_dimension("“三进”融合深度", dimensions.get("three_entries_integration", {}))
        _render_dimension("AI应用有效度", dimensions.get("ai_application_effectiveness", {}), extra_fields=[("AI应用类型", "application_type")])
        _render_dimension(
            "材料一致性",
            dimensions.get("material_consistency", {}),
            list_fields=[
                ("一致之处", "consistent_points"),
                ("断点或不足", "inconsistent_points"),
                ("关键证据", "evidence"),
                ("优化建议", "improvement_suggestions"),
                ("人工复核点", "manual_review_points"),
            ],
        )
        _render_dimension("职业教育类型特色", dimensions.get("vocational_education_characteristics", {}))
        _render_dimension("美育与文化表达质量", dimensions.get("aesthetic_and_cultural_expression", {}))
        _render_dimension(
            "教学闭环完整度",
            dimensions.get("teaching_closure", {}),
            list_fields=[
                ("已形成的闭环", "completed_links"),
                ("薄弱环节", "missing_or_weak_links"),
                ("关键证据", "evidence"),
                ("优化建议", "improvement_suggestions"),
                ("人工复核点", "manual_review_points"),
            ],
        )
        _render_dimension(
            "证据限制与人工复核重点",
            dimensions.get("evidence_limitations_and_review_focus", {}),
            list_fields=[
                ("证据限制", "evidence_limitations"),
                ("高优先级复核", "high_priority_review_points"),
                ("中优先级复核", "medium_priority_review_points"),
                ("低优先级复核", "low_priority_review_points"),
            ],
        )

with items_tab:
    st.subheader("分项评价")
    if score_error:
        st.warning(f"无法读取 score.xlsx：{score_error}")
    elif score_df is not None:
        for section in ["case_design", "lesson_plan", "live_teaching"]:
            st.markdown(f"### {section}")
            section_df = score_df[score_df.get("section", "") == section] if "section" in score_df.columns else score_df
            for _, row in section_df.iterrows():
                name = row.get("indicator_name", row.get("指标名称", "未命名指标"))
                with st.expander(str(name), expanded=False):
                    for field in [
                        "max_score",
                        "suggested_score",
                        "evidence_sufficiency",
                        "document_evidence",
                        "strengths",
                        "deduction_reasons",
                        "manual_review_points",
                        "timestamp_evidence",
                        "ppt_page_evidence",
                        "keyframe_evidence",
                    ]:
                        st.markdown(f"**{field}**")
                        st.write(row.get(field, ""))

with files_tab:
    st.subheader("文件下载")
    download_files = [
        ("report.docx", base / "report.docx"),
        ("score.xlsx", base / "score.xlsx"),
        ("evidence_package.json", base / "evidence" / "evidence_package.json"),
        ("final_judgement.json", base / "agents" / "final_judgement.json"),
        ("overall_review.json", base / "agents" / "overall_review.json"),
    ]
    for label, path in download_files:
        if path.exists():
            with path.open("rb") as file:
                st.download_button(f"下载 {label}（{file_size_label(path)}）", file, file_name=label)
        else:
            st.caption(f"{label} 不存在")
