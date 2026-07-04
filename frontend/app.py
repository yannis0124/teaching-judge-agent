from __future__ import annotations

import sys
from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.file_utils import materials_dir, outputs_dir
from frontend.utils.api_config import api_status_text
from frontend.utils.result_loader import list_candidates, load_summary, normalize_summary


def compact_html(value: str) -> str:
    return "\n".join(line.strip() for line in value.splitlines() if line.strip())


def status_label(value: object) -> str:
    labels = {
        "needs_review": "待人工复核",
        "scored": "已完成评审",
        "unscored": "未生成评分",
    }
    return labels.get(str(value), str(value) if value else "-")


def safe_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len([item for item in path.iterdir() if item.is_dir()])


def load_recent_rows() -> pd.DataFrame:
    summary, error = load_summary(ROOT)
    if error or summary is None or summary.empty:
        return pd.DataFrame()
    normalized = normalize_summary(summary)
    rows = []
    for row in normalized.tail(5).iloc[::-1].to_dict("records"):
        candidate_id = row.get("candidate_id") or row.get("选手编号") or "-"
        status = status_label(row.get("状态") or row.get("status") or "-")
        total = row.get("available_total_score") or row.get("full_total_score_100") or "-"
        max_score = row.get("available_max_score") or 100
        manual_count = row.get("manual_review_count") or row.get("需要人工复核数量") or 0
        score = f"{total} / {max_score}" if total != "-" else "-"
        rows.append(
            {
                "选手编号": candidate_id,
                "当前状态": status,
                "评审分数": score,
                "人工复核": manual_count,
            }
        )
    return pd.DataFrame(rows)


candidate_count = len(list_candidates(ROOT))
material_count = safe_count(materials_dir(ROOT))
output_path = outputs_dir(ROOT)
recent_rows = load_recent_rows()
if recent_rows.empty:
    recent_html = compact_html(
        """
    <div class="empty-state">
        暂未读取到 summary_ranking.xlsx。请先上传材料并运行评审，生成汇总表后这里会显示最近处理记录。
    </div>
    """
    )
else:
    recent_html = recent_rows.to_html(classes="recent-table", index=False, border=0, escape=True)
output_path_label = escape(str(output_path.relative_to(ROOT)))
api_status_label = escape(api_status_text(ROOT))

