import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.services.skill_loader import (
    match_skills,
    load_dynamic_skills,
    SPECIALIZED_SKILLS,
    get_skills_dir
)
from backend.app.services.gemini_client import (
    load_bot_instructions,
    execute_bot_task
)

def test_skills_directory_and_files_exist():
    """앱 내부에 복사된 3개 특화 스킬 폴더 및 SKILL.md 파일 존재 여부 검증"""
    skills_dir = get_skills_dir()
    assert skills_dir.exists(), f"Skills base directory does not exist: {skills_dir}"

    for skill_id, meta in SPECIALIZED_SKILLS.items():
        skill_file = skills_dir / meta["folder"] / "SKILL.md"
        assert skill_file.exists(), f"SKILL.md missing for {skill_id}: {skill_file}"
        content = skill_file.read_text(encoding="utf-8")
        assert len(content) > 100, f"SKILL.md content too short for {skill_id}"

def test_match_skills_suneung_english_creator():
    """수능형 변형문제 키워드 및 대상 봇(assessment) 매칭 검증"""
    # assessment 봇에 수능 변형문제 요청 -> 매칭 성공
    matched = match_skills("assessment", "고2 영어I 3과 본문으로 수능형 빈칸추론 5지선다 변형문제를 만들어주세요.")
    assert "suneung-english-creator" in matched

    # 다른 봇(record)에 동일 요청 -> 대상 봇 불일치로 매칭 제외
    matched_record = match_skills("record", "고2 영어I 3과 본문으로 수능형 빈칸추론 5지선다 변형문제를 만들어주세요.")
    assert "suneung-english-creator" not in matched_record

def test_match_skills_edu_sentence_frame():
    """서술형 문장 비계 키워드 및 대상 봇(lesson, assessment) 매칭 검증"""
    # lesson 봇에 문장틀 요청 -> 매칭 성공
    matched_lesson = match_skills("lesson", "학생들의 서술형 평가 대비를 위해 수준별 문장틀과 담화 표제어를 제공해주세요.")
    assert "edu-sentence-frame" in matched_lesson

    # assessment 봇에도 문장 비계 매칭 가능
    matched_assessment = match_skills("assessment", "에세이 수행평가 서술형 비계 문장 프레임 설계")
    assert "edu-sentence-frame" in matched_assessment

    # curriculum 봇에는 매칭 제외
    matched_curriculum = match_skills("curriculum", "서술형 문장틀 작성")
    assert "edu-sentence-frame" not in matched_curriculum

def test_match_skills_edu_vocab_tiering():
    """3-Tier 어휘 분류 키워드 및 대상 봇(lesson, curriculum, assessment) 매칭 검증"""
    # lesson 봇에 어휘 티어링 요청 -> 매칭 성공
    matched = match_skills("lesson", "3과 단어의 3-Tier 어휘 수준 분류 및 단어 카드 제작")
    assert "edu-vocab-tiering" in matched

    # curriculum 봇에 어휘 수준 분석 요청 -> 매칭 성공
    matched_curr = match_skills("curriculum", "본문 어휘 티어링 및 핵심 어휘 분석")
    assert "edu-vocab-tiering" in matched_curr

    # 무관한 내용 -> 매칭 없음
    matched_none = match_skills("lesson", "중간고사 일정 안내문 작성")
    assert len(matched_none) == 0

def test_load_dynamic_skills_injection():
    """요청 내용에 맞게 SKILL.md가 정상 주입되는지 검증"""
    # 1. 수능 변형문제 요청 시 suneung-english-creator 주입
    injected_suneung = load_dynamic_skills("assessment", "수능형 빈칸추론 변형문제 출제")
    assert "suneung-english-creator" in injected_suneung
    assert "오답 매력도" in injected_suneung or "빈칸" in injected_suneung

    # 2. 문장 비계 요청 시 edu-sentence-frame 주입
    injected_frame = load_dynamic_skills("lesson", "서술형 문장 프레임 비계 구성")
    assert "edu-sentence-frame" in injected_frame
    assert "Sentence Frames" in injected_frame or "문장 틀" in injected_frame

    # 3. 어휘 티어링 요청 시 edu-vocab-tiering 주입
    injected_vocab = load_dynamic_skills("lesson", "3-Tier 어휘 수준 분류 및 지도")
    assert "edu-vocab-tiering" in injected_vocab
    assert "Tier 2" in injected_vocab or "Beck" in injected_vocab

    # 4. 키워드 미해당 시 빈 문자열 반환 (프롬프트 오염 방지)
    injected_empty = load_dynamic_skills("assessment", "일반적인 질문입니다.")
    assert injected_empty == ""

def test_load_bot_instructions_isolation_and_integration():
    """load_bot_instructions에서 기본 프롬프트 격리 및 동적 주입 정상 동작 검증"""
    # 일반 요청: skills 폴더 내용이 혼입되지 않음
    prompt_normal = load_bot_instructions("assessment", "단순 수행평가 배점표 작성")
    assert "[동적 특화 스킬 탑재: " not in prompt_normal

    # 수능 변형문제 요청: 동적 주입 태그 및 스킬 내용 포함
    prompt_suneung = load_bot_instructions("assessment", "수능형 모의고사 변형문제 제작")
    assert "[동적 특화 스킬 탑재: 수능형 영어 변형문제 제작 (suneung-english-creator)]" in prompt_suneung

def test_execute_bot_task_passes_context_for_skill_loading():
    """execute_bot_task가 요청 컨텍스트를 load_bot_instructions에 전달하는지 검증"""
    import asyncio
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "## 수능형 변형문제 산출물 예시"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    async def _run():
        with patch("backend.app.services.gemini_client.genai.Client", return_value=mock_client), \
             patch("backend.app.services.gemini_client.get_gemini_config", return_value={"api_key": "dummy_key", "model": "gemini-3.5-flash-lite"}):

            res = await execute_bot_task(
                bot_id="assessment",
                course_name="영어I",
                unit="3과",
                title="수능형 변형문제 출제",
                deliverable="수능 빈칸추론 1문항",
                teacher_request="3과 본문으로 수능형 빈칸추론 변형문제를 출제해주세요."
            )

            assert res == "## 수능형 변형문제 산출물 예시"
            call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
            sys_instruction = call_kwargs["config"].system_instruction
            assert "suneung-english-creator" in sys_instruction

    asyncio.run(_run())
