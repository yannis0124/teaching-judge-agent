from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.file_utils import candidate_output_dir
from frontend.utils.result_loader import list_candidates, read_excel


st.set_page_config(page_title="证据链查看", layout="wide")
st.title("证据链查看")

candidates = list_candidates(ROOT)
if not candidates:
    st.info("暂未发现输出结果，请先运行评审。")
    st.stop()

candidate_id = st.selectbox("选择选手", candidates)
base = candidate_output_dir(candidate_id, ROOT) / "evidence"

tab_app, tab_lesson, tab_speech, tab_visual, tab_ppt = st.tabs(["申报表证据", "教案证据", "语音证据", "画面证据", "PPT证据"])

with tab_app:
    df, error = read_excel(base / "application_form_evidence.xlsx")
    if error:
        st.warning(f"申报表证据文件不存在或无法读取：{error}")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_lesson:
    df, error = read_excel(base / "lesson_plan_evidence.xlsx")
    if error:
        st.warning(f"教案证据文件不存在或无法读取：{error}")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_speech:
    df, error = read_excel(base / "speech_evidence.xlsx")
    if error:
        st.warning(f"语音证据文件不存在或无法读取：{error}")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_visual:
    df, error = read_excel(base / "visual_evidence.xlsx")
    if error:
        st.warning(f"画面证据文件不存在或无法读取：{error}")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        for _, row in df.iterrows():
            image_path = Path(str(row.get("image_path", "")))
            if image_path.exists():
                st.image(str(image_path), caption=f"{row.get('timestamp', '')} · {row.get('reason', '')}", use_container_width=True)

with tab_ppt:
    df, error = read_excel(base / "ppt_evidence.xlsx")
    if error:
        st.warning(f"PPT证据文件不存在或无法读取：{error}")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        for _, row in df.iterrows():
            image_path = Path(str(row.get("image_path", "")))
            if image_path.exists():
                st.image(str(image_path), caption=f"第{row.get('page', '')}页", use_container_width=True)
