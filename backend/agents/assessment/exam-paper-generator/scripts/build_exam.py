#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_exam.py — 문항 JSON 스펙을 읽어 실제 원안지(.hwpx)를 조립하는 CLI.

사용법:
    python3 build_exam.py spec.json output.hwpx

spec.json 형식은 assets/spec_example.json 및 references/hwpx_build_guide.md 참조.

동작 개요:
  1. meta.template (기본값 "영어II") 에 맞는 원본 hwpx를 assets/templates/ 에서 로드
  2. 헤더/타이틀/안내문/푸터에서 학교명·학년·학기·시험명·과목명 등 리터럴 텍스트를
     정확히 일치하는 문자열만 치환 (구조는 절대 손대지 않음)
  3. "선택형(N문항), 서술형(M문항)이며 총 (N+M)문항" 안내문을 실제 문항 수로 갱신
  4. questions 배열을 순서대로 blocks.py 의 빌더로 변환해 본문에 append
  5. 저장 후 hwpx_engine.validate_hwpx() 로 기계적 정합성 검증, 실패 시 예외 발생
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import hwpx_engine as E
import blocks as B

TEMPLATES = B.TEMPLATES  # {"영어II": {...}, "공통영어2": {...}} — blocks.py 참조

# 템플릿별로 원본 hwpx에 실제로 박혀 있던 리터럴 값 — 치환 시 "이 문자열을 찾아서" 바꾼다.
# (두 파일 모두 같은 학교 원안지 서식이라 school/school_full 값은 동일하다.)
ORIGINAL_VALUES = {
    "영어II": {
        "school": "심인고", "school_full": "심인고등학교",
        "grade": "2학년", "semester": "2학기",
        "exam_name": "중간고사", "subject": "영어II",
        "total_pages": "7",
    },
    "공통영어2": {
        "school": "심인고", "school_full": "심인고등학교",
        "grade": "1학년", "semester": "2학기",
        "exam_name": "기말고사", "subject": "공통영어2",
        "total_pages": "8",
    },
}

BUILDERS = {
    "plain_choice5": B.build_plain_choice5,
    "embedded_underline": B.build_embedded_underline,
    "marker_passage": B.build_marker_passage,
    "insertion": B.build_insertion,
    "ab_table": B.build_ab_table,
    "abc_table": B.build_abc_table,
    "order_choices": B.build_order_choices,
    "translation_blank": B.build_translation_blank,
    "word_box": B.build_word_box,
}

DESCRIPTIVE_TYPES = {"translation_blank", "word_box"}


def build_header_mapping(meta: dict, original: dict) -> dict:
    mapping = {}
    if meta.get("school"):
        mapping[original["school_full"]] = meta["school"] + "등학교" if not meta["school"].endswith("고등학교") else meta["school"]
        mapping[original["school"]] = meta["school"]
    if meta.get("grade"):
        mapping[original["grade"]] = meta["grade"]
    if meta.get("semester"):
        mapping[original["semester"]] = meta["semester"]
    if meta.get("exam_name"):
        mapping[original["exam_name"]] = meta["exam_name"]
    if meta.get("subject"):
        mapping[original["subject"]] = meta["subject"]
    if meta.get("total_pages"):
        mapping[f'/{original["total_pages"]}'] = f'/{meta["total_pages"]}'
    return mapping


