from __future__ import annotations

from pathlib import Path

from zapret_hub_mac.domain import DiagnosticResult
from zapret_hub_mac.services.storage import StorageManager


class DiagnosticsManager:
    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage

    def run(self) -> list[DiagnosticResult]:
        checks = [
            ("Profiles", self.storage.paths.profiles_dir),
            ("Logs", self.storage.paths.logs_dir),
            ("State", self.storage.paths.state_dir),
        ]
        results: list[DiagnosticResult] = []
        for title, path in checks:
            results.append(
                DiagnosticResult(
                    name=title,
                    status="ok" if Path(path).exists() else "error",
                    message=f"{path}",
                )
            )
        return results
