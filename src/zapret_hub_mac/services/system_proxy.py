from __future__ import annotations

import subprocess
from dataclasses import asdict

from zapret_hub_mac.domain import ProxySnapshot
from zapret_hub_mac.services.storage import StorageManager


class SystemProxyManager:
    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage
        self.snapshot_path = self.storage.paths.state_dir / "system_proxy_snapshot.json"

    def apply(self, host: str, port: int, bypass: list[str]) -> None:
        snapshots = [asdict(self._snapshot_service(service)) for service in self.list_services()]
        self.storage.write_json(self.snapshot_path, snapshots)
        for service in self.list_services():
            self._run(["networksetup", "-setwebproxy", service, host, str(port)])
            self._run(["networksetup", "-setsecurewebproxy", service, host, str(port)])
            self._run(["networksetup", "-setsocksfirewallproxy", service, host, str(port)])
            self._run(["networksetup", "-setwebproxystate", service, "on"])
            self._run(["networksetup", "-setsecurewebproxystate", service, "on"])
            self._run(["networksetup", "-setsocksfirewallproxystate", service, "on"])
            if bypass:
                self._run(["networksetup", "-setproxybypassdomains", service, *bypass])

    def restore(self) -> None:
        snapshots = self.storage.read_json(self.snapshot_path, default=[]) or []
        for payload in snapshots:
            snap = ProxySnapshot(**payload)
            if snap.web_enabled and snap.web_server and snap.web_port:
                self._run(["networksetup", "-setwebproxy", snap.service, snap.web_server, str(snap.web_port)])
                self._run(["networksetup", "-setwebproxystate", snap.service, "on"])
            else:
                self._run(["networksetup", "-setwebproxystate", snap.service, "off"])

            if snap.secure_enabled and snap.secure_server and snap.secure_port:
                self._run(["networksetup", "-setsecurewebproxy", snap.service, snap.secure_server, str(snap.secure_port)])
                self._run(["networksetup", "-setsecurewebproxystate", snap.service, "on"])
            else:
                self._run(["networksetup", "-setsecurewebproxystate", snap.service, "off"])

            if snap.socks_enabled and snap.socks_server and snap.socks_port:
                self._run(["networksetup", "-setsocksfirewallproxy", snap.service, snap.socks_server, str(snap.socks_port)])
                self._run(["networksetup", "-setsocksfirewallproxystate", snap.service, "on"])
            else:
                self._run(["networksetup", "-setsocksfirewallproxystate", snap.service, "off"])

    def list_services(self) -> list[str]:
        result = self._run(["networksetup", "-listallnetworkservices"])
        services: list[str] = []
        for line in (result.stdout or "").splitlines():
            cleaned = line.strip()
            if not cleaned or "denotes that a network service is disabled" in cleaned.lower():
                continue
            if cleaned.startswith("*"):
                continue
            services.append(cleaned)
        return services

    def _snapshot_service(self, service: str) -> ProxySnapshot:
        web = self._parse_proxy_state(self._run(["networksetup", "-getwebproxy", service]).stdout or "")
        secure = self._parse_proxy_state(self._run(["networksetup", "-getsecurewebproxy", service]).stdout or "")
        socks = self._parse_proxy_state(self._run(["networksetup", "-getsocksfirewallproxy", service]).stdout or "")
        return ProxySnapshot(
            service=service,
            web_enabled=web["enabled"],
            web_server=web["server"],
            web_port=web["port"],
            secure_enabled=secure["enabled"],
            secure_server=secure["server"],
            secure_port=secure["port"],
            socks_enabled=socks["enabled"],
            socks_server=socks["server"],
            socks_port=socks["port"],
        )

    def _parse_proxy_state(self, text: str) -> dict[str, object]:
        payload = {"enabled": False, "server": "", "port": 0}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = [part.strip() for part in line.split(":", 1)]
            lowered = key.lower()
            if lowered == "enabled":
                payload["enabled"] = value.lower() == "yes"
            elif lowered == "server":
                payload["server"] = value
            elif lowered == "port":
                try:
                    payload["port"] = int(value)
                except ValueError:
                    payload["port"] = 0
        return payload

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True, check=False)
