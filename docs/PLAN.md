# English Crew 개발 계획서

Nov 5, 2026 · @영어과

## 0. 개요

English Crew는 영어 수업·평가 업무를 코디봇이 쪼개 팀원봇 4개에 맡기고, 교사가 결재로 확정하는 데스크톱 앱입니다. 4개 Phase로 나눠 Antigravity가 구현하고 Claude가 Phase마다 검수합니다.

| 항목 | 확정 내용 |
| --- | --- |
| 앱 형태 | 데스크톱 앱: Electron + React(Vite) |
| 백엔드 | FastAPI(Python) 로컬 서버, Electron이 함께 실행 |
| 봇 두뇌 | Gemini API (`google-genai` Python SDK), 모델명은 `.env`로 교체 가능 |
| 저장 | 로컬 SQLite + 작업 폴더 `data/workspaces/{과목}/{단원}` |
| 학생 데이터 | 로컬에만 저장, Gemini 전송 전 실명을 번호로 비식별화 |

**역할 분담**

| 주체 | 하는 일 |
| --- | --- |
| Claude | Phase 계획서, Antigravity 지시서, 검수 체크리스트 작성. 결과물 진단 후 교사에게 보고 |
| Antigravity | 지시서대로 코드 작성·실행·자체 테스트 |
| 교사 | 지시서 전달, 결과 확인, 결재. 수정 의뢰는 교사를 거쳐 Antigravity로 전달 |

**진행 규칙**

1. 한 번에 한 Phase만 진행합니다. 검수 통과 전에는 다음 Phase 지시서를 넣지 않습니다.
2. 각 Phase 지시서 앞에 2장의 공통 규칙을 Antigravity Rules로 먼저 등록합니다.
3. Phase가 끝나면 Antigravity에게 "완료 보고"(변경 파일 목록, 실행 방법, 미구현 항목)를 받아 Claude에게 붙여 넣습니다.

## 1. 공통 설계

모든 Phase가 이 설계를 기준으로 삼습니다. 구조를 바꿀 때는 이 장을 먼저 고치고 Antigravity에 전달합니다.

### 1-1. 폴더 구조

```
english-crew/
├─ docs/                 # 이 계획서, 봇 명세
├─ desktop/              # Electron main, preload
├─ frontend/             # React(Vite) 화면
│  └─ src/ components · pages · stores · api
├─ backend/              # FastAPI
│  ├─ app/ routers · services · db
│  └─ agents/            # 봇별 프롬프트와 스킬 문서
│     ├─ coordinator/  curriculum/  lesson/
│     └─ assessment/   record/
└─ data/                 # 로컬 데이터, git 제외
   ├─ crew.db
   └─ workspaces/{과목}/{단원}/
```

### 1-2. 봇 명세

| 봇 | id | 하는 일 | 출력 | 이식할 스킬 |
| --- | --- | --- | --- | --- |
| 코디봇 | coordinator | 요청 해석, 과업 분해·디스패치, 결과 취합, 결재안 작성 | DispatchPlan, ApprovalRequest (JSON) | 자체 프롬프트 |
| 교육과정봇 | curriculum | 성취기준·평가 요소 매핑 | 성취기준 목록, 평가 요소 | kr-curriculum-2022 |
| 수업봇 | lesson | 차시·활동 설계, 활동지 초안 | 차시안, 활동지 | english-activity-designer, english-lesson-design |
| 평가봇 | assessment | 문항, 루브릭, 채점 기준 | 문항, 루브릭 | exam-paper-generator, rubric-creator, non-suneung-item-writer |
| 기록봇 | record | 관찰 기록 정리, 세특 초안과 검수 | 관찰 체크리스트, 세특 초안 | seteuk-data-curator, seteuk-writer, seteuk-check |

스킬 이식 방식: 각 SKILL.md와 참조 문서를 `backend/agents/{id}/`에 복사하고, 봇 호출 시 시스템 프롬프트로 합쳐 Gemini에 보냅니다.

### 1-3. 데이터 스키마 (SQLite)

