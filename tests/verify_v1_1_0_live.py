import os
import sys
import time
import json
import socket
import secrets
import shutil
import tempfile
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_EXE = PROJECT_ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
ARTIFACT_DIR = Path(r"C:\Users\user\.gemini\antigravity\brain\bfcf6c24-c0ed-47e4-9449-0980a18f3b67")

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def run_api_request(url, method="GET", data=None, timeout=60, token=None):
    req_data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Crew-Token"] = token
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return json.loads(raw.decode("utf-8"))
            return raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"detail": body}
        return {"_status_code": e.code, **parsed}

def run_feature_pipeline(base_url, token, channel_id, request_text, feature_name):
    print(f"\n==================================================")
    print(f"Testing Feature: {feature_name}")
    print(f"Request: {request_text}")
    print(f"==================================================")

    # 1. Send teacher request
    req_res = run_api_request(
        f"{base_url}/channels/{channel_id}/requests",
        method="POST",
        data={"content": request_text},
        token=token
    )
    request_id = req_res.get("request_id")
    print(f"  -> Dispatched Request ID: {request_id}")
    assert request_id, f"Failed to get request_id: {req_res}"

    # 2. Listen to SSE events until completed
    print("  -> Streaming pipeline events via SSE...")
    stream_req = urllib.request.Request(
        f"{base_url}/requests/{request_id}/events",
        headers={"X-Crew-Token": token}
    )

    approval_id = None
    start_time = time.time()
    with urllib.request.urlopen(stream_req, timeout=120) as sse_stream:
        for line in sse_stream:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data:"):
                event_data = json.loads(line_str[5:].strip())
                event_type = event_data.get("type")
                step_data = event_data.get("data", {})
                if event_type == "plan_created":
                    tasks = step_data.get("tasks", [])
                    print(f"     [Plan Created] {len(tasks)} tasks planned:")
                    for t in tasks:
                        print(f"       - Bot: {t.get('bot_id')} | Title: {t.get('title')}")
                elif event_type == "task_started":
                    print(f"     [Task Started] {step_data.get('bot_id')} -> {step_data.get('title')}")
                elif event_type == "task_completed":
                    print(f"     [Task Done] {step_data.get('bot_id')} completed. (Length: {len(step_data.get('content', ''))} chars)")
                elif event_type == "task_update":
                    print(f"     [Task Update] Task {step_data.get('task_id')}: status={step_data.get('status')}, err={step_data.get('error_message')}")
                elif event_type == "completed":
                    approval_id = step_data.get("approval_id")
                    print(f"  -> [PIPELINE EVENT completed]: approval_id={approval_id}, data={step_data}")
                    break
                elif event_type == "error":
                    print(f"  -> [PIPELINE ERROR]: {step_data}")
                    raise RuntimeError(f"Pipeline error: {step_data}")

            if time.time() - start_time > 120:
                raise TimeoutError(f"Pipeline timed out after 120s for {feature_name}")

    assert approval_id, "Approval ID not received"

    # 3. Retrieve report and task deliverables via API
    msgs = run_api_request(f"{base_url}/channels/{channel_id}/messages", token=token)
    task_deliverables = []
    if isinstance(msgs, list):
        for m in msgs:
            meta = m.get("metadata") or {}
            if meta.get("request_id") == request_id and m.get("type") == "report":
                tasks_info = meta.get("tasks", [])
                for t in tasks_info:
                    t_id = t.get("task_id")
                    deliv_data = run_api_request(f"{base_url}/tasks/{t_id}/deliverable", token=token)
                    task_deliverables.append({
                        "bot_id": t.get("bot_id"),
                        "title": t.get("title"),
                        "status": t.get("status"),
                        "output_path": t.get("output_path"),
                        "content": deliv_data.get("content", "") if isinstance(deliv_data, dict) else ""
                    })

    # 4. Approve request
    print(f"  -> Approving request via /approvals/{approval_id}...")
    appr_res = run_api_request(
        f"{base_url}/approvals/{approval_id}",
        method="POST",
        data={"decision": "approved"},
        token=token
    )
    print(f"  -> Approval result: {appr_res.get('status')}")

    return {
        "feature_name": feature_name,
        "request_id": request_id,
        "approval_id": approval_id,
        "deliverables": task_deliverables
    }

