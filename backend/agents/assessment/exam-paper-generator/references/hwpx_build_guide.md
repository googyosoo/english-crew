# HWPX 조립 가이드 (scripts/build_exam.py)

이 스킬의 최종 산출물은 **원본 예시 파일과 동일한 형식의 .hwpx**다. docx가 아니다.
이 문서는 문항 내용을 다 작성한 뒤(Step 3 완료 후) 실제 파일을 만드는 방법을 설명한다.

## 왜 hwpx를 처음부터 만들지 않는가

`assets/templates/` 안의 실제 원안지 hwpx(현재 두 개: `영어II_원안지.hwpx`,
`2025_1학년_2학기_기말고사_원안최종.hwpx`)의 실제 문단·표를 복제해 텍스트만 갈아
끼우는 방식(mail-merge)을 쓴다. 이유:

- 글꼴·여백·표 테두리 스타일이 header.xml에 정의돼 있고, 그 정의를 그대로 재사용하므로
  예시 파일과 서식이 100% 동일하게 유지된다.
- 객관식 선택지 번호(①②③④⑤)는 대부분 **문자가 아니라 문단 스타일의 자동 번호
  매기기**로 렌더링된다. 선택지 문단을 복제하기만 해도 번호가 자동으로 붙는다.
- 정답은 그 학교 원안지 관행대로 **노란 형광펜**으로 표시된다(실제 예시 파일에서 확인).

절대로 XML을 손으로 새로 작성하려 하지 말 것. 반드시 `scripts/build_exam.py` 를
통해서만 hwpx를 생성한다.

## 실행 절차

1. Step 3(문항 작성)에서 정한 모든 문항 내용을 아래 JSON 스펙 형식으로 정리한다.
2. 그 JSON을 파일로 저장한다 (예: `/tmp/exam_spec.json`).
3. 다음 명령으로 실행한다:
   ```
   python3 <스킬경로>/scripts/build_exam.py /tmp/exam_spec.json /mnt/user-data/outputs/{학년}_{학기}_{시험명}_시험지.hwpx
   ```
4. 표준출력에 `[OK] 검증 통과 ...` 가 나오면 성공. `[FATAL] ...` 이 하나라도 나오면
   **그 출력 파일을 사용자에게 전달하지 말고** 원인을 고쳐 다시 실행한다(대부분 JSON
   스펙의 필드 누락/오타).
5. 성공한 hwpx 파일을 `present_files` 로 사용자에게 전달한다.
6. 정답·해설은 별도로 `assets/answer_key_template.md` 양식에 따라 docx로 생성한다
   (`/mnt/skills/public/docx/SKILL.md` 참고) — hwpx 안에도 형광펜으로 정답이 표시되어
   있지만, 왜 그것이 정답인지 해설은 docx 쪽에만 있다.

## JSON 스펙 형식

```json
{
  "meta": {
    "template": "공통영어2",
    "school": "심인고",
    "grade": "1학년",
    "semester": "2학기",
    "exam_name": "기말고사",
    "subject": "공통영어2",
    "total_pages": "6"
  },
  "questions": [ { "type": "...", ... }, ... ]
}
```

`meta.template` 은 어느 원안지 골격을 베이스로 쓸지 고르는 값이다. `"영어II"`
(기본값, 생략 가능) 또는 `"공통영어2"` 중 하나. 두 값 모두 실제 원안지 hwpx 파일에서
검증된 앵커 좌표를 갖고 있어 결과물의 100% 서식 재현이 보장된다. 어떤 템플릿을
고르든 과목명 자체는 `meta.subject` 로 자유롭게 바꿀 수 있다(예: `template: "영어II"`
로 골격을 쓰면서 `subject: "심화영어I"` 로 과목명만 바꾸는 것도 가능 — 같은 학교의
동일 원안지 서식이기 때문). 단, `abc_table`(어법 A/B/C 박스) 유형은 `"공통영어2"`
템플릿에만 표본이 있으므로 이 유형을 쓰려면 반드시 `template: "공통영어2"` 로 지정
해야 한다.

