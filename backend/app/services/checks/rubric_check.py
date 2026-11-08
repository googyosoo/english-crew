import re
from typing import List, Dict, Optional, Set
from backend.app.services.checks.curriculum_check import get_allowed_curriculum_codes, normalize_code

# 확장된 정도 표현 목록 (부사형/형용사형 포함)
DEGREE_EXPRESSIONS = [
    "매우", "완벽하게", "완벽히", "잘", "다소", "대체로", "거의", "충분히", "명확하게", "명확히",
    "정확히", "정확하게", "적절히", "적절하게", "효과적으로", "효과적", "미흡", "모호", "상당",
    "빈번", "다수", "약간", "부분적", "비교적", "대략적", "우수", "탁월"
]

# 관찰 가능한 정량 기준 정규식: "숫자+단위(개/회/문장/단어/가지)" 또는 "조건 n개 중 m개" (단위 목록에서 '점' 제외)
QUANTITATIVE_PATTERN = re.compile(
    r"(\d+\s*(?:개|회|문장|단어|가지)|조건\s*\d+\s*개\s*중\s*\d+\s*개|\d+\s*개\s*(?:이상|이하|미만|초과)|\d+\s*가지\s*(?:이상|이하|미만|초과)|전무함|0개)"
)

# 확장된 감점 표현 정규식: "n점 감점", "n점을 감점", "-n점", "감점한다/감점 처리", "감점 기준/규정"
DEDUCTION_EXTENDED_PATTERN = re.compile(
    r"(?:-\s*\d+(?:\.\d+)?\s*점|"
    r"\d+(?:\.\d+)?\s*점\s*감점|"
    r"\d+(?:\.\d+)?\s*점(?:을|를)\s*감점|"
    r"감점\s*한다|"
    r"감점\s*처리|"
    r"감점\s*기준|"
    r"감점\s*규정)",
    re.IGNORECASE
)

