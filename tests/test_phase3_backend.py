import asyncio
import os
import sys
import shutil
import tempfile
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
from backend.app.services.anonymizer import anonymize_text, deanonymize_text
from backend.app.services.checks.rubric_check import check_rubric
from backend.app.services.checks.seteuk_check import check_seteuk, calculate_neis_bytes
from backend.app.services.workspace_manager import get_workspace_dir, save_task_deliverable

def test_anonymization_and_deanonymization():
    students = [
        {"id": "st1", "course_code": "ENG1", "class_no": 3, "student_no": 12, "name": "김철수"},
        {"id": "st2", "course_code": "ENG1", "class_no": 3, "student_no": 15, "name": "이영희"},
        {"id": "st3", "course_code": "ENG1", "class_no": 3, "student_no": 20, "name": "박민수"},
    ]

    original_teacher_input = "김철수는 본문 3과 발표에서 유창하게 질문했고, 이영희는 모둠 활동을 주도함."
    
    # 1. Anonymize
    masked_text, restore_map = anonymize_text(original_teacher_input, students)
    
    assert "김철수" not in masked_text, "김철수 실명이 남아있습니다!"
    assert "이영희" not in masked_text, "이영희 실명이 남아있습니다!"
    assert "3-12" in masked_text, "가명 3-12가 누락되었습니다!"
    assert "3-15" in masked_text, "가명 3-15가 누락되었습니다!"
    print("PASS: Anonymization masked real names to numbers:", masked_text)

    # 2. Deanonymize
    gemini_simulated_response = "학생 3-12는 적극적인 태도로 발표를 진행했으며, 3-15와 협력하여 과제를 완수함."
    restored_text = deanonymize_text(gemini_simulated_response, restore_map)
    assert "김철수" in restored_text
    assert "이영희" in restored_text
    assert "3-12" not in restored_text
    assert "3-15" not in restored_text
    print("PASS: Deanonymization restored numbers to real names:", restored_text)


def test_rubric_check_logic():
    # 1. Bad rubric: only degree adverbs without observable criteria
    bad_rubric = """
| 평가요소 (배점) | 4점 (우수) | 3점 (보통) | 2점 (미흡) | 1점 (매우 미흡) |
|:---|:---|:---|:---|:---|
| **내용 구성** (8점) | 매우 우수함 | 대체로 잘함 | 다소 미흡함 | 거의 못함 |
"""
    bad_res = check_rubric(bad_rubric)
    assert not bad_res.passed, "부사만 있는 루브릭이 통과되었습니다!"
    assert any("정도 부사" in issue for issue in bad_res.issues)
    print("PASS: Detected bad rubric with only degree adverbs:", bad_res.issues)

    # 2. Good rubric: observable criteria with counts and specific criteria
    good_rubric = """
| 평가요소 (배점) | 8점 (우수) | 6점 (보통) | 4점 (미흡) | 2점 (매우 미흡) |
|:---|:---|:---|:---|:---|
| **내용 구성** (8점) | 핵심 조건 3개 이상 포함하여 논리적으로 서술함 | 핵심 조건 2개를 포함하여 서술함 | 핵심 조건 1개만 포함하거나 오류 3회 이상 발생 | 핵심 조건을 전혀 제시하지 못함 |
"""
    good_res = check_rubric(good_rubric)
    assert good_res.passed, f"올바른 루브릭이 실패했습니다: {good_res.issues}"
    print("PASS: Valid observable rubric passed successfully!")

    # 3. Score mismatch test (Header 8점 vs Level score 10점)
    mismatch_rubric = """
| 평가요소 (배점) | 10점 (우수) | 6점 (보통) | 4점 (미흡) | 2점 (매우 미흡) |
|:---|:---|:---|:---|:---|
| **내용 구성** (8점) | 조건 3개 이상 포함 | 조건 2개 포함 | 조건 1개 포함 | 조건 없음 |
"""
    score_res = check_rubric(mismatch_rubric)
    assert not score_res.passed, "배점 불일치가 감지되지 않았습니다!"
    assert any("배점" in issue for issue in score_res.issues)
    print("PASS: Detected score mismatch:", score_res.issues)

    # 4. Unauthorized curriculum code test
    code_rubric = """
## 성취기준
- [10영01-05] 글을 읽고 세부 정보를 파악할 수 있다.
"""
    allowed = ["[12영I-02-01]", "[12영I-03-01]"]
    code_res = check_rubric(code_rubric, allowed_codes=allowed)
    assert not code_res.passed, "인가되지 않은 성취기준 코드가 통과되었습니다!"
    assert any("승인하지 않은 성취기준 코드" in issue for issue in code_res.issues)
    print("PASS: Detected unauthorized curriculum code:", code_res.issues)