| 테이블 | 주요 컬럼 | 도입 Phase |
| --- | --- | --- |
| channels | id, name, type(all·course), course\_code | 1 |
| bots | id, name, role, prompt\_dir, model | 1 |
| messages | id, channel\_id, sender, content, created\_at | 2 |
| tasks | id, request\_id, bot\_id, title, status, output\_path | 2 |
| approvals | id, request\_id, question, status(pending·approved·rejected), reason | 2 |
| context\_notes | id, course\_code, unit, kind(진도·성취기준·차시기록), content | 3 |
| students | id, course\_code, class\_no, student\_no, name(로컬 전용) | 3 |
| routines | id, name, schedule, prompt, enabled | 4 |

### 1-4. 코디봇 출력 형식

Gemini 구조화 출력(`response_schema`)으로 아래 JSON만 받습니다. 자유 텍스트 파싱은 쓰지 않습니다.

```
{
  "summary": "영어I 3과 수행평가 설계",
  "unit": "3과",
  "tasks": [
    {"bot": "curriculum", "title": "성취기준 매핑", "deliverable": "성취기준 2개와 평가 요소"},
    {"bot": "assessment", "title": "논술형 문항과 루브릭", "deliverable": "문항 1개, 4수준 루브릭"}
  ],
  "approval_question": "논술형 1문항과 4수준 루브릭으로 확정하시겠습니까?"
}
```

### 1-5. 요청 처리 흐름

&#91;embedded content: 요청 처리 흐름 · 6단계, 결재 분기 1개\]

반려는 사유를 담아 코디봇으로 한 번 되돌아가고, 승인된 산출물만 final/에 저장됩니다.

## 2. Antigravity 공통 규칙

아래 블록 전체를 Antigravity의 워크스페이스 Rules에 한 번 등록합니다. 모든 Phase 지시서는 이 규칙을 전제로 합니다.

```
# English Crew — Workspace Rules

## Project
- Desktop app for a Korean high-school English teacher: lesson & assessment agent crew.
- Stack: Electron + React(Vite, JavaScript) / FastAPI(Python 3.11+) / SQLite / Gemini API (google-genai SDK).
- Source of truth: docs/PLAN.md (this plan). Follow its folder structure, bot spec, and schema exactly.

## Scope discipline
- Implement ONLY the current phase's instruction. Do not start the next phase.
- No refactoring outside the requested scope. No extra files, folders, or libraries beyond what the task needs.
- If the plan is ambiguous or conflicts with reality, stop and list the question instead of guessing.

## Code style
- Meaningful English names, verb-first functions (e.g. createDispatchPlan, fetchChannels).
- 2-space indent (JS), PEP 8 with 4-space (Python).
- async/await everywhere for I/O. Separate UI components from data/API logic.
- Self-explanatory code; minimal comments.

## Security & data
- GEMINI_API_KEY and GEMINI_MODEL live in backend/.env only. Never hardcode, log, or commit keys.
- data/ and .env are in .gitignore.
- Student real names never leave the machine: replace with class_no-student_no before any Gemini call.
- Electron: contextIsolation true, nodeIntegration false, expose APIs via preload only.

## UI language
- All user-facing text in Korean.

## Done report (required at the end of every phase)
1. Changed/created files (tree)
2. How to run (exact commands)
3. Acceptance criteria: each item PASS/FAIL with evidence
4. Not implemented / known issues
```

## Phase 0. 준비 (교사)

Antigravity를 열기 전에 교사가 직접 끝낼 준비 항목입니다. 스킬 파일은 해당 봇이 연결되는 Phase 직전까지만 준비하면 됩니다.

- [ ] Node.js LTS, Python 3.11 이상 설치 확인
- [ ] Google AI Studio에서 Gemini API 키 발급
- [ ] 빈 폴더 `english-crew` 생성 후 Antigravity로 열기, `git init`
- [ ] 이 계획서를 Markdown으로 내보내 `docs/PLAN.md`로 저장
- [ ] 2장 공통 규칙을 Antigravity Rules에 등록
- [ ] 과목 채널 목록 확정: 영어I, 심화영어I, 심화영어독해I, 진로영어
- [ ] (Phase 2 전) 평가봇 스킬 3개 SKILL.md를 `backend/agents/assessment/`에 복사
- [ ] (Phase 3 전) 나머지 봇 스킬 6개를 각 봇 폴더에 복사

## Phase 1. 스캐폴딩과 UI 셸

목업 데이터로 예시 화면과 같은 3단 레이아웃을 띄우는 단계입니다. 백엔드와 Gemini는 아직 연결하지 않습니다.

