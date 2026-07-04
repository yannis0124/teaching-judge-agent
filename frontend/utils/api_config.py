from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


API_MODE_KEY = "api_mode"
API_KEY_KEY = "deepseek_api_key"
BASE_URL_KEY = "deepseek_base_url"
MODEL_KEY = "deepseek_model"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


def init_api_config() -> None:
    st.session_state.setdefault(API_MODE_KEY, "system")
    st.session_state.setdefault(BASE_URL_KEY, os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    st.session_state.setdefault(MODEL_KEY, os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL))


def project_env_has_key(root: Path) -> bool:
    env_path = root / ".env"
    if not env_path.exists():
        return False
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DEEPSEEK_API_KEY" and value.strip().strip('"').strip("'"):
            return True
    return False


def system_api_available(root: Path) -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY")) or project_env_has_key(root)


def get_api_env_overrides() -> dict[str, str]:
    init_api_config()
    if st.session_state.get(API_MODE_KEY) != "custom":
        return {}

    api_key = str(st.session_state.get(API_KEY_KEY, "")).strip()
    base_url = str(st.session_state.get(BASE_URL_KEY, "")).strip() or DEFAULT_BASE_URL
    model = str(st.session_state.get(MODEL_KEY, "")).strip() or DEFAULT_MODEL
    overrides = {
        "DEEPSEEK_BASE_URL": base_url,
        "DEEPSEEK_MODEL": model,
    }
    if api_key:
        overrides["DEEPSEEK_API_KEY"] = api_key
    return overrides


def api_status_text(root: Path) -> str:
    init_api_config()
    if st.session_state.get(API_MODE_KEY) == "custom":
        if str(st.session_state.get(API_KEY_KEY, "")).strip():
            model = str(st.session_state.get(MODEL_KEY, "")).strip() or DEFAULT_MODEL
            return f"当前使用：个人 API（{model}）"
        return "当前使用：个人 API（未填写 Key）"
    return "当前使用：系统默认 API" if system_api_available(root) else "当前使用：系统默认 API（未检测到 Key）"


def api_config_error(root: Path) -> str | None:
    init_api_config()
    if st.session_state.get(API_MODE_KEY) == "custom":
        if not str(st.session_state.get(API_KEY_KEY, "")).strip():
            return "已选择个人 API，但还没有填写 API Key。请先到 API设置 页面填写。"
        return None
    if not system_api_available(root):
        return "未检测到系统默认 DEEPSEEK_API_KEY。请切换到个人 API，或在本机配置 .env / 环境变量。"
    return None


def render_api_config(root: Path) -> None:
    init_api_config()
    st.radio(
        "API 使用方式",
        options=["system", "custom"],
        format_func=lambda value: "使用系统默认 API" if value == "system" else "使用我的个人 API",
        key=API_MODE_KEY,
        horizontal=True,
    )

    if st.session_state[API_MODE_KEY] == "system":
        if system_api_available(root):
            st.success("系统默认 API 已可用。评审时会使用本机环境变量或项目 .env 中的配置。")
        else:
            st.warning("未检测到系统默认 DEEPSEEK_API_KEY。其他使用者可以切换到个人 API。")
        return

    st.text_input(
        "DEEPSEEK_API_KEY",
        key=API_KEY_KEY,
        type="password",
        placeholder="粘贴你自己的 API Key",
        help="只保存在当前浏览器会话中，不会写入项目文件。",
    )
    st.text_input("DEEPSEEK_BASE_URL", key=BASE_URL_KEY, placeholder=DEFAULT_BASE_URL)
    st.text_input("DEEPSEEK_MODEL", key=MODEL_KEY, placeholder=DEFAULT_MODEL)
    st.caption("个人 API 配置只对当前 Streamlit 会话生效；刷新服务或换浏览器后需要重新填写。")
