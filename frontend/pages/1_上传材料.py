from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.utils.file_utils import candidate_material_dir, next_candidate_id, outputs_dir, sanitize_candidate_id, save_uploaded_file
from frontend.utils.result_loader import read_json
from frontend.utils.run_backend import run_candidate


def show_total_score(candidate_id: str) -> None:
    final, error = read_json(outputs_dir(ROOT) / candidate_id / "agents" / "final_judgement.json")
    if error:
        st.warning(f"评分已结束，但无法读取总分：{error}")
        return

    if final.get("can_score_total_100"):
        st.metric("100分总评", f"{final.get('full_total_score_100', '')} / 100")
    else:
        total = final.get("available_total_score", "")
        max_score = final.get("available_max_score", "")
        st.metric("已评审分数 / 可评审满分", f"{total} / {max_score}")
        st.caption("材料不全，暂不形成100分总评。")


st.set_page_config(page_title="上传材料", layout="wide")
st.title("上传材料")
st.caption("上传现场教学视频、PPT/HTML课件和字幕稿，保存到本地 materials/{选手编号}/")

default_id = next_candidate_id(ROOT)
if "candidate_id_input" not in st.session_state:
    st.session_state["candidate_id_input"] = default_id
candidate_input = st.text_input(
    "选手编号 candidate_id",
    key="candidate_id_input",
    help="保存材料时会创建 materials/{选手编号}/。可手动输入任意未使用编号，例如 A01、TEAM01、2026-01。",
)
candidate_id = sanitize_candidate_id(candidate_input) if candidate_input else default_id
if candidate_input and not candidate_id:
    st.error("选手编号只支持英文字母、数字、下划线和短横线。请修改后再保存或运行评审。")

st.info(f"当前将创建或使用目录：`materials/{candidate_id}/`")
target_dir = candidate_material_dir(candidate_id, ROOT)
exists = target_dir.exists()
if exists:
    st.warning(f"`materials/{candidate_id}/` 已存在。默认不会覆盖已有材料。")
overwrite = st.checkbox("允许覆盖已存在的同名材料", value=False, disabled=not exists)

application_file = st.file_uploader("上传申报表/案例整体设计材料（用于案例整体设计20分）", type=["docx", "pdf"])
lesson_file = st.file_uploader("上传教案（用于教案20分）", type=["docx", "pdf"])
video_file = st.file_uploader("上传现场教学视频（用于现场教学展示60分）", type=["mp4", "mov", "avi", "mkv"])
st.caption("视频上传上限已从 Streamlit 默认 200MB 调整为 10GB。")
courseware_files = st.file_uploader("上传PPT或HTML课件", type=["pptx", "html", "htm"], accept_multiple_files=True)
subtitle_file = st.file_uploader("上传字幕稿 transcript.srt", type=["srt"])

existing_courseware_paths = [
    target_dir / "slides.pptx",
    target_dir / "slides.html",
    target_dir / "slides.htm",
    *target_dir.glob("slides_*"),
]
has_existing_courseware = any(path.is_file() and path.suffix.lower() in {".pptx", ".html", ".htm"} for path in existing_courseware_paths)
has_existing_subtitle = (target_dir / "transcript.srt").exists()
if video_file is None:
    st.warning("缺少现场教学视频，无法进行现场展示评分。")
if not courseware_files and not has_existing_courseware:
    st.warning("缺少PPT/HTML课件，课件页码证据不足。")
if subtitle_file is None and not has_existing_subtitle:
    st.warning("缺少 transcript.srt，无法进行完整评审。")

