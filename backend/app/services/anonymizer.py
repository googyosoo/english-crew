import re
from typing import List, Dict, Tuple

def get_mask_tag(class_no: int, student_no: int) -> str:
    return f"[S{int(class_no):02d}-{int(student_no):02d}]"

def anonymize_text(text: str, students: List[dict]) -> Tuple[str, Dict[str, str]]:
    """
    텍스트 내 학생 실명을 '[S03-12]' 형식의 고유 가명 토큰으로 정밀 마스킹합니다.
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
        if class_no is None or student_no is None:
            continue

        mask_tag = get_mask_tag(class_no, student_no)

        # 이름 뒤 조사(은/는/이/가/을/를/의/에게/와/과/로/으로/도/만/에/랑/며 등) 결합 또는 문장부호/경계 패턴
        pattern = re.compile(rf"(?<![가-힣a-zA-Z0-9]){re.escape(name)}(?=[은는이가을를의에게와과로도만에랑며]|\b|[^가-힣a-zA-Z0-9]|$)")
        if pattern.search(masked_text):
            masked_text = pattern.sub(mask_tag, masked_text)
            restore_map[mask_tag] = name

    return masked_text, restore_map


def deanonymize_text(text: str, restore_map: Dict[str, str]) -> str:
    """
    Gemini 응답 텍스트 속 '[S03-12]' 고유 가명 토큰을 정확히 로컬 실명으로 복원합니다.
    화면 렌더링 및 로컬 파일 저장 시에만 적용됩니다.
    """
    restored_text = text
    for mask_tag, name in restore_map.items():
        restored_text = restored_text.replace(mask_tag, name)
    return restored_text
