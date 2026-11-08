import asyncio
import os
import sys
import shutil
import tempfile
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Isolated Test Data Directory before importing backend modules
temp_dir = tempfile.mkdtemp(prefix="crew_test_phase3_")
os.environ["CREW_DATA_DIR"] = temp_dir

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db_connection
from backend.app.services.anonymizer import anonymize_text, deanonymize_text, get_mask_tag
from backend.app.services.checks.rubric_check import check_rubric
from backend.app.services.checks.seteuk_check import check_seteuk, calculate_neis_bytes
from backend.app.services.checks.curriculum_check import check_curriculum, get_course_standards_text

def test_anonymization_and_deanonymization():
    students = [
        {"id": "st1", "course_code": "ENG1", "class_no": 3, "student_no": 1, "name": "김일"},
        {"id": "st2", "course_code": "ENG1", "class_no": 3, "student_no": 12, "name": "김십이"},
        {"id": "st3", "course_code": "ENG1", "class_no": 13, "student_no": 1, "name": "이십삼"},
    ]

    original_teacher_input = "김일은 질문하고, 김십이는 발표하며, 이십삼은 기록함."
    
    # 1. Anonymize with [S03-01] format
    masked_text, restore_map = anonymize_text(original_teacher_input, students)
    
    # Collision test: 3-1, 3-12, 13-1 should not collide
    assert "[S03-01]" in masked_text, "[S03-01] 토큰이 누락되었습니다!"
    assert "[S03-12]" in masked_text, "[S03-12] 토큰이 누락되었습니다!"
    assert "[S13-01]" in masked_text, "[S13-01] 토큰이 누락되었습니다!"
    assert "김일" not in masked_text
    assert "김십이" not in masked_text
    assert "이십삼" not in masked_text
    print("PASS: Anonymization collision resistance ([S03-01], [S03-12], [S13-01]):", masked_text)

    # 2. Deanonymize
    simulated_response = "[S03-01]은 적극적으로 질문했고, [S03-12]는 발표를 이끌었으며, [S13-01]은 협력함."
    restored_text = deanonymize_text(simulated_response, restore_map)
    assert "김일" in restored_text
    assert "김십이" in restored_text
    assert "이십삼" in restored_text
    assert "[S03-01]" not in restored_text
    assert "[S03-12]" not in restored_text
    assert "[S13-01]" not in restored_text
    print("PASS: Deanonymization restored [Sxx-yy] tokens to real names:", restored_text)


def test_gemini_payload_anonymity_with_5_students_csv():
    # 5 students CSV representation
    csv_rows = [
        {"class_no": 3, "student_no": 10, "name": "홍길동"},
        {"class_no": 3, "student_no": 11, "name": "김영수"},
        {"class_no": 3, "student_no": 12, "name": "박지민"},
        {"class_no": 3, "student_no": 13, "name": "최수진"},
        {"class_no": 3, "student_no": 14, "name": "강태호"},
    ]

    raw_teacher_prompt = (
        "기록봇, 이번 학기 세특 초안 작성해줘. "
        "홍길동은 영작문에서 어휘력이 매우 뛰어났고, 김영수와 박지민은 모둠 토론을 주도함. "
        "최수진과 강태호는 오류를 능동적으로 수정하고 협력함."
    )

    masked_payload, r_map = anonymize_text(raw_teacher_prompt, csv_rows)

    # Physical verification: exactly 0 occurrences of any real name in the payload sent to Gemini
    real_names = ["홍길동", "김영수", "박지민", "최수진", "강태호"]
    for rn in real_names:
        assert rn not in masked_payload, f"보안 위반: 학생 실명 '{rn}'이 Gemini 전송 페이로드에 포함되어 있습니다!"

    print("PASS: Physical Evidence: Exactly 0 real names present in Gemini payload!")
    print("  -> Masked Payload:", masked_payload)

    # All 5 mask tags must be present
    for st in csv_rows:
        expected_tag = get_mask_tag(st["class_no"], st["student_no"])
        assert expected_tag in masked_payload, f"Expected tag {expected_tag} not in payload!"

    # Deanonymization verification
    restored = deanonymize_text(masked_payload, r_map)
    for rn in real_names:
        assert rn in restored, f"실명 '{rn}'이 복원되지 않았습니다!"
    print("PASS: Successfully deanonymized all 5 students locally.")