`meta`의 나머지 값은 모두 선택값이며, 채우지 않으면 고른 템플릿의 원래 값이 그대로
남는다(영어II: 심인고/2학년/2학기/중간고사/영어II, 공통영어2: 심인고/1학년/2학기/
기말고사/공통영어2). **반드시 실제 학교/학년/과목 정보로 채워서 사용자가 엉뚱한
학교명이 찍힌 파일을 받는 일이 없게 한다.**

`questions` 배열의 순서 = 실제 시험지에 인쇄되는 순서. 객관식을 먼저, 서술형을 나중에
배치한다(서술형 타입은 자동으로 【서술형 1】,【서술형 2】... 번호가 붙는다. 번호를
직접 넣지 말 것). 객관식 문항 번호(1. 2. 3. ...)는 문서 자동 번호 매기기이므로
**stem 텍스트에 번호를 넣지 않는다.**

### type: `plain_choice5`
지문 + 한 줄씩 5지선다. (요지/주제/제목/내용일치/함축의미/응용 등 대부분의 유형)
```json
{
  "type": "plain_choice5",
  "stem": "다음 글의 요지로 가장 적절한 것은? [3점]",
  "passage": "영어 지문 전체...",
  "gloss": "*단어 뜻   **단어 뜻",
  "choices": ["선택지1", "선택지2", "선택지3", "선택지4", "선택지5"],
  "answer_idx": 1
}
```
- `gloss` 는 없으면 생략 가능(빈 문자열 X, 키 자체를 빼거나 null).
- `answer_idx` 는 0-based (0=①, 1=②, ...).
- `choices` 는 정확히 5개.

### type: `embedded_underline`
어법상 틀린 것 찾기 / 문맥상 낱말 쓰임 부적절한 것 찾기. **별도 선택지 줄이 없다** —
지문 속 ①~⑤ 원형숫자가 곧 선택지다.
```json
{
  "type": "embedded_underline",
  "stem": "다음 글의 밑줄 친 부분 중, 어법상 틀린 것은? [3.5점]",
  "lead_text": "①이 나오기 전까지의 지문 앞부분",
  "candidates": [
    ["①과 후보1 사이/후보1 뒤부터 ②까지의 텍스트", "후보1 단어/구"],
    ["...", "후보2"],
    ["...", "후보3"],
    ["...", "후보4"],
    ["...", "후보5(마지막은 지문 끝까지)"]
  ],
  "answer_idx": 2,
  "gloss": "*단어 뜻"
}
```
- `candidates` 는 정확히 5쌍. 각 쌍의 두 번째 값이 밑줄(강조 스타일)로 표시되는
  후보 단어/구다. 첫 번째 값은 **그 후보 다음부터, 다음 원형숫자 직전까지**의 일반
  지문 텍스트(마지막 항목은 지문 끝까지).
- `answer_idx` 0-based: 어느 후보가 오답(정답으로 표시할 지점)인지.

### type: `marker_passage`
무관한 문장 찾기. 별도 선택지 줄 없음.
```json
{
  "type": "marker_passage",
  "stem": "다음 글에서 전체 흐름과 관계 없는 문장은? [3.5점]",
  "lead_text": "① 표시 전, 도입 문장(번호 없음)",
  "sentences": ["①이 붙을 문장1", "문장2", "문장3", "문장4", "문장5"],
  "answer_idx": 2,
  "gloss": null
}
```
- `sentences` 정확히 5개, 각각 자동으로 ①~⑤가 앞에 붙는다.

### type: `insertion`
주어진 문장 삽입 위치 찾기. 별도 선택지 줄 없음.
```json
{
  "type": "insertion",
  "stem": "글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳은? [4점]",
  "given_sentence": "박스 안에 들어갈, 삽입해야 하는 문장",
  "lead_text": "( ① ) 표시 전, 지문 첫 부분",
  "rest_sentences": ["( ① ) 다음 문장", "( ② ) 다음 문장", "( ③ ) 다음", "( ④ ) 다음"],
  "answer_idx": 1
}
```
- `rest_sentences` 는 정확히 4개(위치가 5곳이면 마지막 ( ⑤ ) 이후 문장은 없어도 됨 —
  마지막 위치가 지문 맨 끝일 수도 있기 때문). 위치 표시는 자동으로 ( ① )~( ⑤ )가 붙는다.
