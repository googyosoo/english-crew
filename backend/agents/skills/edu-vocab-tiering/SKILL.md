---
name: edu-vocab-tiering
description: 고등학교 수능·내신 영어 지문 및 교과 텍스트를 Beck & McKeown의 3-Tier 어휘 프레임워크(Tier 1 일상·다의어, Tier 2 학술·수능 빈출어, Tier 3 전문·소재어)로 정밀 분류하고, 교수용 단어 카드 및 5분 퀵 퀴즈를 생성하는 교육 특화 스킬. 트리거: '/vocab-tier', '어휘 티어링', '단어 수준 분류', '티어2 어휘', '수능 어휘 분석', '지문 어휘 추출'
---

# edu-vocab-tiering — 수능·내신 지문 3-Tier 어휘 분석 및 교수 설계 📚

Gareth Manning의 *Education Agent Skills* 및 Beck, McKeown & Kucan(2002, 2013)의 검증된 3단계 어휘 지도 프레임워크에 기반하여, 고등학교 영어 지문에서 **가장 교수 효과(Leverage)가 높은 어휘를 선별하고 수준별 단어 카드와 형성평가 퀴즈**를 설계합니다.

---

## 1. 학술적 근거 (Evidence Foundation)

- **Beck, McKeown & Kucan (2002, 2013) — Bringing Words to Life**:
  - **Tier 1 (기본 일상어)**: 원어민이나 중학생 수준에서 친숙한 기본 단어. 단, **다의어(polysemy)**나 **구동사(phrasal verbs)**는 별도 주의 필요 (예: *address*, *state*, *subject*, *account for*).
  - **Tier 2 (학술 및 수능 빈출 공통어)**: 교과 전반에 걸쳐 등장하며 지문의 논리적 흐름과 변별력을 결정짓는 핵심 어휘 (예: *demonstrate*, *contradict*, *inherent*, *undermine*, *consequently*). **가장 집중적으로 사전 지도(Pre-teaching)해야 하는 핵심 타깃**.
  - **Tier 3 (교과 전문 및 도메인 특화어)**: 특정 학문이나 소재(생물학, 천문학, 철학 등)에 국한된 전문 용어로, 수능에서는 주로 각주로 주어지거나 지문 내 정의됨 (예: *photosynthesis*, *cognitive dissonance*).
- **Coxhead (2000) Academic Word List (AWL)** 및 수능 영어 평가원 기출 빅데이터 반영.

---

## 2. 사용 방법

교사가 영어 지문(수능, 모의고사, 교과서, 영자신문)을 제시하면 다음과 같이 호출합니다:

```text
/vocab-tier [영어 지문 입력]
```
또는
```text
"이 지문에서 수능 대비 핵심 Tier 2 어휘 분석하고 퀴즈 만들어줘"
```

---

## 3. 출력 결과 구조

1. **지문 개요 및 어휘 부하(Lexical Load) 분석**:
   - 총 단어 수, 어휘 다양도, 추정 난이도 (고1/고2/고3 수능 수준)
2. **3-Tier 정밀 분류표**:
   - **Tier 2 (최우선 지도 어휘 5~8개)**: 단어, 품사, 지문 내 문맥 의미, 학술적 일반 의미, 파생어/유의어
   - **Tier 3 (전문 소재 어휘)**: 학문 도메인 및 지문 독해를 위한 최소 개념 정리
   - **Tier 1 주의 어휘 (다의어/구동사)**: 학생들이 쉬운 단어로 착각하기 쉬운 문맥상 특수 의미
3. **교사용 30초 단어 티칭 카드 (Word Teaching Cards)**:
   - 발음 및 직관적 정의
   - 지문 내 원문 예문 + 2차 학술 예문
   - 한국 학생이 자주 혼동하는 포인트 (오답 매력도 함정)
4. **학생용 5분 퀵 형성평가 (Quick Vocab Check)**:
   - 문맥상 빈칸 채우기 3문항 + 반의어/유의어 선택 2문항 (정답 및 해설 포함)
