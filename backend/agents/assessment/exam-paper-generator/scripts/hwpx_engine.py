#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hwpx_engine.py — 심인고 영어과 원안지(.hwpx) 조립 엔진

핵심 설계 원칙
--------------
이 모듈은 HWPX(OWPML) XML을 처음부터 생성하지 않는다. 대신 assets/templates/ 의
실제 원안지 파일(영어II, 심화영어I)에서 이미 검증된 문단/표 블록을 "복제"한 뒤,
텍스트 노드(hp:t)만 갈아끼우는 방식(mail-merge)으로 새 문서를 조립한다.

이렇게 하는 이유:
  - header.xml에 정의된 스타일(charPr/paraPr/borderFill 67~23종)을 그대로 재사용하므로
    글꼴·크기·여백·표 테두리가 예시 파일과 100% 동일하게 유지된다.
  - 객관식 선택지 번호(①②③④⑤)는 대부분 문자가 아니라 outline 자동번호
    (paraPrIDRef=8류, heading level=2, numFormat=CIRCLED_DIGIT)로 렌더링된다.
    즉 선택지 문단을 그대로 복제하기만 하면 번호가 자동으로 붙는다.
  - 정답 표시는 그 학교의 관행대로 노란 형광펜(hp:markpenBegin color=#FFFF00)으로
    표시한다 (원안지에 정답이 이렇게 표시되어 있음을 실제 파일에서 확인함).

좌표계
------
모든 인덱스는 section0.xml의 최상위 hs:sec 직계 자식 hp:p 목록 기준
(root.findall('hp:p', NS), .// 아님) — 표 안에 중첩된 문단과 섞이지 않도록 함.

검증
----
build_exam()이 끝나면 validate_hwpx()를 반드시 호출해 (1) zip이 열리는지
(2) section0.xml이 well-formed XML인지 (3) 모든 charPrIDRef/paraPrIDRef/
borderFillIDRef/styleIDRef가 header.xml에 실존하는지를 기계적으로 확인한다.
Hancom Office가 없는 환경에서는 이것이 우리가 할 수 있는 최선의 정합성 검증이다.
"""

import copy
import os
import random
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from typing import Optional

from lxml import etree

NS = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
}
HP = NS["hp"]


def _q(tag):
    """'hp:p' -> '{ns}p' 형태의 Clark 표기로 변환."""
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"


# --------------------------------------------------------------------------
# 1. 템플릿 로드 / 저장
# --------------------------------------------------------------------------

@dataclass
class Template:
    """압축 해제된 hwpx 템플릿 작업 디렉터리 + 파싱된 section0 트리."""

    workdir: str
    section_path: str
    header_path: str
    section_tree: etree._ElementTree = field(repr=False)
    header_tree: etree._ElementTree = field(repr=False)

    @property
    def sec_root(self):
        return self.section_tree.getroot()

    @property
    def head_root(self):
        return self.header_tree.getroot()

    def top_paras(self):
        """hs:sec 직계 자식 hp:p 목록 (표 내부 중첩 문단 제외)."""
        return self.sec_root.findall(_q("hp:p"))


def load_template(hwpx_path: str, workdir: str) -> Template:
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir)
    with zipfile.ZipFile(hwpx_path) as z:
        z.extractall(workdir)
    section_path = os.path.join(workdir, "Contents", "section0.xml")
    header_path = os.path.join(workdir, "Contents", "header.xml")
    parser = etree.XMLParser(remove_blank_text=False, huge_tree=True)
    section_tree = etree.parse(section_path, parser)
    header_tree = etree.parse(header_path, parser)
    return Template(workdir, section_path, header_path, section_tree, header_tree)


def save_hwpx(workdir: str, out_section_tree: etree._ElementTree, out_path: str):
    """수정된 section0 트리를 workdir에 쓰고, mimetype이 첫 항목/무압축인
    hwpx 규칙을 지켜 재압축한다."""
    section_path = os.path.join(workdir, "Contents", "section0.xml")
    out_section_tree.write(section_path, xml_declaration=True, encoding="UTF-8", standalone=True)

    if os.path.exists(out_path):
        os.remove(out_path)

    mimetype_path = os.path.join(workdir, "mimetype")
    with zipfile.ZipFile(out_path, "w") as zf:
        # mimetype: 반드시 첫 엔트리, 무압축(STORED)
        zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        for root_dir, _dirs, files in os.walk(workdir):
            for fname in files:
                full = os.path.join(root_dir, fname)
                arcname = os.path.relpath(full, workdir).replace(os.sep, "/")
                if arcname == "mimetype":
                    continue
                zf.write(full, arcname, compress_type=zipfile.ZIP_DEFLATED)
    return out_path


# --------------------------------------------------------------------------
# 2. ID 재발급 (복제한 블록끼리 id 충돌 방지용, 안전장치)
# --------------------------------------------------------------------------

_ID_ATTR_CANDIDATES = ("id",)


def _random_big_id():
    return str(random.randint(10 ** 9, 2 ** 31 - 1))


def renumber_ids(el):
    """복제된 elemento 서브트리 내 hp:p/hp:tbl 의 id 속성을 새 난수로 교체.
    header.xml 스타일 참조(*IDRef)는 절대 건드리지 않는다 — 그건 공유 팔레트."""
    for node in el.iter():
        tag = etree.QName(node).localname
        if tag in ("p", "tbl") and node.get("id") is not None:
            node.set("id", _random_big_id())
    return el


def clone_para(p):
    """문단(및 내부 표 포함)을 깊은 복사 + id 재발급."""
    new_p = copy.deepcopy(p)
    renumber_ids(new_p)
    return new_p


# --------------------------------------------------------------------------
# 3. 텍스트 조작 primitives
# --------------------------------------------------------------------------

def _all_runs(p):
    return p.findall(_q("hp:run"))


def _first_charpr(p, default="4"):
    runs = _all_runs(p)
    if not runs:
        return default
    return runs[0].get("charPrIDRef", default)


def set_text(p, text: str):
    """문단의 모든 run을 지우고, 기존 첫 run의 charPrIDRef를 유지한 채
    새 텍스트 하나로 채운다. linesegarray(줄 위치 캐시)는 원본 텍스트 기준의
    절대좌표(vertpos 등)라서 텍스트 길이가 달라지면 그대로 둘 경우 글자가
    겹쳐 보인다 — 최종적으로는 strip_all_linesegarrays()가 문서 전체에서
    한 번 더 정리하지만, 여기서도 남겨두지 않는다."""
    charpr = _first_charpr(p)
    for run in _all_runs(p):
        p.remove(run)
    new_run = etree.SubElement(p, _q("hp:run"))
    new_run.set("charPrIDRef", charpr)
    t = etree.SubElement(new_run, _q("hp:t"))
    t.text = text
    # linesegarray가 있으면 맨 뒤로 이동(구조 유효성 유지), run 뒤에 위치해야 함
    lsa = p.find(_q("hp:linesegarray"))
    if lsa is not None:
        p.remove(lsa)
        p.append(lsa)
    return p


def mark_answer(p):
    """단일 run 문단 전체를 노란 형광펜(정답 표시)으로 감싼다."""
    runs = _all_runs(p)
    if not runs:
        return p
    run = runs[0]
    t = run.find(_q("hp:t"))
    if t is None:
        return p
    text = t.text or ""
    t.text = None
    mb = etree.SubElement(t, _q("hp:markpenBegin"))
    mb.set("color", "#FFFF00")
    mb.tail = text
    etree.SubElement(t, _q("hp:markpenEnd"))
    return p


def set_text_with_candidates(p, prefix_normal: str, segments: list, tail_normal: str = ""):
    """어법/어휘/무관한 문장/삽입 유형처럼, 지문 한 문단 안에 원형 숫자
    ①~⑤ 로 표시된 후보 구간이 여러 개 들어가는 경우.

    segments: [(circle_char, plain_text_before_candidate, candidate_text, is_answer), ...]
      - circle_char: '①' 처럼 후보 앞에 찍는 원형 숫자 (일반 run에 리터럴로 들어감)
      - plain_text_before_candidate: circle_char 뒤, 후보 단어 앞의 일반 지문 텍스트
      - candidate_text: 후보 구간 텍스트 (밑줄 스타일 run으로 들어감)
      - is_answer: 이 후보가 정답(오류/무관/삽입지점)이면 True → 노란 형광펜

    원본 예시 구조를 그대로 재현: 일반 run(charPr=normal) 안에
    "...(직전 텍스트) ①<fwSpace/>" 까지 넣고, 곧바로 밑줄 run(charPr=underline)에
    후보 단어를 넣는다. 두 charPrIDRef는 템플릿 문단의 실제 run에서 동적으로 읽어온다.
    """
    runs = _all_runs(p)
    normal_charpr = None
    underline_charpr = None
    for run in runs:
        cp = run.get("charPrIDRef")
        if normal_charpr is None:
            normal_charpr = cp
        elif cp != normal_charpr and underline_charpr is None:
            underline_charpr = cp
    if underline_charpr is None:
        # 후보 스타일을 못 찾으면 normal과 동일하게 처리(최소 기능 보존)
        underline_charpr = normal_charpr

    for run in runs:
        p.remove(run)

    def _add_run(charpr, text, extra_child=None, answer=False, answer_close=False):
        run = etree.Element(_q("hp:run"))
        run.set("charPrIDRef", charpr)
        t = etree.SubElement(run, _q("hp:t"))
        if answer:
            mb = etree.SubElement(t, _q("hp:markpenBegin"))
            mb.set("color", "#FFFF00")
            mb.tail = text
        else:
            t.text = text
        if extra_child is not None:
            etree.SubElement(t, extra_child)
        if answer_close:
            etree.SubElement(t, _q("hp:markpenEnd"))
        return run

    lsa = p.find(_q("hp:linesegarray"))
    if lsa is not None:
        p.remove(lsa)

    cur_text = prefix_normal
    for circle_char, before_text, candidate_text, is_answer in segments:
        if is_answer:
            # circle 문자까지는 markpen 열고, fwSpace 컨트롤 뒤에 이어붙임
            run = _add_run(normal_charpr, cur_text + circle_char, extra_child=_q("hp:fwSpace"),
                            answer=True)
            p.append(run)
            run2 = _add_run(underline_charpr, candidate_text, answer=False)
            # candidate run에 markpenEnd를 붙여 정답 구간을 닫는다
            t2 = run2.find(_q("hp:t"))
            etree.SubElement(t2, _q("hp:markpenEnd"))
            p.append(run2)
        else:
            run = _add_run(normal_charpr, cur_text + circle_char, extra_child=_q("hp:fwSpace"))
            p.append(run)
            run2 = _add_run(underline_charpr, candidate_text)
            p.append(run2)
        cur_text = before_text
    if cur_text or tail_normal:
        run = _add_run(normal_charpr, cur_text + tail_normal)
        p.append(run)

    if lsa is not None:
        p.append(lsa)
    return p


def set_cell_text(tbl, row, col, text):
    trs = tbl.findall(_q("hp:tr"))
    tr = trs[row]
    tcs = tr.findall(_q("hp:tc"))
    tc = tcs[col]
    cell_p = tc.find(".//" + _q("hp:p"))
    set_text(cell_p, text)
    return tc


def mark_cell_answer(tbl, row, col):
    trs = tbl.findall(_q("hp:tr"))
    tr = trs[row]
    tcs = tr.findall(_q("hp:tc"))
    tc = tcs[col]
    cell_p = tc.find(".//" + _q("hp:p"))
    mark_answer(cell_p)
    return tc


def get_table(p):
    return p.find(".//" + _q("hp:tbl"))


def strip_all_linesegarrays(root):
    """문서 전체(표 안 셀 포함)에서 hp:linesegarray를 모두 제거한다.

    linesegarray는 "이 줄이 페이지의 어디(vertpos/horzpos)에 그려지는가"를
    원본 저작 시점 텍스트 기준으로 캐싱해 둔 값이다. mail-merge로 텍스트
    길이가 달라지거나 문항 수가 달라지면 이 캐시가 새 내용과 더 이상 맞지
    않아 글자가 겹쳐 보이는 렌더링 오류가 생긴다(실사용 중 확인된 증상).
    이 함수를 문서 조립 마지막 단계에서 한 번 호출해 전부 제거하면, 여는
    프로그램이 처음부터 다시 줄바꿈/좌표 계산을 하게 되어 겹침이 사라진다.
    문서를 열 때 한 번 더 계산되는 것뿐이므로 다른 서식에는 영향이 없다.
    """
    removed = 0
    for p in root.iter(_q("hp:p")):
        lsa = p.find(_q("hp:linesegarray"))
        if lsa is not None:
            p.remove(lsa)
            removed += 1
    return removed


# --------------------------------------------------------------------------
# 4. 전역 텍스트 치환 (헤더/푸터용 — 학교명·학년·과목명 등)
# --------------------------------------------------------------------------

def replace_text_everywhere(root, mapping: dict):
    """트리 전체를 순회하며 hp:t 의 .text 와 .tail 안의 문자열을 정확히
    일치하는 부분만 치환한다 (구조는 전혀 건드리지 않음 — 헤더의 플로팅
    텍스트박스처럼 구조를 모를 때도 안전)."""
    for el in root.iter():
        if el.text:
            new_text = el.text
            for k, v in mapping.items():
                new_text = new_text.replace(k, v)
            if new_text != el.text:
                el.text = new_text
        if el.tail:
            new_tail = el.tail
            for k, v in mapping.items():
                new_tail = new_tail.replace(k, v)
            if new_tail != el.tail:
                el.tail = new_tail
    return root


# --------------------------------------------------------------------------
# 5. 문서 조립
# --------------------------------------------------------------------------

def clear_body(sec_root, keep_first_secpr_para=True):
    """secPr(첫 문단)만 남기고 본문 문단을 모두 제거해 빈 캔버스를 만든다."""
    paras = sec_root.findall(_q("hp:p"))
    for p in paras[1:] if keep_first_secpr_para else paras:
        sec_root.remove(p)
    return sec_root


def append_block(sec_root, paras: list):
    for p in paras:
        sec_root.append(p)


# --------------------------------------------------------------------------
# 6. 검증
# --------------------------------------------------------------------------

def _collect_style_ids(head_root):
    ids = {"charPr": set(), "paraPr": set(), "borderFill": set(), "style": set(), "numbering": set()}
    tagmap = {
        "charProperties": ("charPr", "hh:charPr"),
        "paraProperties": ("paraPr", "hh:paraPr"),
        "borderFills": ("borderFill", "hh:borderFill"),
        "styles": ("style", "hh:style"),
        "numberings": ("numbering", "hh:numbering"),
    }
    for parent_tag, (key, child_tag) in tagmap.items():
        parent = head_root.find(f".//{{{NS['hh']}}}{parent_tag}")
        if parent is None:
            continue
        for child in parent:
            cid = child.get("id")
            if cid is not None:
                ids[key].add(cid)
    return ids


def validate_hwpx(hwpx_path: str) -> list:
    """[(level, message), ...] 형태로 문제점을 반환. 빈 리스트면 통과."""
    problems = []
    try:
        z = zipfile.ZipFile(hwpx_path)
    except Exception as e:
        return [("FATAL", f"zip 파일로 열 수 없음: {e}")]

    names = set(z.namelist())
    required = {"mimetype", "Contents/section0.xml", "Contents/header.xml",
                "META-INF/manifest.xml", "version.xml"}
    for r in required:
        if r not in names:
            problems.append(("FATAL", f"필수 항목 누락: {r}"))

    info0 = z.infolist()[0]
    if info0.filename != "mimetype":
        problems.append(("FATAL", "mimetype이 zip의 첫 엔트리가 아님"))
    elif info0.compress_type != zipfile.ZIP_STORED:
        problems.append(("WARN", "mimetype이 압축되어 저장됨(무압축 권장)"))

    try:
        header_tree = etree.fromstring(z.read("Contents/header.xml"))
    except Exception as e:
        return problems + [("FATAL", f"header.xml 파싱 실패: {e}")]
    try:
        section_bytes = z.read("Contents/section0.xml")
        section_tree = etree.fromstring(section_bytes)
    except Exception as e:
        return problems + [("FATAL", f"section0.xml 파싱 실패(well-formed 아님): {e}")]

    style_ids = _collect_style_ids(header_tree)

    ref_attr_to_key = {
        "charPrIDRef": "charPr",
        "paraPrIDRef": "paraPr",
        "borderFillIDRef": "borderFill",
        "styleIDRef": "style",
        "numberingIDRef": "numbering",
    }
    checked = 0
    for el in section_tree.iter():
        for attr, key in ref_attr_to_key.items():
            val = el.get(attr)
            if val is None or val in ("", "0", "4294967295"):
                continue
            checked += 1
            if val not in style_ids[key]:
                problems.append(("FATAL",
                    f"{etree.QName(el).localname} 의 {attr}='{val}' 가 header.xml에 없음"))

    # markpen 짝 확인 (열었는데 안 닫힌 경우)
    begins = len(section_tree.findall(".//" + _q("hp:markpenBegin")))
    ends = len(section_tree.findall(".//" + _q("hp:markpenEnd")))
    if begins != ends:
        problems.append(("FATAL", f"markpenBegin({begins})/markpenEnd({ends}) 개수 불일치"))

    if not problems:
        problems.append(("OK", f"검증 통과 (스타일 참조 {checked}건 모두 header.xml에 존재, "
                                 f"markpen {begins}쌍 정상)"))
    return problems


if __name__ == "__main__":
    import sys
    for path in sys.argv[1:]:
        print(f"=== {path} ===")
        for level, msg in validate_hwpx(path):
            print(f"  [{level}] {msg}")