| 구분 | 내용 |
| --- | --- |
| 포함 | Electron + React 실행, 3단 레이아웃, 메시지 카드 4종, 우측 패널 탭, 목업 데이터 |
| 제외 | FastAPI, Gemini 호출, DB, 실제 파일 저장 |
| 산출물 | `npm run dev` 한 번으로 뜨는 데스크톱 창 |

### Antigravity 지시서

```
[Phase 1] English Crew 스캐폴딩과 UI 셸을 구현해줘. docs/PLAN.md 1장과 Rules를 따를 것.

1. 프로젝트 구성
   - desktop/: Electron main, preload (contextIsolation true)
   - frontend/: React + Vite(JavaScript) + Tailwind CSS
   - 루트 package.json의 `npm run dev`가 Vite와 Electron을 함께 실행

2. 레이아웃 (창 최소 1280x800)
   - 좌측 240px: 앱 이름 "English Crew", 부제 "나만의 영어 수업·평가 크루"
     · 채널: 전체 교무회의(배지 "전원"), 과목 채널 4개(영어I, 심화영어I, 심화영어독해I, 진로영어)
     · 팀원 5: 코디봇(총괄·디스패치), 교육과정봇(성취기준·팩트체크), 수업봇(차시·활동 설계),
       평가봇(문항·루브릭), 기록봇(관찰·세특). 각 항목 우측에 "Gemini" 라벨
     · 하단 상태줄: "연결됨 · Gemini · {모델명}" (지금은 목업 문자열)
   - 중앙: 채널 헤더(이름, 설명), 메시지 목록, 하단 입력창(Enter 전송, Shift+Enter 줄바꿈, 마이크 아이콘은 비활성)
   - 우측 320px: 탭 3개 [산출물 | 수업 맥락 | 루틴]
     · 산출물: 선택한 산출물 미리보기 영역(빈 상태 안내 문구)
     · 수업 맥락: 현재 채널의 과목·단원·성취기준 목업
     · 루틴: 목업 루틴 2개(주간 수능 문항 세트, 학기말 세특 배치)
     · 탭 아래 카드 2개: "학생 데이터 보호"(실명은 로컬에만 저장, AI에는 번호로 전송), "작업 폴더"(data/workspaces/{과목}/{단원})

3. 메시지 카드 컴포넌트 4종 (frontend/src/components/messages/)
   - TextMessage: 교사·봇 일반 메시지
   - DispatchCard: 표 형태 "✓ 과업 → @봇 · 산출물" 행 목록
   - ApprovalCard: 굵은 결재 질문 + [승인] [반려] 버튼 (클릭 시 상태 표시만 바뀜)
   - ReportCard: 봇별 "전문 영역 검토 완료"와 건수 배지

4. 목업 데이터 (frontend/src/mocks/)
   - PLAN.md 1-4의 "영어I 3과 수행평가 설계" 시나리오를 4종 카드로 재현
   - 채널을 바꾸면 해당 채널의 목업 메시지와 수업 맥락이 바뀜

5. 디자인
   - 밝은 배경, 보라 계열 강조색 1개, 카드 rx 12px, 얇은 회색 테두리
   - 상태 관리는 React 기본 훅으로 충분하면 추가 라이브러리 금지

끝나면 Rules의 Done report 형식으로 보고해줘.
```

### 검수 기준 (Claude 체크)

- [ ] `npm run dev` 한 번으로 데스크톱 창이 뜬다
- [ ] 좌·중·우 3단 폭이 240 / 가변 / 320px이다
- [ ] 채널 5개, 팀원 5개가 명세 이름·역할대로 보인다
- [ ] 카드 4종이 시나리오 순서대로 렌더링된다
- [ ] 채널 전환 시 메시지와 수업 맥락이 바뀐다
- [ ] Electron 보안 설정(contextIsolation, nodeIntegration)이 Rules와 일치한다
- [ ] 요청 범위 밖의 파일·라이브러리가 없다

## Phase 2. 백엔드와 Gemini 연결 (코디봇 + 평가봇)

봇 2개만으로 "요청 → 디스패치 → 작업 → 결재 → 확정" 한 바퀴를 실제로 돌리는 단계입니다. 나머지 봇은 비활성 상태로 둡니다.

