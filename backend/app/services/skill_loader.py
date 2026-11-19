import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def get_resource_root() -> Path:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent.parent

# Base directory for skills copied inside the app
SKILLS_DIR = get_resource_root() / "backend" / "agents" / "skills"

# Registry of the 3 specialized skills for English Crew v1.1.0
SPECIALIZED_SKILLS = {
    "suneung-english-creator": {
        "name": "수능형 영어 변형문제 제작",
        "description": "수능/모의고사 영어 영역(빈칸추론, 글의 순서, 문장 삽입, 요약문 등) 지문 및 문항 생성",
        "folder": "suneung-english-creator",
        "target_bots": ["assessment"],
        "keywords": [
            "수능", "모의고사", "변형문제", "빈칸추론", "문장 삽입", "글의 순서",
            "suneung", "수능형", "평가원", "기출", "객관식 5지선다", "오답 매력도"
        ]
    },
    "edu-sentence-frame": {
        "name": "수준별 학술 문장 틀 및 서술형 비계",
        "description": "학생 수준(상/중/하)에 맞춘 단계별 학술 문장 틀(Sentence Frames) 및 담화 표제어 제공",
        "folder": "edu-sentence-frame",
        "target_bots": ["lesson", "assessment"],
        "keywords": [
            "문장틀", "문장 틀", "문장 프레임", "sentence frame", "비계", "서술형 비계",
            "에세이 틀", "담화 표제어", "글쓰기 비계", "문장 템플릿", "수준별 프레임"
        ]
    },
    "edu-vocab-tiering": {
        "name": "3-Tier 어휘 수준 분류 및 교수 설계",
        "description": "Beck & McKeown 3-Tier(Tier 1 기본어, Tier 2 학술·수능 빈출어, Tier 3 전문소재어) 분석 및 단어 카드, 퀴즈 설계",
        "folder": "edu-vocab-tiering",
        "target_bots": ["lesson", "curriculum", "assessment"],
        "keywords": [
            "어휘", "단어", "티어", "tier", "vocab", "어휘 분석", "어휘 수준",
            "단어 카드", "어휘 퀴즈", "3-tier", "어휘 티어링", "어휘 지도", "핵심 어휘"
        ]
    }
}

def match_skills(bot_id: str, context_text: Optional[str] = None) -> List[str]:
    """
    Analyzes the request context text and returns a list of matching skill IDs
    that are applicable to the specified bot.
    """
    if not context_text:
        return []

    text_lower = context_text.lower()
    matched = []

    for skill_id, meta in SPECIALIZED_SKILLS.items():
        if bot_id not in meta["target_bots"]:
            continue

        for kw in meta["keywords"]:
            if kw.lower() in text_lower:
                matched.append(skill_id)
                break

    return matched

def get_skills_dir() -> Path:
    return get_resource_root() / "backend" / "agents" / "skills"

def load_dynamic_skills(bot_id: str, context_text: Optional[str] = None) -> str:
    """
    Dynamically loads only the specialized SKILL.md contents that match the request context.
    If no specialized skills match, returns an empty string without polluting the prompt.
    """
    matched_ids = match_skills(bot_id, context_text)
    if not matched_ids:
        return ""

    skills_base = get_skills_dir()
    loaded_sections = []

    for skill_id in matched_ids:
        skill_meta = SPECIALIZED_SKILLS.get(skill_id)
        if not skill_meta:
            continue

        skill_path = skills_base / skill_meta["folder"] / "SKILL.md"
        if skill_path.exists():
            try:
                content = skill_path.read_text(encoding="utf-8")
                loaded_sections.append(
                    f"\n--- [동적 특화 스킬 탑재: {skill_meta['name']} ({skill_id})] ---\n"
                    f"{content}\n"
                )
                logger.info(f"[DynamicSkillLoader] Successfully injected {skill_id} for bot '{bot_id}'")
            except Exception as e:
                logger.warning(f"[DynamicSkillLoader] Failed to read skill {skill_path}: {e}")

    return "\n".join(loaded_sections)
