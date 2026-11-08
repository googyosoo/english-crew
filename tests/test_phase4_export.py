import asyncio
import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))

# Setup isolated temp data dir
TEMP_DIR = Path(tempfile.mkdtemp(prefix="crew_test_export_"))
os.environ["CREW_DATA_DIR"] = str(TEMP_DIR)
os.environ["PYTHONIOENCODING"] = "utf-8"

import docx
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db_connection
from backend.app.services.exporter import (
    convert_markdown_to_docx,
    assemble_request_content,
    export_request_document,
    get_default_export_dir
)

client = TestClient(app)

class TestPhase41Export(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        asyncio.run(init_db())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

    def test_markdown_to_docx_conversion(self):
        sample_md = """# [영어Ⅰ] 논술형 평가 문항 및 루브릭

## 1. 성취기준 연계 정보
- **성취기준 코드**: [12영Ⅰ-02-04] 듣거나 읽은 내용을 말이나 글로 요약한다.
- **평가요소**: 일반 주제에 대한 자신의 견해 서술하기

---

## 2. 논술형 과제
다음 주제에 대해 **3문장**, **40~50단어**의 영문 주장문을 작성하시오.

> We must limit our digital device usage to protect our mental health.

---

## 3. 채점 루브릭

| 평가요소 | A수준 [10점] | B수준 [8점] | C수준 [6점] | D수준 [4점] |
| :--- | :--- | :--- | :--- | :--- |
| **내용 논리성** | 핵심 주장 및 근거 2개 모두 충족 | 근거 2개 중 1개 충족 | 근거 누락 | 조건 0개 충족 |
| **언어 형식** | 오류 0~1개 이하 | 오류 2~3개 이하 | 오류 4~5개 | 오류 6개 이상 |
"""
        out_docx = TEMP_DIR / "test_out.docx"
        convert_markdown_to_docx(sample_md, out_docx, "테스트 문서")
        self.assertTrue(out_docx.exists(), "docx file was not created!")
        self.assertGreater(out_docx.stat().st_size, 1000, "docx file size too small!")

        # Verify docx structure using python-docx
        doc = docx.Document(str(out_docx))
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        self.assertTrue(any("논술형 평가 문항" in h for h in headings))
        self.assertTrue(any("채점 루브릭" in h for h in headings))

        # Verify table in docx
        self.assertGreaterEqual(len(doc.tables), 1, "Table was not converted to docx table!")
        tbl = doc.tables[0]
        self.assertEqual(len(tbl.columns), 5, f"Expected 5 columns, got {len(tbl.columns)}")
        self.assertEqual(tbl.rows[0].cells[0].text.strip(), "평가요소")
        print("PASS: Markdown to docx conversion successfully preserved headings, lists, and tables!")

    def test_export_endpoints_and_settings(self):
        # 1. Test settings: GET & POST export_dir
        res_get = client.get("/settings/export_dir")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn("export_dir", res_get.json())

        custom_dir = str(TEMP_DIR / "custom_exports")
        res_post = client.post("/settings/export_dir", json={"export_dir": custom_dir})
        self.assertEqual(res_post.status_code, 200)
        self.assertEqual(res_post.json()["export_dir"], custom_dir)

        # 2. Seed a request with approved status and tasks
        req_id = "req_export_test"
        work_dir = TEMP_DIR / "workspaces" / "영어Ⅰ" / "3과"
        final_dir = work_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)

        curriculum_file = final_dir / "tsk_cur.md"
        curriculum_file.write_text("## 1. 교육과정 성취기준\n[12영Ⅰ-01-01] 성취기준 원문", encoding="utf-8")
        assessment_file = final_dir / "tsk_ass.md"
        assessment_file.write_text("## 2. 논술형 문항 및 루브릭\n문항 본문 내용", encoding="utf-8")

        async def seed_data():
            async with get_db_connection() as db:
                await db.execute(
                    """
                    INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                    VALUES ('msg_appr_exp', 'eng1', 'coordinator', 'approval', '승인 완료', ?)
                    """,
                    (json.dumps({"request_id": req_id, "unit": "3과", "approval_id": "appr_exp"}, ensure_ascii=False),)
                )
                await db.execute(
                    "INSERT INTO approvals (id, request_id, question, status) VALUES ('appr_exp', ?, '승인?', 'approved')",
                    (req_id,)
                )
                await db.execute(
                    "INSERT INTO tasks (id, request_id, bot_id, title, deliverable, status, output_path) VALUES ('tsk_cur', ?, 'curriculum', '교육과정', '과업', 'done', ?)",
                    (req_id, str(curriculum_file))
                )
                await db.execute(
                    "INSERT INTO tasks (id, request_id, bot_id, title, deliverable, status, output_path) VALUES ('tsk_ass', ?, 'assessment', '평가문항', '과업', 'done', ?)",
                    (req_id, str(assessment_file))
                )
                await db.commit()

        import json
        asyncio.run(seed_data())

        # 3. Test export docx
        res_exp_docx = client.get(f"/requests/{req_id}/export?format=docx")
        self.assertEqual(res_exp_docx.status_code, 200)
        self.assertIn("application/vnd.openxmlformats", res_exp_docx.headers["content-type"])
        self.assertTrue(res_exp_docx.headers["content-disposition"].startswith("attachment;"))
        self.assertIn("docx", res_exp_docx.headers["content-disposition"])
        print("PASS: GET /requests/{id}/export?format=docx returned 200 with attachment!")

        # 4. Test export md
        res_exp_md = client.get(f"/requests/{req_id}/export?format=md")
        self.assertEqual(res_exp_md.status_code, 200)
        self.assertIn("text/markdown", res_exp_md.headers["content-type"])
        self.assertIn("교육과정 성취기준", res_exp_md.text)
        self.assertIn("논술형 문항 및 루브릭", res_exp_md.text)
        print("PASS: GET /requests/{id}/export?format=md successfully exported unified markdown!")

        # 5. Test unapproved request rejection (400)
        unappr_req = "req_unapproved"
        async def seed_unapproved():
            async with get_db_connection() as db:
                await db.execute(
                    "INSERT INTO approvals (id, request_id, question, status) VALUES ('appr_pending', ?, '승인?', 'pending')",
                    (unappr_req,)
                )
                await db.commit()
        asyncio.run(seed_unapproved())

        res_unappr = client.get(f"/requests/{unappr_req}/export?format=docx")
        self.assertEqual(res_unappr.status_code, 400)
        print("PASS: Unapproved request correctly rejected with 400 status!")


if __name__ == "__main__":
    unittest.main()
