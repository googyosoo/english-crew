import re
import os
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from backend.app.db.database import get_db_connection, get_data_dir

def get_default_export_dir() -> Path:
    """
    기본 내보내기 폴더: 사용자 문서(Documents) 폴더
    """
    doc_dir = Path.home() / "Documents"
    doc_dir.mkdir(parents=True, exist_ok=True)
    return doc_dir

def set_cell_background(cell, fill_hex: str):
    """
    테이블 셀 배경색 설정
    """
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """
    테이블 셀 패딩 설정
    """
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_formatted_paragraph(doc_or_cell, text: str, style: Optional[str] = None):
    """
    인라인 마크다운 볼드(**text**)를 docx run으로 변환하여 단락 추가
    """
    p = doc_or_cell.add_paragraph(style=style)
    # Parse bold **text**
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
            run = p.add_run(part[2:-2])
            run.bold = True
        else:
            p.add_run(part)
    return p

def convert_markdown_to_docx(content: str, docx_path: Path, doc_title: str):
    """
    마크다운 텍스트를 제목, 목록, 인용, 표 서식이 유지된 docx 문서로 변환합니다.
    """
    doc = Document()

    # 페이지 여백 설정 (1인치)
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)

    # 기본 스타일 글꼴 설정 (맑은 고딕)
    normal_style = doc.styles['Normal']
    normal_style.font.name = '맑은 고딕'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    lines = content.splitlines()
    in_table = False
    table_lines: List[str] = []

    def flush_table():
        nonlocal in_table, table_lines
        if not table_lines:
            return
        # Parse table lines
        header_cells = []
        data_rows = []
        sep_found = False

        for r_line in table_lines:
            cells = [c.strip() for c in r_line.strip().split("|")[1:-1]]
            if not cells:
                continue
            is_sep = all(bool(re.match(r"^[:\s-]+$", c)) for c in cells if c)
            if is_sep:
                sep_found = True
                continue
            if not sep_found:
                header_cells = cells
            else:
                data_rows.append(cells)

        # 빈 표 및 빈 행 생성 방지: 실제 내용이 하나라도 있어야 생성
        has_real_content = any(c.strip() for c in header_cells) or any(any(c.strip() for c in r) for r in data_rows)
        if not has_real_content:
            in_table = False
            table_lines = []
            return

        col_count = max(len(header_cells), max((len(r) for r in data_rows), default=0))
        if col_count > 0:
            table = doc.add_table(rows=0, cols=col_count)
            table.style = 'Table Grid'
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            # Add header row
            if header_cells:
                hdr_row = table.add_row()
                # 표 머리글 행이 페이지가 넘어가도 반복되도록 w:tblHeader 설정
                trPr = hdr_row._tr.get_or_add_trPr()
                trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

                for c_idx, h_text in enumerate(header_cells):
                    if c_idx < col_count:
                        cell = hdr_row.cells[c_idx]
                        set_cell_background(cell, "F2F4F7")
                        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
                        p = add_formatted_paragraph(cell, h_text)
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        for r in p.runs:
                            r.bold = True
                            r.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)

            # Add data rows
            for r_idx, r_cells in enumerate(data_rows):
                row = table.add_row()
                for c_idx, d_text in enumerate(r_cells):
                    if c_idx < col_count:
                        cell = row.cells[c_idx]
                        # Alternate row shading
                        if r_idx % 2 == 1:
                            set_cell_background(cell, "FAFAFB")
                        set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
                        # Handle <br> tags in cell content
                        sub_lines = d_text.split("<br>")
                        for s_idx, sl in enumerate(sub_lines):
                            p = add_formatted_paragraph(cell, sl.strip())
                            if c_idx == 0:
                                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                                for r in p.runs:
                                    r.bold = True

            # 행이 페이지 경계에서 깨지지 않도록 cantSplit 설정
            for row in table.rows:
                trPr = row._tr.get_or_add_trPr()
                trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

        in_table = False
        table_lines = []

    for line in lines:
        stripped = line.strip()

        # Check if line is part of a markdown table
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            continue
        elif in_table:
            flush_table()

        if not stripped:
            continue

        # Header 1
        if stripped.startswith("# "):
            h = doc.add_heading(level=1)
            run = h.add_run(stripped[2:].strip())
            run.font.name = '맑은 고딕'
            run.font.size = Pt(18)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
        # Header 2
        elif stripped.startswith("## "):
            h = doc.add_heading(level=2)
            run = h.add_run(stripped[3:].strip())
            run.font.name = '맑은 고딕'
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
        # Header 3
        elif stripped.startswith("### "):
            h = doc.add_heading(level=3)
            run = h.add_run(stripped[4:].strip())
            run.font.name = '맑은 고딕'
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
        # Bullet list
        elif stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
            text = stripped[2:].strip()
            add_formatted_paragraph(doc, text, style='List Bullet')
        # Numbered list
        elif re.match(r"^\d+\.\s+", stripped):
            text = re.sub(r"^\d+\.\s+", "", stripped).strip()
            add_formatted_paragraph(doc, text, style='List Number')
        # Blockquote
        elif stripped.startswith(">"):
            text = re.sub(r"^>\s*", "", stripped).strip()
            p = add_formatted_paragraph(doc, text)
            p.paragraph_format.left_indent = Inches(0.3)
            for r in p.runs:
                r.italic = True
                r.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
        # Horizontal rule
        elif stripped in ["---", "***", "___"]:
            # Horizontal rule spacing
            continue
        # Regular paragraph
        else:
            add_formatted_paragraph(doc, stripped)

    if in_table:
        flush_table()

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_path))


