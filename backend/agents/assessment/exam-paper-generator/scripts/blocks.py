#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blocks.py — 실제 원안지 템플릿에서 검증된 "문항 유형별 블록"을 앵커 인덱스로
찾아내고, 새 내용으로 채워 넣는 빌더 함수 모음.

이 스킬은 서로 다른 두 원안지 파일을 베이스 템플릿으로 지원한다. 각 템플릿은
header.xml 스타일 ID가 서로 다르므로, 한 템플릿에서 뽑은 블록을 다른 템플릿의
본문에 붙이면 안 된다 — 그래서 앵커 인덱스를 템플릿별로 별도 딕셔너리
(ANCHORS_ENG2 / ANCHORS_COMMON2)로 관리하고, 모든 빌더 함수는 어느 템플릿을
쓸지 호출자가 넘겨주는 `anchors` 딕셔너리를 받는다. `TEMPLATES` 가 템플릿
키(사용자가 spec.json meta.template 에 적는 이름) → (파일명, 앵커) 매핑이다.

앵커 인덱스는 각 hwpx의 section0.xml 최상위 문단 목록(0-based, 표 내부 문단
제외)을 실제로 열어 확인한 값이다. (scripts/inspect_template.py 로 재확인 가능)

지원 블록 유형과 커버하는 실제 문항 유형(references/question_types_*.md 참조):
  PLAIN_CHOICE5      : 요지/주제/제목/내용일치/내용불일치/함축의미/글의목적/
                        필자주장/심경 등 "지문 + 5지선다 한 줄씩" 전 유형
  EMBEDDED_UNDERLINE : 어법상 틀린 것 찾기, 문맥상 낱말 쓰임 부적절한 것 찾기
                        (지문 속 ①~⑤ 밑줄 후보 + 정답 형광펜, 별도 선택지 줄 없음)
  MARKER_PASSAGE     : 무관한 문장 찾기 (지문 속 ①~⑤ 문장 앞 표시, 밑줄 없음)
  INSERTION          : 주어진 문장 삽입 위치 찾기 (박스 문장 + ( ① )~( ⑤ ) 위치표시)
  AB_TABLE           : 빈칸 (A)(B) 추론, 요약문 (A)(B) 완성 (6행×4열 표)
  ABC_TABLE          : 어법 (A)(B)(C) 박스 선택 (6행×6열 표) — 공통영어2 템플릿 전용
  ORDER_CHOICES      : 문단 순서 배열 (A)(B)(C) 3문단 + "① (A)-(B)-(C)" 2줄×3
  TRANSLATION_BLANK  : 서술형 - 우리말 해석 / 함축 의미 우리말 서술
  WORD_BOX           : 서술형 - <조건> + <Word Box> 영작 배열

