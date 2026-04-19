from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AppSettings:
    theme: str = "oled"
    language: str = "en"
    launch_at_login: bool = False
    launch_hidden: bool = False
    auto_run_components: bool = False
    notifications_enabled: bool = True
    check_updates_on_start: bool = True
    last_update_prompt_tag: str = ""
    backend_profile_id: str = "system"
    enabled_component_ids: list[str] = field(default_factory=lambda: ["tg-ws-proxy", "traffic-engine"])
    autostart_component_ids: list[str] = field(default_factory=list)
    traffic_engine_id: str = "zapret"
    tg_proxy_host: str = "127.0.0.1"
    tg_proxy_port: int = 1443
    tg_proxy_secret: str = ""
    tg_auto_prompt_on_start: bool = True
    tg_last_prompted_secret: str = ""
    spoofdpi_host: str = "127.0.0.1"
    spoofdpi_port: int = 18080
    spoofdpi_args: str = "--dns-mode https --dns-https-url https://1.1.1.1/dns-query --https-split-mode chunk --https-chunk-size 1 --silent true"
    zapret_host: str = "127.0.0.1"
    zapret_port: int = 11080
    zapret_args: str = "-d 1+s"

    @staticmethod
    def normalize_tg_secret(value: str) -> str:
        secret = value.strip().lower()
        if secret.startswith("dd"):
            secret = secret[2:]
        return secret


@dataclass(slots=True)
class ComponentDefinition:
    id: str
    name: str
    description: str
    source: str
    author: str = ""
    enabled: bool = True
    autostart: bool = False
    can_toggle: bool = True
    can_start_stop: bool = True


@dataclass(slots=True)
class ComponentState:
    component_id: str
    status: str = "stopped"
    pid: int | None = None
    last_error: str = ""


@dataclass(slots=True)
class ManagedRuntimeState:
    tracked_pid: int | None = None
    detached_pid: int | None = None
    launch_token: int = 0
    last_successful_health: bool = False
    last_command: list[str] = field(default_factory=list)
    process_name: str = ""


@dataclass(slots=True)
class ProxyProfile:
    id: str
    name: str
    description: str
    listen_host: str = "127.0.0.1"
    listen_port: int = 9080
    health_port: int = 9081
    connect_timeout: float = 8.0
    excluded_domains: list[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    upstream_proxy_enabled: bool = False
    upstream_proxy_scheme: str = "http"
    upstream_proxy_host: str = ""
    upstream_proxy_port: int = 0


@dataclass(slots=True)
class ProxySnapshot:
    service: str
    web_enabled: bool = False
    web_server: str = ""
    web_port: int = 0
    secure_enabled: bool = False
    secure_server: str = ""
    secure_port: int = 0
    socks_enabled: bool = False
    socks_server: str = ""
    socks_port: int = 0


@dataclass(slots=True)
class DiagnosticResult:
    name: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LogEntry:
    timestamp: str
    level: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AppPaths:
    project_root: Path
    resources_dir: Path
    app_support_dir: Path
    data_dir: Path
    cache_dir: Path
    logs_dir: Path
    state_dir: Path
    profiles_dir: Path
    launch_agents_dir: Path
    runtime_dir: Path