st.set_page_config(page_title="教学比赛多Agent评审助手", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --app-bg: #f7f8fa;
        --surface: #ffffff;
        --surface-soft: #fbfcfd;
        --text: #172033;
        --muted: #667085;
        --line: #d8dee8;
        --line-soft: #edf1f5;
        --primary: #0b7285;
        --primary-dark: #075b6b;
        --success: #14804a;
        --warning: #b45309;
        --danger: #c81e1e;
    }

    .stApp {
        background: var(--app-bg);
        color: var(--text);
    }

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    #MainMenu,
    footer {
        display: none;
        visibility: hidden;
    }

    section.main > div {
        max-width: 1240px;
        padding-top: 1rem;
        padding-bottom: 2.5rem;
    }

    .block-container {
        max-width: 1240px !important;
        padding-top: 1rem !important;
        padding-bottom: 2.5rem !important;
    }

    h1, h2, h3, p, div, span {
        letter-spacing: 0;
    }

    .console-shell {
        display: grid;
        grid-template-columns: 244px minmax(0, 1fr);
        min-height: calc(100vh - 92px);
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
    }

    .rail {
        border-right: 1px solid var(--line);
        background: #fbfcfe;
        padding: 22px 18px;
    }

    .brand {
        font-size: 18px;
        font-weight: 850;
        color: var(--text);
        line-height: 1.32;
        margin-bottom: 24px;
    }

    .rail-label {
        padding-top: 16px;
        border-top: 1px solid var(--line-soft);
        color: var(--muted);
        font-size: 12px;
        font-weight: 750;
        margin: 20px 0 8px;
    }

    .rail-item {
        display: block;
        padding: 11px 12px;
        border-radius: 8px;
        color: var(--text) !important;
        text-decoration: none !important;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .rail-item.active {
        background: var(--primary);
        color: #ffffff !important;
    }

    .rail-item:hover {
        background: #eef7f9;
        color: var(--primary-dark) !important;
    }

    .rail-item.active:hover {
        background: var(--primary-dark);
        color: #ffffff !important;
    }

    .user-box {
        margin-top: 72px;
        padding: 14px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        color: var(--muted);
        font-size: 13px;
        line-height: 1.55;
    }

    .user-box strong {
        color: var(--text);
    }

    .workspace {
        padding: 28px 30px;
    }

    .hero-title {
        margin: 0;
        color: var(--text);
        font-size: 38px !important;
        line-height: 1.16 !important;
        font-weight: 850 !important;
        word-break: keep-all;
    }

    .hero-copy {
        max-width: 640px;
        color: var(--muted);
        font-size: 17px;
        line-height: 1.56;
        margin: 12px 0 24px;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 18px;
    }

    .metric-card {
        min-height: 122px;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 18px 18px 16px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 13px;
        font-weight: 750;
        margin-bottom: 10px;
    }

    .metric-value {
        color: var(--text);
        font-size: 24px;
        line-height: 1.15;
        font-weight: 850;
    }

    .metric-note {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
        margin-top: 10px;
    }

    .status-ok {
        color: var(--success);
        font-weight: 850;
    }

    .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        margin-top: 18px;
    }

    .panel-header {
        padding: 16px 20px;
        border-bottom: 1px solid var(--line-soft);
        color: var(--text);
        font-size: 17px;
        font-weight: 850;
    }

    .flow {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        padding: 18px 20px 20px;
    }

    .flow-step {
        min-height: 118px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface-soft);
        padding: 16px;
    }

    .step-number {
        display: inline-flex;
        width: 30px;
        height: 30px;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: var(--primary);
        color: #ffffff;
        font-size: 14px;
        font-weight: 850;
        margin-bottom: 12px;
    }

    .step-title {
        color: var(--text);
        font-size: 16px;
        font-weight: 850;
        margin-bottom: 6px;
    }

    .step-copy {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.5;
    }

    .content-grid {
        display: grid;
        grid-template-columns: 0.92fr 1.08fr;
        gap: 18px;
        margin-top: 18px;
    }

    .task-list,
    .recent-list {
        padding: 0;
    }

    .task-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 14px;
        align-items: center;
        padding: 14px 20px;
        border-bottom: 1px solid var(--line-soft);
    }

    .task-row:last-child {
        border-bottom: 0;
    }

    .task-title {
        color: var(--text);
        font-size: 15px;
        font-weight: 850;
        margin-bottom: 3px;
    }

    .task-copy {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
    }

    .task-count {
        min-width: 42px;
        text-align: right;
        color: var(--primary);
        font-size: 20px;
        font-weight: 850;
    }

    .recent-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }

    .recent-table th,
    .recent-table td {
        padding: 12px 14px;
        border-bottom: 1px solid var(--line-soft);
        text-align: left;
        vertical-align: top;
    }

    .recent-table th {
        color: var(--muted);
        font-size: 12px;
        font-weight: 850;
        background: var(--surface-soft);
    }

    .recent-table td {
        color: var(--text);
    }

    .empty-state {
        padding: 24px 20px;
        color: var(--muted);
        font-size: 14px;
        line-height: 1.55;
    }

    .note {
        margin-top: 18px;
        padding: 14px 16px;
        border: 1px solid #b8d9ee;
        border-radius: 8px;
        background: #f0f8fd;
        color: #28556a;
        font-size: 14px;
        line-height: 1.55;
    }

    .quick-links {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin-top: 14px;
    }

    .quick-link {
        display: flex;
        min-height: 42px;
        align-items: center;
        justify-content: center;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        color: var(--text) !important;
        text-decoration: none !important;
        font-size: 14px;
        font-weight: 750;
    }

    .quick-link:hover {
        border-color: var(--primary);
        color: var(--primary-dark) !important;
    }

    div[data-testid="stPageLink"] a {
        min-height: 42px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        font-weight: 750;
    }

    div[data-testid="stPageLink"] a:hover {
        border-color: var(--primary);
        color: var(--primary-dark);
    }

    @media (max-width: 980px) {
        .console-shell {
            grid-template-columns: 1fr;
        }

        .rail {
            border-right: 0;
            border-bottom: 1px solid var(--line);
        }

        .user-box {
            margin-top: 20px;
        }

        .metric-grid,
        .flow,
        .content-grid,
        .quick-links {
            grid-template-columns: 1fr;
        }

        .workspace {
            padding: 22px 18px;
        }

        .hero-title {
            font-size: 34px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

homepage_html = compact_html(
    dedent(
        f"""
    <div class="console-shell">
        <aside class="rail">
            <div class="brand">教学比赛多Agent评审助手</div>
            <div class="rail-label">导航</div>
            <a class="rail-item active" href="./">工作台首页</a>
            <a class="rail-item" href="/上传材料" target="_self">上传材料</a>
            <a class="rail-item" href="/评审总览" target="_self">评审总览</a>
            <a class="rail-item" href="/选手详情" target="_self">选手详情</a>
            <a class="rail-item" href="/证据链查看" target="_self">证据链查看</a>

            <div class="rail-label">更多功能</div>
            <a class="rail-item" href="/Agent输出查看" target="_self">Agent输出查看</a>
            <a class="rail-item" href="/横向排名" target="_self">横向排名</a>
            <a class="rail-item" href="/Agent自测" target="_self">Agent自测</a>
            <a class="rail-item" href="/API设置" target="_self">API设置</a>

            <div class="user-box">
                <strong>当前用户</strong><br />
                评审员 · reviewer01<br /><br />
                角色：评审员<br />
                权限：评审、查看证据链<br />
                {api_status_label}
            </div>
        </aside>
        <main class="workspace">
            <h1 class="hero-title">教学比赛多Agent评审助手</h1>
            <p class="hero-copy">本地处理选手材料，生成可追溯的辅助评审建议。首页只保留评审入口、状态概览和流程提示，方便评委快速进入下一步。</p>

            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-label">系统状态</div>
                    <div class="metric-value"><span class="status-ok">运行正常</span></div>
                    <div class="metric-note">服务在线，前端可访问本地材料与输出目录。</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">已发现选手</div>
                    <div class="metric-value">{candidate_count} 位</div>
                    <div class="metric-note">来自本地 outputs/ 目录；materials/ 中有 {material_count} 个材料目录。</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">100分评分结构</div>
                    <div class="metric-value">3 大模块</div>
                    <div class="metric-note">案例20、教案20、现场展示60，覆盖15个分项指标。</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">输出目录</div>
                    <div class="metric-value">outputs/</div>
                    <div class="metric-note">报告、分项结果、证据包和横向排名保存在 {output_path_label}/。</div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">评审流程</div>
                <div class="flow">
                    <div class="flow-step">
                        <div class="step-number">1</div>
                        <div class="step-title">材料准备</div>
                        <div class="step-copy">上传并校验选手材料，确认文档、视频、课件与字幕完整可读。</div>
                    </div>
                    <div class="flow-step">
                        <div class="step-number">2</div>
                        <div class="step-title">后端评审</div>
                        <div class="step-copy">多 Agent 并行分析材料，生成分项评分建议和结构化输出。</div>
                    </div>
                    <div class="flow-step">
                        <div class="step-number">3</div>
                        <div class="step-title">证据核验</div>
                        <div class="step-copy">查看文档、语音、画面和课件证据，核验评分依据。</div>
                    </div>
                    <div class="flow-step">
                        <div class="step-number">4</div>
                        <div class="step-title">人工复核</div>
                        <div class="step-copy">评委结合完整材料确认最终结果，必要时调整辅助建议。</div>
                    </div>
                </div>
            </div>

            <div class="content-grid">
                <section class="panel">
                    <div class="panel-header">待办与提醒</div>
                    <div class="task-list">
                        <div class="task-row">
                            <div>
                                <div class="task-title">待上传材料</div>
                                <div class="task-copy">尚未上传或材料不完整的选手。</div>
                            </div>
                            <div class="task-count">{max(material_count - candidate_count, 0)}</div>
                        </div>
                        <div class="task-row">
                            <div>
                                <div class="task-title">后端评审中</div>
                                <div class="task-copy">Agent 正在评审中的选手。</div>
                            </div>
                            <div class="task-count">0</div>
                        </div>
                        <div class="task-row">
                            <div>
                                <div class="task-title">待证据核验</div>
                                <div class="task-copy">已生成评分，需要复查证据链。</div>
                            </div>
                            <div class="task-count">{candidate_count}</div>
                        </div>
                        <div class="task-row">
                            <div>
                                <div class="task-title">待人工复核</div>
                                <div class="task-copy">辅助建议生成后，仍需人工确认最终分数。</div>
                            </div>
                            <div class="task-count">{candidate_count}</div>
                        </div>
                    </div>
                </section>

                <section class="panel">
                    <div class="panel-header">最近处理选手</div>
                    {recent_html}
                </section>
            </div>

            <div class="note">不把缺失项记为0分；材料不全时显示“已评审分数 / 可评审满分”。系统生成辅助建议，最终分数由人工评委确认。</div>

            <div class="quick-links">
                <a class="quick-link" href="/上传材料" target="_self">上传材料</a>
                <a class="quick-link" href="/评审总览" target="_self">评审总览</a>
                <a class="quick-link" href="/证据链查看" target="_self">证据链查看</a>
                <a class="quick-link" href="/API设置" target="_self">切换 API</a>
            </div>
        </main>
    </div>
    """
)
)

st.markdown(homepage_html, unsafe_allow_html=True)
