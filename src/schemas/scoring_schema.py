from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Indicator:
    id: str
    section: str
    agent_file: str
    name: str
    max_score: float
    focus: str
    cautions: list[str]


@dataclass(frozen=True)
class ScoringModule:
    id: str
    name: str
    max_score: float
    required_material: str
    indicators: list[Indicator]


@dataclass(frozen=True)
class ScoringSchema:
    scoring_mode: str
    total_score: float
    score_precision: float
    modules: list[ScoringModule]
    indicators: list[Indicator]
    evidence_sufficiency: dict[str, str]


def load_scoring_schema(path: Path) -> ScoringSchema:
    if not path.exists():
        raise FileNotFoundError(f"评分schema不存在：{path}")
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    modules: list[ScoringModule] = []
    indicators: list[Indicator] = []
    for module_data in data.get("modules", []):
        module_indicators = [
            Indicator(
                id=item["id"],
                section=module_data["id"],
                agent_file=item.get("agent_file", f"{item['id']}.json"),
                name=item["name"],
                max_score=float(item["max_score"]),
                focus=item["focus"],
                cautions=list(item.get("cautions", [])),
            )
            for item in module_data.get("indicators", [])
        ]
        indicators.extend(module_indicators)
        modules.append(
            ScoringModule(
                id=module_data["id"],
                name=module_data["name"],
                max_score=float(module_data["max_score"]),
                required_material=module_data.get("required_material", ""),
                indicators=module_indicators,
            )
        )
    total_score = float(data.get("total_score", 0))
    if total_score != 100:
        raise ValueError("scoring_schema.yaml必须包含完整评分表100分。")
    if len(modules) != 3:
        raise ValueError("scoring_schema.yaml必须包含案例整体设计、教案、现场教学展示三个模块。")
    return ScoringSchema(
        scoring_mode=data["scoring_mode"],
        total_score=total_score,
        score_precision=float(data.get("score_precision", 0.5)),
        modules=modules,
        indicators=indicators,
        evidence_sufficiency=dict(data.get("evidence_sufficiency", {})),
    )
