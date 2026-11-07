# Selection Criteria (본문→활동 매칭 가이드)

추천 단계(SKILL.md Step 3)에서 사용하는 매칭 표. 본문 분석 결과(Step 2)와 사용자 입력을 이 표에 통과시켜 5개를 선정한다.

---

## 1. 본문 길이 × 활동 적합도

| 활동 유형 | 짧음(≤150) | 보통(150-300) | 김(>300) |
|---|---|---|---|
| Cloze, Vocabulary Log | 상 | 상 | 중 |
| T/F+Justify, 5W1H Map | 중 | 상 | 상 |
| Reading Q&A 3단, Grammar Hunt | 중 | 상 | 상 |
| 3-Sentence Summary, Retell | 상 | 상 | 상 |
| Opinion Paragraph, Continue Story | 중 | 상 | 상 |
| Jigsaw Reading | 하 | 중 | **상** (반드시 분할 가능 본문) |
| Hot Seat | 상 (인물 있을 때) | 상 | 상 |
| Vocabulary Bingo, Quiz Quiz Trade | 상 | 상 | 중 |
| Information Gap, Running Dictation | **상** | 중 | 하 |
| Reader's Theater | 상 (대화 본문) | 중 | 하 |
| Poster, Gallery Walk | 중 | 상 | 상 |
| Mini-Debate | 하 | 중 | 상 |
| Concept Map | 중 | 상 | 상 |
| Cross-Reading, PSA, 세특 보고서 | 중 | 상 | 상 |

---

## 2. 장르 × 적합 활동 (강한 매칭만)

| 장르 | 강하게 어울리는 활동 (적합도 상) |
|---|---|
| 내러티브 (이야기·일화·소설) | Hot Seat, Continue the Story, Letter to Character, Reader's Theater, 5W1H Map, Retell Relay |
| 설명문 (정보·개념·과학) | Concept Map, Jigsaw Reading, T/F+Justify, 3-Sentence Summary, Vocabulary Bingo, Poster |
| 논설문 (주장·의견) | Mini-Debate, Opinion Paragraph, PSA Script, Cross-Reading, Reading Q&A 3단 |
| 대화문·인터뷰 | Reader's Theater, Information Gap, Hot Seat, Continue the Dialogue |
| 안내문·실용문 | Running Dictation, Find Someone Who, Tweet Translation, Reading Q&A |
| 자전적·체험기 | Letter to Character, Continue the Story, 세특 보고서, Opinion Paragraph |

---

## 3. 차시 위치 × 활동 목적

| 차시 위치 | 권장 활동 목적 | 대표 활동 |
|---|---|---|
| 도입 (Pre-reading) | 사전 지식 활성화·어휘 노출 | Vocabulary Bingo, Find Someone Who, Quiz Quiz Trade, Concept Map (예측용) |
| 전개 (While-reading) | 이해 점검·세부 정보 추출 | Reading Q&A 3단, T/F+Justify, 5W1H Map, Jigsaw, Order the Events, Grammar Hunt |
| 정리 (Post-reading) | 통합·산출 | 3-Sentence Summary, Retell Relay, Hot Seat, Opinion Paragraph |
| 차시 후 (Extension) | 심화·전이 | Cross-Reading, Mini-Debate, Poster, PSA, Continue the Story, 세특 보고서 |

---

## 4. 학생 수준 × 권장/주의 활동

| 수준 | 권장 (시작점으로 좋음) | 주의 (스캐폴딩 필수) |
|---|---|---|
| 기초 (A2 이하) | Cloze, Vocabulary Log, Find Someone Who, Vocabulary Bingo, Information Gap | Mini-Debate, Continue the Story, PSA Script |
| 중급 (B1) | T/F+Justify, 5W1H Map, Retell Relay, Jigsaw, Hot Seat, Opinion Paragraph | 자유 토론 / 즉흥 발화 비중 높은 활동 |
| 심화 (B2 이상) | Mini-Debate, Cross-Reading, PSA, 세특 보고서, Continue the Story | (제약 없음. 도전 과제로 운영) |

---

## 5. 시간 적합성 (대략치)

| 시간대 | 적합 활동 |
|---|---|
| 10-15분 (단시간 활동) | Cloze, Vocabulary Bingo, Quiz Quiz Trade, Find Someone Who, Tweet Translation |
| 20-25분 (표준 활동) | T/F+Justify, 5W1H Map, Hot Seat, Opinion Paragraph, Running Dictation, Concept Map, Information Gap, Letter to Character |
| 30-40분 (확장 활동) | Jigsaw Reading, Reader's Theater, Mini-Debate, Poster + Gallery Walk |
| 차시 분리 (1차시 이상) | PSA Script, Cross-Reading, Continue the Story (장편), 세특 연계 보고서 |

---

## 6. 사회적 형태별 활동 분류 (요약)

| 형태 | 활동 |
|---|---|
| **개인** | Cloze, Vocabulary Log, T/F+Justify, 5W1H Map, Reading Q&A, 3-Sentence Summary, Opinion Paragraph, Letter to Character, Continue the Story, Concept Map, Tweet Translation, Grammar Hunt |
| **짝** | Quiz Quiz Trade, Information Gap, Retell Relay (짝), Running Dictation (짝버전), Reader's Theater (2인) |
| **모둠** | Jigsaw Reading, Hot Seat, Vocabulary Bingo (모둠전), Reader's Theater (4인), Poster, Mini-Debate (4-corner), Cross-Reading 비교, PSA Script |
| **반 전체** | Find Someone Who, Gallery Walk, Class Debate (8 vs 8) |

---

## 7. 추천 5개 선정 알고리즘 (구현 절차)

1. 본문 분석 결과로 위 표 1·2를 통과 → "적합도 상" 활동만 후보 풀로 모은다.
2. 사용자 차시 위치·시간으로 표 3·5 필터 적용 → 후보를 좁힌다.
3. 학생 수준으로 표 4 필터 적용 → "권장" 우선, "주의" 활동은 1개까지만 통과.
4. 카테고리 균형 강제: 4개 카테고리 모두에서 최소 1개씩 선택. 부족한 카테고리는 "적합도 중"까지 완화해서 채운다.
5. 사회적 형태 다양성: 5개 안에 개인·짝·모둠 중 최소 2개 형태가 들어가도록 조정.
6. 사용자 선호 카테고리가 있으면 해당 카테고리에서 1개 추가 (총 5개 유지를 위해 다른 카테고리에서 1개 빼되, 4개 카테고리 모두 등장 원칙은 유지).
7. 본문에 인물·갈등·논쟁점 같은 강한 후크가 있으면 그 후크를 활용하는 활동(Hot Seat, Mini-Debate 등)을 1개 이상 포함시킨다.

---

## 8. 추천 시 표시 형식

추천 표는 다음 6개 열을 반드시 포함한다:

| # | 활동명 | 카테고리 | 형태 | 시간 | 한 줄 설명 | 적합도 근거 (본문의 무엇 때문에 좋은지) |
|---|---|---|---|---|---|---|

"적합도 근거"는 본문에서 구체적으로 무엇이 이 활동을 좋게 만드는지 한 줄로 적는다. 예: "주인공의 도덕적 갈등이 명확해 인물 인터뷰 형식이 살아남", "정의·예시·결과 3단 구조라 분할 모둠 학습에 적합", "찬반 진술이 균등해 토론 자료 추출 용이".
