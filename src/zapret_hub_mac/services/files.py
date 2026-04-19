from __future__ import annotations

from pathlib import Path

from zapret_hub_mac.services.storage import StorageManager


class FilesManager:
    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage

    def editable_files(self) -> list[Path]:
        return [
            self.storage.paths.state_dir / "domains.txt",
            self.storage.paths.state_dir / "exclude_domains.txt",
            self.storage.paths.state_dir / "ips.txt",
            self.storage.paths.state_dir / "merged_profile.json",
        ]

    def read_text(self, path: Path) -> str:
        self._guard(path)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def write_text(self, path: Path, text: str) -> None:
        self._guard(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _guard(self, path: Path) -> None:
        resolved = path.resolve()
        roots = [self.storage.paths.state_dir.resolve(), self.storage.paths.profiles_dir.resolve()]
        if not any(str(resolved).startswith(str(root)) for root in roots):
            raise ValueError(f"Path outside editable roots: {resolved}")
