from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from zapret_hub_mac.domain import AppPaths
from zapret_hub_mac.services.autostart import AutostartManager
from zapret_hub_mac.services.components import ProcessManager
from zapret_hub_mac.services.diagnostics import DiagnosticsManager
from zapret_hub_mac.services.logging_service import LoggingManager
from zapret_hub_mac.services.merge import MergeManager
from zapret_hub_mac.services.profiles import ProfilesManager
from zapret_hub_mac.services.settings import SettingsManager
from zapret_hub_mac.services.storage import StorageManager
from zapret_hub_mac.services.system_proxy import SystemProxyManager


class ApplicationContext:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self.storage = StorageManager(paths)
        self.storage.ensure_layout()
        self._hydrate_resources()

        self.logging = LoggingManager(paths)
        self.settings = SettingsManager(self.storage)
        self.profiles = ProfilesManager(self.storage)
        self.merge = MergeManager(self.storage, self.settings, self.profiles)
        self.system_proxy = SystemProxyManager(self.storage)
        self.autostart = AutostartManager(self.storage)
        self.processes = ProcessManager(self.storage, self.settings, self.logging, self.merge, self.system_proxy)
        self.diagnostics = DiagnosticsManager(self.storage)
        self.merge.build_runtime_state()

    def _hydrate_resources(self) -> None:
        for resource_dir in ("profiles",):
            source_root = self.paths.resources_dir / resource_dir
            target_root = getattr(self.paths, f"{resource_dir}_dir")
            if not source_root.exists():
                continue
            for item in source_root.iterdir():
                target = target_root / item.name
                if target.exists():
                    continue
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)


def bootstrap_application() -> ApplicationContext:
    if getattr(sys, "frozen", False):
        executable_path = Path(sys.executable).resolve()
        macos_dir = executable_path.parent
        contents_dir = macos_dir.parent
        resources_dir = contents_dir / "Resources"
        bundled_resources_dir = resources_dir / "resources"
        if bundled_resources_dir.exists():
            resources_dir = bundled_resources_dir
        meipass_value = getattr(sys, "_MEIPASS", "")
        if meipass_value:
            meipass_dir = Path(meipass_value).resolve()
            meipass_resources_dir = meipass_dir / "resources"
            if meipass_resources_dir.exists():
                resources_dir = meipass_resources_dir
            elif not resources_dir.exists():
                resources_dir = meipass_dir
        project_root = contents_dir
        runtime_dir = macos_dir
    else:
        project_root = Path(__file__).resolve().parents[2]
        resources_dir = project_root / "resources"
        runtime_dir = project_root / "src" / "zapret_hub_mac" / "runtime"
    app_support_override = os.environ.get("ZAPRET_HUB_MAC_HOME", "").strip()
    if app_support_override:
        app_support_dir = Path(app_support_override).expanduser().resolve()
    else:
        app_support_dir = Path.home() / "Library" / "Application Support" / "Zapret Hub Mac"
    paths = AppPaths(
        project_root=project_root,
        resources_dir=resources_dir,
        app_support_dir=app_support_dir,
        data_dir=app_support_dir / "data",
        cache_dir=app_support_dir / "cache",
        logs_dir=app_support_dir / "logs",
        state_dir=app_support_dir / "state",
        profiles_dir=app_support_dir / "profiles",
        launch_agents_dir=Path.home() / "Library" / "LaunchAgents",
        runtime_dir=runtime_dir,
    )
    return ApplicationContext(paths)