# 수준 칸 내 점수 표기 제거 정규식 (단일 점수 및 범위 점수: [5~6점], (5~6점), 5~6점, [4점], (4점), 4점 등)
SCORE_LABEL_PATTERN = re.compile(
    r"\[\s*\d+(?:\.\d+)?\s*(?:~|-)\s*\d+(?:\.\d+)?\s*점\s*\]|"
    r"\(\s*\d+(?:\.\d+)?\s*(?:~|-)\s*\d+(?:\.\d+)?\s*점\s*\)|"
    r"\b\d+(?:\.\d+)?\s*(?:~|-)\s*\d+(?:\.\d+)?\s*점\b|"
    r"\[\s*\d+(?:\.\d+)?\s*점\s*\]|"
    r"\(\s*\d+(?:\.\d+)?\s*점\s*\)|"
    r"\b\d+(?:\.\d+)?\s*점[:\s]*"
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


def parse_markdown_tables(content: str):
    """
    마크다운 표들을 파싱합니다.
    규칙: 키워드가 아니라 마크다운 표 구분선(|---|) 바로 위 행만 머리글(header)로 처리.
    """
    lines = content.splitlines()
    tables = []

    for idx, line in enumerate(lines):
        line_str = line.strip()
        if not (line_str.startswith("|") and line_str.endswith("|")):
            continue
        cells = [c.strip() for c in line_str.split("|")[1:-1]]
        if not cells:
            continue

        # 구분선 판정: 모든 셀이 -, :, 공백만으로 구성됨
        is_sep = all(bool(re.match(r"^[:\s-]+$", c)) for c in cells if c)
        if is_sep and idx > 0:
            prev_line = lines[idx - 1].strip()
            if prev_line.startswith("|") and prev_line.endswith("|"):
                header_cols = [c.strip() for c in prev_line.split("|")[1:-1]]
                table_info = {
                    "header_row_idx": idx - 1,
                    "header_cols": header_cols,
                    "data_rows": []
                }
                # 구분선 다음 행부터 표가 끝날 때까지 수집
                for data_idx in range(idx + 1, len(lines)):
                    d_line = lines[data_idx].strip()
                    if not (d_line.startswith("|") and d_line.endswith("|")):
                        break
                    d_cells = [c.strip() for c in d_line.split("|")[1:-1]]
                    if not d_cells or all(bool(re.match(r"^[:\s-]+$", c)) for c in d_cells if c):
                        continue
                    table_info["data_rows"].append((data_idx, d_cells))
                tables.append(table_info)

    return tables


def split_cell_into_criteria_items(cell_text: str) -> List[str]:
    """
    [4-0c 1번] 칸 안을 <br>, - , * , 줄바꿈, 절(쉼표, 마침표) 단위로 나눠
    개별 기준 항목 목록으로 분리합니다.
    """
    # 1. <br>, <br/>, <br /> 태그를 줄바꿈으로 변환
    normalized = re.sub(r"<br\s*/?>", "\n", cell_text, flags=re.IGNORECASE)
    raw_lines = normalized.splitlines()

    items = []
    for line in raw_lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        # 불릿 기호(-, *, •, 숫자.) 분리
        sub_items = re.split(r"(?:^|\s+)(?:[-*•]|\d+\.)\s+", line_clean)
        for sub in sub_items:
            sub_clean = sub.strip()
            if not sub_clean:
                continue
            # 쉼표(,)나 마침표(.)로 연결된 절 분리 (단, 숫자 사이 소수점/천단위 쉼표는 보존)
            clauses = re.split(r"(?:(?<!\d)[,;](?!\d)|\.(?!\d)|\n+)", sub_clean)
            for cl in clauses:
                cl_clean = cl.strip()
                if cl_clean:
                    items.append(cl_clean)
    return items if items else ([cell_text.strip()] if cell_text.strip() else [])


def extract_level_quantity_metric(cell_text: str, total_conditions: Optional[int] = None):
    """
    수준 셀 텍스트에서 관찰 가능한 정량 수치/기준을 추출합니다.
    반환:
      ("condition", total_n, met_count, desc)
      ("range", item_type, low, high, unit, desc)
      ("count", item_type, low, high, op, desc)
      None
    """
    cleaned = SCORE_LABEL_PATTERN.sub("", cell_text).strip()

    # 1. "조건 n개 중 m개" 또는 조건 기반 충족/위반 판정
    # 1-a. 조건 n개 모두 포함 / 충족
    m = re.search(r"조건\s*(\d+)\s*개\s*(?:모두\s*)?(?:포함|충족)", cleaned)
    if m:
        n = int(m.group(1))
        return ("condition", n, n, f"조건 {n}개 중 {n}개 충족")

    # 1-b. 조건 n개 중 m개
    m = re.search(r"조건\s*(\d+)\s*개\s*중\s*(\d+)\s*개", cleaned)
    if m:
        n = int(m.group(1))
        met = int(m.group(2))
        return ("condition", n, met, f"조건 {n}개 중 {met}개 충족")

    # 1-c. 조건 n개 중 m개 위반 또는 n개 모두 위반
    m = re.search(r"(?:조건\s*(\d+)\s*개\s*중\s*)?(\d+)\s*개\s*(?:모두\s*)?위반", cleaned)
    if m:
        tot = int(m.group(1)) if m.group(1) else (total_conditions or 2)
        viol = int(m.group(2))
        met = max(0, tot - viol)
        return ("condition", tot, met, f"조건 {tot}개 중 {viol}개 위반(충족 {met}개)")

    # 1-d. 조건 0개 충족 / 조건 n개 중 0개
    if re.search(r"조건\s*0개\s*충족|조건\s*\d+\s*개\s*중\s*0개", cleaned):
        tot = total_conditions or 2
        return ("condition", tot, 0, f"조건 {tot}개 중 0개 충족")

    # 2. [4-0c 3번] 범위 수량 기준: "2~3회", "3~4회", "1~2개", "3~4개", "40~60단어" 등 (경계 겹침 검출용)
    m_range = re.search(r"(?:([가-힣A-Za-z]+)\s*)?(\d+)\s*(?:~|-)\s*(\d+)\s*(회|개|문장|단어|가지)", cleaned)
    if m_range:
        item_type = m_range.group(1) or "일반"
        low = int(m_range.group(2))
        high = int(m_range.group(3))
        unit = m_range.group(4)
        return ("range", f"{item_type}_{unit}", low, high, unit, f"{item_type} {low}~{high}{unit}")

    # 3. 특정 단일 항목 수량 기준: "오류 n개", "근거 n개", "어휘 n개", "5개 이상", "0개" 등
    m = re.search(r"(?:([가-힣A-Za-z]+)\s*)?(\d+)\s*(개|회|문장|단어|가지)\s*(이상|이하|미만|초과)?", cleaned)
    if m:
        item_type = m.group(1) or "일반"
        val = int(m.group(2))
        unit = m.group(3)
        op = m.group(4) or "exact"
        low = val
        high = val
        if op == "이상":
            high = 9999
        elif op == "이하":
            low = 0
        elif op == "미만":
            low = 0
            high = max(0, val - 1)
        elif op == "초과":
            low = val + 1
            high = 9999
        return ("count", f"{item_type}_{unit}", low, high, op, f"{item_type} {val}{unit} {op}")

    return None


def is_level_indicator(cell_str: str) -> bool:
    """셀 텍스트가 A, B, C, D 또는 수준 1, 2, 3, 4 등의 수준 표기인지 판별합니다."""
    clean = re.sub(r"[\s*#_`\[\]()]", "", cell_str).upper()
    if clean in ["A", "B", "C", "D", "E", "A수준", "B수준", "C수준", "D수준", "상", "중", "하", "우수", "보통", "미흡"]:
        return True
    if re.match(r"^(?:수준\s*[A-E1-5]|[A-E1-5]\s*수준|LEVEL\s*[A-E1-5])$", clean, re.IGNORECASE):
        return True
    return False


def normalize_table_for_rubric_check(tbl: dict) -> List[dict]:
    """
    [4-0c 2번] 표준형(열=수준)과 전치형(행=수준) 표를 모두 감지하여
    일관된 평가요소별 [요소명, 수준별 셀 목록, 점수 목록] 구조로 정규화합니다.
    """
    header_cols = tbl["header_cols"]
    data_rows = tbl["data_rows"]
    if not data_rows:
        return []

    # 전치형 표 판정:
    # 1. 모든 또는 대부분의 데이터 행의 첫 번째 셀이 A, B, C, D 등 수준 표기인 경우
    # 2. 또는 머리글의 첫 번째 열이 '수준', '등급', 'Level'인 경우
    first_col_header = re.sub(r"[\s*#_`\[\]()]", "", header_cols[0]) if header_cols else ""
    first_cells = [r[1][0] for r in data_rows if r[1]]
    is_transposed = (
        first_col_header in ["수준", "등급", "Level", "단계"] or
        (len(first_cells) >= 3 and sum(1 for c in first_cells if is_level_indicator(c)) >= 3)
    )

    normalized_criteria_rows = []

    if is_transposed:
        # 전치형 표: 행이 수준(A, B, C, D)이고, 열(1번 인덱스부터)이 평가 기준 또는 배점
        # 예: | 수준 | 기준 1 (내용) | 기준 2 (형식) | 배점 |
        # 또는 | 수준 | 평가 기준 및 관찰 가능한 정량 수량 기준 | 배점 |
        num_cols = len(header_cols)
        # 배점 열 위치 파악
        score_col_idx = None
        for col_i, h in enumerate(header_cols):
            clean_h = re.sub(r"[\s*#_`]", "", h)
            if clean_h in ["배점", "점수", "배점(점)"]:
                score_col_idx = col_i
                break

        # 각 평가요소 열(수준 열과 배점 열 제외)을 하나의 가상 평가요소 행으로 추출
        for col_i in range(1, num_cols):
            if col_i == score_col_idx:
                continue
            crit_name = header_cols[col_i]
            level_cells = []
            level_scores = []
            for row_idx, r_cells in data_rows:
                if col_i < len(r_cells):
                    level_cells.append((row_idx, col_i, r_cells[col_i]))
                if score_col_idx is not None and score_col_idx < len(r_cells):
                    sm = re.search(r"(\d+)\s*점", r_cells[score_col_idx])
                    if sm:
                        level_scores.append(int(sm.group(1)))

            normalized_criteria_rows.append({
                "crit_name": crit_name,
                "is_transposed": True,
                "level_cells": level_cells, # [(row_idx, col_idx, text), ...]
                "level_scores": level_scores
            })

    else:
        # 표준형 표: 각 데이터 행이 하나의 평가요소이고, 열(1번 인덱스부터)이 수준(A, B, C, D)
        # 머리글에 점수가 있는 경우 파싱
        header_scores = []
        for col in header_cols[1:]:
            sm = re.search(r"(\d+)\s*점", col)
            if sm:
                header_scores.append(int(sm.group(1)))

        for row_idx, r_cells in data_rows:
            if not r_cells:
                continue
            crit_name = r_cells[0]
            level_cells = []
            level_scores = []
            for col_i, cell in enumerate(r_cells[1:], start=2):
                col_pos = col_i - 1
                if col_pos < len(header_cols):
                    col_header = header_cols[col_pos].replace(" ", "")
                    if col_header in ["배점", "점수", "배점(점)"]:
                        continue
                level_cells.append((row_idx, col_i, cell))
                sm = re.search(r"(\d+)\s*점", cell)
                if sm:
                    level_scores.append(int(sm.group(1)))

            if not level_scores and header_scores:
                level_scores = list(header_scores)

            normalized_criteria_rows.append({
                "crit_name": crit_name,
                "is_transposed": False,
                "level_cells": level_cells,
                "level_scores": level_scores
            })

    return normalized_criteria_rows


def check_rubric_quantitative_cells(content: str) -> List[str]:
    """
    [4-0c 1, 2, 3번]
    1. '칸' 단위가 아니라 '기준 항목' 단위로 검사: 칸 안을 <br>, - , 줄바꿈으로 나눠
       정도 표현이 있는 항목은 그 항목 안에 수량 기준이 있어야 함.
    2. 행=수준, 열=기준인 전치형 표(첫 열이 A/B/C/D 또는 수준)도 같은 규칙으로 검사.
    3. 인접 수준 범위 겹침 검사: '2~3회'와 '3~4회'처럼 경계가 겹치면 '수정 필요'.
    4. 같은 평가요소 안에서 '조건 n개' 숫자가 수준마다 다르면 '수정 필요'.
    """
    issues = []
    tables = parse_markdown_tables(content)

    for tbl in tables:
        header_cols = tbl["header_cols"]
        if len(header_cols) < 2:
            continue

        normalized_rows = normalize_table_for_rubric_check(tbl)

        for crit_info in normalized_rows:
            crit_name = crit_info["crit_name"]
            is_transposed = crit_info["is_transposed"]
            level_cells = crit_info["level_cells"] # [(row_idx, col_idx, text), ...]

            row_condition_ns = []
            level_metrics = []

            # Determine dominant total conditions in this criteria if any
            combined_text = " ".join(c[2] for c in level_cells)
            n_match = re.search(r"조건\s*(\d+)\s*개", combined_text)
            dominant_n = int(n_match.group(1)) if n_match else None

            for pos_tuple in level_cells:
                row_idx, col_idx, cell = pos_tuple
                if not cell:
                    continue

                pos_label = f"열 {col_idx}행 {row_idx+1}" if is_transposed else f"{row_idx+1}행 {col_idx}번째 칸"

                cleaned_cell = SCORE_LABEL_PATTERN.sub("", cell).strip()

                # 조건 n개 중 m개 추출
                cond_matches = re.findall(r"(?:조건|요구된\s*조건)\s*(\d+)\s*개\s*중", cleaned_cell)
                for cm in cond_matches:
                    row_condition_ns.append(int(cm))

                # 칸 전체의 정량 기준 및 정도 표현 확인
                has_quant_in_cell = bool(QUANTITATIVE_PATTERN.search(cleaned_cell))
                cell_degrees = [deg for deg in DEGREE_EXPRESSIONS if deg in cleaned_cell]

                if not has_quant_in_cell:
                    if cell_degrees:
                        issues.append(
                            f"루브릭 {pos_label}({crit_name[:15]})에 객관적 정량 기준 없이 정도 표현('{', '.join(cell_degrees)}')만 사용됨: \"{cell[:35]}...\""
                        )
                    else:
                        issues.append(
                            f"루브릭 {pos_label}({crit_name[:15]})에 관찰 가능한 수량 기준(숫자+단위 또는 조건 n개 중 m개)이 누락됨: \"{cell[:35]}...\""
                        )

                # [4-0c 1번] 칸 안을 <br>, - , 줄바꿈 등으로 나눠 "기준 항목" 단위로 검사
                items = split_cell_into_criteria_items(cleaned_cell)
                if len(items) > 1:
                    for itm in items:
                        item_degrees = [deg for deg in DEGREE_EXPRESSIONS if deg in itm]
                        item_has_quant = bool(QUANTITATIVE_PATTERN.search(itm))
                        if item_degrees and not item_has_quant:
                            issues.append(
                                f"루브릭 {pos_label}({crit_name[:15]}) 항목에 객관적 정량 기준 없이 정도 표현('{', '.join(item_degrees)}')만 사용됨: \"{itm[:35]}...\""
                            )

                # Extract metric for overlap / duplicate checking
                metric = extract_level_quantity_metric(cleaned_cell, dominant_n)
                level_metrics.append((pos_label, cell, metric))

            # 같은 평가요소 행 안에서 "조건 n개" 숫자가 수준마다 다르면 "수정 필요"
            unique_ns = set(row_condition_ns)
            if len(unique_ns) > 1:
                issues.append(
                    f"루브릭 평가요소 '{crit_name[:20]}'의 기준 조건 개수(n)가 수준마다 불일치합니다: {sorted(list(unique_ns))}"
                )

            # [4-0c 3번] 인접 수준의 수량 기준이 동일하거나 범위가 겹치면 "수정 필요" (경계 겹침 포함)
            for m_idx in range(len(level_metrics) - 1):
                pos1, text1, m1 = level_metrics[m_idx]
                pos2, text2, m2 = level_metrics[m_idx + 1]
                if not m1 or not m2:
                    continue

                # 1) condition vs condition
                if m1[0] == "condition" and m2[0] == "condition":
                    tot1, met1 = m1[1], m1[2]
                    tot2, met2 = m2[1], m2[2]
                    if met1 == met2:
                        issues.append(
                            f"루브릭 평가요소 '{crit_name[:15]}'의 인접 수준({pos1} vs {pos2}) 간 수량 기준이 동일하여 변별이 불가능합니다: {m1[3]} = {m2[3]}"
                        )
                    elif met1 < met2:
                        issues.append(
                            f"루브릭 평가요소 '{crit_name[:15]}'의 상위 수준({pos1}) 기준이 하위 수준({pos2})보다 낮게 역전되었습니다: {m1[3]} < {m2[3]}"
                        )

                # 2) range/count 범위 겹침 검사
                elif m1[0] in ("range", "count") and m2[0] in ("range", "count"):
                    type1 = m1[1]
                    type2 = m2[1]
                    low1, high1 = m1[2], m1[3]
                    low2, high2 = m2[2], m2[3]

                    if type1 == type2:
                        # 동일 수치
                        if low1 == low2 and high1 == high2:
                            issues.append(
                                f"루브릭 평가요소 '{crit_name[:15]}'의 인접 수준({pos1} vs {pos2}) 간 수량 기준이 동일합니다: {m1[-1]} = {m2[-1]}"
                            )
                        else:
                            # 닫힌 구간 [low1, high1]과 [low2, high2]의 교집합 존재 여부 (경계 겹침 포함)
                            # e.g. 2~3회 vs 3~4회 -> max(2, 3) <= min(3, 4) -> 3 <= 3 (True!)
                            if max(low1, low2) <= min(high1, high2):
                                issues.append(
                                    f"루브릭 평가요소 '{crit_name[:15]}'의 인접 수준({pos1} vs {pos2}) 간 수량 범위가 겹치거나 경계가 중복되어 변별이 불가능합니다: {m1[-1]} vs {m2[-1]}"
                                )

    return issues


def check_rubric_scores_and_deductions(content: str) -> List[str]:
    """
    [4-0c 4번]
    1. 각 평가요소에 수준별 점수가 모두 있어야 하고, 최고점 합계 = 총점일 것.
    2. 감점 표현 확장: "n점 감점", "n점을 감점", "-n점", "감점한다/감점 처리", "감점 기준/규정" 모두 탐지.
    """
    issues = []

    # Detect declared total score in metadata (e.g., '10점 만점' or '배점: 10점')
    declared_total = None
    tot_match = re.search(r"(?:배점|총점)[:\s]*(\d+)\s*점", content)
    if tot_match:
        declared_total = int(tot_match.group(1))

    # 마크다운 표 바깥 본문에서 별도 감점 규정 탐지
    non_table_lines = [l for l in content.splitlines() if not (l.strip().startswith("|") and l.strip().endswith("|"))]
    non_table_text = "\n".join(non_table_lines)

    deduction_matches = DEDUCTION_EXTENDED_PATTERN.findall(non_table_text)
    if deduction_matches:
        issues.append(
            f"루브릭 외부에 별도 감점 규정('{', '.join(deduction_matches[:3])}')이 명시되어 있습니다. "
            "별도 감점 규정을 배제하고 루브릭 수준별 배점으로 일원화해야 합니다."
        )

    tables = parse_markdown_tables(content)
    row_max_scores = []

    for tbl in tables:
        normalized_rows = normalize_table_for_rubric_check(tbl)
        if not normalized_rows:
            continue

        for crit_info in normalized_rows:
            crit_name = crit_info["crit_name"]
            row_scores = crit_info["level_scores"]

            if not row_scores:
                issues.append(
                    f"루브릭 평가요소 '{crit_name[:20]}'에 각 수준별 점수(숫자+점)가 명시되지 않았습니다."
                )
                continue

            # Check descending order
            for i in range(len(row_scores) - 1):
                if row_scores[i] <= row_scores[i+1]:
                    issues.append(
                        f"루브릭 평가요소 '{crit_name[:20]}'의 수준별 점수가 내림차순이 아닙니다: {row_scores}"
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
    [10점]과 같은 배점 표기 오탐 방지: 교육과정 성취기준 규격상 하이픈(-)이 반드시 포함됨.
    """
    allowed_codes = get_allowed_curriculum_codes()
    if not allowed_codes:
        return []

    issues = []
    found_codes = re.findall(r"\[([0-9]{2}[가-힣A-Za-zⅠⅡⅰⅱ]+-[0-9A-Za-z-]+)\]", content)
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
