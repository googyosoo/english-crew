import re
from typing import List, Dict, Optional, Set
from backend.app.services.checks.curriculum_check import get_allowed_curriculum_codes, normalize_code

# 확장된 정도 표현 목록 (22개)
DEGREE_EXPRESSIONS = [
    "매우", "완벽하게", "잘", "다소", "대체로", "거의", "충분히", "명확하게", "정확히", "적절히",
    "효과적으로", "미흡", "모호", "상당", "빈번", "다수", "약간", "부분적", "비교적", "대략적",
    "우수", "탁월"
]

# 관찰 가능한 정량 기준 정규식: "숫자+단위(개/회/문장/단어/가지/점)" 또는 "조건 n개 중 m개"
QUANTITATIVE_PATTERN = re.compile(
    r"(\d+\s*(?:개|회|문장|단어|가지|점)|조건\s*\d+\s*개\s*중\s*\d+\s*개|\d+\s*개\s*(?:이상|이하|미만|초과)|\d+\s*가지\s*(?:이상|이하|미만|초과)|전무함|0개)"
)

class RubricCheckResult:
    def __init__(self, passed: bool, issues: List[str]):
        self.passed = passed
        self.issues = issues

    @property
    def status_label(self) -> str:
        if self.passed:
            return "통과"
        return f"수정 필요 ({len(self.issues)}건)"

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "status_label": self.status_label
        }


def check_rubric_quantitative_cells(content: str) -> List[str]:
    """
    각 수준 칸은 '숫자+단위(개/회/문장/단어)' 또는 '조건 n개 중 m개' 형태의 기준을 1개 이상 포함해야 통과.
    정도 표현이 있으면 그것만으로는 불가.
    """
    issues = []
    lines = content.splitlines()

    for idx, line in enumerate(lines):
        line_str = line.strip()
        if not (line_str.startswith("|") and line_str.endswith("|")):
            continue

        cells = [c.strip() for c in line_str.split("|")[1:-1]]
        if not cells or any("---" in c for c in cells):
            continue

        # Skip header rows
        first_cell = cells[0]
        first_clean = first_cell.replace(" ", "")
        if any(h in first_clean for h in ["평가요소", "수준", "배점", "영역", "항목", "구분"]):
            continue

        # Check each level cell (usually index 1 onwards)
        for cell_idx, cell in enumerate(cells[1:], start=2):
            if not cell:
                continue

            has_quant = bool(QUANTITATIVE_PATTERN.search(cell))
            found_degrees = [deg for deg in DEGREE_EXPRESSIONS if deg in cell]

            # Rule: must have quantitative criteria, degree words alone are forbidden
            if not has_quant:
                if found_degrees:
                    issues.append(
                        f"루브릭 {idx+1}행 {cell_idx}번째 칸에 객관적 정량 기준 없이 정도 표현('{', '.join(found_degrees)}')만 사용됨: \"{cell[:35]}...\""
                    )
                else:
                    issues.append(
                        f"루브릭 {idx+1}행 {cell_idx}번째 칸에 관찰 가능한 수량 기준(숫자+단위 또는 조건 n개 중 m개)이 누락됨: \"{cell[:35]}...\""
                    )

    return issues


def check_rubric_scores_and_deductions(content: str) -> List[str]:
    """
    1. 각 평가요소 행에 수준별 점수가 모두 있어야 하고, 최고점 합계 = 총점일 것.
    2. 별도 감점 규정과 중복 금지.
    """
    issues = []
    lines = content.splitlines()

    # Detect declared total score in metadata (e.g., '10점 만점' or '배점: 10점')
    declared_total = None
    tot_match = re.search(r"(?:배점|총점)[:\s]*(\d+)\s*점", content)
    if tot_match:
        declared_total = int(tot_match.group(1))

    # Detect duplicate deduction section
    if re.search(r"#{2,}\s*(?:\d+\.\s*)?(?:감점\s*규정|감점\s*기준|채점\s*및\s*감점)", content):
        # If the content contains separate deduction rules like '-1점 감점'
        if re.search(r"-\d+(?:\.\d+)?\s*점\s*감점|\d+\s*점\s*감점", content):
            issues.append(
                "별도 감점 규정과 루브릭 평가요소가 중복됩니다. 별도 감점 규정을 배제하고 루브릭 수준별 배점으로 일원화해야 합니다."
            )

    row_max_scores = []
    in_rubric_table = False

    for idx, line in enumerate(lines):
        line_str = line.strip()
        if not (line_str.startswith("|") and line_str.endswith("|")):
            continue

        cells = [c.strip() for c in line_str.split("|")[1:-1]]
        if not cells or any("---" in c for c in cells):
            continue

        first_cell = cells[0]
        first_clean = first_cell.replace(" ", "")
        if any(h in first_clean for h in ["평가요소", "수준", "배점", "영역", "항목", "구분"]):
            in_rubric_table = True
            continue

        if not in_rubric_table:
            continue

        # Extract scores from all level cells in this row
        row_scores = []
        for cell in cells[1:]:
            sm = re.search(r"(\d+)\s*점", cell)
            if sm:
                row_scores.append(int(sm.group(1)))

        if not row_scores:
            issues.append(
                f"루브릭 {idx+1}행({first_cell[:20]})에 각 수준별 점수(숫자+점)가 명시되지 않았습니다."
            )
            continue

        # Check descending order
        for i in range(len(row_scores) - 1):
            if row_scores[i] <= row_scores[i+1]:
                issues.append(
                    f"루브릭 {idx+1}행({first_cell[:20]})의 수준별 점수가 내림차순이 아닙니다: {row_scores}"
                )
                break

        row_max_scores.append(row_scores[0])

    # Check sum of max scores == declared total
    if declared_total is not None and row_max_scores:
        sum_max = sum(row_max_scores)
        if sum_max != declared_total:
            issues.append(
                f"루브릭 평가요소 최고점 합계({sum_max}점)가 선언된 총점({declared_total}점)과 일치하지 않습니다."
            )

    return issues


def check_curriculum_codes(content: str) -> List[str]:
    """
    산출물에 기재된 모든 성취기준 코드가 english_2022.jsonl에 실재하는지 검사합니다.
    """
    allowed_codes = get_allowed_curriculum_codes()
    if not allowed_codes:
        return []

    issues = []
    found_codes = re.findall(r"\[([0-9]{2}[가-힣A-Za-z0-9ⅠⅡⅰⅱ-]+)\]", content)
    unique_found = set(found_codes)

    for code in unique_found:
        norm = normalize_code(code)
        if code not in allowed_codes and norm not in allowed_codes:
            issues.append(
                f"공인 교육과정 jsonl에 존재하지 않는 성취기준 코드 [{code}]가 인용되었습니다."
            )

    return issues


def check_rubric(content: str, allowed_codes: Optional[List[str]] = None) -> RubricCheckResult:
    """
    평가봇 출력 전체를 정밀 후처리 검사합니다.
    """
    issues = []

    # 1. 수량 기준 누락 및 정도 표현 검사
    quant_issues = check_rubric_quantitative_cells(content)
    issues.extend(quant_issues)

    # 2. 수준별 점수 및 감점 규정 중복 검사
    score_issues = check_rubric_scores_and_deductions(content)
    issues.extend(score_issues)

    # 3. 공인 교육과정 jsonl 기준 코드 검사
    code_issues = check_curriculum_codes(content)
    issues.extend(code_issues)

    passed = (len(issues) == 0)
    return RubricCheckResult(passed=passed, issues=issues)