| 구분 | 내용 |
| --- | --- |
| 포함 | FastAPI 서버, SQLite, Gemini 호출, 코디봇·평가봇, 결재 승인·반려, 산출물 파일 저장, 진행 상황 실시간 표시 |
| 제외 | 교육과정봇·수업봇·기록봇, 수업 맥락 저장, 학생 명단, 내보내기, 루틴 |
| 산출물 | 영어I 채널에서 시나리오 요청 1건이 결재 확정까지 동작 |

### Antigravity 지시서

```
[Phase 2] FastAPI 백엔드와 Gemini를 연결하고 코디봇·평가봇으로 end-to-end 흐름을 구현해줘.
Phase 1 UI는 유지하고 목업만 API로 교체할 것. docs/PLAN.md 1장과 Rules를 따를 것.

1. 백엔드 기동
   - backend/: FastAPI, 127.0.0.1:8765, GET /health
   - 개발 모드에서 Electron main이 backend/.venv의 uvicorn을 자식 프로세스로 실행하고 앱 종료 시 함께 종료
   - backend/.env: GEMINI_API_KEY, GEMINI_MODEL. 키가 없으면 /health가 {"gemini": "missing_key"} 반환

2. DB (data/crew.db)
   - PLAN 1-3의 channels, bots, messages, tasks, approvals 테이블 생성
   - 시드: 채널 5개, 봇 5개 (curriculum·lesson·record는 enabled=false)

3. Gemini 서비스 (backend/app/services/gemini_client.py)
   - google-genai SDK의 비동기 클라이언트 사용, 모델명은 GEMINI_MODEL
   - 봇 호출 시 backend/agents/{bot_id}/ 안의 .md 파일을 모두 읽어 system instruction으로 합침
   - 코디봇은 response_schema(Pydantic)로 DispatchPlan JSON만 받음
     필드: summary, unit, tasks[{bot, title, deliverable}], approval_question
   - 코디봇 프롬프트에는 enabled=true인 봇 목록만 넣어서 비활성 봇에 배정하지 않게 할 것

4. 코디봇 프롬프트 (backend/agents/coordinator/prompt.md 새로 작성)
   - 역할: 영어 교사의 요청을 과업으로 나눠 팀원봇에 배정하는 총괄
   - 규칙: 과업은 1~4개, 산출물은 구체적 분량으로, 결재 질문은 예/아니오로 답할 수 있게,
     평가 확정·학생 기록 확정은 반드시 결재 질문에 포함
   - 결과 취합 단계: 팀원 산출물을 3줄 이내로 요약하고 결재 질문을 다시 다듬음

5. 처리 흐름 (POST /channels/{id}/requests {content})
   a. 교사 메시지 저장
   b. 코디봇 → DispatchPlan → DispatchCard 메시지 저장
   c. tasks 생성 후 팀원봇 병렬 실행(asyncio.gather), 결과를
      data/workspaces/{과목}/{unit}/{task_id}.md 로 저장, status: queued→running→done|failed
   d. 코디봇 취합 → ApprovalCard + ReportCard 메시지 저장
   - 진행 상황은 SSE(GET /requests/{id}/events)로 화면에 실시간 반영

6. 결재 (POST /approvals/{id} {decision, reason})
   - approved: 산출물을 같은 폴더의 final/ 로 복사, 카드에 "확정" 표시
   - rejected: reason을 코디봇에 넘겨 1회 재디스패치(새 DispatchCard부터 다시)

7. 화면 연결
   - 채널·봇·메시지를 API에서 로드, 상태줄에 실제 모델명과 키 상태 표시
   - 우측 [산출물] 탭: 작업 보고의 항목을 누르면 해당 .md를 렌더링(react-markdown 허용)
   - Gemini 오류 시 해당 task 카드에 실패 사유 표시, 앱은 멈추지 않음

끝나면 Rules의 Done report 형식으로 보고하고, 시나리오 실행 결과 화면 캡처를 첨부해줘.
```

### 검수 기준 (Claude 체크)