각 빌더는 (paragraphs: list[lxml.Element]) 를 반환한다. 호출자는 이를
sec_root 에 순서대로 append 하면 된다.
"""

import copy
from lxml import etree
import hwpx_engine as E

Q = E._q


# --------------------------------------------------------------------------
# 앵커: 영어II 템플릿 (2학년, 영어II_원안지.hwpx)
# --------------------------------------------------------------------------

ANCHORS_ENG2 = {
    "intro": {"range": (0, 4)},               # 헤더 타이틀 + 안내문 3줄 + 공백
    "footer_title": {"idx": 271},
    "footer_box": {"idx": 272},
    "plain_choice5": {                          # 요지 문항을 표본으로 사용
        "stem": 5, "passage": 6, "gloss": 7, "spacer_before": 8,
        "choices": (9, 10, 11, 12, 13), "spacer_after": 14,
    },
    "embedded_underline": {                      # 어법 문항을 표본으로 사용
        "stem": 41, "passage": 42,
    },
    "marker_passage": {                          # 무관한 문장 문항을 표본으로 사용
        "stem": 116, "passage": 117, "gloss": 118,
    },
    "ab_table": {                                # 빈칸 (A)(B) 문항을 표본으로 사용
        "stem": 112, "passage": 113, "gloss": 114, "table_para": 115,
    },
    "order_choices": {                           # 문단순서 문항(13번)을 표본으로 사용
        "stem": 121, "boxed_passage": 123,
        "abc_paras": (124, 125, 126),
        "choice_lines": (128, 129, 130),
    },
    "insertion": {                                # 삽입 문항을 표본으로 사용
        "stem": 145, "given_box": 147, "passage": 148, "gloss": 149,
    },
    "boxed_1x1": 147,                             # 범용 1x1 테두리 박스(삽입 문항의 주어진 문장 박스를 재사용)
    "translation_blank": {                        # 서술형1 을 표본으로 사용
        "stem": 180, "passage": 182, "gloss": 183,
        "answer_lines": (185, 186, 187),
    },
    "word_box": {                                 # 서술형4 의 (2)를 표본으로 사용
        "stem": 220, "passage": 221,
        "instruction": 231, "box_table_para": 233,
        "answer_lines": (235, 237, 239),
    },
    # abc_table 없음 — 이 템플릿에는 어법 (A)(B)(C) 박스 유형 예시가 없다.
}


# --------------------------------------------------------------------------
# 앵커: 공통영어2 템플릿 (1학년, 2025_1학년_2학기_기말고사_원안최종.hwpx)
# --------------------------------------------------------------------------

ANCHORS_COMMON2 = {
    "intro": {"range": (0, 4)},
    "footer_box": {"idx": 361},
    "footer_title": {"idx": 362},
    "plain_choice5": {                          # 함축의미(idx156) 문항을 표본으로 사용 — gloss 포함된 완전한 예
        "stem": 156, "passage": 157, "gloss": 158, "spacer_before": 160,
        "choices": (161, 162, 163, 164, 165), "spacer_after": 166,
    },
    "embedded_underline": {                      # 어법 문항을 표본으로 사용
        "stem": 32, "passage": 33,
    },
    "marker_passage": {                          # 무관한 문장 문항을 표본으로 사용
        "stem": 53, "passage": 54, "gloss": 55,
    },
    "ab_table": {                                # 빈칸 (A)(B) 문항을 표본으로 사용
        "stem": 62, "passage": 63, "gloss": 63, "table_para": 64,
    },
    "abc_table": {                                # 어법 (A)(B)(C) 박스 문항을 표본으로 사용
        "stem": 34, "passage": 35, "table_para": 36,
    },
    "order_choices": {                           # [13~14] 첫 번째 순서 문항을 표본으로 사용
        "stem": 100, "boxed_passage": 102,
        "abc_paras": (104, 105, 106),
        "choice_lines": (110, 111, 112),
    },
    "insertion": {                                # 삽입 문항을 표본으로 사용
        "stem": 128, "given_box": 129, "passage": 130, "gloss": 131,
    },
    "boxed_1x1": 129,
    "translation_blank": {                        # 서술형1 을 표본으로 사용
        "stem": 170, "passage": 173, "gloss": 173,
        "answer_lines": (182, 183, 184, 185, 186, 187, 188),
    },
    "word_box": {                                 # translation_blank와 동일 계열 스타일 재사용
        "stem": 170, "passage": 173,
        "instruction": 170, "box_table_para": 129,
        "answer_lines": (182, 183, 184, 185, 186, 187, 188),
    },
}


TEMPLATES = {
    "영어II": {"file": "영어II_원안지.hwpx", "anchors": ANCHORS_ENG2},
    "공통영어2": {"file": "2025_1학년_2학기_기말고사_원안최종.hwpx", "anchors": ANCHORS_COMMON2},
}


def get_para(tmpl: "E.Template", idx: int):
    return tmpl.top_paras()[idx]


def _clone(tmpl, idx):
    return E.clone_para(get_para(tmpl, idx))


def _clone_range(tmpl, lo, hi):
    paras = tmpl.top_paras()
    return [E.clone_para(p) for p in paras[lo:hi + 1]]


# --------------------------------------------------------------------------
# 빌더: PLAIN_CHOICE5
# --------------------------------------------------------------------------

def build_plain_choice5(tmpl, anchors, stem_text, passage_text, choices, answer_idx,
                          gloss_text=None, score_label=None):
    """지문 + 5지선다 한 줄씩. answer_idx 는 0-based(0=①).
    stem_text 에 배점 [3점] 등을 이미 포함해서 넘길 것 (score_label 은 보조용)."""
    a = anchors["plain_choice5"]
    out = []

    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    passage_p = _clone(tmpl, a["passage"])
    E.set_text(passage_p, passage_text)
    out.append(passage_p)

    if gloss_text:
        gloss_p = _clone(tmpl, a["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)

    out.append(_clone(tmpl, a["spacer_before"]))

    choice_anchor_idxs = a["choices"]
    if len(choices) != 5:
        raise ValueError("PLAIN_CHOICE5는 정확히 5개 선택지가 필요합니다.")
    for i, choice_text in enumerate(choices):
        cp = _clone(tmpl, choice_anchor_idxs[i])
        E.set_text(cp, choice_text)
        if i == answer_idx:
            E.mark_answer(cp)
        out.append(cp)

    out.append(_clone(tmpl, a["spacer_after"]))
    return out


# --------------------------------------------------------------------------
# 빌더: EMBEDDED_UNDERLINE (어법 / 어휘 단일 오류)
# --------------------------------------------------------------------------

def build_embedded_underline(tmpl, anchors, stem_text, lead_text, candidates, answer_idx,
                               gloss_text=None):
    """candidates: [(plain_text_after_this_candidate, candidate_word), ...] 5개.
    즉 candidates[i][1] 은 ①,②,③,④,⑤ 뒤에 밑줄로 표시될 단어/구,
    candidates[i][0] 은 그 후보 뒤부터 다음 후보(또는 지문 끝)까지의 일반 텍스트.
    lead_text 는 지문 맨 앞, 첫 번째 ① 이전까지의 텍스트.
    answer_idx: 0-based, 어느 후보가 오류(정답)인지.
    """
    a = anchors["embedded_underline"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    passage_p = _clone(tmpl, a["passage"])
    circles = ["①", "②", "③", "④", "⑤"]
    segments = []
    for i, (after_text, cand_word) in enumerate(candidates):
        segments.append((circles[i], after_text, cand_word, i == answer_idx))
    E.set_text_with_candidates(passage_p, lead_text, segments)
    out.append(passage_p)

    if gloss_text:
        # gloss 문단은 embedded_underline 앵커에 없으므로 marker_passage의 gloss 스타일을 빌려온다
        gloss_p = _clone(tmpl, anchors["marker_passage"]["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)
    return out


# --------------------------------------------------------------------------
# 빌더: MARKER_PASSAGE (무관한 문장 찾기)
# --------------------------------------------------------------------------

def build_marker_passage(tmpl, anchors, stem_text, lead_text, sentences, answer_idx,
                           gloss_text=None):
    """sentences: [(circle_char 뒤 문장, ) ...] 5개 문장. 각 문장 앞에 원형숫자만
    붙이고 밑줄 스타일 전환은 하지 않는다(일반 지문과 동일 스타일 유지)."""
    a = anchors["marker_passage"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    passage_p = _clone(tmpl, a["passage"])
    circles = ["①", "②", "③", "④", "⑤"]
    full_text = lead_text
    for i, sent in enumerate(sentences):
        full_text += f" {circles[i]}{sent}"
    E.set_text(passage_p, full_text)
    if 0 <= answer_idx < 5:
        # 정답 문장 부분만 강조하기 어려우므로(단일 run) 전체 지문 중 정답 문장을
        # 별도 run으로 분리해 형광펜 처리한다.
        _highlight_substring(passage_p, f"{circles[answer_idx]}{sentences[answer_idx]}")
    out.append(passage_p)

    if gloss_text:
        gloss_p = _clone(tmpl, a["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)
    return out


def _highlight_substring(p, needle):
    """문단이 단일 run(hp:t)인 상태에서, 그 텍스트 중 needle 부분만 markpen으로
    감싼다. 못 찾으면 조용히 무시(전체 텍스트는 이미 정상적으로 들어가 있음)."""
    runs = E._all_runs(p)
    if not runs:
        return
    run = runs[0]
    t = run.find(Q("hp:t"))
    if t is None or not t.text or needle not in t.text:
        return
    full = t.text
    idx = full.index(needle)
    before, mid, after = full[:idx], full[idx:idx + len(needle)], full[idx + len(needle):]
    charpr = run.get("charPrIDRef")
    parent = p
    parent.remove(run)
    lsa = p.find(Q("hp:linesegarray"))
    if lsa is not None:
        p.remove(lsa)

    r1 = etree.SubElement(parent, Q("hp:run"))
    r1.set("charPrIDRef", charpr)
    t1 = etree.SubElement(r1, Q("hp:t"))
    t1.text = before

    r2 = etree.SubElement(parent, Q("hp:run"))
    r2.set("charPrIDRef", charpr)
    t2 = etree.SubElement(r2, Q("hp:t"))
    mb = etree.SubElement(t2, Q("hp:markpenBegin"))
    mb.set("color", "#FFFF00")
    mb.tail = mid
    etree.SubElement(t2, Q("hp:markpenEnd"))

    r3 = etree.SubElement(parent, Q("hp:run"))
    r3.set("charPrIDRef", charpr)
    t3 = etree.SubElement(r3, Q("hp:t"))
    t3.text = after

    if lsa is not None:
        parent.append(lsa)


# --------------------------------------------------------------------------
# 빌더: INSERTION (주어진 문장 삽입)
# --------------------------------------------------------------------------

def build_insertion(tmpl, anchors, stem_text, given_sentence, lead_text, rest_sentences,
                      answer_idx, gloss_text=None):
    """rest_sentences: 위치 표시 ( ① )~( ⑤ ) 로 구분되는 5개 지점 뒤 텍스트 조각들.
    answer_idx: 정답 위치(0-based)."""
    a = anchors["insertion"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    box_p = _clone(tmpl, a["given_box"])
    tbl = E.get_table(box_p)
    cell_p = tbl.find(".//" + Q("hp:p"))
    E.set_text(cell_p, given_sentence)
    out.append(box_p)

    passage_p = _clone(tmpl, a["passage"])
    markers = ["( ① )", "( ② )", "( ③ )", "( ④ )", "( ⑤ )"]
    full_text = lead_text
    for i, chunk in enumerate(rest_sentences):
        full_text += f" {markers[i]} {chunk}"
    E.set_text(passage_p, full_text)
    if 0 <= answer_idx < 5:
        _highlight_substring(passage_p, markers[answer_idx])
    out.append(passage_p)

    if gloss_text:
        gloss_p = _clone(tmpl, a["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)
    return out


# --------------------------------------------------------------------------
# 빌더: AB_TABLE (빈칸 A/B 추론, 요약문 A/B 완성 공용)
# --------------------------------------------------------------------------

def build_ab_table(tmpl, anchors, stem_text, passage_text, ab_rows, answer_idx,
                     gloss_text=None, col_a_label="(A)", col_b_label="(B)"):
    """ab_rows: [(word_a, word_b), ...] 정확히 5개. answer_idx 0-based."""
    a = anchors["ab_table"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    passage_p = _clone(tmpl, a["passage"])
    E.set_text(passage_p, passage_text)
    out.append(passage_p)

    if gloss_text and a.get("gloss") != a.get("passage"):
        gloss_p = _clone(tmpl, a["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)

    table_p = _clone(tmpl, a["table_para"])
    tbl = E.get_table(table_p)
    E.set_cell_text(tbl, 0, 1, col_a_label)
    E.set_cell_text(tbl, 0, 3, col_b_label)
    if len(ab_rows) != 5:
        raise ValueError("AB_TABLE은 정확히 5행이 필요합니다.")
    circles = ["①", "②", "③", "④", "⑤"]
    for i, (wa, wb) in enumerate(ab_rows):
        row = i + 1
        E.set_cell_text(tbl, row, 0, circles[i])
        E.set_cell_text(tbl, row, 1, wa)
        E.set_cell_text(tbl, row, 2, "……")
        E.set_cell_text(tbl, row, 3, wb)
        if i == answer_idx:
            E.mark_cell_answer(tbl, row, 0)
    out.append(table_p)
    return out


# --------------------------------------------------------------------------
# 빌더: ABC_TABLE (어법 (A)(B)(C) 박스 선택 — 공통영어2 템플릿 전용)
# --------------------------------------------------------------------------

def build_abc_table(tmpl, anchors, stem_text, passage_text, abc_rows, answer_idx,
                      gloss_text=None, col_labels=("(A)", "(B)", "(C)")):
    """abc_rows: [(val_a, val_b, val_c), ...] 정확히 5개. answer_idx 0-based.
    이 유형은 이 스킬이 지원하는 두 템플릿 중 '공통영어2' 에만 표본이 있다
    (anchors 딕셔너리에 'abc_table' 키가 없는 템플릿에서는 KeyError 발생)."""
    a = anchors["abc_table"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    passage_p = _clone(tmpl, a["passage"])
    E.set_text(passage_p, passage_text)
    out.append(passage_p)

    if gloss_text and "gloss" in a:
        gloss_p = _clone(tmpl, a["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)

    table_p = _clone(tmpl, a["table_para"])
    tbl = E.get_table(table_p)
    E.set_cell_text(tbl, 0, 1, f" {col_labels[0]}")
    E.set_cell_text(tbl, 0, 3, f" {col_labels[1]}")
    E.set_cell_text(tbl, 0, 5, f" {col_labels[2]}")
    if len(abc_rows) != 5:
        raise ValueError("ABC_TABLE은 정확히 5행이 필요합니다.")
    circles = ["①", "②", "③", "④", "⑤"]
    for i, (va, vb, vc) in enumerate(abc_rows):
        row = i + 1
        E.set_cell_text(tbl, row, 0, circles[i])
        E.set_cell_text(tbl, row, 1, va)
        E.set_cell_text(tbl, row, 2, "…")
        E.set_cell_text(tbl, row, 3, vb)
        E.set_cell_text(tbl, row, 4, "…")
        E.set_cell_text(tbl, row, 5, vc)
        if i == answer_idx:
            E.mark_cell_answer(tbl, row, 0)
    out.append(table_p)
    return out


# --------------------------------------------------------------------------
# 빌더: ORDER_CHOICES (문단 순서)
# --------------------------------------------------------------------------

def build_order_choices(tmpl, anchors, stem_text, passage_lead, para_a, para_b, para_c,
                          answer_idx, gloss_text=None):
    """(A)(B)(C) 순서를 뒤섞어 배치하는 문제. 5개 순서 조합 중 answer_idx(0-based)가 정답.
    표준 5개 조합: (A)-(B)-(C), (B)-(A)-(C), (B)-(C)-(A), (C)-(A)-(B), (C)-(B)-(A)
    (실제 두 템플릿의 원본 조합 순서는 서로 다르지만, 이 값은 어차피 우리가 새로
    채워 넣는 내용이므로 두 템플릿 공통으로 이 순서를 표준으로 사용한다.)"""
    a = anchors["order_choices"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    boxed_p = _clone(tmpl, a["boxed_passage"])
    tbl = E.get_table(boxed_p)
    cell_p = tbl.find(".//" + Q("hp:p"))
    E.set_text(cell_p, passage_lead)
    out.append(boxed_p)

    for anchor_idx, text in zip(a["abc_paras"], (para_a, para_b, para_c)):
        p = _clone(tmpl, anchor_idx)
        E.set_text(p, text)
        out.append(p)

    combos = [
        "(A) - (B) - (C)", "(B) - (A) - (C)", "(B) - (C) - (A)",
        "(C) - (A) - (B)", "(C) - (B) - (A)",
    ]
    circles = ["①", "②", "③", "④", "⑤"]
    line_specs = [(0, 1), (2, 3), (4, None)]  # 각 줄에 들어갈 선택지 인덱스(2개,2개,1개)
    for line_i, (idx_a, idx_b) in enumerate(line_specs):
        template_p = get_para(tmpl, a["choice_lines"][line_i])
        new_p = E.clone_para(template_p)
        runs = E._all_runs(new_p)
        lsa = new_p.find(Q("hp:linesegarray"))
        if lsa is not None:
            new_p.remove(lsa)
        for run in runs:
            new_p.remove(run)

        def _mk_pair(idx, charpr_num, charpr_val, is_last_on_line):
            r1 = etree.Element(Q("hp:run"))
            r1.set("charPrIDRef", charpr_num)
            t1 = etree.SubElement(r1, Q("hp:t"))
            is_ans = (idx == answer_idx)
            if is_ans:
                mb = etree.SubElement(t1, Q("hp:markpenBegin"))
                mb.set("color", "#FFFF00")
                mb.tail = f"{circles[idx]} "
            else:
                t1.text = f"{circles[idx]} "
            new_p.append(r1)

            r2 = etree.Element(Q("hp:run"))
            r2.set("charPrIDRef", charpr_val)
            t2 = etree.SubElement(r2, Q("hp:t"))
            pad = "                 " if not is_last_on_line else ""
            if is_ans:
                t2.text = combos[idx] + pad
                etree.SubElement(t2, Q("hp:markpenEnd"))
            else:
                t2.text = combos[idx] + pad
            new_p.append(r2)

        # charPrIDRef 값은 원본 템플릿 문단에서 읽어온다
        orig_runs = template_p.findall(Q("hp:run"))
        charpr_num = orig_runs[0].get("charPrIDRef") if orig_runs else "4"
        charpr_val = orig_runs[1].get("charPrIDRef") if len(orig_runs) > 1 else charpr_num

        _mk_pair(idx_a, charpr_num, charpr_val, is_last_on_line=(idx_b is None))
        if idx_b is not None:
            _mk_pair(idx_b, charpr_num, charpr_val, is_last_on_line=True)

        if lsa is not None:
            new_p.append(lsa)
        out.append(new_p)

    if gloss_text:
        gloss_p = _clone(tmpl, anchors["ab_table"]["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)
    return out


# --------------------------------------------------------------------------
# 빌더: TRANSLATION_BLANK (서술형 - 우리말 해석/함축의미 서술)
# --------------------------------------------------------------------------

def build_translation_blank(tmpl, anchors, stem_text, passage_text, gloss_text=None,
                              num_answer_lines=3):
    a = anchors["translation_blank"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    passage_p = _clone(tmpl, a["passage"])
    E.set_text(passage_p, passage_text)
    out.append(passage_p)

    if gloss_text and a.get("gloss") != a.get("passage"):
        gloss_p = _clone(tmpl, a["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)

    line_anchor = a["answer_lines"][0]
    line_template = get_para(tmpl, line_anchor)
    n = max(num_answer_lines, 1)
    for _ in range(n):
        out.append(E.clone_para(line_template))
    return out


# --------------------------------------------------------------------------
# 빌더: WORD_BOX (서술형 - <조건> + <Word Box> 영작)
# --------------------------------------------------------------------------

def build_word_box(tmpl, anchors, stem_text, passage_text, condition_lines, word_tokens,
                     num_answer_lines=3, gloss_text=None):
    a = anchors["word_box"]
    out = []
    stem_p = _clone(tmpl, a["stem"])
    E.set_text(stem_p, stem_text)
    out.append(stem_p)

    passage_p = _clone(tmpl, a["passage"])
    E.set_text(passage_p, passage_text)
    out.append(passage_p)

    if gloss_text:
        gloss_p = _clone(tmpl, anchors["translation_blank"]["gloss"])
        E.set_text(gloss_p, gloss_text)
        out.append(gloss_p)

    # <조건> / <Word Box> 는 검증된 1x1 테두리 박스(삽입 문항의 "주어진 문장" 박스와
    # 동일 구조)를 재사용한다. 원본의 다중 셀 word-box 표는 셀 수가 많아 안전하게
    # 재활용하기 어려워 채택하지 않았다.
    cond_p = _clone(tmpl, anchors["boxed_1x1"])
    cond_tbl = E.get_table(cond_p)
    cond_cell_p = cond_tbl.find(".//" + Q("hp:p"))
    E.set_text(cond_cell_p, "< 조 건 >  " + "  ".join(condition_lines))
    out.append(cond_p)

    box_p = _clone(tmpl, anchors["boxed_1x1"])
    tbl = E.get_table(box_p)
    cell_p = tbl.find(".//" + Q("hp:p"))
    E.set_text(cell_p, "<Word Box>  " + " / ".join(word_tokens))
    out.append(box_p)

    line_template = get_para(tmpl, a["answer_lines"][0])
    n = max(num_answer_lines, 1)
    for _ in range(n):
        out.append(E.clone_para(line_template))
    return out
