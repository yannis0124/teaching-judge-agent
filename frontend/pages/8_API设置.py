from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.api_config import api_status_text, render_api_config


st.set_page_config(page_title="API设置", layout="wide")
st.title("API设置")
st.caption("切换评审时使用的 DeepSeek 兼容 API。个人配置只保存在当前浏览器会话中。")

render_api_config(ROOT)

st.divider()
st.info(api_status_text(ROOT))
st.caption("安全提示：不要把 API Key 写入 README、代码或提交到版本库。")