def test_curriculum_check_logic():
    # 1. Valid curriculum output
    valid_output = """
# 영어I 교육과정 분석
- [12영Ⅰ-01-01] 말이나 글의 세부 정보를 파악한다.
- [12영Ⅰ-01-02] 말이나 글의 주제나 요지를 파악한다.
"""
    res1 = check_curriculum(valid_output)
    assert res1.passed, f"공인 교육과정 출력이 실패했습니다: {res1.issues}"
    print("PASS: Valid curriculum standard & exact statement passed!")

    # 2. Fabricated code
    fake_code_output = """
- [12영Ⅰ-99-99] 임의로 날조한 성취기준 진술문입니다.
"""
    res2 = check_curriculum(fake_code_output)
    assert not res2.passed
    assert any("실재하지 않는" in iss or "존재하지 않는" in iss for iss in res2.issues)
    print("PASS: Fabricated curriculum code rejected:", res2.issues)

    # 3. Statement mismatch
    mismatch_output = """
- [12영Ⅰ-01-01] 공식 원문과 다르게 조작된 텍스트입니다.
"""
    res3 = check_curriculum(mismatch_output)
    assert not res3.passed
    assert any("일치하지 않습니다" in iss for iss in res3.issues)
    print("PASS: Statement mismatch rejected:", res3.issues)


def test_rubric_check_logic():
    # 1. Regression test: tsk_3583c3ec fixture must FAIL
    fixture_path = Path("tests/fixtures/regression_rubric_tsk_3583c3ec.md")
    assert fixture_path.exists(), "회귀 픽스처 파일이 누락되었습니다!"
    fixture_content = fixture_path.read_text(encoding="utf-8")
    reg_res = check_rubric(fixture_content)
    assert not reg_res.passed, "회귀 테스트 실패: tsk_3583c3ec는 신규 강화 규칙에서 반드시 수정 필요 판정이 나와야 합니다!"
    print("PASS: Regression fixture tsk_3583c3ec correctly rejected with issues count:", len(reg_res.issues))

    # 2. Valid rubric with quantitative criteria and descending scores on each row
    valid_rubric = """
# 영어I 논술형 문항 및 4수준 채점 루브릭
총점: 12점

| 평가 요소 | 수준 4 | 수준 3 | 수준 2 | 수준 1 |
|:---|:---|:---|:---|:---|
| 내용 타당성 [12영Ⅰ-01-01] | 4점: 본문 실천 방안 2가지 이상 제시함 | 3점: 본문 실천 방안 1개만 제시함 | 2점: 본문 실천 방안 0개이나 관련 내용 1문장 서술함 | 1점: 관련 내용을 전혀 제시하지 못함 (0개) |
| 영작문 완성도 [12영Ⅰ-02-01] | 4점: 지정 어휘 2개 이상 활용하고 3문장 이상 작성함 | 3점: 지정 어휘 1개 활용하고 2문장 작성함 | 2점: 지정 어휘 0개이고 1문장 작성함 | 1점: 영문 작성을 수행하지 못함 (0문장) |
| 어법 정확성 | 4점: 어법 오류 0회 유지함 | 3점: 어법 오류 1회 발생함 | 2점: 어법 오류 2회 발생함 | 1점: 어법 오류 3회 이상 발생함 |
"""
    v_res = check_rubric(valid_rubric)
    assert v_res.passed, f"올바른 정량 루브릭이 실패했습니다: {v_res.issues}"
    print("PASS: Valid quantitative rubric passed successfully!")

    # 3. New Specific Regression Fixture (a): Must FAIL (degree adverbs with score suffix)
    fixture_a = """
# 루브릭 검사 (a)
총점: 4점

| 평가 요소 | 수준 4 | 수준 3 | 수준 2 | 수준 1 |
|:---|:---|:---|:---|:---|
| 내용 (4점) | 핵심 내용을 매우 정확하게 이해함 (4점) | 대체로 이해함 (3점) | 부분적으로 이해함 (2점) | 거의 이해하지 못함 (1점) |
"""
    res_a = check_rubric(fixture_a)
    assert not res_a.passed, "회귀 픽스처 (a)가 실패하지 않고 통과되었습니다 (점수 표기 우회 방어 실패)!"
    print("PASS: Regression fixture (a) correctly rejected (score suffix did not bypass degree checks):", res_a.issues)

    # 4. New Specific Regression Fixture (b): Must PASS (genuine quantitative counts with score suffix)
    fixture_b = """
# 루브릭 검사 (b)
총점: 4점

| 평가 요소 | 수준 4 | 수준 3 | 수준 2 | 수준 1 |
|:---|:---|:---|:---|:---|
| 내용 (4점) | 본문 근거 3개 이상 제시 (4점) | 본문 근거 2개 제시 (3점) | 본문 근거 1개 제시 (2점) | 본문 근거 0개 (1점) |
"""
    res_b = check_rubric(fixture_b)
    assert res_b.passed, f"회귀 픽스처 (b)가 통과하지 못했습니다: {res_b.issues}"
    print("PASS: Regression fixture (b) passed 100% cleanly!")


