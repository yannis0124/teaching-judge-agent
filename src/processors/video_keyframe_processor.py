from __future__ import annotations

import math
import subprocess
from pathlib import Path

from src.processors.srt_processor import seconds_to_time
from src.schemas.evidence_schema import KeyframeEvidence


KEY_NODE_TAGS = {"导入", "提问", "追问", "学生回答", "小组活动", "AI", "展示", "总结"}


def extract_keyframes(
    video_path: Path | None,
    srt_entries: list[dict],
    output_dir: Path,
    interval_seconds: int = 30,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    if video_path is None or not video_path.exists():
        return {
            "available": False,
            "status": "缺少视频，不能抽取关键帧，不能生成正式现场展示评分。",
            "frames": [],
        }
    duration = _probe_duration(video_path)
    if duration is None:
        return {
            "available": False,
            "status": "无法读取视频时长，画面证据不足，需要人工复核。",
            "frames": [],
        }

    targets = _fixed_targets(duration, interval_seconds)
    targets.update(_keyword_targets(srt_entries, duration))
    frames: list[KeyframeEvidence] = []
    for seconds, reason in sorted(targets.items()):
        timestamp = seconds_to_time(seconds)
        image_name = f"frame_{int(round(seconds)):06d}.jpg"
        image_path = output_dir / image_name
        if not image_path.exists():
            ok = _extract_one_frame(video_path, seconds, image_path)
            if not ok:
                continue
        frames.append(
            KeyframeEvidence(
                timestamp=timestamp,
                seconds=seconds,
                image_path=str(image_path),
                reason=reason,
            )
        )
    status = f"已抽取{len(frames)}张关键帧。关键帧仅作为画面辅助证据，不得用单帧推断整堂课整体状态。"
    return {"available": bool(frames), "status": status, "frames": [frame.to_dict() for frame in frames]}


def _probe_duration(video_path: Path) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def _fixed_targets(duration: float, interval_seconds: int) -> dict[float, str]:
    count = max(1, math.ceil(duration / interval_seconds))
    return {float(i * interval_seconds): "固定间隔30秒抽帧" for i in range(count)}


def _keyword_targets(srt_entries: list[dict], duration: float) -> dict[float, str]:
    targets: dict[float, str] = {}
    for entry in srt_entries:
        tags = set(entry.get("tags", []))
        matched = sorted(tags & KEY_NODE_TAGS)
        if not matched:
            continue
        start = float(entry.get("start_seconds", 0))
        for offset in (-2, 0, 2):
            seconds = min(max(start + offset, 0), max(duration - 0.5, 0))
            rounded = round(seconds, 1)
            targets[rounded] = f"SRT关键节点额外抽帧：{','.join(matched)}"
    return targets


def _extract_one_frame(video_path: Path, seconds: float, image_path: Path) -> bool:
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{seconds:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(image_path),
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
