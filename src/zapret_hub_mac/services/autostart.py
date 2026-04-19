from __future__ import annotations

import plistlib
import sys
from pathlib import Path

from zapret_hub_mac.services.storage import StorageManager


class AutostartManager:
    LABEL = "io.github.goshkow.zapret-hub-mac"

    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage
        self.path = self.storage.paths.launch_agents_dir / f"{self.LABEL}.plist"

    def is_enabled(self) -> bool:
        return self.path.exists()

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_bytes(plistlib.dumps(self._build_payload()))
        else:
            self.path.unlink(missing_ok=True)

    def _build_payload(self) -> dict[str, object]:
        executable = Path(sys.executable).resolve()
        launch_hidden = False
        settings_path = self.storage.paths.data_dir / "settings.json"
        try:
            launch_hidden = bool(self.storage.read_json(settings_path, default={}).get("launch_hidden", False))
        except Exception:
            launch_hidden = False
        payload: dict[str, object] = {
            "Label": self.LABEL,
            "RunAtLoad": True,
            "KeepAlive": False,
            "StandardOutPath": str(self.storage.paths.logs_dir / "launchd.stdout.log"),
            "StandardErrorPath": str(self.storage.paths.logs_dir / "launchd.stderr.log"),
        }
        if self._is_frozen_app(executable):
            arguments = [str(executable)]
            if launch_hidden:
                arguments.append("--launch-hidden")
            payload["ProgramArguments"] = arguments
            payload["WorkingDirectory"] = str(executable.parent)
        else:
            arguments = [str(executable), "-m", "zapret_hub_mac.main"]
            if launch_hidden:
                arguments.append("--launch-hidden")
            payload["ProgramArguments"] = arguments
            payload["WorkingDirectory"] = str(self.storage.paths.project_root)
            payload["EnvironmentVariables"] = {
                "PYTHONPATH": str(self.storage.paths.project_root / "src"),
            }
        return payload

    def _is_frozen_app(self, executable: Path) -> bool:
        if not getattr(sys, "frozen", False):
            return False
        parts = executable.parts
        return ".app" in executable.as_posix() and "Contents" in parts and "MacOS" in parts
