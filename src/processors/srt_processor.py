from __future__ import annotations

import re
from pathlib import Path

from src.schemas.evidence_schema import SrtEntry


TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)

KEYWORD_TAGS = {
    "导入": ["导入", "引入", "情境", "案例"],
    "提问": ["请问", "问题", "为什么", "怎么", "谁来", "思考"],
    "追问": ["追问", "再想", "还有", "进一步", "继续"],
    "学生回答": ["学生", "回答", "同学", "小组代表"],
    "小组活动": ["小组", "讨论", "合作", "任务单", "活动"],
    "AI": ["AI", "人工智能", "大模型", "智能", "生成", "算法"],
    "展示": ["展示", "汇报", "呈现", "演示"],
    "总结": ["总结", "回顾", "归纳", "评价"],
    "思政": ["习近平", "文化思想", "立德树人", "德技并修", "价值", "使命", "责任"],
    "美育": ["美", "审美", "美育", "艺术", "欣赏", "创造美"],
    "职业教育": ["岗位", "职业", "工匠", "技能", "实训", "任务", "标准"],
}


def parse_srt(srt_path: Path | None) -> dict:
    if srt_path is None or not srt_path.exists():
        return {
            "available": False,
            "status": "缺少transcript.srt，无法进行完整评审。",
            "entries": [],
        }
    text = srt_path.read_text(encoding="utf-8-sig", errors="ignore")
    blocks = re.split(r"\n\s*\n", text.strip())
    entries: list[SrtEntry] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        index = _parse_index(lines[0], len(entries) + 1)
        time_line_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if time_line_index is None:
            continue
        match = TIME_RE.search(lines[time_line_index])
        if not match:
            continue
        content = " ".join(lines[time_line_index + 1 :]).strip()
        if not content:
            continue
        start = match.group("start").replace(",", ".")
        end = match.group("end").replace(",", ".")
        entries.append(
            SrtEntry(
                index=index,
                start=start,
                end=end,
                start_seconds=time_to_seconds(start),
                end_seconds=time_to_seconds(end),
                text=content,
                tags=classify_text(content),
            )
        )
    return {
        "available": True,
        "status": f"已解析{len(entries)}条字幕。",
        "entries": [entry.to_dict() for entry in entries],
    }


def time_to_seconds(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(".")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def seconds_to_time(seconds: float) -> str:
    seconds = max(0, seconds)
    whole = int(seconds)
    millis = int(round((seconds - whole) * 1000))
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    sec = whole % 60
    return f"{hours:02d}:{minutes:02d}:{sec:02d}.{millis:03d}"


def classify_text(text: str) -> list[str]:
    tags = []
    for tag, keywords in KEYWORD_TAGS.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            tags.append(tag)
    return tags


def _parse_index(value: str, fallback: int) -> int:
    try:
        return int(value)
    except ValueError:
        return fallback
