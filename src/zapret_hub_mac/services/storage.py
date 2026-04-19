from __future__ import annotations

import json
import shutil
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from zapret_hub_mac.domain import AppPaths


class StorageManager:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def ensure_layout(self) -> None:
        for path in (
            self.paths.app_support_dir,
            self.paths.data_dir,
            self.paths.cache_dir,
            self.paths.logs_dir,
            self.paths.state_dir,
            self.paths.profiles_dir,
            self.paths.launch_agents_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def read_json(self, path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if is_dataclass(payload):
            payload = asdict(payload)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def copy_tree(self, source: Path, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target)
