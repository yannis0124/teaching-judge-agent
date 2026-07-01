from __future__ import annotations

import sys
import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.result_loader import AGENT_FILES, list_candidates, load_agent_outputs


def display_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


st.set_page_config(page_title="Agent输出查看", layout="wide")
st.title("Agent输出查看")

candidates = list_candidates(ROOT)
if not candidates:
    st.info("暂未发现输出结果，请先运行评审。")
    st.stop()

candidate_id = st.selectbox("选择选手", candidates)
outputs = load_agent_outputs(candidate_id, ROOT)

for file_name in AGENT_FILES:
    data, error = outputs[file_name]
    with st.expander(file_name, expanded=file_name == "final_judgement.json"):
        if error:
            st.warning(f"{file_name} 不存在或格式异常：{error}。该Agent可能未完成评分。")
            continue
        key_fields = [
            "indicator_name",
            "max_score",
            "suggested_score",
            "evidence_sufficiency",
            "strengths",
            "deduction_reasons",
            "manual_review_points",
            "summary",
            "overall_summary",
            "review_scope",
            "dimensions",
            "total_suggested_score",
        ]
        rows = [{"字段": key, "值": display_value(data.get(key))} for key in key_fields if key in data]
        if rows:
            st.table(rows)
        st.caption("原始JSON")
        st.json(data)
