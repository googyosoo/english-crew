import re
from typing import List, Dict, Tuple, Optional

# 정도 부사 목록
DEGREE_ADVERBS = ["매우", "완벽하게", "잘", "다소", "대체로", "거의", "충분히", "명확하게"]

# 관찰 가능한 객관적 기준 키워드 (개수, 조건, 빈도 등)
OBSERVABLE_CRITERIA_KEYWORDS = [
    "개", "단어", "회", "이상", "이하", "미만", "초과",
    "포함", "미포함", "오류", "오자", "문장", "조건",
    "누락", "제시함", "제시하지", "모두", "각각"
]

class RubricCheckResult:
    def __init__(self, passed: bool, issues: List[str]):
        self.passed = passed
        self.issues = issues

    @property
    def status_label(self) -> str:
        if self.passed:
            return "통과"
        return f"수정 필요: {'; '.join(self.issues)}"

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "status_label": self.status_label
        }


def check_rubric_adverbs(content: str) -> List[str]:
    """
    루브릭 표 내에서 관찰 가능한 기준 없이 정도 부사만으로 수준을 구분한 셀이 있는지 검사합니다.
    """
    issues = []
    lines = content.splitlines()
    in_table = False

    for idx, line in enumerate(lines):
        line_str = line.strip()
        if line_str.startswith("|") and line_str.endswith("|"):
            in_table = True
            cells = [c.strip() for c in line_str.split("|")[1:-1]]
            # 헤더 구분선 제외 (---)
            if any("---" in c for c in cells):
                continue
            # 헤더 행 제외
            if any("평가요소" in c or "수준" in c or "배점" in c for c in cells):
                continue

            for cell_idx, cell in enumerate(cells):
                if not cell:
                    continue
                # 셀 안에 정도 부사가 들어있는지 확인
                found_adverbs = [adv for adv in DEGREE_ADVERBS if adv in cell]
                if found_adverbs:
                    # 관찰 가능한 객관적 지표(숫자, 개수, 조건, 오류 등)가 전혀 없는지 확인
                    has_observable = any(kw in cell for kw in OBSERVABLE_CRITERIA_KEYWORDS) or bool(re.search(r"\d+", cell))
                    if not has_observable:
                        issues.append(
                            f"루브릭 {idx+1}행 {cell_idx+1}번째 칸에 객관적 지표 없이 정도 부사('{', '.join(found_adverbs)}')만으로 수준을 서술함: \"{cell[:30]}...\""
                        )
        else:
            in_table = False

    return issues


def check_rubric_scores(content: str) -> List[str]:
    """
    평가요소별 배점과 수준별 점수가 일치하고 적합한지 검사합니다.
    (예: 8점 요소면 수준 점수가 8/6/4/2 형태 등)
    """
    issues = []
    lines = content.splitlines()

    header_scores = []

    for idx, line in enumerate(lines):
        line_str = line.strip()
        if not (line_str.startswith("|") and line_str.endswith("|")):
            continue

        cells = [c.strip() for c in line_str.split("|")[1:-1]]
        if not cells or any("---" in c for c in cells):
            continue

        first_cell = cells[0]

        # 1. 헤더 행인 경우 수준별 점수 추출
        if any(h in first_cell for h in ["평가요소", "영역", "항목", "기준"]):
            header_scores = []
            for cell in cells[1:]:
                sm = re.search(r"(\d+)\s*점", cell)
                if sm:
                    header_scores.append(int(sm.group(1)))
            continue

        # 2. 데이터 행인 경우 요소 배점 추출 (예: '내용 및 아이디어 (8점)' 또는 '[8점]')
        max_score_match = re.search(r"\((\d+)\s*점\)|\[(\d+)\s*점\]|(\d+)\s*점", first_cell)
        if not max_score_match:
            continue

        max_score = int(max_score_match.group(1) or max_score_match.group(2) or max_score_match.group(3))

        # 뒤따르는 수준별 셀에서 점수 형태 검출 (예: '8점' 등)
        cell_scores = []
        for cell in cells[1:]:
            score_match = re.search(r"(\d+)\s*점", cell)
            if score_match:
                cell_scores.append(int(score_match.group(1)))

        eval_scores = cell_scores if cell_scores else header_scores

        if eval_scores:
            if eval_scores[0] != max_score:
                issues.append(
                    f"평가요소 배점({max_score}점)과 수준 점수 최고점({eval_scores[0]}점)이 불일치합니다 (행: {first_cell})"
                )
            # 내림차순 검사
            for i in range(len(eval_scores) - 1):
                if eval_scores[i] <= eval_scores[i+1]:
                    issues.append(
                        f"수준별 점수가 내림차순으로 올바르게 배정되지 않았습니다: {eval_scores}"
                    )
                    break

    return issues


def check_curriculum_codes(content: str, allowed_codes: Optional[List[str]] = None) -> List[str]:
    """
    평가봇 산출물에 기재된 성취기준 코드가 교육과정봇이 도출한 코드 목록에 존재하는지 검사합니다.
    """
    if not allowed_codes:
        return []

    issues = []
    # 코드 패턴: [12영I-01-01], [10영01-01], [12공영1-01-01] 등
    found_codes = re.findall(r"\[([0-9]{2}[가-힣A-Za-z0-9-]+)\]", content)
    unique_found = set(found_codes)
    clean_allowed = {c.strip("[]") for c in allowed_codes}

    for code in unique_found:
        if code not in clean_allowed:
            issues.append(
                f"교육과정봇이 승인하지 않은 성취기준 코드 [{code}]를 임의로 인용했습니다 (허용 코드: {list(clean_allowed)})"
            )

    return issues


def check_rubric(content: str, allowed_codes: Optional[List[str]] = None) -> RubricCheckResult:
    """
    평가봇 출력 전체를 정밀 후처리 검사합니다.
    """
    issues = []

    # 1. 정도 부사만으로 수준 구분 검사
    adverb_issues = check_rubric_adverbs(content)
    issues.extend(adverb_issues)

    # 2. 배점 및 점수 일관성 검사
    score_issues = check_rubric_scores(content)
    issues.extend(score_issues)

    # 3. 성취기준 코드 정합성 검사
    code_issues = check_curriculum_codes(content, allowed_codes)
    issues.extend(code_issues)

    passed = len(issues) == 0
    return RubricCheckResult(passed=passed, issues=issues)