def test_seteuk_check_and_byte_counter_3_cases():
    # Verify byte counting against byte_counter.py logic
    cases = [
        "교내 영어 발표 활동에서 생태적 책임을 주제로 유창하게 발표함.",
        "Climate Change and Global Citizenship (12영Ⅰ-01-01)\n영문 에세이를 작성하고 피드백을 수용함.",
        "A quick brown fox jumps over the lazy dog. 12345! @#$%^&*()\r\n한글과 영문 혼합 텍스트."
    ]

    for idx, text in enumerate(cases, 1):
        # byte_counter.py reference formula
        expected = sum(3 if "가" <= ch <= "힣" else 1 for ch in text)
        actual = calculate_neis_bytes(text)
        assert expected == actual, f"Byte counter mismatch on case {idx}: {expected} vs {actual}"
    print("PASS: 3 byte-counter parity test cases verified 100%!")

    # Format checks: middle dot, tilde, parenthesis, verb ending
    bad_fmt1 = "환경·생태 문제를 탐구함."
    assert not check_seteuk(bad_fmt1).passed
    assert any("가운데점" in iss for iss in check_seteuk(bad_fmt1).issues)

    bad_fmt2 = "2026.03.02.~2026.07.18. 동안 활동함."
    assert not check_seteuk(bad_fmt2).passed
    assert any("물결표" in iss for iss in check_seteuk(bad_fmt2).issues)

    bad_fmt3 = "영문 에세이(지속가능성)를 작성함."
    assert not check_seteuk(bad_fmt3).passed
    assert any("괄호 병기" in iss for iss in check_seteuk(bad_fmt3).issues)

    bad_fmt4 = "생태적 실천 방안을 조사하고 영문으로 발표했다."
    assert not check_seteuk(bad_fmt4).passed
    assert any("명사형 종결 위반" in iss for iss in check_seteuk(bad_fmt4).issues)

    print("PASS: All Seteuk format checks (middle dot, tilde, parenthesis, noun endings) caught violations correctly!")


def test_channels_courses_md_alignment():
    client = TestClient(app)
    res = client.get("/channels")
    assert res.status_code == 200
    channels = res.json()
    assert len(channels) == 8, f"채널 개수가 8개가 아닙니다: {len(channels)}"
    
    expected_courses = {
        "general": None,
        "common1": "공통영어1",
        "common2": "공통영어2",
        "eng1": "영어Ⅰ",
        "eng2": "영어Ⅱ",
        "readwrite": "영어 독해와 작문",
        "adv_readwrite": "심화 영어 독해와 작문",
        "media": "미디어 영어",
    }
    
    ch_dict = {c["id"]: c for c in channels}
    for ch_id, exp_course in expected_courses.items():
        assert ch_id in ch_dict, f"채널 {ch_id}가 누락되었습니다!"
        assert ch_dict[ch_id].get("course") == exp_course, f"채널 {ch_id}의 course({ch_dict[ch_id].get('course')})가 {exp_course}와 다릅니다!"

    # Deprecated channels check
    for old_id in ["adv_eng1", "adv_read1", "career_eng"]:
        assert old_id not in ch_dict, f"구버전 채널 {old_id}가 삭제되지 않았습니다!"

    print("PASS: channels table aligned 100% with docs/source-skills/COURSES.md (8 channels, course column verified)!")


