from __future__ import annotations

import json
import re
import urllib.request
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any

from zapret_hub_mac.services.logging_service import LoggingManager
from zapret_hub_mac.services.worker_dispatcher import SerialWorkerDispatcher


@dataclass(slots=True)
class ReleaseInfo:
    tag_name: str
    name: str
    html_url: str
    prerelease: bool


class UpdateService:
    def __init__(
        self,
        logging: LoggingManager,
        *,
        current_version: str,
        owner: str = "goshkow",
        repo: str = "Zapret-Hub-Mac",
    ) -> None:
        self.logging = logging
        self.current_version = current_version
        self.owner = owner
        self.repo = repo
        self._dispatcher = SerialWorkerDispatcher("zapret-hub-updates-worker")

    def check_for_updates_async(self) -> Future[ReleaseInfo | None]:
        return self._dispatcher.submit(self._check_for_updates)

    def _check_for_updates(self) -> ReleaseInfo | None:
        api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases?per_page=10"
        request = urllib.request.Request(
            api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Zapret-Hub-Mac",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=8.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.logging.log("warning", "Update check failed", error=str(exc), api_url=api_url)
            return None

        if not isinstance(payload, list):
            return None
        release_payload = next((item for item in payload if isinstance(item, dict) and not bool(item.get("draft", False))), None)
        if not release_payload:
            return None

        latest = ReleaseInfo(
            tag_name=str(release_payload.get("tag_name", "")).strip(),
            name=str(release_payload.get("name", "")).strip(),
            html_url=str(release_payload.get("html_url", "")).strip(),
            prerelease=bool(release_payload.get("prerelease", False)),
        )
        if not latest.tag_name or not latest.html_url:
            return None
        if self._is_newer(latest.tag_name, self.current_version):
            return latest
        return None

    def _is_newer(self, candidate: str, current: str) -> bool:
        return self._normalize_version(candidate) > self._normalize_version(current)

    def _normalize_version(self, value: str) -> tuple[int, int, int, int, int]:
        normalized = value.strip().lower()
        if normalized.startswith("v"):
            normalized = normalized[1:]
        normalized = normalized.replace("-", "")
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d*))?$", normalized)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            patch = int(match.group(3))
            stage = match.group(4) or ""
            stage_number = int(match.group(5) or 0)
            stage_rank = {"a": 0, "b": 1, "rc": 2, "": 3}.get(stage, 3)
            return (major, minor, patch, stage_rank, stage_number)

        numbers = [int(chunk) for chunk in re.findall(r"\d+", normalized)]
        if not numbers:
            return (0, 0, 0, 0, 0)
        padded = (numbers + [0, 0, 0])[:3]
        return (padded[0], padded[1], padded[2], 3, 0)

    def shutdown(self) -> None:
        self._dispatcher.shutdown()