- `answer_idx` 0-based, 어느 위치가 정답인지.

### type: `ab_table`
빈칸 (A)(B) 추론 / 요약문 (A)(B) 완성 공용. 6행(헤더+5choices)×4열 표.
```json
{
  "type": "ab_table",
  "stem": "다음 글의 빈칸 (A), (B)에 들어갈 말로 가장 적절한 것은? [3.5점]",
  "passage": "지문... (A) ... (B) ... 를 포함",
  "ab_rows": [["word1a","word1b"], ["word2a","word2b"], ["...","..."], ["...","..."], ["...","..."]],
  "answer_idx": 0,
  "col_a_label": "(A)",
  "col_b_label": "(B)"
}
```
- `ab_rows` 정확히 5쌍. `col_a_label`/`col_b_label` 은 생략하면 "(A)"/"(B)".

### type: `abc_table` — **`meta.template: "공통영어2"` 전용**
어법 (A)(B)(C) 박스 선택. 6행(헤더+5choices)×6열 표. `영어II` 템플릿에는 이 유형의
표본이 없으므로 반드시 공통영어2 템플릿에서만 사용한다(다른 템플릿에서 쓰면
`KeyError`로 즉시 실패한다 — 조용히 깨지지 않는다).
```json
{
  "type": "abc_table",
  "stem": "다음 글의 (A), (B), (C)에서 어법상 옳은 것끼리 짝지어진 것은? [3점]",
  "passage": "지문... (A) [has / have] ... (B) [challenge / challenges] ... (C) [is / are] ... 를 포함",
  "abc_rows": [
    ["has", "challenge", "is"],
    ["has", "challenges", "are"],
    ["have", "challenge", "are"],
    ["have", "challenges", "is"],
    ["have", "challenges", "are"]
  ],
  "answer_idx": 4,
  "col_labels": ["(A)", "(B)", "(C)"]
}
```
- `abc_rows` 정확히 5개(각 3값 튜플). `col_labels` 생략하면 "(A)"/"(B)"/"(C)".
- `answer_idx` 0-based.

### type: `order_choices`
문단 순서 배열. (A)(B)(C) 3문단 + 5개 순서 조합(고정: (A)-(B)-(C), (B)-(A)-(C),
(B)-(C)-(A), (C)-(A)-(B), (C)-(B)-(A)).
```json
{
  "type": "order_choices",
  "stem": "(A), (B), (C)를 순서에 맞게 배열한 것으로 가장 적절한 것은? [4점]",
  "passage_lead": "주어진 글(도입 단락)",
  "para_a": "(A) ...", "para_b": "(B) ...", "para_c": "(C) ...",
  "answer_idx": 2
}
```
- `answer_idx` 0-based, 5개 고정 조합 중 몇 번째가 정답인지(순서는 위 목록과 동일).

### type: `translation_blank` (서술형)
우리말 해석 / 함축 의미 서술 / 대명사 지칭 등 "지문 + 서술형 답란" 공용.
```json
{
  "type": "translation_blank",
  "stem": "다음 밑줄 친 문장을 우리말로 해석하시오. [6점]",
  "passage": "영어 지문...",
  "gloss": null,
  "num_answer_lines": 4
}
```
- 스킬 SKILL.md의 R2 규칙(답란 줄 수 표준)에 맞춰 `num_answer_lines` 를 정한다
  (해석 4-6줄, 단어찾기 1줄 등). `type`은 자동으로 앞에 `【서술형 N】`이 붙으므로
  stem에 번호를 넣지 않는다.

### type: `word_box` (서술형)
Word Box 단어 배열 영작 / 조건부 영작.
```json
{
  "type": "word_box",
  "stem": "다음 글을 읽고, <조건>에 따라 밑줄 친 우리말과 의미가 같도록 Word Box 안의 단어들을 배열하시오. [6점, 부분점수 있음]",
  "passage": "영어 지문 (한국어 밑줄 부분 포함 가능)",
  "condition_lines": ["1. Word Box의 단어를 빠짐없이 한 번씩 사용할 것.", "2. 단어의 어형을 필요하면 변화할 것."],
  "word_tokens": ["word1", "word2", "..."],
  "num_answer_lines": 2
}
```

