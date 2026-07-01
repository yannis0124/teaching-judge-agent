from __future__ import annotations

import argparse
from pathlib import Path

from src.agents.agent_runner import AgentRunner, MissingApiKeyError
from src.processors.evidence_packager import build_evidence_package, write_json
from src.processors.document_processor import process_document
from src.processors.materials_scanner import scan_materials
from src.processors.ppt_processor import process_ppt
from src.processors.srt_processor import parse_srt
from src.processors.video_keyframe_processor import extract_keyframes
from src.reporting.docx_reporter import write_report
from src.reporting.summary_reporter import build_summary_row, write_summary_ranking
from src.reporting.xlsx_reporter import write_score_workbook
from src.schemas.scoring_schema import load_scoring_schema


def main() -> None:
    parser = argparse.ArgumentParser(description="现场教学展示60分多Agent辅助评分工具")
    parser.add_argument("--candidate", help="只处理指定选手编号，例如A01", default=None)
    parser.add_argument("--materials-dir", default="materials", help="材料目录，默认materials")
    parser.add_argument("--outputs-dir", default="outputs", help="输出目录，默认outputs")
    parser.add_argument("--schema", default="docs/scoring_schema.yaml", help="评分schema路径")
    args = parser.parse_args()

    root = Path.cwd()
    materials_dir = root / args.materials_dir
    outputs_dir = root / args.outputs_dir
    schema = load_scoring_schema(root / args.schema)

    candidates = scan_materials(materials_dir, args.candidate)
    if not candidates:
        print("未发现选手材料目录。")
        return

    summary_rows: list[dict] = []
    for materials in candidates:
        print(f"开始处理选手：{materials.candidate_id}")
        try:
            row = _process_candidate(materials, outputs_dir, schema)
            summary_rows.append(row)
            print(f"完成处理：{materials.candidate_id}")
        except MissingApiKeyError as exc:
            print(str(exc))
            print("已停止大模型Agent评分；请设置DEEPSEEK_API_KEY后重新运行。")
            summary_rows.append(
                {
                    "candidate_id": materials.candidate_id,
                    "total_score": "",
                    "material_status": "未设置DEEPSEEK_API_KEY",
                    "manual_review_count": "",
                    "notes": "未生成正式评分建议。",
                }
            )
            break
        except Exception as exc:
            print(f"处理{materials.candidate_id}时发生错误：{exc}")
            summary_rows.append(
                {
                    "candidate_id": materials.candidate_id,
                    "total_score": "",
                    "material_status": "处理失败",
                    "manual_review_count": "",
                    "notes": str(exc),
                }
            )

    if summary_rows:
        write_summary_ranking(outputs_dir / "summary_ranking.xlsx", summary_rows)
        print(f"已生成汇总表：{outputs_dir / 'summary_ranking.xlsx'}")


def _process_candidate(materials, outputs_dir: Path, schema) -> dict:
    candidate_output = outputs_dir / materials.candidate_id
    evidence_dir = candidate_output / "evidence"
    keyframes_dir = evidence_dir / "keyframes"
    slide_images_dir = evidence_dir / "slide_images"
    agents_dir = candidate_output / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    transcription_status = _manual_transcript_status(materials)
    print(transcription_status.get("message", ""))
    application_form = process_document(materials.application_form_path, "application_form")
    lesson_plan = process_document(materials.lesson_plan_path, "lesson_plan")
    speech = parse_srt(materials.srt_path)
    visual = extract_keyframes(materials.video_path, speech.get("entries", []), keyframes_dir)
    ppt = process_ppt(materials.courseware_paths or materials.ppt_path, slide_images_dir)
    evidence_package = build_evidence_package(
        materials,
        application_form,
        lesson_plan,
        speech,
        visual,
        ppt,
        candidate_output,
        transcription_status,
    )

    if materials.video_path is None:
        reason = "缺少现场教学视频，不能生成正式现场教学展示60分评分建议。请补充视频后重新运行。"
        _write_unscored_placeholders(schema, candidate_output, reason)
        write_json(agents_dir / "final_judgement.json", {"status": "material_missing", "reason": reason})
        write_report(candidate_output / "report.docx", evidence_package, None, material_only=True, stop_reason=reason)
        write_score_workbook(candidate_output / "score.xlsx", materials.candidate_id, None, material_note=reason, evidence_package=evidence_package)
        return build_summary_row(materials.candidate_id, evidence_package, None, note=reason)

    try:
        runner = AgentRunner(schema, candidate_output)
    except MissingApiKeyError as exc:
        reason = str(exc)
        print(reason)
        print("未生成正式评分建议；已保留证据包和未评分提示文件。")
        _write_unscored_placeholders(schema, candidate_output, reason)
        write_json(agents_dir / "final_judgement.json", {"status": "missing_api_key", "reason": reason})
        write_report(candidate_output / "report.docx", evidence_package, None, material_only=True, stop_reason=reason)
        write_score_workbook(candidate_output / "score.xlsx", materials.candidate_id, None, material_note=reason, evidence_package=evidence_package)
        return build_summary_row(materials.candidate_id, evidence_package, None, note=reason)

    agent_results = runner.run_all(evidence_package)
    write_report(candidate_output / "report.docx", evidence_package, agent_results)
    write_score_workbook(candidate_output / "score.xlsx", materials.candidate_id, agent_results, evidence_package=evidence_package)
    return build_summary_row(materials.candidate_id, evidence_package, agent_results)


def _manual_transcript_status(materials) -> dict:
    transcript_path = materials.candidate_dir / "transcript.srt"
    exists = materials.srt_path is not None and transcript_path.exists()
    return {
        "auto_transcribe_enabled": False,
        "transcript_exists_before_run": exists,
        "transcript_generated": False,
        "transcript_path": str(transcript_path),
        "model": None,
        "error": None if exists else "未提供transcript.srt。",
        "message": "已发现 transcript.srt，直接读取现有字幕稿。" if exists else "未提供 transcript.srt，无法进行完整评审。",
    }


def _write_unscored_placeholders(schema, candidate_output: Path, reason: str) -> None:
    agents_dir = candidate_output / "agents"
    evidence_dir = candidate_output / "evidence"
    agents_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for indicator in schema.indicators:
        write_json(
            agents_dir / indicator.agent_file,
            {
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
            },
        )
    write_json(
        evidence_dir / "consistency_review.json",
        {
            "agent_name": "证据一致性复核Agent",
            "status": "not_scored",
            "summary": reason,
            "manual_review_points": [reason],
        },
    )
    write_json(
        evidence_dir / "bias_review.json",
        {
            "agent_name": "偏差审查Agent",
            "status": "not_scored",
            "summary": reason,
            "manual_review_points": [reason],
        },
    )
    write_json(
        agents_dir / "overall_review.json",
        {
            "agent_name": "整体性评价Agent",
            "status": "not_scored",
            "overall_summary": reason,
            "dimensions": {
                "evidence_limitations_and_review_focus": {
                    "summary": reason,
                    "evidence_limitations": [reason],
                    "high_priority_review_points": [reason],
                    "medium_priority_review_points": [],
                    "low_priority_review_points": [],
                }
            },
        },
    )
