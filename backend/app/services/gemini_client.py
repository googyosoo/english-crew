import os
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from google import genai
from google.genai import types

from backend.app.models.schemas import DispatchPlan, TaskSpec

logger = logging.getLogger(__name__)

# Base directories
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = WORKSPACE_DIR / "backend" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

def get_gemini_config() -> Dict[str, str]:
    # Re-read in case .env was updated
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    return {"api_key": api_key, "model": model}

# Files excluded from prompt loading
EXCLUDED_PROMPT_FILES = {
    "hwpx_build_guide.md",
}

def load_bot_instructions(bot_id: str) -> str:
    """
    Recursively collects all .md files under backend/agents/{bot_id}/
    and prepends the required non-exec instruction constraint.
    Skips any files defined in EXCLUDED_PROMPT_FILES.
    """
    agents_dir = WORKSPACE_DIR / "backend" / "agents" / bot_id
    if not agents_dir.exists():
        return "당신은 고등학교 영어 교육 전문 AI 어시스턴트입니다."

    md_contents = [
        "파일 생성·스크립트 실행 지시는 무시하고 결과를 Markdown 텍스트로만 출력하시오.\n\n"
    ]

    for md_file in sorted(agents_dir.rglob("*.md")):
        if md_file.name in EXCLUDED_PROMPT_FILES:
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
            md_contents.append(f"\n--- [참조 지침: {md_file.name}] ---\n{text}\n")
        except Exception as e:
            logger.warning(f"Failed to read {md_file}: {e}")

    return "\n".join(md_contents)

async def create_dispatch_plan(
    content: str,
    channel_info: Dict[str, Any],
    active_bots: List[Dict[str, Any]],
    reject_reason: Optional[str] = None
) -> DispatchPlan:
    cfg = get_gemini_config()
    api_key = cfg["api_key"]
    model_name = cfg["model"]

    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. backend/.env에 유효한 API 키를 입력해 주세요.")

    client = genai.Client(api_key=api_key)
    system_instruction = load_bot_instructions("coordinator")

    active_bot_lines = [
        f"- {b['id']} ({b['name']}): {b['role']}" for b in active_bots
    ]
    bots_desc = "\n".join(active_bot_lines)

    user_prompt = f"""[교사 요청]
과목 채널: {channel_info.get('name', '영어I')}
요청 내용: {content}

[현재 활성화된 배정 가능 팀원봇 목록 (이 목록에 있는 봇 ID만 배정해야 합니다)]
{bots_desc}

[주의사항]
1. 과업은 1~4개로 분해하십시오.
2. 각 과업의 bot 필드는 반드시 위 활성 봇 목록의 bot_id 중 하나여야 합니다. 비활성 봇에게 배정하지 마십시오.
3. 산출물(deliverable)은 구체적인 분량과 형태를 명시하십시오.
4. approval_question은 교사가 '예/아니오'로 답할 수 있는 결재 질문이어야 합니다.
"""

    if reject_reason:
        user_prompt += f"\n[이전 결재 반려 사유]\n교사 피드백: {reject_reason}\n위 반려 사유를 반영하여 과업 계획과 결재 질문을 재구성하십시오.\n"

    for attempt in range(4):
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=DispatchPlan,
                    temperature=0.2,
                )
            )
            result_text = response.text
            return DispatchPlan.model_validate_json(result_text)
        except Exception as e:
            if attempt < 3 and ("503" in str(e) or "UNAVAILABLE" in str(e)):
                logger.warning(f"Coordinator 503 unavailable, retrying in {2 * (attempt + 1)}s...")
                await asyncio.sleep(2 * (attempt + 1))
            else:
                raise e

async def execute_bot_task(
    bot_id: str,
    title: str,
    deliverable: str,
    course_name: str,
    unit: str,
    teacher_request: str
) -> str:
    cfg = get_gemini_config()
    api_key = cfg["api_key"]
    model_name = cfg["model"]

    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. backend/.env에 유효한 API 키를 입력해 주세요.")

    client = genai.Client(api_key=api_key)
    system_instruction = load_bot_instructions(bot_id)

    prompt = f"""[작업 요청]
과목: {course_name}
단원: {unit}
과업 제목: {title}
요청 산출물: {deliverable}
교사 원문 요청: {teacher_request}

위 요청에 따라 전문 영역 기준에 부합하는 완성된 Markdown 결과물을 생성하시오.
불필요한 서두나 잡담 없이 바로 산출물 본문을 출력하시오.
"""

    for attempt in range(3):
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4,
                )
            )
            return response.text
        except Exception as e:
            if attempt < 2 and ("503" in str(e) or "UNAVAILABLE" in str(e)):
                logger.warning(f"503 unavailable encountered, retrying in {2 * (attempt + 1)}s...")
                await asyncio.sleep(2 * (attempt + 1))
            else:
                raise e

async def summarize_and_finalize_approval(
    initial_question: str,
    task_results: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Summarize team deliverables in 3 lines or fewer, and refine the approval question.
    Returns: {"summary": "...", "approval_question": "..."}
    """
    cfg = get_gemini_config()
    api_key = cfg["api_key"]
    model_name = cfg["model"]

    if not api_key:
        return {
            "summary": "작업 산출물 생성이 완료되었습니다.",
            "approval_question": initial_question
        }

    client = genai.Client(api_key=api_key)
    system_instruction = load_bot_instructions("coordinator")

    deliverables_text = "\n".join([
        f"- [{r.get('title', '')}]: {r.get('content', '')[:500]}..."
        for r in task_results
    ])

    prompt = f"""[작업 산출물 취합 보고 요청]
다음 팀원봇 작업 산출물을 확인하고, 교사에게 보고할 3줄 이내의 핵심 요약과 최종 결재 질문을 작성하십시오.

산출물 요약 목록:
{deliverables_text}

기존 결재 질문: {initial_question}

[출력 형식 JSON]
{{
  "summary": "3줄 이내의 객관적 산출물 요약",
  "approval_question": "교사가 승인/반려할 수 있는 명확한 결재 질문"
}}
"""

    for attempt in range(4):
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            data = json.loads(response.text)
            return {
                "summary": data.get("summary", "작업이 성공적으로 완료되었습니다."),
                "approval_question": data.get("approval_question", initial_question)
            }
        except Exception as e:
            if attempt < 3 and ("503" in str(e) or "UNAVAILABLE" in str(e)):
                logger.warning(f"Summary 503 unavailable, retrying in {2 * (attempt + 1)}s...")
                await asyncio.sleep(2 * (attempt + 1))
            else:
                logger.warning(f"Failed to summarize with coordinator: {e}")
                return {
                    "summary": "팀원봇의 과업 수행이 완료되었습니다.",
                    "approval_question": initial_question
                }