- [ ] 앱 실행 시 백엔드가 자동으로 뜨고 종료 시 함께 꺼진다
- [ ] 키가 없을 때 상태줄에 안내가 뜨고 앱이 죽지 않는다
- [ ] 코디봇 출력이 스키마 JSON이며 비활성 봇에 배정하지 않는다
- [ ] 산출물이 `data/workspaces/영어I/3과/`에 저장되고 \[산출물\] 탭에서 보인다
- [ ] 승인 시 `final/` 복사, 반려 시 사유 반영 재디스패치가 1회 일어난다
- [ ] API 키가 코드·로그·git에 없다 (`.env`, `data/`가 `.gitignore`에 있음)
- [ ] 평가봇 결과 품질: 루브릭 수준 구분이 관찰 가능한 기준으로 쓰였는지 교사가 샘플 1건 확인

## Phase 3. 나머지 봇, 과목 채널, 수업 맥락

봇 5개가 모두 협업하고, 과목 채널마다 진도·성취기준 맥락이 따로 쌓이는 단계입니다. 학생 기록을 다루므로 비식별화와 규정 검사를 코드로 강제합니다.

| 구분 | 내용 |
| --- | --- |
| 포함 | 교육과정봇·수업봇·기록봇 활성화, 과업 선후 관계, 수업 맥락 편집·주입, 학생 명단과 비식별화, 세특 규정 자동 검사 |
| 제외 | docx·hwpx 내보내기, Drive 연동, 루틴, 설치 파일 |
| 산출물 | 과목 채널별로 맥락이 분리된 5봇 협업 |

### Antigravity 지시서

```
[Phase 3] 나머지 봇 3개를 활성화하고 과목 채널별 수업 맥락과 학생 비식별화를 구현해줘.
Phase 2 흐름은 유지. docs/PLAN.md 1장과 Rules를 따를 것.

1. 봇 활성화
   - curriculum, lesson, record를 enabled=true로 변경
   - 각 backend/agents/{id}/ 의 SKILL.md와 참조 문서를 system instruction으로 사용
   - SKILL.md에 스크립트 실행 단계가 있으면 봇이 아니라 백엔드가 처리:
     해당 로직을 backend/app/services/checks/ 에 Python 함수로 옮기고 봇 출력 후처리로 실행

2. 과업 선후 관계
   - DispatchPlan tasks에 depends_on(bot id 배열) 추가
   - 선행 과업이 없는 것부터 병렬 실행, 이후 단계는 선행 산출물을 입력에 포함
   - 예: curriculum → assessment, lesson

3. 수업 맥락 (context_notes)
   - 우측 [수업 맥락] 탭에서 과목별 진도·성취기준·차시기록 조회·추가·수정
   - 과목 채널 요청 시 해당 과목 맥락을 코디봇과 팀원봇 입력에 포함
   - 결재 승인 시 "날짜 · 확정 내용 1줄"을 차시기록으로 자동 추가

4. 전체 교무회의 채널
   - DispatchPlan에 course_code(nullable), clarification(nullable) 추가
   - 과목을 특정할 수 없으면 디스패치 대신 코디봇이 과목을 되묻는 메시지만 보냄

5. 학생 명단과 비식별화
   - 과목별 CSV 가져오기(class_no, student_no, name) → students 테이블
   - Gemini 호출 직전 입력 속 실명을 "{class_no}-{student_no}"로 치환,
     응답을 화면·파일에 보여줄 때만 로컬에서 실명으로 되돌림
   - 치환 전 원문은 Gemini로 절대 전송 금지, 테스트로 증명할 것

6. 기록봇 자동 검사 (seteuk-check 규칙 기반)
   - 세특 초안마다 NEIS 바이트 수, 기재금지 표현 검사를 실행
   - 결과를 ReportCard에 "통과 / 수정 필요(사유)"로 표시

끝나면 Rules의 Done report 형식으로 보고해줘. 비식별화 테스트 결과를 반드시 포함할 것.
```

### 검수 기준 (Claude 체크)

- [ ] 영어I 요청에 심화영어I 맥락이 섞이지 않는다
- [ ] 교육과정봇 산출물이 평가봇·수업봇 입력에 들어간다 (로그로 확인)
- [ ] 전체 교무회의에서 과목 없는 요청은 되묻기로 끝난다
- [ ] Gemini 요청 페이로드에 실명이 0건이다 (테스트 코드와 실행 결과)
- [ ] 세특 초안의 바이트 수와 기재금지 검사가 기존 seteuk-check 결과와 일치한다 (샘플 3건 대조)
- [ ] 승인 후 차시기록이 \[수업 맥락\] 탭에 추가된다

## Phase 4. 내보내기, 루틴, 설치 파일