def test_seteuk_check_logic():
    # 1. Prohibited items test
    bad_seteuk = "토익(TOEIC) 900점을 획득하였으며, 영어 올림피아드 금상을 수상하고 하버드대학교 진학을 희망함."
    bad_res = check_seteuk(bad_seteuk)
    assert not bad_res.passed
    assert len(bad_res.issues) >= 3
    print("PASS: Seteuk check caught multiple prohibitions:", bad_res.issues)

    # 2. Byte calculation and clean seteuk test
    good_seteuk = "영어 텍스트에 나타난 사회적 쟁점을 비판적으로 분석하고 자신의 논리적 견해를 타당한 근거와 함께 영어 에세이로 작성함. 모둠 토의에서 다양한 의견을 경청하며 합의점을 도출하는 의사소통 역량을 발휘함."
    good_res = check_seteuk(good_seteuk)
    assert good_res.passed
    assert good_res.bytes_count <= 1500
    print(f"PASS: Clean seteuk passed ({good_res.bytes_count} bytes)!")


def test_context_notes_and_students_api():
    client = TestClient(app)

    # 1. Context Notes API
    # Save textbook body
    body_res = client.post("/channels/eng1/context", json={
        "course_code": "ENG1",
        "unit": "3과",
        "kind": "본문",
        "content": "Technology has transformed the way we communicate and learn across the globe."
    })
    assert body_res.status_code == 200
    print("PASS: Saved textbook body to context_notes:", body_res.json())

    # Get context notes
    get_res = client.get("/channels/eng1/context?unit=3과")
    assert get_res.status_code == 200
    notes = get_res.json()
    assert len(notes) >= 1
    assert notes[0]["kind"] == "본문"
    assert "Technology has transformed" in notes[0]["content"]
    print("PASS: Fetched 3과 context notes successfully:", len(notes))

    # 2. Students API
    st_res = client.post("/channels/eng1/students", json=[
        {"course_code": "ENG1", "class_no": 3, "student_no": 1, "name": "홍길동"},
        {"course_code": "ENG1", "class_no": 3, "student_no": 2, "name": "김영희"}
    ])
    assert st_res.status_code == 200
    assert st_res.json()["count"] == 2

    st_get = client.get("/channels/eng1/students")
    assert st_get.status_code == 200
    assert len(st_get.json()) >= 2
    print("PASS: Students API verified successfully:", len(st_get.json()))


def test_approval_adds_lesson_record_automatically():
    client = TestClient(app)

    async def setup_approval_db():
        async with get_db_connection() as db:
            await db.execute("INSERT OR REPLACE INTO channels (id, name, type, course_code) VALUES ('eng1', '영어I', 'course', 'ENG1')")
            req_id = "req_phase3_appr"
            appr_id = "appr_phase3_test"
            await db.execute(
                "INSERT OR REPLACE INTO approvals (id, request_id, question, status) VALUES (?, ?, '논술형 1문항과 루브릭을 확정하시겠습니까?', 'pending')",
                (appr_id, req_id)
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_p3_appr', 'eng1', 'coordinator', 'approval', '확정하시겠습니까?', ?)
                """,
                (f'{{"request_id": "{req_id}", "approval_id": "{appr_id}", "unit": "3과", "status": "pending"}}',)
            )
            await db.commit()

    asyncio.run(setup_approval_db())

    # Approve
    res = client.post("/approvals/appr_phase3_test", json={"decision": "approved"})
    assert res.status_code == 200

    # Verify context_notes has a new '차시기록'
    client = TestClient(app)
    c_res = client.get("/channels/eng1/context")
    assert c_res.status_code == 200
    all_notes = c_res.json()
    record_note = next((n for n in all_notes if n["kind"] == "차시기록"), None)
    assert record_note is not None, "차시기록이 context_notes에 자동 추가되지 않았습니다!"
    assert "확정" in record_note["content"]
    print("PASS: Approval successfully added lesson record (차시기록) to context_notes:", record_note["content"])


if __name__ == "__main__":
    try:
        asyncio.run(init_db())
        test_anonymization_and_deanonymization()
        test_rubric_check_logic()
        test_seteuk_check_logic()
        test_context_notes_and_students_api()
        test_approval_adds_lesson_record_automatically()
        print("\nALL ISOLATED PHASE 3 BACKEND TESTS PASSED 100%!")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("PASS: Cleaned up isolated test temp directory.")