async def assemble_request_content(request_id: str) -> Tuple[str, Dict[str, Any]]:
    """
    요청 ID에 해당하는 승인된 산출물들을
    교육과정 -> 문항 -> 모범답안 -> 루브릭 순서로 병합하여 마크다운 텍스트와 메타데이터를 반환합니다.
    """
    async with get_db_connection() as db:
        # Check approval status
        async with db.execute(
            """
            SELECT a.status, a.request_id, m.channel_id, m.metadata_json
            FROM approvals a
            JOIN messages m ON a.id = json_extract(m.metadata_json, '$.approval_id')
            WHERE a.request_id = ?
            LIMIT 1
            """,
            (request_id,)
        ) as cursor:
            row = await cursor.fetchone()

        # If not found via approval message, query approval directly
        channel_id = "eng1"
        unit = "1과"
        if row:
            appr_status = row["status"]
            channel_id = row["channel_id"]
            if row["metadata_json"]:
                try:
                    meta = json.loads(row["metadata_json"])
                    unit = meta.get("unit", unit)
                except Exception:
                    pass
        else:
            async with db.execute("SELECT status FROM approvals WHERE request_id = ?", (request_id,)) as cur2:
                r2 = await cur2.fetchone()
                appr_status = r2["status"] if r2 else "unknown"

        # Fetch channel course name
        async with db.execute("SELECT name, course FROM channels WHERE id = ?", (channel_id,)) as c_cur:
            ch_row = await c_cur.fetchone()
            course_name = ch_row["course"] or ch_row["name"] if ch_row else "영어Ⅰ"

        # Fetch tasks in order
        async with db.execute(
            "SELECT id, bot_id, title, deliverable, status, output_path FROM tasks WHERE request_id = ? ORDER BY id ASC",
            (request_id,)
        ) as t_cur:
            tasks = [dict(t) for t in await t_cur.fetchall()]

    # Collect deliverables: check final/ first, then output_path
    curriculum_text = ""
    assessment_text = ""
    other_texts = []

    for t in tasks:
        out_p = t.get("output_path")
        if not out_p:
            continue
        p = Path(out_p)
        # Check final/ directory first if approved
        final_p = p.parent / "final" / p.name
        target_path = final_p if final_p.exists() else p

        if target_path.exists():
            txt = target_path.read_text(encoding="utf-8").strip()
            if t["bot_id"] == "curriculum":
                curriculum_text = txt
            elif t["bot_id"] == "assessment":
                assessment_text = txt
            else:
                other_texts.append(txt)

    # Order: 교육과정 -> 문항 -> 모범답안 -> 루브릭
    combined_sections = []
    
    # 1. 교육과정
    if curriculum_text:
        combined_sections.append(curriculum_text)

    # 2. 평가 산출물 (문항, 모범답안, 루브릭)
    if assessment_text:
        combined_sections.append(assessment_text)

    # 3. 기타 산출물
    for ot in other_texts:
        combined_sections.append(ot)

    full_markdown = "\n\n---\n\n".join(combined_sections)
    
    metadata = {
        "request_id": request_id,
        "channel_id": channel_id,
        "course_name": course_name,
        "unit": unit,
        "approved": appr_status == "approved"
    }
    return full_markdown, metadata


async def export_request_document(
    request_id: str,
    export_format: str = "docx",
    target_dir: Optional[str] = None
) -> Tuple[Path, str]:
    """
    요청을 docx 또는 md 파일로 내보내고 (파일 경로, 파일명)을 반환합니다.
    파일명: {과목}_{단원}_{YYYYMMDD}.{ext}
    """
    full_md, meta = await assemble_request_content(request_id)
    if not full_md:
        raise ValueError(f"요청 ID {request_id}에 해당하는 산출물을 찾을 수 없습니다.")

    today_str = datetime.date.today().strftime("%Y%m%d")
    clean_course = meta["course_name"].replace(" ", "_")
    clean_unit = meta["unit"].replace(" ", "_")
    
    ext = export_format.lower()
    filename = f"{clean_course}_{clean_unit}_{today_str}.{ext}"

    dest_dir = Path(target_dir) if target_dir else get_default_export_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_file = dest_dir / filename

    if ext == "docx":
        convert_markdown_to_docx(full_md, out_file, f"{meta['course_name']} {meta['unit']} 평가 설계")
    elif ext == "md":
        out_file.write_text(full_md, encoding="utf-8")
    else:
        raise ValueError(f"지원하지 않는 내보내기 형식입니다: {export_format}")

    return out_file, filename
