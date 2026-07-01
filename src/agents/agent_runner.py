from __future__ import annotations

import json
import os
from pathlib import Path

from src.processors.evidence_packager import write_json
from src.schemas.agent_output_schema import ensure_scoring_agent_output, parse_json_object
from src.schemas.scoring_schema import Indicator, ScoringSchema


class MissingApiKeyError(RuntimeError):
    pass


class AgentRunner:
    def __init__(self, schema: ScoringSchema, output_dir: Path, model: str | None = None) -> None:
        _load_local_env()
        self.schema = schema
        self.output_dir = output_dir
        self.agents_dir = output_dir / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        if not api_key:
            raise MissingApiKeyError(
                "未检测到DEEPSEEK_API_KEY。已停止在大模型Agent评分前；请设置环境变量后重新运行。"
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("缺少openai依赖，请先安装requirements.txt。") from exc
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def run_all(self, evidence_package: dict) -> dict:
        compact_evidence = _compact_evidence(evidence_package)
        scoring_results: dict[str, dict] = {}
        for indicator in self.schema.indicators:
            if _can_score_section(indicator.section, evidence_package):
                result = self._run_scoring_agent(indicator, compact_evidence)
                result = _enforce_evidence_limits(result, indicator.max_score, evidence_package)
            else:
                result = _missing_section_output(indicator)
            scoring_results[indicator.id] = result
            write_json(self.agents_dir / indicator.agent_file, result)

        consistency = self._run_review_agent(
            "证据一致性复核Agent",
            _consistency_prompt(),
            {"evidence_package": compact_evidence, "scoring_results": scoring_results},
        )
        write_json(self.output_dir / "evidence" / "consistency_review.json", consistency)

        bias = self._run_review_agent(
            "偏差审查Agent",
            _bias_prompt(),
            {"evidence_package": compact_evidence, "scoring_results": scoring_results},
        )
        write_json(self.output_dir / "evidence" / "bias_review.json", bias)

        final = self._run_review_agent(
            "综合裁判Agent",
            _final_prompt(),
            {
                "scoring_scope": "按材料可评审模块输出：案例20、教案20、现场60；材料不全不输出100分总分。",
                "scoring_results": scoring_results,
                "consistency_review": consistency,
                "bias_review": bias,
            },
        )
        final.update(_score_totals(scoring_results, evidence_package))
        final["scoring_scope"] = "完整评分表100分（按材料可评审模块输出）"
        if final.get("can_score_total_100") and "未输出100分总分" in str(final.get("notes", "")):
            final["notes"] = "材料齐全，无缺失模块。评分基于可评审模块输出，已形成100分总分建议。"
        write_json(self.agents_dir / "final_judgement.json", final)

        overall = self._run_review_agent(
            "整体性评价Agent",
            _overall_review_prompt(),
            {
                "candidate_id": evidence_package.get("candidate_id"),
                "review_constraints": [
                    "不判断比赛档次",
                    "不输出排名建议",
                    "不输出获奖建议",
                    "不改变任何分项分数或总分",
                    "只做基于证据的整体结构分析",
                ],
                "evidence_package": compact_evidence,
                "scoring_results": scoring_results,
                "consistency_review": consistency,
                "bias_review": bias,
                "final_judgement": final,
            },
        )
        write_json(self.agents_dir / "overall_review.json", overall)
        return {
            "scoring_results": scoring_results,
            "consistency_review": consistency,
            "bias_review": bias,
            "final_judgement": final,
            "overall_review": overall,
        }

    def _run_scoring_agent(self, indicator: Indicator, compact_evidence: dict) -> dict:
        payload = {
            "indicator": {
                "id": indicator.id,
                "section": indicator.section,
                "name": indicator.name,
                "max_score": indicator.max_score,
                "focus": indicator.focus,
                "cautions": indicator.cautions,
            },
            "evidence_package": compact_evidence,
            "required_output_fields": [
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
            ],
        }
        parse_result = self._call_json_agent(_scoring_system_prompt(indicator), payload)
        if parse_result["format_error"]:
            return _format_error_scoring_output(indicator, parse_result)
        data = ensure_scoring_agent_output(parse_result["data"], indicator.max_score)
        data["indicator_id"] = indicator.id
        data["section"] = indicator.section
        return data

    def _run_review_agent(self, agent_name: str, system_prompt: str, payload: dict) -> dict:
        parse_result = self._call_json_agent(system_prompt, payload)
        if parse_result["format_error"]:
            return {
                "agent_name": agent_name,
                "format_error": True,
                "raw_output": parse_result.get("raw_output"),
                "error": parse_result.get("error"),
                "manual_review_points": ["该Agent输出格式异常，需要人工复核。"],
            }
        data = parse_result["data"]
        data.setdefault("agent_name", agent_name)
        data.setdefault("manual_review_points", [])
        return data

    def _call_json_agent(self, system_prompt: str, payload: dict) -> dict:
        raw_output = self._chat(system_prompt, json.dumps(payload, ensure_ascii=False))
        try:
            return {"format_error": False, "data": parse_json_object(raw_output), "raw_output": raw_output}
        except Exception as first_error:
            retry_raw = self._chat(
                "上一次输出不是合法JSON。请只返回一个合法JSON对象，不要使用Markdown代码块，不要添加解释文字。",
                raw_output,
            )
            try:
                return {"format_error": False, "data": parse_json_object(retry_raw), "raw_output": retry_raw}
            except Exception as second_error:
                return {
                    "format_error": True,
                    "data": {},
                    "raw_output": retry_raw,
                    "error": f"{first_error}; retry: {second_error}",
                }

    def _chat(self, system_prompt: str, user_content: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            extra_body={"thinking": {"type": "disabled"}},
        )
        return response.choices[0].message.content or "{}"


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _scoring_system_prompt(indicator: Indicator) -> str:
    extra = ""
    if indicator.id == "ai_application":
        extra = (
            "必须区分AI应用层级：低水平为教师展示AI结果；中等水平为学生使用AI完成任务；"
            "高水平为学生在AI支持下完成分析、判断、生成、评价、修正，教师引导学生审查AI结果，形成真正的人机协同学习过程。"
        )
    if indicator.id == "teacher_quality":
        extra = (
            "必须评价教师语言感染力，包括语言清晰度、语速节奏、情绪投入、亲和力、启发性表达和课堂带入感；"
            "不得把声音大、语速快、表达流畅简单等同于感染力。"
        )
    evidence_note = (
        "线上材料评审主要使用document_evidence，必须引用文件名、段落/表格/标题附近位置和摘录。"
        if indicator.section in {"case_design", "lesson_plan"}
        else "现场展示评审继续使用timestamp_evidence、ppt_page_evidence、keyframe_evidence。"
    )
    return f"""
你是“{indicator.name}”专项评审Agent，只评价section={indicator.section}中的该指标，不评价其他指标。
系统支持案例整体设计20分、教案20分、现场教学展示60分。材料缺失的模块不得计0分。
请基于证据包输出结构化JSON。评分采用0.5分制，满分为{indicator.max_score}分。

约束：
- 证据充分性低时不得给出过高建议分。
- 证据不足时不要强行判断，应标注人工复核。
- 高分必须有明确证据链。
- 不得虚构申报表、教案、SRT、PPT或视频内容。
- 不得因为文字写得华丽就给高分，要看是否对齐评分要点。
- 不得因为出现课程思政、文化思想、美育、AI等词语就直接给高分。
- 不得仅凭单帧、PPT美观、口号表达或AI露出给高分。
- 文档证据不足、模板未填写、只有标题无正文时，必须提示人工复核。
- {evidence_note}
{extra}

只返回JSON对象，字段至少包含：
section, indicator_name, max_score, suggested_score, evidence_sufficiency, document_evidence,
timestamp_evidence, ppt_page_evidence, keyframe_evidence, strengths, deduction_reasons, manual_review_points。
"""


def _consistency_prompt() -> str:
    return """
你是证据一致性复核Agent。请检查申报表、教案、语音证据、画面关键帧证据、PPT页码证据之间是否一致。
重点检查：教案中设计的AI活动，现场是否实际出现；教案中的课程思政，现场是否自然落实；
申报表中的特色创新，教案和现场是否有支撑；教师说有小组讨论画面是否有对应关键帧；
PPT有任务页课堂是否有实施证据；给AI高分或思政高分是否有充分证据。
只返回JSON对象，包含summary, consistency_issues, score_adjustment_suggestions, manual_review_points。
"""


def _bias_prompt() -> str:
    return """
你是偏差审查Agent。请检查评分是否被表象带偏。
必须检查：文字包装高估、教案模板化高估、PPT美观高估、课堂热闹高估、AI露出高估、思政口号高估；
不得因为单帧学生低头判断整体参与度低，不得因为单帧AI界面给AI技术高分。
score_adjustment_suggestions必须输出数组。每项包含indicator, current_score, suggested_direction, reason。
如果没有明确调整建议，输出空数组[]，不得只输出Agent名称或指标id列表。
只返回JSON对象，包含summary, bias_risks, score_adjustment_suggestions, manual_review_points。
"""


def _final_prompt() -> str:
    return """
你是综合裁判Agent。请整合案例整体设计20分、教案20分、现场教学展示60分专项Agent意见、证据一致性复核和偏差审查。
材料缺失模块不得计0分；材料不全时只输出已评审分数/可评审满分，不得输出100分总分。
只返回JSON对象，包含summary, main_strengths, main_problems, missing_sections, manual_review_points, notes。
"""


def _overall_review_prompt() -> str:
    return """
你是整体性评价Agent。请基于已生成的证据包、分项Agent结果、证据一致性复核、偏差审查和综合裁判结果，生成整体性结构分析。

任务边界：
- 不重新打分，不改变分项得分，不改变总分。
- 不输出选手档次、A/B/C/D档、比赛竞争力等级、排名建议、获奖建议、高分档判断。
- 不替代人工评委，只帮助评委理解分数背后的整体逻辑。
- 所有判断必须基于材料证据；证据不足时必须标注限制。
- 不得因为文字包装、PPT美观、课堂热闹、AI露出、思政口号而过度正向评价。
- 不要重复分项评价中的长篇证据，证据字段只保留关键证据。

请重点分析：
1. “三进”融合深度：课程思政、习近平文化思想、美育、专业教学是否自然融合并贯穿目标、内容、方法、评价。
2. AI应用有效度：AI是展示型、辅助型、任务型、协同型、批判型还是证据不足，是否进入学生学习任务。
3. 申报表-教案-PPT-现场展示一致性：设计是否在现场落实，是否存在申报表写得好但现场落实不足。
4. 职业教育类型特色：是否有职业情境、岗位任务、实践活动、做中学和行业新方法新技术新标准。
5. 美育与文化表达质量：是否引导发现美、欣赏美、创造美，而不仅是PPT好看或图片展示。
6. 教学闭环完整度：是否形成目标-任务-活动-评价-反思/迁移闭环。
7. 证据限制与人工复核重点：材料是否完整，哪些判断必须人工复核。

字段写作要求：
- overall_summary控制在200到300字。
- 每个summary控制在100到180字。
- strengths、weaknesses、improvement_suggestions、manual_review_points各2到4条为宜。
- evidence每个维度最多3条关键证据。

只返回JSON对象，结构必须为：
{
  "candidate_id": "",
  "review_scope": {
    "case_design_available": true,
    "lesson_plan_available": true,
    "live_teaching_available": true,
    "can_score_total_100": true,
    "available_max_score": 100,
    "evidence_limitations": []
  },
  "overall_summary": "",
  "dimensions": {
    "three_entries_integration": {
      "summary": "",
      "strengths": [],
      "weaknesses": [],
      "evidence": [],
      "improvement_suggestions": [],
      "manual_review_points": []
    },
    "ai_application_effectiveness": {
      "application_type": "展示型/辅助型/任务型/协同型/批判型/证据不足",
      "summary": "",
      "strengths": [],
      "weaknesses": [],
      "evidence": [],
      "improvement_suggestions": [],
      "manual_review_points": []
    },
    "material_consistency": {
      "summary": "",
      "consistent_points": [],
      "inconsistent_points": [],
      "evidence": [],
      "improvement_suggestions": [],
      "manual_review_points": []
    },
    "vocational_education_characteristics": {
      "summary": "",
      "strengths": [],
      "weaknesses": [],
      "evidence": [],
      "improvement_suggestions": [],
      "manual_review_points": []
    },
    "aesthetic_and_cultural_expression": {
      "summary": "",
      "strengths": [],
      "weaknesses": [],
      "evidence": [],
      "improvement_suggestions": [],
      "manual_review_points": []
    },
    "teaching_closure": {
      "summary": "",
      "completed_links": [],
      "missing_or_weak_links": [],
      "evidence": [],
      "improvement_suggestions": [],
      "manual_review_points": []
    },
    "evidence_limitations_and_review_focus": {
      "summary": "",
      "evidence_limitations": [],
      "high_priority_review_points": [],
      "medium_priority_review_points": [],
      "low_priority_review_points": []
    }
  }
}
"""


def _can_score_section(section: str, evidence_package: dict) -> bool:
    completeness = evidence_package.get("material_completeness", {})
    return {
        "case_design": bool(completeness.get("can_score_case_design_20")),
        "lesson_plan": bool(completeness.get("can_score_lesson_plan_20")),
        "live_teaching": bool(completeness.get("can_score_live_teaching_60")),
    }.get(section, False)


def _missing_section_output(indicator: Indicator) -> dict:
    reason = {
        "case_design": "申报表/案例整体设计材料缺失或解析失败，不评价案例整体设计20分。",
        "lesson_plan": "教案材料缺失或解析失败，不评价教案20分。",
        "live_teaching": "视频缺失，不能生成现场教学展示60分正式建议。",
    }.get(indicator.section, "材料缺失，未评分。")
    return {
        "section": indicator.section,
        "indicator_id": indicator.id,
        "indicator_name": indicator.name,
        "max_score": indicator.max_score,
        "suggested_score": None,
        "evidence_sufficiency": "不足",
        "document_evidence": [],
        "timestamp_evidence": [],
        "ppt_page_evidence": [],
        "keyframe_evidence": [],
        "strengths": [],
        "deduction_reasons": [reason],
        "manual_review_points": [reason],
        "status": "not_scored",
    }


def _score_totals(scoring_results: dict[str, dict], evidence_package: dict) -> dict:
    section_scores: dict[str, float | None] = {}
    for section in ["case_design", "lesson_plan", "live_teaching"]:
        items = [item for item in scoring_results.values() if item.get("section") == section]
        if items and all(item.get("suggested_score") is not None for item in items):
            section_scores[section] = round(sum(float(item["suggested_score"]) for item in items) * 2) / 2
        else:
            section_scores[section] = None
    completeness = evidence_package.get("material_completeness", {})
    available_total = sum(float(score) for score in section_scores.values() if score is not None)
    can_total = bool(completeness.get("can_score_total_100"))
    missing_sections = []
    if not completeness.get("can_score_case_design_20"):
        missing_sections.append("case_design")
    if not completeness.get("can_score_lesson_plan_20"):
        missing_sections.append("lesson_plan")
    if not completeness.get("can_score_live_teaching_60"):
        missing_sections.append("live_teaching")
    return {
        "case_design_score_20": section_scores["case_design"],
        "lesson_plan_score_20": section_scores["lesson_plan"],
        "live_teaching_score_60": section_scores["live_teaching"],
        "available_total_score": round(available_total * 2) / 2,
        "available_max_score": int(completeness.get("available_max_score", 0) or 0),
        "full_total_score_100": round(available_total * 2) / 2 if can_total else None,
        "can_score_total_100": can_total,
        "missing_sections": missing_sections,
    }


def _compact_evidence(package: dict) -> dict:
    speech_entries = package.get("speech_evidence", {}).get("entries", [])
    visual_frames = package.get("visual_evidence", {}).get("frames", [])
    ppt_slides = package.get("ppt_evidence", {}).get("slides", [])
    return {
        "candidate_id": package.get("candidate_id"),
        "scoring_scope": package.get("scoring_scope"),
        "material_integrity": package.get("material_integrity"),
        "material_completeness": package.get("material_completeness"),
        "application_form_evidence": _compact_document(package.get("application_form_evidence", {})),
        "lesson_plan_evidence": _compact_document(package.get("lesson_plan_evidence", {})),
        "speech_status": package.get("speech_evidence", {}).get("status"),
        "speech_entries": speech_entries[:120],
        "visual_status": package.get("visual_evidence", {}).get("status"),
        "keyframes": visual_frames[:120],
        "ppt_status": package.get("ppt_evidence", {}).get("status"),
        "ppt_image_status": package.get("ppt_evidence", {}).get("image_status"),
        "ppt_slides": ppt_slides[:120],
        "truncated": {
            "speech_entries": len(speech_entries) > 120,
            "keyframes": len(visual_frames) > 120,
            "ppt_slides": len(ppt_slides) > 120,
        },
        "evidence_rules": package.get("evidence_rules"),
    }


def _compact_document(document: dict) -> dict:
    text = "\n".join([document.get("extracted_text", ""), document.get("tables_text", "")]).strip()
    return {
        "exists": document.get("exists"),
        "file_path": document.get("file_path"),
        "file_name": document.get("file_name"),
        "extraction_status": document.get("extraction_status"),
        "evidence_sufficiency": document.get("evidence_sufficiency"),
        "warnings": document.get("warnings", []),
        "error": document.get("error"),
        "detected_sections": document.get("detected_sections", []),
        "section_candidates": document.get("section_candidates", {}),
        "text_excerpt": text[:12000],
        "text_truncated": len(text) > 12000,
    }


def _format_error_scoring_output(indicator: Indicator, parse_result: dict) -> dict:
    return {
        "section": indicator.section,
        "indicator_id": indicator.id,
        "indicator_name": indicator.name,
        "max_score": indicator.max_score,
        "suggested_score": 0.0,
        "evidence_sufficiency": "不足",
        "document_evidence": [],
        "timestamp_evidence": [],
        "ppt_page_evidence": [],
        "keyframe_evidence": [],
        "strengths": [],
        "deduction_reasons": ["该Agent输出格式异常，需要人工复核。"],
        "manual_review_points": ["该Agent输出格式异常，需要人工复核。"],
        "format_error": True,
        "raw_output": parse_result.get("raw_output"),
        "error": parse_result.get("error"),
    }


def _enforce_evidence_limits(result: dict, max_score: float, evidence_package: dict) -> dict:
    if result.get("section") in {"case_design", "lesson_plan"}:
        document = evidence_package.get("application_form_evidence" if result.get("section") == "case_design" else "lesson_plan_evidence", {})
        if document.get("evidence_sufficiency") == "不足":
            result["evidence_sufficiency"] = "不足"
            result["suggested_score"] = 0.0
            result.setdefault("manual_review_points", []).append("文档证据不足，必须人工复核。")
        return result

    has_srt = bool(evidence_package.get("speech_evidence", {}).get("available"))
    has_visual = bool(evidence_package.get("visual_evidence", {}).get("available"))
    has_ppt = bool(evidence_package.get("ppt_evidence", {}).get("text_available"))
    available_count = sum([has_srt, has_visual, has_ppt])
    max_level = {3: "高", 2: "中", 1: "低", 0: "不足"}[available_count]
    rank = {"不足": 0, "低": 1, "中": 2, "高": 3}
    current = result.get("evidence_sufficiency", "不足")
    if rank.get(current, 0) > rank[max_level]:
        result["evidence_sufficiency"] = max_level
        result.setdefault("manual_review_points", []).append(f"系统根据材料完整性将证据充分性上限调整为“{max_level}”。")
    if result["evidence_sufficiency"] == "低":
        cap = round(float(max_score) * 0.6 * 2) / 2
        if float(result.get("suggested_score", 0)) > cap:
            result["suggested_score"] = cap
            result.setdefault("deduction_reasons", []).append("证据充分性低，系统限制过高建议分。")
    if result["evidence_sufficiency"] == "不足":
        result["suggested_score"] = 0.0
        result.setdefault("manual_review_points", []).append("证据不足，必须人工复核。")
    return result
