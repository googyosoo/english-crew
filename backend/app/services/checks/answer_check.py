import re
from typing import List, Dict, Optional, Tuple

class AnswerCheckResult:
    def __init__(
        self,
        passed: bool,
        issues: List[str],
        word_condition: Optional[Tuple[Optional[int], Optional[int]]] = None,
        sentence_condition: Optional[Tuple[Optional[int], Optional[int]]] = None,
        actual_words: int = 0,
        actual_sentences: int = 0
    ):
        self.passed = passed
        self.issues = issues
        self.word_condition = word_condition
        self.sentence_condition = sentence_condition
        self.actual_words = actual_words
        self.actual_sentences = actual_sentences

    @property
    def status_label(self) -> str:
        if self.passed:
            return "통과"
        return f"수정 필요 ({len(self.issues)}건)"

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "status_label": self.status_label,
            "actual_words": self.actual_words,
            "actual_sentences": self.actual_sentences,
            "word_condition": self.word_condition,
            "sentence_condition": self.sentence_condition
        }


def extract_answer_text(content: str) -> str:
    """
    산출물 본문에서 모범 답안(Sample Answer) 텍스트를 추출합니다.
    """
    # 1. Look for section heading or bullet item related to 모범 답안
    sample_match = re.search(
        r"(?:##+|###+|\*\*|- \*\*)\s*(?:\d+\.\s*)?(?:모범\s*답안|모범답안|Sample\s*Answer)[^\n]*[:\n]+(.*?)(?=\n#{2,}|\n---|\n- \*\*|\Z)",
        content,
        re.DOTALL | re.IGNORECASE
    )
    if sample_match:
        section_text = sample_match.group(1).strip()
    else:
        # Fallback: look for blockquote or text under 문항
        section_text = content

    # Clean up parenthetical/asterisk metadata notes: e.g. *(45 words, 3 sentences)*, (단어 수: 18단어...), (104 words...)
    section_text = re.sub(r"\*?\([^\)]*(?:words?|sentences?|단어|문장)[^\)]*\)\*?", "", section_text, flags=re.IGNORECASE)
    section_text = re.sub(r"\*?[\[\(][^\]\)]*(?:Note|참고|각주)[^\]\)]*[\]\)]\*?", "", section_text, flags=re.IGNORECASE)

    # Extract blockquotes (lines starting with >)
    blockquotes = []
    other_lines = []
    for line in section_text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith(">"):
            cleaned = re.sub(r"^>\s*", "", line_str)
            # Remove bracket labels like [Sample Answer] or [모범 답안]
            cleaned = re.sub(r"^\[(?:Sample\s*Answer|모범\s*답안)\]\s*", "", cleaned, flags=re.IGNORECASE)
            blockquotes.append(cleaned)
        elif not line_str.startswith("#") and not line_str.startswith("-") and not line_str.startswith("*"):
            other_lines.append(line_str)

    target_text = " ".join(blockquotes) if blockquotes else " ".join(other_lines)

    # Clean up markdown markup
    target_text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", target_text)
    target_text = re.sub(r"`([^`]+)`", r"\1", target_text)
    return target_text.strip()


def count_english_words(text: str) -> int:
    """
    텍스트 내 영문 단어 수를 계산합니다.
    """
    words = re.findall(r"\b[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?(?:-[A-Za-z0-9]+)?\b", text)
    return len(words)


def count_sentences(text: str) -> int:
    """
    텍스트 내 완성된 문장 수를 계산합니다.
    """
    # Handle common abbreviations to avoid false split
    cleaned = re.sub(r"\b(?:e\.g\.|i\.e\.|etc\.|vs\.|Mr\.|Ms\.|Dr\.)", "abbr", text, flags=re.IGNORECASE)
    # Split by period, exclamation, question mark followed by space or end
    raw_sentences = [s.strip() for s in re.split(r"[.!?]+(?:\s+|\Z)", cleaned) if s.strip()]
    return len(raw_sentences)


def check_model_answer(content: str) -> AnswerCheckResult:
    """
    문항의 지시문/조건에서 단어 수와 문장 수 조건을 추출하고 모범답안이 이를 충족하는지 검사합니다.
    """
    issues = []

    # 1. Extract word condition: (min_words, max_words)
    min_words = None
    max_words = None

    # Pattern A: 150단어 이상 200단어 이내 / 150~200단어 내외 / 150~200단어 이내
    range_match = re.search(r"(\d+)\s*(?:단어\s*이상|~|-)\s*(\d+)\s*단어\s*(?:이내|내외|이하)?", content)
    if range_match:
        min_words = int(range_match.group(1))
        max_words = int(range_match.group(2))
    else:
        # Single conditions
        max_m = re.search(r"(\d+)\s*단어\s*(?:이내|이하)", content)
        if max_m:
            max_words = int(max_m.group(1))
        min_m = re.search(r"(\d+)\s*단어\s*이상", content)
        if min_m:
            min_words = int(min_m.group(1))

    # 2. Extract sentence condition: (min_sentences, max_sentences)
    min_sentences = None
    max_sentences = None

    # Pattern A: 3~4문장 / 3문장 이상 4문장 이내
    s_range_match = re.search(r"(\d+)\s*(?:문장\s*이상|~|-)\s*(\d+)\s*문장\s*(?:이내|내외|이하)?", content)
    if s_range_match:
        min_sentences = int(s_range_match.group(1))
        max_sentences = int(s_range_match.group(2))
    else:
        s_max_m = re.search(r"(\d+)\s*문장\s*(?:이내|이하)", content)
        if s_max_m:
            max_sentences = int(s_max_m.group(1))
        s_min_m = re.search(r"(\d+)\s*문장\s*이상", content)
        if s_min_m:
            min_sentences = int(s_min_m.group(1))

    # 3. Extract model answer
    answer_text = extract_answer_text(content)
    actual_words = count_english_words(answer_text)
    actual_sentences = count_sentences(answer_text)

    # 4. Verify word count condition
    if min_words is not None and actual_words < min_words:
        issues.append(
            f"모범 답안 단어 수({actual_words}단어)가 문항의 최소 요구 조건({min_words}단어 이상)에 미달합니다."
        )
    if max_words is not None and actual_words > max_words:
        issues.append(
            f"모범 답안 단어 수({actual_words}단어)가 문항의 최대 허용 조건({max_words}단어 이내)을 초과했습니다."
        )

    # 5. Verify sentence count condition
    if min_sentences is not None and actual_sentences < min_sentences:
        issues.append(
            f"모범 답안 문장 수({actual_sentences}문장)가 문항의 최소 요구 조건({min_sentences}문장 이상)에 미달합니다."
        )
    if max_sentences is not None and actual_sentences > max_sentences:
        issues.append(
            f"모범 답안 문장 수({actual_sentences}문장)가 문항의 최대 허용 조건({max_sentences}문장 이내)을 초과했습니다."
        )

    word_cond = (min_words, max_words) if (min_words or max_words) else None
    sentence_cond = (min_sentences, max_sentences) if (min_sentences or max_sentences) else None

    passed = (len(issues) == 0)
    return AnswerCheckResult(
        passed=passed,
        issues=issues,
        word_condition=word_cond,
        sentence_condition=sentence_cond,
        actual_words=actual_words,
        actual_sentences=actual_sentences
    )