def test_context_notes_and_students_api():
    client = TestClient(app)

    # 1. Add Textbook note
    res = client.post("/channels/eng1/context", json={
        "course_code": "ENG1",
        "unit": "3과",
        "kind": "본문",
        "content": "Living a sustainable life is imperative for modern youth."
    })
    assert res.status_code == 200
    print("PASS: Context textbook note saved.")

    # 2. Get notes
    res2 = client.get("/channels/eng1/context?unit=3과")
    assert res2.status_code == 200
    notes = res2.json()
    assert len(notes) >= 1
    assert notes[0]["kind"] == "본문"
    print("PASS: Fetched 3과 context notes.")


def test_approval_adds_lesson_record_automatically():
    client = TestClient(app)

    async def setup_approval():
        async with get_db_connection() as db:
            # Insert report message with summary
            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_test_rep', 'eng1', 'coordinator', 'report', '영어I 3과 핵심 논술형 평가 문항 개발 완료\n2. 4수준 루브릭 작성 완료', ?)
                """,
                (json.dumps({"request_id": "req_phase3_test", "summary": "영어I 3과 핵심 논술형 평가 문항 개발 완료\n2. 4수준 루브릭 작성 완료"}, ensure_ascii=False),)
            )
            # Insert approval message
            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_test_appr', 'eng1', 'coordinator', 'approval', '승인 요청', ?)
                """,
                (json.dumps({"request_id": "req_phase3_test", "unit": "3과", "approval_id": "appr_phase3_test"}, ensure_ascii=False),)
            )
            # Insert approval row
            await db.execute(
                """
                INSERT INTO approvals (id, request_id, question, status)
                VALUES ('appr_phase3_test', 'req_phase3_test', '승인하시겠습니까?', 'pending')
                """
            )
            await db.commit()

    asyncio.run(setup_approval())

    # Approve
    res = client.post("/approvals/appr_phase3_test", json={"decision": "approved"})
    assert res.status_code == 200

    # Verify context_notes has a new '차시기록' with exact unit and coordinator summary first line
    c_res = client.get("/channels/eng1/context")
    assert c_res.status_code == 200
    all_notes = c_res.json()
    record_note = next((n for n in all_notes if n["kind"] == "차시기록"), None)
    assert record_note is not None, "차시기록이 추가되지 않았습니다!"
    assert record_note["unit"] == "3과", f"차시기록 unit이 일치하지 않습니다: {record_note['unit']}"
    assert record_note["content"] == "영어I 3과 핵심 논술형 평가 문항 개발 완료", f"내용이 코디봇 요약 첫 줄과 다릅니다: {record_note['content']}"
    print("PASS: Approval successfully added lesson record (차시기록) with exact unit and first summary line!")


