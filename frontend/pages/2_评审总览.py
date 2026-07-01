from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.result_loader import load_summary, normalize_summary


st.set_page_config(page_title="评审总览", layout="wide")
st.title("评审总览")
st.caption("读取 outputs/summary_ranking.xlsx")

df, error = load_summary(ROOT)
if error:
    st.info("暂未生成汇总表，请先上传材料并运行评审。")
    st.stop()

df = normalize_summary(df)
if df.empty:
    st.info("汇总表为空，请先运行评审。")
    st.stop()

preferred = [
    "candidate_id",
    "status",
    "case_design_score_20",
    "lesson_plan_score_20",
    "live_teaching_score_60",
    "available_total_score",
    "available_max_score",
    "full_total_score_100",
    "can_score_total_100",
    "missing_sections",
    "manual_review_count",
    "three_entries_summary",
    "ai_application_type",
    "material_consistency_summary",
    "teaching_closure_summary",
    "key_review_points",
    "remarks",
]
columns = [column for column in preferred if column in df.columns]
remaining = [column for column in df.columns if column not in columns]
st.dataframe(df[columns + remaining], use_container_width=True, hide_index=True)
