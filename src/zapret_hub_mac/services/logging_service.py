from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from zapret_hub_mac.domain import AppPaths, LogEntry


class LoggingManager:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self.path = self.paths.logs_dir / "app.log"

    def log(self, level: str, message: str, **context: Any) -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=level.upper(),
            message=message,
            context=context,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def read_text(self) -> str:
        if not self.path.exists():
            return ""
        return self.path.read_text(encoding="utf-8", errors="ignore")

