import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

CURRICULUM_JSONL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "curriculum" / "english_2022.jsonl"

def normalize_code(code: str) -> str:
    """Normalize curriculum code: remove brackets, normalize roman numerals to arabic/standard."""
    c = code.strip("[]() \t")
    # Normalize Roman numerals: Ⅰ -> 1, Ⅱ -> 2 (or standard code format)
    c = c.replace("Ⅰ", "1").replace("Ⅱ", "2").replace("I", "1").replace("i", "1")
    return c

_STANDARDS_CACHE: Optional[Dict[str, Dict]] = None

def load_curriculum_standards() -> Dict[str, Dict]:
    global _STANDARDS_CACHE
    if _STANDARDS_CACHE is not None:
        return _STANDARDS_CACHE

    standards: Dict[str, Dict] = {}
    if not CURRICULUM_JSONL_PATH.exists():
        return standards

    with open(CURRICULUM_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            raw_code = row.get("code", "")
            norm_code = normalize_code(raw_code)
            standards[raw_code] = row
            standards[norm_code] = row

    _STANDARDS_CACHE = standards
    return _STANDARDS_CACHE

def get_allowed_curriculum_codes() -> Set[str]:
    stds = load_curriculum_standards()
    codes = set()
    for k, v in stds.items():
        codes.add(v.get("code", ""))
        codes.add(normalize_code(v.get("code", "")))
    return codes

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
    2022 개정 영어과 교육과정 jsonl에서 해당 과목에 속하는 행만 추출하여
    코드, 진술문, A~E 성취수준 원문을 그대로 텍스트로 구성합니다.
    (docs/source-skills/COURSES.md 매핑 기준)
    """
    if not CURRICULUM_JSONL_PATH.exists():
        return ""

    target_course = None
    if channel_id and channel_id in CHANNEL_COURSE_MAP:
        target_course = CHANNEL_COURSE_MAP[channel_id]
    else:
        # Match by name
        clean_name = course_name.replace(" ", "").upper()
        if "공통영어1" in clean_name or "COMMON1" in clean_name:
            target_course = "공통영어1"
        elif "공통영어2" in clean_name or "COMMON2" in clean_name:
            target_course = "공통영어2"
        elif "영어I" in clean_name or "영어Ⅰ" in clean_name or "ENG1" in clean_name or "영어1" in clean_name:
            target_course = "영어Ⅰ"
        elif "영어II" in clean_name or "영어Ⅱ" in clean_name or "ENG2" in clean_name or "영어2" in clean_name:
            target_course = "영어Ⅱ"
        elif "심화" in clean_name:
            target_course = "심화 영어 독해와 작문"
        elif "독해" in clean_name or "작문" in clean_name:
            target_course = "영어 독해와 작문"
        elif "미디어" in clean_name:
            target_course = "미디어 영어"
        else:
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

def check_curriculum(output_text: str) -> CurriculumCheckResult:
    stds = load_curriculum_standards()
    issues: List[str] = []
    
    # 1. Extract all curriculum code tokens
    # e.g., [12영1-01-01], [10영1-01-01], 12영Ⅰ-01-01, [12영-01-01], etc.
    code_pattern = re.compile(r"\[?([0-9]{2}[가-힣A-Za-z0-9ⅠⅡⅰⅱ-]+)\]?")
    raw_matches = code_pattern.findall(output_text)
    
    # Filter candidates that look like valid curriculum code structure: starts with 2 digits, contains subject hangul
    found_codes = []
    for m in raw_matches:
        if any(subj in m for subj in ["영", "공", "기"]):
            # Exclude false positives like dates or student ids
            if not m.startswith("20") and not m.startswith("S"):
                found_codes.append(m)

    # Deduplicate while preserving order
    unique_codes = list(dict.fromkeys(found_codes))

    if not unique_codes:
        issues.append("산출물에 2022 개정 교육과정 성취기준 코드가 명시되지 않았습니다.")
        return CurriculumCheckResult(passed=False, issues=issues, found_codes=[])

    # 2. Check each found code against official jsonl
    for c in unique_codes:
        norm = normalize_code(c)
        match_entry = stds.get(c) or stds.get(norm)
        
        if not match_entry:
            issues.append(f"성취기준 코드 [{c}]는 2022 개정 영어과 공인 교육과정에 존재하지 않는 날조된 코드입니다.")
            continue

        official_statement = match_entry.get("statement", "").strip()
        if not official_statement:
            continue

        # 3. Check exact verbatim statement match in the output text
        # If the output claims to present the statement for this code, it must match verbatim.
        # Find where the code is mentioned, and check if statement text appears verbatim in the same block/document
        if official_statement not in output_text:
            # Check if there is an attempted statement near the code that does not match
            # Search for pattern: 진술문, 내용, etc.
            issues.append(
                f"성취기준 [{c}]의 진술문이 공식 원문과 글자 그대로 일치하지 않습니다. "
                f"(공식 원문: '{official_statement}')"
            )

    passed = (len(issues) == 0)
    return CurriculumCheckResult(passed=passed, issues=issues, found_codes=unique_codes)
