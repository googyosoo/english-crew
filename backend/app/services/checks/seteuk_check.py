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
    NEIS 공식 바이트 산출:
    - 한글 1자 = 3바이트
    - 영문, 숫자, 공백, 특수문자 = 1바이트
    - 줄바꿈(\\r\\n) = 2바이트
    """
    # 끝 줄바꿈 제외
    normalized = text.rstrip("\r\n").replace("\r\n", "\n").replace("\r", "\n")
    byte_count = 0
    for char in normalized:
        if char == "\n":
            byte_count += 2
        elif ord(char) > 127:
            byte_count += 3
        else:
            byte_count += 1
    return byte_count

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

    # 3. 문장 서두 학생 이름 주어 서술 검사
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if re.match(r"^[가-힣]{2,4}[은는이가]\s+", first_line):
        issues.append("문장 서두에 학생 이름을 주어로 서술함 (구체적 활동으로 시작할 것)")

    passed = len(issues) == 0
    return SeteukCheckResult(passed=passed, bytes_count=bytes_count, issues=issues)
