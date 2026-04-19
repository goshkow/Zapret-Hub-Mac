from __future__ import annotations

import locale
import subprocess
from dataclasses import asdict
from dataclasses import fields

from zapret_hub_mac.domain import AppSettings
from zapret_hub_mac.services.storage import StorageManager


class SettingsManager:
    LEGACY_SPOOFDPI_ARGS = {
        "-enable-doh -dns-addr 1.1.1.1 -window-size 1 -system-proxy=false -silent",
    }

    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage
        self.path = self.storage.paths.data_dir / "settings.json"
        self._settings = self.load()

    def load(self) -> AppSettings:
        raw = self.storage.read_json(self.path, default={}) or {}
        allowed = {field.name for field in fields(AppSettings)}
        normalized_raw = {key: value for key, value in raw.items() if key in allowed}
        settings = AppSettings(**normalized_raw)
        changed = False

        if normalized_raw != raw:
            changed = True

        if str(raw.get("language", "")).strip().lower() not in {"ru", "en"}:
            settings.language = self._detect_language()
            changed = True

        if raw.get("theme") not in {"system", "light", "oled", "dark"}:
            settings.theme = "oled"
            changed = True
        elif raw.get("theme") == "dark":
            settings.theme = "oled"
            changed = True

        if settings.traffic_engine_id not in {"spoofdpi", "zapret"}:
            settings.traffic_engine_id = "zapret"
            changed = True

        normalized_enabled = self._normalize_component_ids(settings.enabled_component_ids)
        if normalized_enabled != settings.enabled_component_ids:
            settings.enabled_component_ids = normalized_enabled
            changed = True

        normalized_autostart = self._normalize_component_ids(settings.autostart_component_ids)
        if normalized_autostart != settings.autostart_component_ids:
            settings.autostart_component_ids = normalized_autostart
            changed = True

        normalized_secret = AppSettings.normalize_tg_secret(settings.tg_proxy_secret)
        if normalized_secret != settings.tg_proxy_secret:
            settings.tg_proxy_secret = normalized_secret
            changed = True

        normalized_last_prompted = AppSettings.normalize_tg_secret(settings.tg_last_prompted_secret)
        if normalized_last_prompted != settings.tg_last_prompted_secret:
            settings.tg_last_prompted_secret = normalized_last_prompted
            changed = True

        normalized_spoofdpi_args = self._normalize_spoofdpi_args(settings.spoofdpi_args)
        if normalized_spoofdpi_args != settings.spoofdpi_args:
            settings.spoofdpi_args = normalized_spoofdpi_args
            changed = True

        if settings.notifications_enabled is not True:
            settings.notifications_enabled = True
            changed = True

        if settings.tg_auto_prompt_on_start is not True:
            settings.tg_auto_prompt_on_start = True
            changed = True

        if changed:
            self.storage.write_json(self.path, asdict(settings))
        return settings

    def get(self) -> AppSettings:
        return self._settings

    def update(self, **changes: object) -> AppSettings:
        if "traffic_engine_id" in changes and str(changes["traffic_engine_id"]) not in {"spoofdpi", "zapret"}:
            changes["traffic_engine_id"] = "spoofdpi"
        if "enabled_component_ids" in changes:
            changes["enabled_component_ids"] = self._normalize_component_ids(changes["enabled_component_ids"])
        if "autostart_component_ids" in changes:
            changes["autostart_component_ids"] = self._normalize_component_ids(changes["autostart_component_ids"])
        if "tg_proxy_secret" in changes:
            changes["tg_proxy_secret"] = AppSettings.normalize_tg_secret(str(changes["tg_proxy_secret"]))
        if "tg_last_prompted_secret" in changes:
            changes["tg_last_prompted_secret"] = AppSettings.normalize_tg_secret(str(changes["tg_last_prompted_secret"]))
        if "spoofdpi_args" in changes:
            changes["spoofdpi_args"] = self._normalize_spoofdpi_args(str(changes["spoofdpi_args"]))
        changes["notifications_enabled"] = True
        changes["tg_auto_prompt_on_start"] = True
        for key, value in changes.items():
            setattr(self._settings, key, value)
        self.save()
        return self._settings

    def save(self) -> None:
        self.storage.write_json(self.path, asdict(self._settings))

    def detect_effective_theme(self) -> str:
        if self._settings.theme in {"light", "oled"}:
            return self._settings.theme
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "oled" if result.returncode == 0 and "dark" in result.stdout.lower() else "light"
        except Exception:
            return "light"

    def _detect_language(self) -> str:
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleLanguages"],
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout.strip().lower()
            if "ru" in output:
                return "ru"
        except Exception:
            pass
        try:
            locale_name = (locale.getlocale()[0] or "").lower()
        except Exception:
            locale_name = ""
        return "ru" if locale_name.startswith("ru") else "en"

    def _normalize_component_ids(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            component_id = str(item).strip()
            if not component_id:
                continue
            if component_id in {"spoofdpi", "zapret"}:
                component_id = "traffic-engine"
            if component_id == "backend":
                continue
            normalized.append(component_id)
        return sorted(dict.fromkeys(normalized))

    def _normalize_spoofdpi_args(self, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized in self.LEGACY_SPOOFDPI_ARGS or "-enable-doh" in normalized:
            return AppSettings().spoofdpi_args
        return normalized
