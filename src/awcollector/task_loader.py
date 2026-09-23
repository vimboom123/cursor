from __future__ import annotations

from pathlib import Path

import yaml

from awcollector.models import TaskSpec


def load_task(path: str | Path) -> TaskSpec:
    task_path = Path(path)
    raw = yaml.safe_load(task_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"任务文件格式错误: {path}")
    task = TaskSpec.model_validate(raw)
    if task.html_file:
        html = Path(task.html_file)
        if not html.is_absolute():
            beside_task = (task_path.parent / html).resolve()
            from_cwd = (Path.cwd() / html).resolve()
            if beside_task.exists():
                task.html_file = str(beside_task)
            elif from_cwd.exists():
                task.html_file = str(from_cwd)
            else:
                task.html_file = str(beside_task)
    return task
