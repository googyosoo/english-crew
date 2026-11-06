#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_template.py — 새 hwpx 원안지를 blocks.py 의 앵커로 등록하기 전에,
최상위 문단 목록(0-based, 표 내부 중첩 문단 제외)과 각 문단의 텍스트/paraPr/
표 여부를 훑어보는 진단 도구.

사용법:
    python3 inspect_template.py <파일.hwpx> [시작idx] [끝idx]

표가 있는 문단은 [TBL rNxcM] 로 표시되고, 그 표의 각 셀 텍스트도 함께 출력된다.
markpen(형광펜) 표시가 있으면 <<HL>> 로 표시된다 — 원본 예시 파일에서 정답을
찾을 때 유용하다.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hwpx_engine as E

Q = E._q


def inspect(path, lo=0, hi=None):
    tmpl = E.load_template(path, "/tmp/_hwpx_inspect")
    paras = tmpl.top_paras()
    if hi is None:
        hi = len(paras) - 1
    print(f"파일: {path}")
    print(f"최상위 문단 총 {len(paras)}개, {lo}~{hi} 범위 출력\n")
    for i in range(lo, min(hi + 1, len(paras))):
        p = paras[i]
        text = "".join(p.itertext())
        tbl = p.find(".//" + Q("hp:tbl"))
        mp = p.findall(".//" + Q("hp:markpenBegin"))
        hl = " <<HL>>" if mp else ""
        tblinfo = ""
        if tbl is not None:
            rows = tbl.findall(Q("hp:tr"))
            cols = len(rows[0].findall(Q("hp:tc"))) if rows else 0
            tblinfo = f" [TBL r{len(rows)}xc{cols}]"
        print(f"[{i}] paraPr={p.get('paraPrIDRef')} style={p.get('styleIDRef')}"
              f"{tblinfo}{hl} {text.strip()[:100]!r}")
        if tbl is not None:
            for ri, tr in enumerate(tbl.findall(Q("hp:tr"))):
                for ci, tc in enumerate(tr.findall(Q("hp:tc"))):
                    ctext = "".join(tc.itertext()).strip()
                    print(f"      r{ri}c{ci}: {ctext[:60]!r}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else None
    inspect(path, lo, hi)
