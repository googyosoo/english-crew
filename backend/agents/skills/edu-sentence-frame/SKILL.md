---
name: edu-sentence-frame
description: 고등학교 영어 서술형 평가, 수행평가 에세이, 수업 내 학술 토의를 위해 학생 수준(상/중/하)에 맞춘 단계별 학술 문장 틀(Sentence Frames)과 담화 표제어(Discourse Markers)를 자동 생성하는 교육 특화 스킬. 트리거: '/sentence-frame', '문장 프레임', '서술형 비계', '에세이 문장틀', '학술 문장 템플릿', '수행평가 비계'
---

# edu-sentence-frame — 고교 영어 학술 문장 틀 & 서술형 비계 생성기 ✍️

Gareth Manning의 *Education Agent Skills* 및 Gibbons(2015), Zwiers(2014)의 학술 언어 비계(Scaffolding Academic Language) 프레임워크에 기반하여, 고등학교 학생들이 영어 서술형 문항이나 수행평가 글쓰기/말하기를 수행할 때 인지적 부하를 줄이고 논리적인 고차원 영작을 완성할 수 있도록 **수준별 문장 프레임(Sentence Frames)**을 제공합니다.

---

## 1. 학술적 근거 (Evidence Foundation)

- **Gibbons (2015) — Scaffolding Language, Scaffolding Learning**:
  - 언어 학습자에게 비계(Scaffolding)는 일시적인 지원대이며, 학생의 숙달도에 따라 점진적으로 제거(Fade)되어야 함.
- **Zwiers (2014) — Building Academic Language**:
  - 학술적 사고 기능(비교/대조, 인과관계 규명, 주장 및 논증, 반론 제시, 요약)은 일상 대화체와 전혀 다른 문장 구조와 접속사를 요구함.
- **한국 2022 개정 교육과정 영어과**:
  - 학생 참여형 글쓰기 및 논술형 평가 비중 확대에 따른 수준별 비계 제공 의무화 반영.

---

## 2. 지원하는 학술 과제 유형 (Task Types)

1. **주장 및 논증 (Arguing & Justifying)**: 수행평가 논설문, 의견 제시
2. **비교 및 대조 (Comparing & Contrasting)**: 두 지문/개념 비교, 도표 분석
3. **원인과 결과 (Explaining Cause & Effect)**: 사회 현상이나 과학적 원리 설명
4. **문제와 해결책 (Problem & Solution)**: 환경/사회 문제 해결 방안 제안
5. **요약 및 결론 도출 (Summarizing & Synthesizing)**: 수능 지문 한 줄 요약(40번 유형 연계)

---

## 3. 출력 결과 구조

교사가 주제나 지문, 과제 유형을 제시하면 3단계 수준별 프레임을 출력합니다:

### ① Level 1: 전폭적 지원 프레임 (Heavily Scaffolded - 하위권)
- 뼈대와 접속사가 완전히 제공되어 핵심 단어/구만 채우면 되는 구조
- *예시: "Although [원인/상황], it leads to [결과] because [이유]."*

### ② Level 2: 부분적 지원 프레임 (Moderately Scaffolded - 중위권)
- 절(Clause) 단위의 논리적 연결을 유도하는 복합문 구조
- *예시: "While proponents argue that [상대 주장], evidence suggests [내 주장], specifically regarding [세부 논거]."*

### ③ Level 3: 최소 지원 프레임 (Lightly Scaffolded - 상위권 / 1등급 지향)
- 고난도 구문(도치, 분사구문, 가정법, 학술 명사화)을 활용한 세련된 문장 틀
- *예시: "Not only does [현상 A] demonstrate [의미], but it also fundamentally challenges the assumption that [기존 통념]."*

### ④ 필수 담화 표제어 박스 (Word Bank / Discourse Markers)
- 해당 과제에 즉시 활용할 수 있는 전환어(Transition words) 모음

### ⑤ 교사용 채점 루브릭(Rubric) 연계 포인트
- 내용 타당성, 구문 다양성, 어휘 정확성 채점 기준 제공
