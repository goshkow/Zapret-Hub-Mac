from __future__ import annotations

import platform
import stat
from pathlib import Path

from zapret_hub_mac.domain import AppPaths


class ZapretMacOSManager:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def executable_path(self) -> Path:
        machine = platform.machine().lower()
        arch = "darwin_arm64" if machine in {"arm64", "aarch64"} else "darwin_x86_64"
        executable = self.paths.resources_dir / "bin" / "zapret_macos" / arch / "ciadpi"
        if not executable.exists():
            raise RuntimeError(f"Bundled Zapret macOS binary is missing: {executable}")
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return executable
