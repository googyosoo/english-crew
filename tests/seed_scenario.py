import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import os
if not os.getenv("CREW_DATA_DIR"):
    # Guard against accidental write to real data/
    import tempfile
    default_test_dir = tempfile.mkdtemp(prefix="crew_seed_scenario_")
    os.environ["CREW_DATA_DIR"] = default_test_dir
    print(f"[TEST ISOLATION] CREW_DATA_DIR not set. Using isolated temp directory: {default_test_dir}")

from backend.app.db.database import get_db_connection, init_db
from backend.app.services.workspace_manager import get_workspace_dir, save_task_deliverable, copy_to_final

async def seed_eng1_scenario():
    async with get_db_connection() as db:
        # Clear existing test messages and tasks for eng1
        await db.execute("DELETE FROM messages WHERE channel_id = 'eng1'")
        await db.execute("DELETE FROM tasks WHERE request_id = 'req_scenario_1'")
        await db.execute("DELETE FROM approvals WHERE request_id = 'req_scenario_1'")

        # 1. Teacher Request
        req_id = "req_scenario_1"
        teacher_content = "영어I 3과 본문 어휘와 문법을 연계한 서술형 수행평가 문항 2개와 평가 루브릭을 설계해 줘."
        await db.execute(
            """
            INSERT INTO messages (id, channel_id, sender, type, content, metadata_json, created_at)
            VALUES ('msg_sc_1', 'eng1', 'teacher', 'text', ?, ?, '2026-11-06 09:10:00')
            """,
            (teacher_content, json.dumps({"request_id": req_id}))
        )

        # 2. Coordinator Dispatch
        _, abs_dir = get_workspace_dir("course", "영어I", "3과")
        t1_id = "tsk_item_writer"
        t2_id = "tsk_rubric_creator"

        t1_md = """# 영어I 3과 서술형 수행평가 문항

### [문항 1] 지문 빈칸 추론 및 핵심 어휘 활용 영작 (배점: 10점)
- **문항 설명**: 3과 본문 주요 개념(인공지능과 윤리적 의사결정)을 다룬 지문을 읽고, 빈칸에 들어갈 핵심 결론 문장을 조건에 맞추어 영작하시오.
- **조건**:
  1. 본문에 제시된 핵심 어휘 'accountability', 'algorithmic bias'를 반드시 포함할 것.
  2. 관계대명사 계속적 용법(, which)을 활용하여 1문장의 완전한 절로 서술할 것.
- **모범 답안**:
  Developers must ensure ethical accountability for algorithmic bias, which can otherwise lead to discriminatory outcomes.

### [문항 2] 필자의 주장 반박 및 논거 제시 서술형 (배점: 10점)
- **문항 설명**: 인공지능 창작물의 저작권 인정 여부에 대한 본문 주장을 읽고, 이에 대한 반대 의견을 논리적 근거 1가지와 함께 40단어 내외로 서술하시오.
- **모범 답안**:
  AI systems lack genuine human intent and consciousness; therefore, copyright protections should strictly remain reserved for human creators who direct the creative process.
"""

        t2_md = """# 영어I 3과 서술형 수행평가 채점 기준표 (루브릭)

| 평가 척도 | 수준 (배점) | 관찰 가능한 성취 기준 및 세부 설명 |
| :--- | :--- | :--- |
| **내용 타당성** | **탁월 (5점)** | 논제에서 요구한 핵심 개념을 정확히 파악하고 논리적 비약 없이 완전한 논거를 구성함. |
| | **보통 (3점)** | 핵심 개념은 다루었으나 논거 설명이 부분적으로 모호하거나 불충분함. |
| | **미흡 (1점)** | 논제와 무관하거나 핵심 주장이 결여됨. |
| **언어 형식 및 문법** | **탁월 (5점)** | 요구된 문법 구조(관계대명사 계속적 용법)와 어휘를 완벽히 준수하며 비문이 없음. |
| | **보통 (3점)** | 조건 어휘는 사용하였으나 시제나 수 일치 등 사소한 문법 오류가 1~2개 관찰됨. |
| | **미흡 (1점)** | 조건 어휘를 누락하거나 심각한 문법 오류로 문장의 의미 전달이 왜곡됨. |
"""

        save_task_deliverable(abs_dir, t1_id, t1_md)
        save_task_deliverable(abs_dir, t2_id, t2_md)

        tasks_meta = [
            {"id": t1_id, "bot": "assessment", "title": "서술형 문항 2종 출제", "deliverable": "문항 및 모범 답안", "status": "done", "output_path": f"data/workspaces/영어I/3과/{t1_id}.md"},
            {"id": t2_id, "bot": "assessment", "title": "분석적 채점 기준표(루브릭)", "deliverable": "4단계 평가 척도표", "status": "done", "output_path": f"data/workspaces/영어I/3과/{t2_id}.md"}
        ]

        await db.execute(
            """
            INSERT INTO messages (id, channel_id, sender, type, content, metadata_json, created_at)
            VALUES ('msg_sc_2', 'eng1', 'coordinator', 'dispatch', '영어I 3과 수행평가 문항 및 채점 기준표 제작 과업 분해', ?, '2026-11-06 09:10:05')
            """,
            (json.dumps({"request_id": req_id, "unit": "3과", "workspace_dir": "data/workspaces/영어I/3과", "tasks": tasks_meta}, ensure_ascii=False),)
        )

        for tm in tasks_meta:
            await db.execute(
                """
                INSERT INTO tasks (id, request_id, bot_id, title, deliverable, status, output_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (tm["id"], req_id, tm["bot"], tm["title"], tm["deliverable"], tm["status"], tm["output_path"])
            )

        # 3. Coordinator Report
        report_summary = "영어I 3과 단원 연계 서술형 평가 문항 2종과 4단계 분석적 루브릭 작성을 완료했습니다.\n- 문항 1, 2는 핵심 어휘 및 문법 성취기준에 부합하도록 출제되었습니다.\n- 루브릭은 학생 관찰 가능한 행동 지표로 세분화되었습니다."
        await db.execute(
            """
            INSERT INTO messages (id, channel_id, sender, type, content, metadata_json, created_at)
            VALUES ('msg_sc_3', 'eng1', 'coordinator', 'report', ?, ?, '2026-11-06 09:10:20')
            """,
            (report_summary, json.dumps({"request_id": req_id, "tasks": tasks_meta}, ensure_ascii=False))
        )

        # 4. Approval Request Card
        appr_id = "appr_sc_1"
        appr_question = "영어I 3과 서술형 수행평가 2문항 및 분석적 채점 기준표를 최종 확정하시겠습니까?"
        await db.execute(
            """
            INSERT INTO approvals (id, request_id, question, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (appr_id, req_id, appr_question)
        )
        await db.execute(
            """
            INSERT INTO messages (id, channel_id, sender, type, content, metadata_json, created_at)
            VALUES ('msg_sc_4', 'eng1', 'coordinator', 'approval', ?, ?, '2026-11-06 09:10:25')
            """,
            (appr_question, json.dumps({"request_id": req_id, "approval_id": appr_id, "status": "pending", "tasks": tasks_meta}, ensure_ascii=False))
        )

        await db.commit()
        print("PASS: Scenario seed created successfully in DB!")

if __name__ == "__main__":
    asyncio.run(seed_eng1_scenario())
