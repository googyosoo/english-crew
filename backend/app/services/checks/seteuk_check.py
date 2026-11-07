import re
from typing import List, Tuple

PROHIBITED_PATTERNS = [
    # 1. 공인어학시험
    (r"(?i)\b(TOEIC|TOEFL|TEPS|JLPT|HSK|OPIC|SAT|AP|ACT|FLEX|G-TELP)\b|토익|토플|텝스|오픽", "공인어학시험 명칭 기재 금지"),
    # 2. 교외대회 및 수상
    (r"올림피아드|경시대회|교외대회|공모전|인증시험|수상경력|금상|은상|동상\s*수상|최우수상", "교외 대회 및 수상 실적 기재 금지"),
    # 3. 논문 및 출판
    (r"소논문|학술지|학술저널|도서출간|특허출원|특허등록|\bR&E\b|연구논문", "논문, R&E, 특허 및 출판물 기재 금지"),
    # 4. 대학교명 및 사설기관
    (r"[가-힣A-Za-z]+대학교|[가-힣A-Za-z]+대학원|하버드|MIT|옥스퍼드|영재교육원|사설학원|어학원", "대학교명 및 사설기관 명칭 기재 금지"),
    # 5. 모의고사 및 석차
    (r"수능|모의고사|\d+등급|전교\s*\d+등|백분위|석차", "수능, 모의고사 및 성적 석차 기재 금지"),
    # 6. 상용 플랫폼 및 브랜드
    (r"(?i)\b(ChatGPT|YouTube|Google|Papago|Naver)\b|챗지피티|유튜브|구글|네이버|파파고", "상용 플랫폼 및 특정 상호명 기재 금지"),
    # 7. 부모 지위 암시
    (r"(부모님|아버지|어머니)의?\s*(직업|지위|교수|의사|법조인|고위공직자)", "부모 및 친인척의 사회·경제적 지위 암시 금지"),
]

def calculate_neis_bytes(text: str) -> int:
    """
    seteuk-check/scripts/byte_counter.py 와 100% 동일한 NEIS 바이트 계산:
    - 한글 완성형('가' <= ch <= '힣')만 3바이트
    - 나머지(영문, 숫자, 공백, 특수문자, 줄바꿈 포함)는 1바이트
    """
    total = 0
    for ch in text:
        if "가" <= ch <= "힣":
            total += 3
        else:
            total += 1
    return total

class SeteukCheckResult:
    def __init__(self, passed: bool, bytes_count: int, issues: List[str]):
        self.passed = passed
        self.bytes_count = bytes_count
        self.issues = issues

    @property
    def status_label(self) -> str:
        if self.passed:
            return f"통과 ({self.bytes_count} Bytes)"
        return f"수정 필요: {'; '.join(self.issues)} ({self.bytes_count} Bytes)"

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "bytes_count": self.bytes_count,
            "issues": self.issues,
            "status_label": self.status_label
        }

def check_seteuk(text: str) -> SeteukCheckResult:
    issues = []
    bytes_count = calculate_neis_bytes(text)

    # 1. 바이트 초과 검사 (최대 1,500 바이트)
    if bytes_count > 1500:
        issues.append(f"NEIS 바이트 한도 초과 (1,500바이트 기준 {bytes_count}바이트)")

    # 2. 기재 금지어 전수 검사
    for pattern, reason in PROHIBITED_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            matched_samples = list(set(matches))[:3]
            issues.append(f"{reason} (발견: {', '.join(str(m) for m in matched_samples)})")

    # 3. 특수기호 서식 금지: 가운데점(·), 물결표(~), 괄호 병기
    if "·" in text:
        issues.append("가운데점(·) 사용 금지: 쉼표(,)나 '와/과'로 대체하십시오.")

    if "~" in text:
        issues.append("물결표(~) 사용 금지: 하이픈(-)이나 '에서/까지'로 대체하십시오.")

    # 괄호 병기 금지: 예: (리처드 도킨스), (지구온난화) 등 괄호로 부가 설명 병기하는 행위
    paren_matches = re.findall(r"\([가-힣A-Za-z0-9\s,._-]+\)", text)
    if paren_matches:
        issues.append(f"괄호 병기 금지: 부가 설명이나 외래어 병기 괄호를 삭제하고 문장으로 풀어서 서술하십시오 (발견: {', '.join(paren_matches[:2])})")

    # 4. 명사형 종결 검사
    # 마침표(.)나 줄바꿈으로 구분된 문장별로 검사
    sentences = [s.strip() for s in re.split(r"[.\n]+", text) if s.strip()]
    for s in sentences:
        # 끝 문자가 명사형 종결(함, 음, 임, 됨, 봄, 보임, 확인 등)인지 검사
        last_word = s.split()[-1] if s.split() else ""
        if last_word.endswith("다") or last_word.endswith("었다") or last_word.endswith("했다") or last_word.endswith("한다") or last_word.endswith("합니다") or last_word.endswith("이다"):
            issues.append(f"명사형 종결 위반: 모든 문장은 '~함', '~음', '~임', '~보임' 등 명사형으로 종결해야 합니다 (발견: '{last_word}')")
            break

    # 5. 문장 서두 학생 이름 주어 서술 검사
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if re.match(r"^[가-힣]{2,4}[은는이가]\s+", first_line):
        issues.append("문장 서두에 학생 이름을 주어로 서술함 (구체적 활동으로 시작할 것)")

    passed = (len(issues) == 0)
    return SeteukCheckResult(passed=passed, bytes_count=bytes_count, issues=issues)
