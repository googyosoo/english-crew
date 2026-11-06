import asyncio
import json
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URL = "http://127.0.0.1:8765"

async def run_e2e_real():
    print("[1/4] Sending teacher request to eng1 channel...")
    req_body = json.dumps({"content": "영어I 3과 본문으로 논술형 1문항과 4수준 루브릭 만들어줘"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/channels/eng1/requests",
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        print("Request created:", res_data)
        request_id = res_data["request_id"]

    print(f"[2/4] Listening to SSE events for {request_id}...")
    stream_req = urllib.request.Request(f"{BASE_URL}/requests/{request_id}/events")
    approval_id = None
    with urllib.request.urlopen(stream_req) as sse_stream:
        for line in sse_stream:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data:"):
                event_data = json.loads(line_str[5:].strip())
                event_type = event_data.get("type")
                print(f" -> Event [{event_type}]:", event_data.get("data"))

                if event_type == "completed":
                    approval_id = event_data["data"]["approval_id"]
                    print("\n[SUCCESS] Pipeline completed! approval_id:", approval_id)
                    break
                elif event_type == "error":
                    print("\n[ERROR] Pipeline error:", event_data["data"])
                    break

    if not approval_id:
        print("[FAIL] Approval ID not received.")
        return

    print(f"\n[3/4] Approving request via POST /approvals/{approval_id}...")
    appr_body = json.dumps({"decision": "approved"}).encode("utf-8")
    appr_req = urllib.request.Request(
        f"{BASE_URL}/approvals/{approval_id}",
        data=appr_body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(appr_req) as resp:
        appr_res = json.loads(resp.read().decode("utf-8"))
        print("Approval decision result:", appr_res)

    print("\n[4/4] Checking generated files on disk...")
    workspace_root = Path(__file__).resolve().parent.parent
    work_dir = workspace_root / "data" / "workspaces" / "영어I" / "3과"
    if work_dir.exists():
        files = list(work_dir.glob("*.md"))
        print(f"Found {len(files)} files in {work_dir}:")
        for f in files:
            print(f"File: {f.name} ({f.stat().st_size} bytes)")
        final_files = list((work_dir / "final").glob("*.md")) if (work_dir / "final").exists() else []
        print(f"Found {len(final_files)} final files in {work_dir / 'final'}:")
        for ff in final_files:
            print(f"Final File: {ff.name} ({ff.stat().st_size} bytes)")
    else:
        print(f"Work dir does not exist: {work_dir}")

if __name__ == "__main__":
    asyncio.run(run_e2e_real())
