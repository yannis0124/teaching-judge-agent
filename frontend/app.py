from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.result_loader import list_candidates


candidate_count = len(list_candidates(ROOT))

st.set_page_config(page_title="教学比赛多Agent评审助手", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --app-bg: #f5f5f7;
        --panel: rgba(255, 255, 255, 0.82);
        --panel-strong: #ffffff;
        --text: #1d1d1f;
        --muted: #6e6e73;
        --line: rgba(0, 0, 0, 0.08);
        --blue: #0071e3;
        --green: #2e7d55;
        --amber: #9a6a00;
    }

    .stApp {
        background: var(--app-bg);
        color: var(--text);
    }

    section.main > div {
        max-width: 1180px;
        padding-top: 2.4rem;
    }

    h1, h2, h3, p, div {
        letter-spacing: 0;
    }

    .apple-hero {
        padding: 56px 0 24px;
        border-bottom: 1px solid var(--line);
    }

    .eyebrow {
        color: var(--blue);
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 14px;
    }

    .hero-title {
        max-width: 960px;
        font-size: clamp(44px, 6vw, 76px);
        line-height: 1.03;
        font-weight: 800;
        color: var(--text);
        margin: 0;
    }

    .hero-copy {
        max-width: 760px;
        color: var(--muted);
        font-size: 21px;
        line-height: 1.48;
        margin: 22px 0 0;
    }

    .hero-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 30px;
    }

    .hero-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 42px;
        padding: 0 18px;
        border-radius: 8px;
        text-decoration: none !important;
        font-size: 15px;
        font-weight: 700;
    }

    .hero-link.primary {
        background: var(--blue);
        color: #fff !important;
    }

    .hero-link.secondary {
        background: #fff;
        color: var(--text) !important;
        border: 1px solid var(--line);
    }

    .status-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin: 28px 0 8px;
    }

    .status-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 20px 22px;
        box-shadow: 0 18px 45px rgba(0,0,0,0.05);
    }

    .status-label {
        color: var(--muted);
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .status-value {
        color: var(--text);
        font-size: 32px;
        line-height: 1;
        font-weight: 800;
    }

    .status-note {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
        margin-top: 10px;
    }

    .section-title {
        font-size: 28px;
        font-weight: 800;
        margin: 42px 0 14px;
        color: var(--text);
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin-top: 12px;
    }

    .feature-card {
        min-height: 150px;
        background: var(--panel-strong);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 18px;
    }

    .feature-index {
        color: var(--blue);
        font-size: 13px;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .feature-title {
        color: var(--text);
        font-size: 17px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .feature-copy {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.52;
    }

    .split-grid {
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 16px;
        margin-top: 14px;
    }

    .plain-panel {
        background: var(--panel-strong);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 22px;
    }

    .check-row {
        display: grid;
        grid-template-columns: 10px 1fr;
        gap: 12px;
        align-items: start;
        padding: 12px 0;
        border-bottom: 1px solid var(--line);
    }

    .check-row:last-child {
        border-bottom: 0;
    }

    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--green);
        margin-top: 7px;
    }

    .check-title {
        font-size: 15px;
        font-weight: 800;
        color: var(--text);
    }

    .check-copy {
        font-size: 13px;
        color: var(--muted);
        line-height: 1.5;
        margin-top: 3px;
    }

    .notice {
        border-left: 3px solid var(--amber);
        padding-left: 14px;
        color: var(--muted);
        font-size: 14px;
        line-height: 1.55;
    }

    div[data-testid="stPageLink"] a {
        border-radius: 8px;
        border: 1px solid var(--line);
        background: #fff;
        min-height: 42px;
    }

    @media (max-width: 900px) {
        .status-grid,
        .feature-grid,
        .split-grid {
            grid-template-columns: 1fr;
        }
        .hero-title {
            font-size: 42px;
        }
        .hero-copy {
            font-size: 18px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="apple-hero">
        <div class="eyebrow">Local review workspace</div>
        <h1 class="hero-title">教学比赛多Agent评审助手</h1>
        <p class="hero-copy">
            面向课程思政与课堂展示材料的本地评审工作台。上传材料，运行多Agent辅助分析，
            在证据链、分项结果和总控判断之间保持可追溯。
        </p>
        <div class="hero-actions">
            <a class="hero-link primary" href="/上传材料" target="_self">开始上传材料</a>
            <a class="hero-link secondary" href="/Agent自测" target="_self">检查Agent状态</a>
        </div>
    </section>

    <div class="status-grid">
        <div class="status-card">
            <div class="status-label">已发现选手</div>
            <div class="status-value">{candidate_count}</div>
            <div class="status-note">来自本地 outputs 目录。</div>
        </div>
        <div class="status-card">
            <div class="status-label">评分范围</div>
            <div class="status-value">100</div>
            <div class="status-note">案例20、教案20、现场展示60。</div>
        </div>
        <div class="status-card">
            <div class="status-label">运行方式</div>
            <div class="status-value">Local</div>
            <div class="status-note">材料与输出保存在本机工作区。</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">核心流程</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-index">01</div>
            <div class="feature-title">上传材料</div>
            <div class="feature-copy">提交申报表、教案、视频、PPT/HTML课件和 transcript.srt。</div>
        </div>
        <div class="feature-card">
            <div class="feature-index">02</div>
            <div class="feature-title">运行评审</div>
            <div class="feature-copy">前端调用本地后端命令，对当前选手材料生成辅助评分建议。</div>
        </div>
        <div class="feature-card">
            <div class="feature-index">03</div>
            <div class="feature-title">核验证据</div>
            <div class="feature-copy">查看文档、语音、画面和课件证据，定位每项建议的来源。</div>
        </div>
        <div class="feature-card">
            <div class="feature-index">04</div>
            <div class="feature-title">复核总控</div>
            <div class="feature-copy">使用 Agent 自测检查分项 Agent 与总控 Agent 的输出一致性。</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">快速入口</div>', unsafe_allow_html=True)
quick_cols = st.columns(4)
with quick_cols[0]:
    st.page_link("pages/1_上传材料.py", label="上传材料")
with quick_cols[1]:
    st.page_link("pages/2_评审总览.py", label="评审总览")
with quick_cols[2]:
    st.page_link("pages/4_证据链查看.py", label="证据链查看")
with quick_cols[3]:
    st.page_link("pages/7_Agent自测.py", label="Agent自测")

st.markdown('<div class="section-title">评审前检查</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="split-grid">
        <div class="plain-panel">
            <div class="check-row">
                <div class="dot"></div>
                <div>
                    <div class="check-title">材料齐全</div>
                    <div class="check-copy">申报表、教案、现场视频、PPT/HTML课件和 transcript.srt 均为完整评审所需材料。</div>
                </div>
            </div>
            <div class="check-row">
                <div class="dot"></div>
                <div>
                    <div class="check-title">本地可追溯</div>
                    <div class="check-copy">证据包、Agent 输出、Word 报告和 Excel 汇总均写入 outputs/{选手编号}/。</div>
                </div>
            </div>
            <div class="check-row">
                <div class="dot"></div>
                <div>
                    <div class="check-title">人工确认</div>
                    <div class="check-copy">系统生成辅助建议，最终分数仍由人工评委结合完整材料确认。</div>
                </div>
            </div>
        </div>
        <div class="plain-panel">
            <div class="notice">
                请勿将真实选手隐私材料提交到版本库。多Agent评审需要设置
                DEEPSEEK_API_KEY；如果缺少 transcript.srt，现场展示模块不会进入完整评分。
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
