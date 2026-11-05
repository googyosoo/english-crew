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
