import re
from typing import List, Dict, Tuple

class StudentInfo:
    def __init__(self, id: str, course_code: str, class_no: int, student_no: int, name: str):
        self.id = id
        self.course_code = course_code
        self.class_no = class_no
        self.student_no = student_no
        self.name = name

    @property
    def mask_tag(self) -> str:
        return f"{self.class_no}-{self.student_no}"

def anonymize_text(text: str, students: List[dict]) -> Tuple[str, Dict[str, str]]:
    """
    텍스트 내 학생 실명을 '{class_no}-{student_no}' 가명으로 마스킹합니다.
    Gemini API로 전송되기 전에 반드시 실행됩니다.
    반환값: (마스킹된 텍스트, 복원 맵 {mask_tag: original_name})
    """
    masked_text = text
    restore_map: Dict[str, str] = {}

    # 긴 이름부터 먼저 치환하여 부분 일치 충돌 방지
    sorted_students = sorted(students, key=lambda s: len(s.get("name", "")), reverse=True)

    for st in sorted_students:
        name = st.get("name", "").strip()
        if not name or len(name) < 2:
            continue

        class_no = st.get("class_no")
        student_no = st.get("student_no")
        mask_tag = f"{class_no}-{student_no}"

        # 이름 뒤 조사(은/는/이/가/을/를/의/에게 등)가 붙는 패턴 고려
        # 단어 경계 또는 한글 조사 결합
        pattern = re.compile(rf"(?<![가-힣a-zA-Z0-9]){re.escape(name)}(?![가-힣a-zA-Z0-9])|{re.escape(name)}(?=[은는이가을를의에게])")
        if pattern.search(masked_text):
            masked_text = pattern.sub(mask_tag, masked_text)
            restore_map[mask_tag] = name

    return masked_text, restore_map


def deanonymize_text(text: str, restore_map: Dict[str, str]) -> str:
    """
    Gemini 응답 텍스트 속 '{class_no}-{student_no}' 가명을 로컬 실명으로 복원합니다.
    화면 렌더링 및 로컬 파일 저장 시에만 적용됩니다.
    """
    restored_text = text
    for mask_tag, name in restore_map.items():
        restored_text = restored_text.replace(mask_tag, name)
    return restored_text