def test_phase4_0_rubric_check_enhancements():
    from backend.app.services.checks.rubric_check import check_rubric

    # 1. Regression fixture: regression_rubric_no_body.md MUST fail
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "regression_rubric_no_body.md"
    assert fixture_path.exists(), "regression_rubric_no_body.md does not exist!"
    res = check_rubric(fixture_path.read_text(encoding="utf-8"))
    assert not res.passed, "regression_rubric_no_body.md should have failed!"
    # Check that issues contain content D and organization C/D
    all_issues_str = " ".join(res.issues)
    assert "29행" in all_issues_str or "31행" in all_issues_str or "수량 기준" in all_issues_str or "미흡" in all_issues_str
    print(f"PASS: regression_rubric_no_body.md correctly caught {len(res.issues)} issues!")

    # 2. Condition n mismatch in the same row
    mismatched_row_rubric = """
# 루브릭 테스트

| 평가요소 | A 수준 | B 수준 | C 수준 | D 수준 |
| :--- | :--- | :--- | :--- | :--- |
| 조건 충족도 (10점) | 4개 중 4개 충족 (10점) | 조건 4개 중 3개 충족 (8점) | 조건 3개 중 2개 충족 (6점) | 조건 4개 중 1개 충족 (4점) |
"""
    res_mismatch = check_rubric(mismatched_row_rubric)
    assert not res_mismatch.passed, "Mismatched condition n should fail!"
    assert any("불일치" in issue for issue in res_mismatch.issues), f"Missing mismatch issue in: {res_mismatch.issues}"
    print("PASS: Inconsistent condition count (n) within the same row correctly caught!")

    # 3. Clean rubric with scope score formats [5~6점] correctly stripped before check
    valid_with_scope_scores = """
# 루브릭 테스트

| 평가요소 | A 수준 | B 수준 | C 수준 | D 수준 |
| :--- | :--- | :--- | :--- | :--- |
| 내용 요약 (10점) | [9~10점] 핵심 근거 3개 이상 제시 | [7~8점] 핵심 근거 2개 제시 | [5~6점] 핵심 근거 1개 제시 | [0~4점] 핵심 근거 0개 제시 |
"""
    res_scope = check_rubric(valid_with_scope_scores)
    assert res_scope.passed, f"Valid rubric with scope scores failed: {res_scope.issues}"
    print("PASS: Scope score formats [5~6점] stripped cleanly without breaking quantitative checks!")


def test_phase4_0_answer_check():
    from backend.app.services.checks.answer_check import check_model_answer

    # Case 1: Meets all conditions
    valid_prompt = """
## 2. 논술형 평가 문항
다음 일반 주제에 대해 30~50단어 내외, 2~3문장의 영문 에세이를 작성하시오.

## 3. 모범 답안
> In modern society, continuous learning is essential for personal growth. It enables individuals to adapt to technological changes effectively. Therefore, developing a habit of daily reading contributes to long-term success.
"""
    v_res = check_model_answer(valid_prompt)
    assert v_res.passed, f"Valid answer check failed: {v_res.issues}"
    print(f"PASS: AnswerCheck passed valid answer ({v_res.actual_words} words, {v_res.actual_sentences} sentences)")

    # Case 2: Word count too low
    short_prompt = """
## 2. 논술형 평가 문항
150단어 이상 200단어 이내로 서술하시오.

## 3. 모범 답안
> Technology changes communication quickly and effectively.
"""
    s_res = check_model_answer(short_prompt)
    assert not s_res.passed, "Too short answer should fail!"
    assert any("최소 요구 조건" in i for i in s_res.issues), f"Wrong issue: {s_res.issues}"
    print("PASS: Under-length model answer correctly caught by AnswerCheck!")

    # Case 3: Sentence count too high
    long_sentences_prompt = """
## 2. 논술형 평가 문항
반드시 2문장 이내로 작성하시오.

## 3. 모범 답안
> First sentence is here. Second sentence is here. Third sentence is here.
"""
    ls_res = check_model_answer(long_sentences_prompt)
    assert not ls_res.passed, "Too many sentences should fail!"
    assert any("최대 허용 조건" in i for i in ls_res.issues), f"Wrong issue: {ls_res.issues}"
    print("PASS: Over-sentence model answer correctly caught by AnswerCheck!")


if __name__ == "__main__":
    try:
        asyncio.run(init_db())
        test_channels_courses_md_alignment()
        test_anonymization_and_deanonymization()
        test_gemini_payload_anonymity_with_5_students_csv()
        test_curriculum_check_logic()
        test_rubric_check_logic()
        test_phase4_0_rubric_check_enhancements()
        test_phase4_0_answer_check()
        test_seteuk_check_and_byte_counter_3_cases()
        test_context_notes_and_students_api()
        test_approval_adds_lesson_record_automatically()
        print("\n=======================================================")
        print("ALL ISOLATED PHASE 3 BACKEND TESTS PASSED 100%!")
        print("=======================================================")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("PASS: Cleaned up isolated test temp directory.")