확정 산출물을 학교 서식 파일로 꺼내고, 반복 업무를 루틴으로 돌리고, 설치 파일로 묶는 마무리 단계입니다. Drive 연동은 OAuth 대신 "Google Drive 데스크톱 동기화 폴더"를 내보내기 경로로 지정하는 방식으로 단순화합니다.

| 구분 | 내용 |
| --- | --- |
| 포함 | docx·hwpx·md 내보내기, 내보내기 폴더 설정, 루틴 스케줄러, Windows 설치 파일 |
| 제외 | Google API 직접 연동, 다중 사용자, 자동 업데이트 |
| 산출물 | 설치 후 실제 수업 1회 시범 운영 가능한 앱 |

### Antigravity 지시서

```
[Phase 4] 내보내기, 루틴, 설치 파일을 구현해줘. 기존 흐름은 유지. docs/PLAN.md 1장과 Rules를 따를 것.

1. 내보내기
   - 확정(final/)된 산출물 카드에 [내보내기 ▾ docx | hwpx | md] 메뉴
   - docx: python-docx, 제목·표·목록 서식 유지
   - hwpx: backend/agents/ 아래 hwpx 스킬 문서의 생성 방식을 이식.
     구현이 어렵다면 docx만 완료하고 Done report에 사유와 대안을 적을 것
   - 설정 화면에서 내보내기 폴더 지정(Drive 동기화 폴더 가능), 기본값은 문서 폴더

2. 루틴
   - routines 테이블, 우측 [루틴] 탭에서 추가·수정·켜기/끄기
   - 필드: 이름, 채널, 요청 문장, 일정(요일·시각)
   - 백엔드 스케줄러가 앱 실행 중에만 동작, 놓친 실행은 다음 실행 시 1회 보충
   - 루틴 결과도 일반 요청과 같이 결재 대기로 끝남 (자동 확정 금지)

3. 설치 파일 (Windows)
   - 백엔드를 PyInstaller로 단일 실행 파일로 묶고, 배포 모드에서 Electron이 이를 실행
   - electron-builder로 Windows 설치 파일(.exe) 생성
   - data/와 .env 위치는 사용자 데이터 폴더(app.getPath('userData'))로 이동,
     첫 실행 시 API 키 입력 화면 제공

끝나면 Rules의 Done report 형식으로 보고하고, 설치부터 첫 요청까지의 절차를 docs/INSTALL.md로 작성해줘.
```

### 검수 기준 (Claude 체크)

- [ ] docx 파일이 한글·표 깨짐 없이 열린다
- [ ] hwpx가 한글에서 열리거나, 미구현 사유와 대안이 보고되었다
- [ ] 루틴이 지정 시각에 실행되고 결재 대기로 끝난다
- [ ] 새 PC에 설치 후 API 키 입력만으로 첫 요청이 동작한다
- [ ] 설치본의 데이터가 사용자 데이터 폴더에 있고 설치 폴더에 키가 없다
- [ ] 교사 시범 운영 1회: 실제 수업 단원으로 요청 → 확정 → 내보내기까지 완료

## 검수 루프와 미결 사항

Phase마다 Antigravity의 Done report를 Claude에게 붙여 넣으면, Claude가 아래 형식으로 판정하고 수정 의뢰문을 만들어 드립니다.

```
[검수 결과] Phase N — 통과 / 조건부 통과 / 재작업
1. 검수 기준별 판정: PASS · FAIL · 확인 불가(사유)
2. 발견한 문제: 위치, 증상, 영향
3. Antigravity 수정 의뢰문 (그대로 복사해 전달)
4. 다음 Phase 진행 가능 여부
```

**미결 사항**

| 항목 | 결정 시점 | 현재 가정 |
| --- | --- | --- |
| Gemini 모델 선택 (속도형 vs 고성능형, 봇별 차등 여부) | Phase 2 시작 전 | 전 봇 동일 모델, `.env`로 교체 |
| 앱 이름 | Phase 4 설치 파일 전 | English Crew (가칭) |
| hwpx 내보내기 방식 | Phase 4 | 기존 hwpx 스킬 로직 이식, 안 되면 docx 우선 |
| 학생 명단 원본 형식 | Phase 3 시작 전 | 과목별 CSV (반, 번호, 이름) |
| macOS 지원 | 필요 시 | Windows만 |
