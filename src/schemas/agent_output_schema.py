from __future__ import annotations

import json


REQUIRED_SCORING_FIELDS = [
    "section",
    "indicator_name",
    "max_score",
    "suggested_score",
    "evidence_sufficiency",
    "document_evidence",
    "timestamp_evidence",
    "ppt_page_evidence",
    "keyframe_evidence",
    "strengths",
    "deduction_reasons",
    "manual_review_points",
]


def parse_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    return json.loads(stripped)


def ensure_scoring_agent_output(data: dict, max_score: float) -> dict:
    for field in REQUIRED_SCORING_FIELDS:
        data.setdefault(field, [] if field.endswith(("evidence", "reasons", "points")) or field == "strengths" else "")
    try:
        score = float(data.get("suggested_score", 0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(float(max_score), round(score * 2) / 2))
    data["suggested_score"] = score
    data["max_score"] = float(max_score)
    if data.get("evidence_sufficiency") not in {"高", "中", "低", "不足"}:
        data["evidence_sufficiency"] = "不足"
        data.setdefault("manual_review_points", [])
        if isinstance(data["manual_review_points"], list):
            data["manual_review_points"].append("证据充分性字段异常，需要人工复核。")
    for list_field in [
        "document_evidence",
        "timestamp_evidence",
        "ppt_page_evidence",
        "keyframe_evidence",
        "strengths",
        "deduction_reasons",
        "manual_review_points",
    ]:
        if isinstance(data.get(list_field), str):
            data[list_field] = [data[list_field]]
        elif data.get(list_field) is None:
            data[list_field] = []
    return data
