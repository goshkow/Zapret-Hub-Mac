from __future__ import annotations

from zapret_hub_mac.domain import ProxyProfile
from zapret_hub_mac.services.storage import StorageManager


class ProfilesManager:
    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage

    def list_profiles(self) -> list[ProxyProfile]:
        profiles: list[ProxyProfile] = []
        for path in sorted(self.storage.paths.profiles_dir.glob("*.json")):
            payload = self.storage.read_json(path, default={}) or {}
            if payload:
                profiles.append(ProxyProfile(**payload))
        return profiles

    def get_profile(self, profile_id: str) -> ProxyProfile:
        for profile in self.list_profiles():
            if profile.id == profile_id:
                return profile
        raise KeyError(profile_id)

