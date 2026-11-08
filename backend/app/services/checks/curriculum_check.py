import sys
import re
import json
import unicodedata
import difflib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

def get_resource_root() -> Path:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent.parent.parent

PROJECT_ROOT = get_resource_root()
CURRICULUM_JSONL_PATH = PROJECT_ROOT / "docs" / "source-skills" / "kr-curriculum-2022" / "data" / "high" / "f08.jsonl"
if not CURRICULUM_JSONL_PATH.exists():
    CURRICULUM_JSONL_PATH = PROJECT_ROOT / "backend" / "data" / "curriculum" / "english_2022.jsonl"

_ABBR = r"[가-힣]{1,4}(?:\([가-힣]{1,4}\))?(?:[ⅠⅡ]|I{1,2})?"
_ABBR3 = r"[가-힣]{1,4}(?:[ⅠⅡ]|I{1,2})|[가-힣]{2}\d"
_DASH = r"[-–—‒−]"
_CLOSE_LIKE = r"[\]\)\}〕】］|]"
_THREE = re.compile(rf"(1[02])({_ABBR3}){_DASH}(\d{{2}}){_DASH}(\d{{2}})")
_TWO = re.compile(rf"(10|12|[2469])({_ABBR})(\d{{2}}){_DASH}(\d{{2}})({_CLOSE_LIKE})?")
_THIRD_GROUP = re.compile(rf"{_DASH}\d{{2}}")

WINDOW = 400
LEVEL_WINDOW = 1200
ALTERED = 0.55
EVIDENCE_MIN = 12
MIN_CLAIM = 15
MIN_LEVEL_CLAIM = 10

_NORM = re.compile(r"[\s·⋅･ㆍ・∙•]+")
_CLOSERS = "]})〕】］|`"
_HEAD_JUNK = re.compile(r"^[\s\]\})〕】］|`:：*>·⋅･ㆍ]+")
_META = ("성취기준", "성취수준", "차시", "단원", "지도안", "교사", "학생", "모둠",
         "교과서", "학습지", "활동지", "학습목표", "평가계획", "지필평가", "수행평가",
         "형성평가", "총괄평가", "채점", "루브릭", "피드백", "유의점", "준비물")
_LEVEL_LINE = re.compile(r"(?:^|[^A-Za-z])([A-Ea-e])\s*(?:수준|등급)\s*[:：]\s*(\S.*)")

_STANDARDS_DB: Optional[Dict[str, List[Dict]]] = None

def _norm(s):
    return _NORM.sub("", unicodedata.normalize("NFC", s or ""))

def normalize_code(code: str) -> str:
    """Normalize curriculum code: remove whitespace and special middle dot characters."""
    return _norm(code)

def load_curriculum_db() -> Dict[str, List[Dict]]:
    global _STANDARDS_DB
    if _STANDARDS_DB is not None:
        return _STANDARDS_DB

    db = {}
    if CURRICULUM_JSONL_PATH.exists():
        with open(CURRICULUM_JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("subject") == "영어":
                    db.setdefault(r["code"], []).append(r)
    _STANDARDS_DB = db
    return _STANDARDS_DB

def get_allowed_curriculum_codes() -> Set[str]:
    d = load_curriculum_db()
    codes = set()
    for code, recs in d.items():
        codes.add(code)
        codes.add(_norm(code))
        for r in recs:
            codes.add(r.get("code", ""))
    return codes

def find_codes(text: str) -> List[Tuple[str, int, int]]:
    """[(코드, 시작 오프셋, 끝 오프셋), ...] 등장 순서대로."""
    found = []
    for m in _THREE.finditer(text):
        found.append((m.start(), f"{m.group(1)}{m.group(2)}-{m.group(3)}-{m.group(4)}", m.end()))
    taken = [(s, e) for s, _, e in found]
    for m in _TWO.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        if m.group(5) is None and _THIRD_GROUP.match(text, m.end()):
            continue
        found.append((m.start(), f"{m.group(1)}{m.group(2)}{m.group(3)}-{m.group(4)}", m.end()))
    return [(c, s, e) for s, c, e in sorted(found)]

def _match(rec, window):
    s = _norm(rec["statement"])
    if not s:
        return (0, -1.0)
    if s in _norm(window):
        return (1, 1.0)
    head = _norm(_HEAD_JUNK.sub("", window))
    return (0, difflib.SequenceMatcher(None, s, head[: len(s)]).ratio())

@dataclass
class CurriculumCheckResult:
    passed: bool
    issues: List[str] = field(default_factory=list)
    found_codes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "status_label": "통과" if self.passed else f"수정 필요 ({len(self.issues)}건)",
            "found_codes": self.found_codes
        }

