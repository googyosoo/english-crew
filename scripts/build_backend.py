import sys
import subprocess
import shutil
from pathlib import Path

def build_backend():
    project_root = Path(__file__).resolve().parent.parent
    main_py = project_root / "backend" / "app" / "main.py"
    agents_dir = project_root / "backend" / "agents"
    curriculum_data_dir = project_root / "docs" / "source-skills" / "kr-curriculum-2022" / "data"
    frontend_dist_dir = project_root / "frontend" / "dist"
    output_dir = project_root / "backend-dist"

    print("==================================================")
    print("Building English Crew Backend Binary (PyInstaller)")
    print(f"Project Root: {project_root}")
    print(f"Entry Point: {main_py}")
    print(f"Output Dir: {output_dir}")
    print("==================================================")

    # Clean existing build / dist
    build_tmp = project_root / "build_backend_tmp"
    if build_tmp.exists():
        shutil.rmtree(build_tmp, ignore_errors=True)
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "english-crew-backend",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath", str(output_dir),
        "--workpath", str(build_tmp),
        "--specpath", str(build_tmp),
        f"--add-data={agents_dir}{sep}backend/agents",
        f"--add-data={curriculum_data_dir}{sep}docs/source-skills/kr-curriculum-2022/data",
        f"--add-data={frontend_dist_dir}{sep}frontend/dist",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=aiosqlite",
        "--hidden-import=google.genai",
        "--hidden-import=docx",
        "--hidden-import=fastapi",
        "--hidden-import=starlette",
        "--hidden-import=starlette.staticfiles",
        "--hidden-import=backend.app.routers.health",
        "--hidden-import=backend.app.routers.channels",
        "--hidden-import=backend.app.routers.approvals",
        "--hidden-import=backend.app.routers.context",
        "--hidden-import=backend.app.routers.export",
        "--hidden-import=backend.app.routers.routines",
        "--hidden-import=backend.app.routers.settings",
        str(main_py)
    ]

    print("Running PyInstaller command:")
    print(" ".join(cmd))
    res = subprocess.run(cmd, check=True)
    print(f"PyInstaller build finished with exit code {res.returncode}")

    # Cleanup temp
    if build_tmp.exists():
        shutil.rmtree(build_tmp, ignore_errors=True)

    exe_name = "english-crew-backend.exe" if sys.platform == "win32" else "english-crew-backend"
    built_binary = output_dir / exe_name
    if built_binary.exists():
        size_mb = built_binary.stat().st_size / (1024 * 1024)
        print(f"SUCCESS: Built backend binary at {built_binary} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"ERROR: Expected binary {built_binary} not found!")
        return False

if __name__ == "__main__":
    success = build_backend()
    sys.exit(0 if success else 1)