## 지원하지 않는 유형(수동 마무리 필요)

`references/question_types_objective.md`, `references/question_types_descriptive.md`
의 "HWPX 조립 매핑" 표에서 "⚠️ 수동 마무리"로 표시된 유형(표·요약 빈칸 채우기,
어법 오류 표 등 다중 셀 표 구조)은 이번 블록 라이브러리에 없다. (어법 A/B/C 박스는
`abc_table` 로 지원되므로 더 이상 이 목록에 없다 — 위 항목 참조.) 이 유형이 꼭
필요하면:

1. 가장 비슷한 지원 유형(`plain_choice5` 또는 `translation_blank`)으로 발문+지문
   뼈대만 만들고
2. 생성된 hwpx를 사용자에게 전달하며 "이 문항은 표/박스 부분을 한글과오피스에서
   직접 삽입해야 합니다"라고 명확히 안내한다.

**표준 18+5 구성을 목표로 할 때는 애초에 지원 유형만으로 유형 배정을 짜는 것을
권장한다** (Step 2 유형 매칭 단계에서 이 표를 먼저 확인).

## 새 템플릿(다른 과목/학교) 추가하기

이미 "영어II" → "공통영어2" 두 번째 템플릿을 이 방식으로 추가해 본 실제 사례가
있다(`scripts/blocks.py` 의 `ANCHORS_ENG2`/`ANCHORS_COMMON2`/`TEMPLATES` 참조).
세 번째 템플릿을 추가할 때도 동일한 절차를 따른다:

1. 새 hwpx 파일을 `assets/templates/` 에 복사한다.
2. `scripts/inspect_template.py <새파일.hwpx>` 로 최상위 문단 인덱스/텍스트를 출력해
   본다.
3. 새 파일에서 각 지원 블록 유형(plain_choice5/embedded_underline/marker_passage/
   insertion/ab_table/order_choices/translation_blank/word_box, 있다면 abc_table도)의
   stem/passage/gloss/choices/table_para 등 앵커 인덱스를 찾아 `scripts/blocks.py` 에
   `ANCHORS_<이름>` 딕셔너리를 새로 만든다(`ANCHORS_COMMON2` 형식 그대로 따라 하면
   된다). 그 템플릿에 없는 유형(예: 새 템플릿에 어법 A/B/C 박스 표본이 없으면
   `abc_table` 키)은 딕셔너리에서 아예 빼둔다 — 호출 시 자연스럽게 `KeyError`로
   실패해 실수로 잘못된 골격에 섞이는 일을 막아준다.
4. `TEMPLATES` 딕셔너리에 `"<새 이름>": {"file": "...", "anchors": ANCHORS_<이름>}` 항목을
   추가한다.
5. `scripts/build_exam.py` 의 `ORIGINAL_VALUES` 딕셔너리에 그 템플릿 원본에 실제로
   박혀 있던 학교/학년/학기/시험명/과목명/총쪽수 리터럴 값을 그대로 추가한다(치환
   시 "이 문자열을 찾아서" 바꾸는 기준값이므로 정확히 원본과 일치해야 한다).
6. 모든 빌더 함수는 이미 `anchors` 를 인자로 받으므로 새 코드 없이 그대로 재사용된다.
7. **주의**: header.xml의 charPr/paraPr/borderFill ID는 파일마다 다르게 매겨지므로,
   한 템플릿에서 뽑은 블록을 다른 템플릿의 section0.xml에 붙이면 안 된다. 반드시
   같은 파일에서 로드한 블록만 그 파일의 본문에 붙인다(현재 구조상 `anchors` 와
   `tmpl` 이 항상 짝을 이뤄 넘어가므로 자연히 지켜진다).
8. `meta.template: "<새 이름>"` 을 쓰는 스펙 하나를 만들어
   `hwpx_engine.validate_hwpx()` 가 통과하는지 반드시 확인한다.
