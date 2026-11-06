import os
import shutil
import re
from pathlib import Path
from typing import Tuple

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent

def get_data_dir() -> Path:
    custom_dir = os.getenv("CREW_DATA_DIR")
    if custom_dir:
        return Path(custom_dir)
    return WORKSPACE_DIR / "data"

def sanitize_name(name: str) -> str:
    return re.sub(r'\s+', '_', name.strip())

def get_workspace_dir(
    channel_type: str,
    channel_name: str,
    unit: str = "1과",
    create_dir: bool = True
) -> Tuple[str, Path]:
    """
    Returns (relative_display_path, absolute_fs_path).
    Creates directory on disk only if create_dir is True.
    """
    data_dir = get_data_dir()
    if channel_type == "all" or channel_name == "전체 교무회의":
        rel_path = "data/workspaces/_공통/"
        abs_path = data_dir / "workspaces" / "_공통"
    else:
        safe_course = sanitize_name(channel_name)
        safe_unit = sanitize_name(unit if unit else "1과")
        rel_path = f"data/workspaces/{safe_course}/{safe_unit}"
        abs_path = data_dir / "workspaces" / safe_course / safe_unit

    if create_dir:
        abs_path.mkdir(parents=True, exist_ok=True)

    return rel_path, abs_path

def save_task_deliverable(abs_work_dir: Path, task_id: str, content: str) -> str:
    abs_work_dir.mkdir(parents=True, exist_ok=True)
    file_path = abs_work_dir / f"{task_id}.md"
    file_path.write_text(content, encoding="utf-8")
    try:
        return str(file_path.relative_to(WORKSPACE_DIR)).replace("\\", "/")
    except ValueError:
        return str(file_path).replace("\\", "/")

def copy_to_final(abs_work_dir: Path, task_id: str) -> str:
    source_path = abs_work_dir / f"{task_id}.md"
    if not source_path.exists():
        return ""
    final_dir = abs_work_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    target_path = final_dir / f"{task_id}.md"
    shutil.copy2(source_path, target_path)
    try:
        return str(target_path.relative_to(WORKSPACE_DIR)).replace("\\", "/")
    except ValueError:
        return str(target_path).replace("\\", "/")