def build_exam(spec: dict, out_path: str, workdir: str = "/tmp/_hwpx_build"):
    meta = spec.get("meta", {})
    questions = spec["questions"]

    template_key = meta.get("template", "영어II")
    if template_key not in TEMPLATES:
        raise ValueError(f"알 수 없는 템플릿: {template_key}. 지원 템플릿: {list(TEMPLATES)}")
    template_file = TEMPLATES[template_key]["file"]
    anchors = TEMPLATES[template_key]["anchors"]
    original = ORIGINAL_VALUES[template_key]
    template_path = os.path.join(SCRIPT_DIR, "..", "assets", "templates", template_file)
    tmpl = E.load_template(template_path, workdir)

    n_obj = sum(1 for q in questions if q["type"] not in DESCRIPTIVE_TYPES)
    n_desc = sum(1 for q in questions if q["type"] in DESCRIPTIVE_TYPES)
    total = n_obj + n_desc

    header_map = build_header_mapping(meta, original)
    # "총 23문항" 부분과 "선택형(18문항)..." 부분이 서로 다른 run(hp:t)에 나뉘어
    # 있으므로(굵게 강조된 총 문항수만 별도 run) 각각 정확히 일치하는 조각으로 치환한다.
    header_map["선택형(18문항), 서술형(5문항)이며 총 "] = \
        f"선택형({n_obj}문항), 서술형({n_desc}문항)이며 총 "
    header_map["23문항"] = f"{total}문항"
    E.replace_text_everywhere(tmpl.sec_root, header_map)

    intro_range = anchors["intro"]["range"]
    intro_paras = [E.clone_para(p) for p in tmpl.top_paras()[intro_range[0]:intro_range[1] + 1]]
    footer_title_p = E.clone_para(B.get_para(tmpl, anchors["footer_title"]["idx"]))
    footer_box_p = E.clone_para(B.get_para(tmpl, anchors["footer_box"]["idx"]))

    question_blocks = []
    desc_counter = 0
    for q in questions:
        qtype = q["type"]
        if qtype not in BUILDERS:
            raise ValueError(f"알 수 없는 문항 유형: {qtype}. 지원 유형: {list(BUILDERS)}")
        params = {k: v for k, v in q.items() if k != "type"}
        # blocks.py 함수 시그니처와 맞추기 위한 키 정리 (stem/passage/gloss -> *_text)
        params = _normalize_params(qtype, params)
        if qtype in DESCRIPTIVE_TYPES:
            desc_counter += 1
            label = f"【서술형 {desc_counter}】 "
            params["stem_text"] = label + params.get("stem_text", "")
        block = BUILDERS[qtype](tmpl, anchors, **params)
        question_blocks.append(block)

    E.clear_body(tmpl.sec_root, keep_first_secpr_para=True)
    E.append_block(tmpl.sec_root, intro_paras)
    for block in question_blocks:
        E.append_block(tmpl.sec_root, block)
    E.append_block(tmpl.sec_root, [footer_title_p, footer_box_p])

    # 문항 수/내용이 원본과 달라지면 문서 전체의 줄 흐름이 바뀌므로, 캐시된
    # 줄 위치(linesegarray)를 모두 지워 여는 프로그램이 처음부터 다시
    # 배치하게 한다 — 지우지 않으면 글자가 겹쳐 보이는 문제가 생긴다.
    removed = E.strip_all_linesegarrays(tmpl.sec_root)
    print(f"[INFO] linesegarray {removed}개 제거(재계산 강제) — 겹침 방지")

    E.save_hwpx(workdir, tmpl.section_tree, out_path)

    problems = E.validate_hwpx(out_path)
    fatals = [p for p in problems if p[0] == "FATAL"]
    for level, msg in problems:
        print(f"[{level}] {msg}")
    if fatals:
        raise RuntimeError(f"{len(fatals)}건의 치명적 오류로 검증 실패 — 출력 파일을 신뢰하지 마세요.")
    return out_path


_ALIAS_MAP = {
    "passage": "passage_text",
    "gloss": "gloss_text",
    "stem": "stem_text",
}


def _normalize_params(qtype, params):
    """spec.json 의 편의 키(stem/passage/gloss 등)를 각 builder 함수의 정식
    인자명(stem_text/passage_text/gloss_text)으로 정리."""
    for short, full in _ALIAS_MAP.items():
        if short in params and full not in params:
            params[full] = params.pop(short)
        elif short in params and full in params:
            params.pop(short)
    if "answer_idx" not in params and "answer" in params:
        ans = params.pop("answer")
        params["answer_idx"] = ans if isinstance(ans, int) else "①②③④⑤".index(ans)
    return params


def main():
    ap = argparse.ArgumentParser(description="원안지(.hwpx) 조립기")
    ap.add_argument("spec_json", help="문항 스펙 JSON 경로")
    ap.add_argument("output_hwpx", help="출력 hwpx 경로")
    ap.add_argument("--workdir", default="/tmp/_hwpx_build")
    args = ap.parse_args()

    with open(args.spec_json, encoding="utf-8") as f:
        spec = json.load(f)

    out = build_exam(spec, args.output_hwpx, args.workdir)
    print(f"완료: {out}")


if __name__ == "__main__":
    main()
