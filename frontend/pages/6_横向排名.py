from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.result_loader import load_summary, normalize_summary


st.set_page_config(page_title="横向排名", layout="wide")
st.title("横向排名")

df, error = load_summary(ROOT)
if error:
    st.info("暂未生成汇总表，请先上传材料并运行评审。")
    st.stop()

df = normalize_summary(df)
if df.empty:
    st.info("汇总表为空。")
    st.stop()

status_filter = st.radio("筛选", ["全部", "可形成100分总评", "仅现场展示", "缺申报表", "缺教案", "待人工复核"], horizontal=True)
if status_filter == "可形成100分总评" and "can_score_total_100" in df.columns:
    df = df[df["can_score_total_100"] == True]
elif status_filter == "仅现场展示" and "missing_sections" in df.columns:
    df = df[df["missing_sections"].astype(str).str.contains("case_design") & df["missing_sections"].astype(str).str.contains("lesson_plan")]
elif status_filter == "缺申报表" and "missing_sections" in df.columns:
    df = df[df["missing_sections"].astype(str).str.contains("case_design")]
elif status_filter == "缺教案" and "missing_sections" in df.columns:
    df = df[df["missing_sections"].astype(str).str.contains("lesson_plan")]
elif status_filter == "待人工复核" and "manual_review_count" in df.columns:
    df = df[df["manual_review_count"].fillna(0).astype(int) > 0]

score_column = "available_total_score" if "available_total_score" in df.columns else None
if score_column:
    df = df.copy()
    df["_score_sort"] = pd.to_numeric(df[score_column], errors="coerce").fillna(-1)
    df = df.sort_values("_score_sort", ascending=False).drop(columns=["_score_sort"])

st.dataframe(df, use_container_width=True, hide_index=True)