st.subheader("当前可评审模块")
can_case = application_file is not None or (target_dir / "application_form.docx").exists() or (target_dir / "application_form.pdf").exists()
can_lesson = lesson_file is not None or (target_dir / "lesson_plan.docx").exists() or (target_dir / "lesson_plan.pdf").exists()
has_video = video_file is not None or (target_dir / "videos.mp4").exists() or (target_dir / "video.mp4").exists()
has_subtitle = subtitle_file is not None or has_existing_subtitle
can_live = has_video and has_subtitle
cols = st.columns(4)
cols[0].metric("案例整体设计20分", "可评" if can_case else "缺申报表")
cols[1].metric("教案20分", "可评" if can_lesson else "缺教案")
cols[2].metric("现场展示60分", "可评" if can_live else ("缺视频" if not has_video else "缺字幕"))
cols[3].metric("100分完整评审", "具备" if can_case and can_lesson and can_live else "材料不全")

saved = False
if st.button("保存材料", type="primary"):
    if exists and not overwrite:
        st.error("目录已存在。请勾选允许覆盖，或更换选手编号。")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
        if application_file is not None:
            save_uploaded_file(application_file, target_dir / f"application_form{Path(application_file.name).suffix.lower()}")
        if lesson_file is not None:
            save_uploaded_file(lesson_file, target_dir / f"lesson_plan{Path(lesson_file.name).suffix.lower()}")
        if video_file is not None:
            save_uploaded_file(video_file, target_dir / "videos.mp4")
        if courseware_files:
            for old_path in existing_courseware_paths:
                if old_path.is_file() and old_path.suffix.lower() in {".pptx", ".html", ".htm"}:
                    old_path.unlink()
            for index, courseware_file in enumerate(courseware_files, start=1):
                suffix = Path(courseware_file.name).suffix.lower()
                courseware_name = (
                    ("slides.pptx" if suffix == ".pptx" else f"slides{suffix}")
                    if len(courseware_files) == 1
                    else f"slides_{index:03d}{suffix}"
                )
                save_uploaded_file(courseware_file, target_dir / courseware_name)
        if subtitle_file is not None:
            save_uploaded_file(subtitle_file, target_dir / "transcript.srt")
        st.session_state["last_saved_candidate"] = candidate_id
        saved = True
        st.success(f"材料已保存到 `materials/{candidate_id}/`")

run_candidate_id = candidate_id

st.divider()
st.subheader("运行评审")
st.caption(f"点击后调用现有后端命令：python app.py --candidate {run_candidate_id}")
st.info(f"当前将运行：`materials/{run_candidate_id}/`")

if st.button("运行评审", disabled=not bool(candidate_id)):
    candidate_dir = candidate_material_dir(run_candidate_id, ROOT)
    if not candidate_dir.exists():
        st.error(f"`materials/{run_candidate_id}/` 不存在。请先保存上方材料后再运行评审。")
    elif not (candidate_dir / "videos.mp4").exists() and not (candidate_dir / "video.mp4").exists():
        st.error("缺少现场教学视频，无法进行现场展示评分。")
    elif not (candidate_dir / "transcript.srt").exists():
        st.error("缺少 transcript.srt。请先上传并保存字幕稿后再运行评审。")
    else:
        with st.spinner("后端评审运行中，请稍候..."):
            return_code, log_text = run_candidate(run_candidate_id, ROOT)
        st.code(log_text or "无运行日志", language="text")
        if return_code == 0:
            st.success(f"评审流程已结束。输出目录：`outputs/{run_candidate_id}/`")
            st.session_state["last_output_candidate"] = run_candidate_id
        else:
            st.error("后端运行失败，请查看上方日志或 outputs 目录。")

last_output_candidate = st.session_state.get("last_output_candidate")
if last_output_candidate:
    output_dir = outputs_dir(ROOT) / last_output_candidate
    show_total_score(last_output_candidate)
    if st.button(f"打开输出文件夹 outputs/{last_output_candidate}/"):
        if output_dir.exists():
            import os

            os.startfile(str(output_dir))
        else:
            st.error(f"输出目录不存在：{output_dir}")

st.divider()
st.caption(
    "隐私提示：上传文件将保存到本地 materials/ 目录。正式比赛材料请注意授权、隐私和保密。"
)
