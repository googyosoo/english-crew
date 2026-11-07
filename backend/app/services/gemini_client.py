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

# Retry delays for 503 (UNAVAILABLE) and 429 (RESOURCE_EXHAUSTED) errors
RETRY_DELAYS = [3.0, 8.0, 15.0]

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

    # Rule 5: Assessment bot specific guidelines
    if bot_id == "assessment":
        md_contents.append(
            """--- [평가봇 필수 준수 규정] ---
1. 교사가 본문을 제공하지 않았으면 본문 내용, 인용, 등장인물을 지어내지 말고, 산출물 맨 위에 '본문 미제공: 일반 주제 기준으로 작성함'을 반드시 명시하십시오.
2. 루브릭 수준 구분은 주관적 부사('완벽하게', '잘', '부분적으로' 등)가 아니라 관찰 가능한 기준(개수, 조건 포함 여부, 문법 및 표현 오류 빈도 등)으로 객관적으로 구분하십시오.
3. 성취기준 코드는 해당 과목의 공식 기준만 사용하고, 확실하지 않으면 코드를 임의로 지어내거나 쓰지 마십시오.

"""
        )

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
    reject_reason: Optional[str] = None,
    context_notes: Optional[List[Dict[str, Any]]] = None
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

    context_section = ""
    if context_notes:
        note_lines = []
        for n in context_notes:
            note_lines.append(f"- [{n.get('kind', '메모')}] (단원: {n.get('unit', '')}):\n{n.get('content', '')}")
        context_section = f"\n[현재 채널의 수업 맥락 및 본문 자료]\n" + "\n".join(note_lines) + "\n"

    user_prompt = f"""[교사 요청]
과목 채널: {channel_info.get('name', '영어I')} (타입: {channel_info.get('type', 'course')}, 코드: {channel_info.get('course_code', '')})
요청 내용: {content}
{context_section}
[현재 활성화된 배정 가능 팀원봇 목록 (이 목록에 있는 봇 ID만 배정해야 합니다)]
{bots_desc}

[과업 분해 및 디스패치 주의사항]
1. 과업은 1~4개로 분해하십시오.
   - 문항 출제 및 평가 설계 요청 시, 반드시 교육과정봇(curriculum)이 성취기준과 평가 요소를 먼저 도출하도록 선행 과업으로 배정하십시오 (depends_on=[]).
   - 평가봇(assessment)과 수업봇(lesson)은 교육과정봇의 산출물을 활용하므로 depends_on: ["curriculum"]을 명시하십시오.
   - 동일 문항에 대한 '문항 출제'와 '채점 루브릭'은 하나의 과업으로 묶으십시오(나누지 마십시오).
2. 전체 교무회의(all) 채널에서 과목(영어I, 심화영어I 등)을 특정할 수 없다면, tasks를 비우고 clarification 필드에 교사에게 과목을 되묻는 정중한 안내 문장을 작성하십시오.
3. 각 과업의 bot 필드는 반드시 위 활성 봇 목록의 bot_id 중 하나여야 합니다.
4. 산출물(deliverable)은 구체적인 분량과 형태를 명시하십시오.
5. approval_question은 교사가 '예/아니오'로 답할 수 있는 결재 질문이어야 합니다.
"""

    if reject_reason:
        user_prompt += f"\n[이전 결재 반려 사유]\n교사 피드백: {reject_reason}\n위 반려 사유를 반영하여 과업 계획과 결재 질문을 재구성하십시오.\n"

    for attempt in range(len(RETRY_DELAYS) + 1):
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
            err_str = str(e)
            if attempt < len(RETRY_DELAYS) and any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Coordinator rate/overload ({err_str[:80]}), retrying in {delay}s (attempt {attempt + 1}/3)...")
                await asyncio.sleep(delay)
            else:
                raise e

async def execute_bot_task(
    bot_id: str,
    title: str,
    deliverable: str,
    course_name: str,
    unit: str,
    teacher_request: str,
    extra_context: Optional[str] = None,
    feedback_instructions: Optional[str] = None
) -> str:
    cfg = get_gemini_config()
    api_key = cfg["api_key"]
    model_name = cfg["model"]

    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. backend/.env에 유효한 API 키를 입력해 주세요.")

    client = genai.Client(api_key=api_key)
    system_instruction = load_bot_instructions(bot_id)

    extra_section = ""
    if extra_context:
        extra_section = f"\n[선행 과업 산출물 및 참고 맥락 자료]\n{extra_context}\n"

    feedback_section = ""
    if feedback_instructions:
        feedback_section = f"\n[이전 산출물 검사 피드백 및 수정 지침]\n{feedback_instructions}\n위 지침을 반드시 준수하여 지적된 오류를 완벽히 수정해 다시 작성하십시오.\n"

    prompt = f"""[작업 요청]
과목: {course_name}
단원: {unit}
과업 제목: {title}
요청 산출물: {deliverable}
교사 원문 요청: {teacher_request}
{extra_section}{feedback_section}
위 요청에 따라 전문 영역 기준에 부합하는 완성된 Markdown 결과물을 생성하시오.
불필요한 서두나 잡담 없이 바로 산출물 본문을 출력하시오.
"""

    for attempt in range(len(RETRY_DELAYS) + 1):
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
            err_str = str(e)
            if attempt < len(RETRY_DELAYS) and any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Bot task rate/overload ({err_str[:80]}), retrying in {delay}s (attempt {attempt + 1}/3)...")
                await asyncio.sleep(delay)
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

    for attempt in range(len(RETRY_DELAYS) + 1):
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
            err_str = str(e)
            if attempt < len(RETRY_DELAYS) and any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Summary rate/overload ({err_str[:80]}), retrying in {delay}s (attempt {attempt + 1}/3)...")
                await asyncio.sleep(delay)
            else:
                logger.warning(f"Failed to summarize with coordinator: {e}")
                return {
                    "summary": "팀원봇의 과업 수행이 완료되었습니다.",
                    "approval_question": initial_question
                }