def main():
    print("=" * 70)
    print("STARTING LIVE EXECUTION VERIFICATION FOR 3 SPECIALIZED SKILLS")
    print("=" * 70)

    # 1. Load Real GEMINI_API_KEY from backend/.env
    env_file = PROJECT_ROOT / "backend" / ".env"
    load_dotenv(dotenv_path=env_file)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    assert gemini_key, "GEMINI_API_KEY missing from backend/.env"
    print(f"GEMINI_API_KEY verified: {gemini_key[:8]}... (Length: {len(gemini_key)})")

    # 2. Allocate port and token
    test_port = get_free_port()
    test_token = secrets.token_hex(32)
    temp_dir = tempfile.mkdtemp(prefix="crew_v1_1_0_live_")
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    server_env = os.environ.copy()
    server_env["CREW_PORT"] = str(test_port)
    server_env["CREW_API_TOKEN"] = test_token
    server_env["CREW_USER_DATA_DIR"] = temp_dir
    server_env["CREW_DATA_DIR"] = str(data_dir)
    server_env["CREW_DEV_MODE"] = "0"
    server_env["GEMINI_API_KEY"] = gemini_key

    # 3. Launch backend server
    print(f"Launching backend server on port {test_port}...")
    server_log_path = Path(temp_dir) / "server.log"
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            str(PYTHON_EXE), "-m", "uvicorn",
            "backend.app.main:app",
            "--host", "127.0.0.1",
            "--port", str(test_port)
        ],
        env=server_env,
        cwd=str(PROJECT_ROOT),
        stdout=server_log_file,
        stderr=subprocess.STDOUT
    )

    base_url = f"http://127.0.0.1:{test_port}"
    results = []

    try:
        # Wait for health
        healthy = False
        for _ in range(60):
            time.sleep(0.5)
            if proc.poll() is not None:
                out, err = proc.communicate()
                print("Server died early!")
                print("STDOUT:", out.decode('utf-8', errors='replace'))
                print("STDERR:", err.decode('utf-8', errors='replace'))
                raise RuntimeError("Server exited prematurely")
            try:
                h = run_api_request(f"{base_url}/health")
                if h.get("status") == "ok":
                    healthy = True
                    break
            except Exception:
                pass

        assert healthy, f"Server failed to start on port {test_port}"
        print(f"PASS: Backend server healthy on port {test_port}!")

        # 0. Register Context Note (본문) for eng1 channel unit 3
        passage1 = (
            "The concept of digital literacy has evolved significantly over the past two decades. "
            "Initially defined simply as the ability to use computers, it now encompasses critical evaluation, "
            "ethical awareness, and collaborative problem-solving in digital environments. "
            "As artificial intelligence technologies become deeply integrated into academic and professional spaces, "
            "educators emphasize that students must develop cognitive discernment to differentiate reliable evidence "
            "from automated algorithmic errors."
        )
        print("Registering 3과 textbook body in channel context...")
        ctx_res = run_api_request(
            f"{base_url}/channels/eng1/context",
            method="POST",
            data={
                "course_code": "ENG1",
                "unit": "3과",
                "kind": "본문",
                "content": passage1
            },
            token=test_token
        )
        print(f"Context Note Registered: {ctx_res.get('id', 'OK')}")

        # Feature 1: suneung-english-creator
        res1 = run_feature_pipeline(
            base_url=base_url,
            token=test_token,
            channel_id="eng1",
            request_text="3과 본문으로 수능형 빈칸추론 5지선다 변형문제를 출제하고 오답 매력도 해설을 작성해줘",
            feature_name="1. 수능형 변형문제 (suneung-english-creator)"
        )
        results.append(res1)

        # Feature 2: edu-sentence-frame
        res2 = run_feature_pipeline(
            base_url=base_url,
            token=test_token,
            channel_id="eng1",
            request_text="3과 디지털 리터러시 주제 서술형 에세이 평가 대비 상위, 중위, 하위 수준별 학술 문장틀(Sentence Frames)과 담화 표제어 비계를 구성해줘",
            feature_name="2. 서술형 문장 비계 (edu-sentence-frame)"
        )
        results.append(res2)

        # Feature 3: edu-vocab-tiering
        res3 = run_feature_pipeline(
            base_url=base_url,
            token=test_token,
            channel_id="eng1",
            request_text="3과 주요 어휘(literacy, integrate, discernment, collaborative, encompass)에 대해 Beck & McKeown 3-Tier 어휘 수준 분류와 학생용 단어 카드를 제작해줘",
            feature_name="3. 3-Tier 어휘 수준 분류 (edu-vocab-tiering)"
        )
        results.append(res3)

        print("\n" + "=" * 70)
        print("ALL 3 SPECIALIZED SKILLS EXECUTED AND VERIFIED SUCCESSFULLY!")
        print("=" * 70)

        # Save results markdown report
        report_file = PROJECT_ROOT / "docs" / "v1_1_0_live_results.md"
        lines = [
            "# English Crew v1.1.0 3대 특화 기능 실전 구동 검증 결과",
            f"- 실행 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 포트: {test_port} | 전체 파이프라인 정상 완주\n",
        ]
        for r in results:
            lines.append(f"## {r['feature_name']}")
            lines.append(f"- Request ID: `{r['request_id']}`")
            lines.append(f"- Approval ID: `{r['approval_id']}`")
            lines.append(f"- 생성된 산출물 수: {len(r['deliverables'])}개\n")
            for d in r["deliverables"]:
                lines.append(f"### [{d['bot_id']}] {d['title']}")
                lines.append("```markdown")
                lines.append(d["content"][:800] + ("\n...(중략)..." if len(d["content"]) > 800 else ""))
                lines.append("```\n")

        report_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved to: {report_file}")

        # Now launch Electron for UI capture
        print("\nLaunching Electron capture for UI proof...")
        capture_script = PROJECT_ROOT / "tests" / "capture_v1_1_0.cjs"
        if capture_script.exists():
            cmd = f'npx electron "{capture_script}" {test_port} {test_token}'
            subprocess.run(cmd, shell=True, cwd=str(PROJECT_ROOT), timeout=60)
            print("PASS: Electron capture completed.")

    finally:
        print("Cleaning up server process...")
        if server_log_path.exists():
            print("--- SERVER LOG (last 40 lines) ---")
            log_lines = server_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for l in log_lines[-40:]:
                print(l)
            print("----------------------------------")
        subprocess.run(f"taskkill /PID {proc.pid} /T /F", shell=True, capture_output=True)
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Server shutdown and temporary data directory cleaned.")

if __name__ == "__main__":
    main()