def check_curriculum(text: str) -> CurriculumCheckResult:
    """
    docs/source-skills/kr-curriculum-2022/scripts/verify.py 로직을 그대로 재사용하여
    산출물의 모든 코드가 f08.jsonl에 있고 진술문이 글자 그대로 일치하는지 검사합니다.
    """
    text_norm = unicodedata.normalize("NFC", text.replace("\x00", ""))
    D = load_curriculum_db()
    codes = find_codes(text_norm)

    issues: List[str] = []
    found_code_names = []

    if not codes:
        return CurriculumCheckResult(
            passed=False,
            issues=["산출물에 2022 개정 영어과 교육과정 성취기준 코드가 명시되지 않았습니다."],
            found_codes=[]
        )

    for i, (code, _, end) in enumerate(codes):
        found_code_names.append(code)
        recs = D.get(code)
        if not recs:
            issues.append(f"성취기준 코드 [{code}]는 2022 개정 영어과 공인 교육과정(f08.jsonl)에 실재하지 않는 코드입니다.")
            continue

        nxt = codes[i + 1][1] if i + 1 < len(codes) else len(text_norm)
        window = text_norm[end: min(nxt, end + WINDOW)]
        rec = max(recs, key=lambda r: _match(r, window) + (r["statement"] is not None,))

        exact, ratio = _match(rec, window)
        # If the statement is not exact verbatim in the output text
        expected_stmt = rec.get("statement", "").strip()
        if expected_stmt and _norm(expected_stmt) not in _norm(text_norm):
            issues.append(
                f"성취기준 [{code}]의 진술문이 공식 원문과 글자 그대로 일치하지 않습니다.\n"
                f"  - 공식 원문: '{expected_stmt}'"
            )

        # [4-0b 3번] 본문 미제공 시 요약·이해 성취기준(지문이 필요한 것) 차단
        is_no_body = "본문 미제공" in text_norm or "지문 없음" in text_norm or "일반 주제" in text_norm
        if is_no_body:
            stmt_norm = _norm(expected_stmt)
            if "요약" in stmt_norm or "듣거나읽은" in stmt_norm:
                issues.append(
                    f"본문 미제공(지문 없음) 모드에서는 지문이 필요한 요약 성취기준 [{code}]를 선택할 수 없습니다. "
                    "독립 작문 성취기준([12영Ⅰ-02-03] 자신의 의견이나 감정을 글로 쓴다, [12영Ⅰ-02-05] 생각이나 의견을 형식에 맞추어 글로 쓴다 등)을 선택해야 합니다."
                )

    passed = (len(issues) == 0)
    return CurriculumCheckResult(passed=passed, issues=issues, found_codes=found_code_names)

CHANNEL_COURSE_MAP = {
    "common1": "공통영어1",
    "common2": "공통영어2",
    "eng1": "영어Ⅰ",
    "eng2": "영어Ⅱ",
    "readwrite": "영어 독해와 작문",
    "adv_readwrite": "심화 영어 독해와 작문",
    "media": "미디어 영어",
}

def get_course_standards_text(course_name: str, channel_id: Optional[str] = None) -> str:
    """
    2022 개정 영어과 교육과정 f08.jsonl에서 해당 과목에 속하는 행만 추출하여
    코드, 진술문, A~E 성취수준 원문을 그대로 텍스트로 구성합니다.
    (docs/source-skills/COURSES.md 매핑 기준)
    """
    if not CURRICULUM_JSONL_PATH.exists():
        return ""

    target_course = None
    if channel_id and channel_id in CHANNEL_COURSE_MAP:
        target_course = CHANNEL_COURSE_MAP[channel_id]
    else:
        clean_name = course_name.replace(" ", "")
        for ch_id, c_name in CHANNEL_COURSE_MAP.items():
            if c_name.replace(" ", "") == clean_name or ch_id.upper() in clean_name.upper():
                target_course = c_name
                break
        if not target_course:
            target_course = "영어Ⅰ"

    matched_rows = []
    with open(CURRICULUM_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            course = row.get("course", "")
            if course == target_course or course.replace(" ", "") == target_course.replace(" ", ""):
                matched_rows.append(row)

    if not matched_rows:
        return ""

    lines = [f"=== [2022 개정 교육과정 공인 성취기준 및 성취수준: {target_course}] ==="]
    for r in matched_rows:
        code = r.get("code", "")
        stmt = r.get("statement", "").strip()
        area = r.get("area", "")
        lines.append(f"\n#### [{code}] ({area})")
        lines.append(f"- 공식 성취기준 진술문: {stmt}")
        levels = r.get("levels")
        if isinstance(levels, dict):
            lines.append("- 성취수준 (A~E):")
            for lvl in ["A", "B", "C", "D", "E"]:
                if lvl in levels:
                    lines.append(f"  - [{lvl}]: {levels[lvl].strip()}")

    return "\n".join(lines)
