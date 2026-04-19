from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
from typing import Any

from zapret_hub_mac.domain import ProxyProfile
from zapret_hub_mac.services.profiles import ProfilesManager
from zapret_hub_mac.services.settings import SettingsManager
from zapret_hub_mac.services.storage import StorageManager


class MergeManager:
    def __init__(
        self,
        storage: StorageManager,
        settings: SettingsManager,
        profiles: ProfilesManager,
    ) -> None:
        self.storage = storage
        self.settings = settings
        self.profiles = profiles

    def build_runtime_state(self) -> Path:
        profile = self.profiles.get_profile(self.settings.get().backend_profile_id)
        merged = deepcopy(asdict(profile))
        settings = self.settings.get()
        use_engine = "traffic-engine" in settings.enabled_component_ids
        merged["upstream_proxy_enabled"] = use_engine
        if not use_engine:
            merged["upstream_proxy_scheme"] = "http"
            merged["upstream_proxy_host"] = ""
            merged["upstream_proxy_port"] = 0
        elif settings.traffic_engine_id == "zapret":
            merged["upstream_proxy_scheme"] = "socks5"
            merged["upstream_proxy_host"] = settings.zapret_host
            merged["upstream_proxy_port"] = int(settings.zapret_port)
        else:
            merged["upstream_proxy_scheme"] = "http"
            merged["upstream_proxy_host"] = settings.spoofdpi_host
            merged["upstream_proxy_port"] = int(settings.spoofdpi_port)
        self.storage.write_json(self.storage.paths.state_dir / "merged_profile.json", merged)
        for list_name in ("domains.txt", "exclude_domains.txt", "ips.txt"):
            path = self.storage.paths.state_dir / list_name
            if not path.exists():
                path.write_text("", encoding="utf-8")
        return self.storage.paths.state_dir / "merged_profile.json"

    def current_profile(self) -> ProxyProfile:
        payload = self.storage.read_json(self.storage.paths.state_dir / "merged_profile.json", default=None)
        if payload:
            return ProxyProfile(**payload)
        return self.profiles.get_profile(self.settings.get().backend_profile_id)

    def _merge_dicts(self, base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(base)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result
