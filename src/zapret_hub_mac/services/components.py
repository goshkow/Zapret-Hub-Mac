from __future__ import annotations

import os
import signal
import secrets
import shlex
import socket
import subprocess
import sys
import time
from concurrent.futures import Future
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Callable

from zapret_hub_mac.domain import AppSettings, ComponentDefinition, ComponentState, ManagedRuntimeState
from zapret_hub_mac.services.logging_service import LoggingManager
from zapret_hub_mac.services.merge import MergeManager
from zapret_hub_mac.services.settings import SettingsManager
from zapret_hub_mac.services.spoofdpi import SpoofDPIManager
from zapret_hub_mac.services.storage import StorageManager
from zapret_hub_mac.services.system_proxy import SystemProxyManager
from zapret_hub_mac.services.worker_dispatcher import SerialWorkerDispatcher
from zapret_hub_mac.services.zapret_macos import ZapretMacOSManager


class ProcessManager:
    def __init__(
        self,
        storage: StorageManager,
        settings: SettingsManager,
        logging: LoggingManager,
        merge: MergeManager,
        system_proxy: SystemProxyManager,
    ) -> None:
        self.storage = storage
        self.settings = settings
        self.logging = logging
        self.merge = merge
        self.system_proxy = system_proxy
        self.spoofdpi = SpoofDPIManager(storage.paths)
        self.zapret_macos = ZapretMacOSManager(storage.paths)
        self._lock = RLock()
        self._dispatcher = SerialWorkerDispatcher("zapret-hub-process-worker")
        self._processes: dict[str, subprocess.Popen[bytes]] = {}
        self._states: dict[str, ComponentState] = {}
        self._operation_versions: dict[str, int] = {}
        self._runtime_state: dict[str, ManagedRuntimeState] = {
            "zapret": ManagedRuntimeState(process_name="ciadpi"),
        }

    def list_components(self) -> list[ComponentDefinition]:
        settings = self.settings.get()
        enabled = set(settings.enabled_component_ids)
        autostart = set(settings.autostart_component_ids)
        return [
            ComponentDefinition(
                id="backend",
                name="PulseRoute Engine",
                description="Local proxy bridge managed automatically by the selected traffic engine. Proxies both TCP and UDP traffic, but UDP may not work in apps that do not support it.",
                source="internal://mac-proxy-engine",
                author="goshkow",
                enabled="traffic-engine" in enabled,
                autostart="traffic-engine" in autostart,
                can_toggle=False,
                can_start_stop=False,
            ),
            ComponentDefinition(
                id="tg-ws-proxy",
                name="TG WS Proxy",
                description="Telegram bridge proxy bundled from Flowseal core.",
                source="https://github.com/Flowseal/tg-ws-proxy",
                author="Flowseal",
                enabled="tg-ws-proxy" in enabled,
                autostart="tg-ws-proxy" in autostart,
            ),
            ComponentDefinition(
                id="traffic-engine",
                name="Traffic Engine",
                description="Selectable DPI bypass engine for browser and app traffic.",
                source="internal://traffic-engine",
                author="xvzc / ollesss",
                enabled="traffic-engine" in enabled,
                autostart="traffic-engine" in autostart,
            ),
        ]

    def list_states(self) -> list[ComponentState]:
        return [self._state_for(component.id) for component in self.list_components()]

    def start_component(self, component_id: str) -> ComponentState:
        return self.start_component_async(component_id)

    def start_component_async(self, component_id: str) -> ComponentState:
        if component_id == "backend":
            return self._submit_component_task(component_id, "starting", self._start_backend)
        if component_id == "tg-ws-proxy":
            return self._submit_component_task(component_id, "starting", self._start_tg_ws_proxy)
        if component_id == "traffic-engine":
            return self._submit_component_task(component_id, "starting", self._start_selected_traffic_engine)
        raise KeyError(component_id)

    def stop_component(self, component_id: str) -> ComponentState:
        return self.stop_component_async(component_id)

    def stop_component_async(self, component_id: str) -> ComponentState:
        if component_id == "backend":
            return self._submit_component_task(component_id, "stopping", self._stop_backend)
        if component_id == "tg-ws-proxy":
            return self._submit_component_task(component_id, "stopping", self._stop_tg_ws_proxy)
        if component_id == "traffic-engine":
            return self._submit_component_task(component_id, "stopping", self._stop_selected_traffic_engine)
        raise KeyError(component_id)

    def start_enabled_components(self) -> list[ComponentState]:
        return self.start_enabled_components_async()

    def start_enabled_components_async(self) -> list[ComponentState]:
        results: list[ComponentState] = []
        enabled = {component.id for component in self.list_components() if component.enabled}
        if "traffic-engine" in enabled:
            results.append(self.start_component_async("backend"))
        if "tg-ws-proxy" in enabled:
            results.append(self.start_component_async("tg-ws-proxy"))
        return results

    def stop_all(self) -> list[ComponentState]:
        return self.stop_all_async()

    def stop_all_async(self) -> list[ComponentState]:
        return [
            self.stop_component_async("tg-ws-proxy"),
            self.stop_component_async("backend"),
        ]

    def toggle_component_enabled(self, component_id: str) -> ComponentDefinition:
        if component_id == "backend":
            return next(item for item in self.list_components() if item.id == component_id)
        components = self.list_components()
        enabled = {item.id for item in components if item.enabled}
        stack_running = self.any_bypass_running()
        if component_id in enabled:
            enabled.remove(component_id)
            self.settings.update(enabled_component_ids=sorted(enabled))
            if component_id == "traffic-engine":
                self.stop_component_async("backend")
            else:
                self.stop_component_async(component_id)
        else:
            enabled.add(component_id)
            self.settings.update(enabled_component_ids=sorted(enabled))
            if stack_running:
                if component_id == "traffic-engine":
                    self.start_component_async("backend")
                else:
                    self.start_component_async(component_id)
        return next(item for item in self.list_components() if item.id == component_id)

    def toggle_component_autostart(self, component_id: str) -> ComponentDefinition:
        if component_id == "backend":
            return next(item for item in self.list_components() if item.id == component_id)
        components = self.list_components()
        autostart = {item.id for item in components if item.autostart}
        if component_id in autostart:
            autostart.remove(component_id)
        else:
            autostart.add(component_id)
        self.settings.update(autostart_component_ids=sorted(autostart))
        return next(item for item in self.list_components() if item.id == component_id)

    def prompt_telegram_proxy_link(self) -> None:
        settings = self.settings.get()
        secret, settings = self._ensure_tg_secret(settings)
        if self._open_telegram_proxy_link(settings, secret):
            self._mark_tg_secret_prompted(secret)

    def auto_prompt_telegram_proxy_link_on_start(self) -> bool:
        settings = self.settings.get()
        if not settings.tg_auto_prompt_on_start:
            return False
        secret, settings = self._ensure_tg_secret(settings)
        if not secret or AppSettings.normalize_tg_secret(settings.tg_last_prompted_secret) == secret:
            return False
        if self._open_telegram_proxy_link(settings, secret):
            self._mark_tg_secret_prompted(secret)
            return True
        return False

    def rebuild_runtime(self) -> Future[Path]:
        return self._dispatcher.submit(self.merge.build_runtime_state)

    def wait_for_idle(self, timeout: float | None = None) -> None:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                if not any(state.status in {"starting", "stopping"} for state in self._states.values()):
                    return
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("Process manager is still busy.")
            time.sleep(0.05)

    def _start_backend(self) -> ComponentState:
        self._stop_backend_runtime(stop_engine=False)
        if self._traffic_engine_required():
            engine_state = self._start_selected_traffic_engine()
            if engine_state.status != "running":
                raise RuntimeError(engine_state.last_error or "Traffic engine failed to start.")
        profile_path = self.merge.build_runtime_state()
        profile = self.merge.current_profile()
        log_path = self.storage.paths.logs_dir / "backend.log"
        command = self._component_command(
            "backend",
            "--profile",
            str(profile_path),
            "--log-file",
            str(log_path),
        )
        process = self._spawn_component(command, log_path)
        with self._lock:
            self._processes["backend"] = process
        started = False
        for _ in range(40):
            if process.poll() is not None:
                break
            if self._is_port_open(profile.listen_host, profile.health_port):
                started = True
                break
            time.sleep(0.15)
        if not started:
            state = ComponentState("backend", status="error", pid=process.pid, last_error="PulseRoute Engine health check failed.")
            with self._lock:
                self._states["backend"] = state
            return state
        self.system_proxy.apply(profile.listen_host, profile.listen_port, profile.excluded_domains)
        state = ComponentState("backend", status="running", pid=process.pid)
        with self._lock:
            self._states["backend"] = state
        self.logging.log("info", "PulseRoute Engine started", command=command, profile=asdict(profile))
        return state

    def _stop_backend(self) -> ComponentState:
        return self._stop_backend_runtime(stop_engine=True)

    def _stop_backend_runtime(self, *, stop_engine: bool) -> ComponentState:
        with self._lock:
            process = self._processes.pop("backend", None)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
        self.system_proxy.restore()
        if stop_engine:
            self._stop_selected_traffic_engine_runtime()
        state = ComponentState("backend", status="stopped")
        with self._lock:
            self._states["backend"] = state
        self.logging.log("info", "PulseRoute Engine stopped")
        return state

    def _start_spoofdpi(self) -> ComponentState:
        running_state = self._state_for("spoofdpi")
        if running_state.status == "running":
            return running_state

        self._stop_spoofdpi()
        settings = self.settings.get()
        self._terminate_listeners(int(settings.spoofdpi_port))
        executable = self.spoofdpi.executable_path()
        log_path = self.storage.paths.logs_dir / "spoofdpi.log"
        command = [
            str(executable),
            "--listen-addr",
            f"{settings.spoofdpi_host}:{settings.spoofdpi_port}",
            *shlex.split(settings.spoofdpi_args),
        ]
        process = self._spawn_component(command, log_path)
        with self._lock:
            self._processes["spoofdpi"] = process
        started = False
        for _ in range(50):
            if process.poll() is not None:
                break
            if self._is_port_open(settings.spoofdpi_host, int(settings.spoofdpi_port)):
                started = True
                break
            time.sleep(0.15)
        if not started:
            state = ComponentState("spoofdpi", status="error", pid=process.pid, last_error="SpoofDPI health check failed.")
            with self._lock:
                self._states["spoofdpi"] = state
            return state
        state = ComponentState("spoofdpi", status="running", pid=process.pid)
        with self._lock:
            self._states["spoofdpi"] = state
        self.logging.log("info", "SpoofDPI started", command=command)
        return state

    def _stop_spoofdpi(self) -> ComponentState:
        backend_state = self._state_for("backend")
        if backend_state.status in {"running", "starting"}:
            self._stop_backend_runtime(stop_engine=False)
        settings = self.settings.get()
        with self._lock:
            process = self._processes.pop("spoofdpi", None)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
        self._terminate_listeners(int(settings.spoofdpi_port))
        state = ComponentState("spoofdpi", status="stopped")
        with self._lock:
            self._states["spoofdpi"] = state
        self.logging.log("info", "SpoofDPI stopped")
        return state

    def _start_zapret_macos(self) -> ComponentState:
        running_state = self._state_for("zapret")
        if running_state.status == "running":
            return running_state

        self._stop_zapret_macos()
        settings = self.settings.get()
        self._terminate_listeners(int(settings.zapret_port))
        executable = self.zapret_macos.executable_path()
        log_path = self.storage.paths.logs_dir / "zapret-macos.log"
        command = [
            str(executable),
            "--ip",
            settings.zapret_host,
            "--port",
            str(settings.zapret_port),
            *shlex.split(settings.zapret_args),
        ]
        process = self._spawn_component(command, log_path)
        with self._lock:
            self._processes["zapret"] = process
            runtime = self._runtime_state.setdefault("zapret", ManagedRuntimeState(process_name="ciadpi"))
            runtime.launch_token += 1
            runtime.tracked_pid = process.pid
            runtime.detached_pid = None
            runtime.last_successful_health = False
            runtime.last_command = command[:]
        started = False
        for _ in range(50):
            if process.poll() is not None:
                break
            if self._is_port_open(settings.zapret_host, int(settings.zapret_port)):
                started = True
                break
            time.sleep(0.15)
        if not started:
            state = ComponentState("zapret", status="error", pid=process.pid, last_error="ByeDPI health check failed.")
            with self._lock:
                self._states["zapret"] = state
                runtime = self._runtime_state.setdefault("zapret", ManagedRuntimeState(process_name="ciadpi"))
                runtime.last_successful_health = False
            return state
        detached_pid = self._find_listener_pid(int(settings.zapret_port), process_name="ciadpi")
        state = ComponentState("zapret", status="running", pid=process.pid)
        with self._lock:
            self._states["zapret"] = state
            runtime = self._runtime_state.setdefault("zapret", ManagedRuntimeState(process_name="ciadpi"))
            runtime.last_successful_health = True
            runtime.detached_pid = detached_pid if detached_pid and detached_pid != process.pid else None
        self.logging.log("info", "ByeDPI started", command=command)
        return state

    def _stop_zapret_macos(self) -> ComponentState:
        backend_state = self._state_for("backend")
        if backend_state.status in {"running", "starting"}:
            self._stop_backend_runtime(stop_engine=False)
        settings = self.settings.get()
        runtime = self._runtime_state.setdefault("zapret", ManagedRuntimeState(process_name="ciadpi"))
        with self._lock:
            process = self._processes.pop("zapret", None)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
        self._terminate_matching_listener(int(settings.zapret_port), process_name="ciadpi")
        state = ComponentState("zapret", status="stopped")
        with self._lock:
            self._states["zapret"] = state
            runtime.tracked_pid = None
            runtime.detached_pid = None
            runtime.last_successful_health = False
            runtime.last_command = []
        self.logging.log("info", "ByeDPI stopped")
        return state

    def _start_tg_ws_proxy(self) -> ComponentState:
        self._stop_tg_ws_proxy()
        settings = self.settings.get()
        secret, settings = self._ensure_tg_secret(settings)
        log_path = self.storage.paths.logs_dir / "tg-ws-proxy.log"
        command = self._component_command(
            "tg-ws-proxy",
            "--host",
            settings.tg_proxy_host,
            "--port",
            str(settings.tg_proxy_port),
        )
        if secret:
            command.extend(["--secret", secret])
        process = self._spawn_component(command, log_path)
        with self._lock:
            self._processes["tg-ws-proxy"] = process
        started = False
        for _ in range(40):
            if process.poll() is not None:
                break
            if self._is_port_open(settings.tg_proxy_host, int(settings.tg_proxy_port)):
                started = True
                break
            time.sleep(0.15)
        if not started:
            state = ComponentState("tg-ws-proxy", status="error", pid=process.pid, last_error="TG WS Proxy health check failed.")
            with self._lock:
                self._states["tg-ws-proxy"] = state
            return state
        state = ComponentState("tg-ws-proxy", status="running", pid=process.pid)
        with self._lock:
            self._states["tg-ws-proxy"] = state
        self.logging.log("info", "TG WS Proxy started", command=command)
        self.auto_prompt_telegram_proxy_link_on_start()
        return state

    def _stop_tg_ws_proxy(self) -> ComponentState:
        with self._lock:
            process = self._processes.pop("tg-ws-proxy", None)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
        state = ComponentState("tg-ws-proxy", status="stopped")
        with self._lock:
            self._states["tg-ws-proxy"] = state
        self.logging.log("info", "TG WS Proxy stopped")
        return state

    def _state_for(self, component_id: str) -> ComponentState:
        if component_id == "traffic-engine":
            selected = self.settings.get().traffic_engine_id
            selected_state = self._state_for(selected)
            return ComponentState(
                component_id="traffic-engine",
                status=selected_state.status,
                pid=selected_state.pid,
                last_error=selected_state.last_error,
            )
        if component_id == "backend" and not self._traffic_engine_required():
            return ComponentState(component_id="backend", status="stopped")
        with self._lock:
            process = self._processes.get(component_id)
            current = self._states.get(component_id)
            state = ComponentState(
                component_id=component_id,
                status=current.status if current else "stopped",
                pid=current.pid if current else None,
                last_error=current.last_error if current else "",
            )
            if state.status in {"starting", "stopping"}:
                if process and process.poll() is None:
                    state.pid = process.pid
                return state
            health_running = self._component_health_running(component_id)
            if process and process.poll() is None:
                state.status = "running"
                state.pid = process.pid
            elif component_id == "zapret" and health_running and self._is_matching_detached_runtime("zapret"):
                state.status = "running"
                runtime = self._runtime_state.get("zapret")
                if runtime and runtime.detached_pid:
                    state.pid = runtime.detached_pid
            elif state.status == "running":
                state.status = "stopped"
                state.pid = None
            return state

    def _component_health_running(self, component_id: str) -> bool:
        try:
            settings = self.settings.get()
            if component_id == "spoofdpi":
                return self._is_port_open(settings.spoofdpi_host, int(settings.spoofdpi_port))
            if component_id == "zapret":
                return self._is_port_open(settings.zapret_host, int(settings.zapret_port))
            if component_id == "backend" and self._traffic_engine_required():
                profile = self.merge.current_profile()
                return self._is_port_open(profile.listen_host, profile.health_port)
        except Exception:
            return False
        return False

    def _is_matching_detached_runtime(self, component_id: str) -> bool:
        if component_id != "zapret":
            return False
        settings = self.settings.get()
        runtime = self._runtime_state.get("zapret")
        if runtime is None:
            return False
        if runtime.launch_token <= 0 or not runtime.last_command:
            runtime.detached_pid = None
            runtime.last_successful_health = False
            return False
        pid = self._find_listener_pid(int(settings.zapret_port), process_name=runtime.process_name or "ciadpi")
        if pid is None:
            runtime.detached_pid = None
            runtime.last_successful_health = False
            return False
        runtime.detached_pid = pid
        runtime.last_successful_health = True
        return True

    def _ensure_tg_secret(self, settings: AppSettings) -> tuple[str, AppSettings]:
        secret = AppSettings.normalize_tg_secret(settings.tg_proxy_secret)
        if secret:
            return secret, settings
        secret = secrets.token_hex(16)
        settings = self.settings.update(tg_proxy_secret=secret)
        return secret, settings

    def _telegram_proxy_link(self, settings: AppSettings, secret: str) -> str:
        return f"tg://proxy?server={settings.tg_proxy_host}&port={settings.tg_proxy_port}&secret=dd{secret}"

    def _open_telegram_proxy_link(self, settings: AppSettings, secret: str) -> bool:
        link = self._telegram_proxy_link(settings, secret)
        commands = (
            ["open", "-a", "Telegram", link],
            ["open", link],
        )
        for command in commands:
            try:
                result = subprocess.run(command, check=False, capture_output=True, text=True)
            except OSError as exc:
                self.logging.log("warning", "Failed to invoke macOS open for Telegram proxy link", command=command, error=str(exc))
                continue
            if result.returncode == 0:
                self.logging.log("info", "Opened Telegram proxy link", command=command)
                return True
            self.logging.log(
                "warning",
                "macOS open could not handle Telegram proxy link",
                command=command,
                returncode=result.returncode,
                stderr=result.stderr.strip(),
            )
        return False

    def _mark_tg_secret_prompted(self, secret: str) -> None:
        normalized = AppSettings.normalize_tg_secret(secret)
        settings = self.settings.get()
        if AppSettings.normalize_tg_secret(settings.tg_last_prompted_secret) != normalized:
            self.settings.update(tg_last_prompted_secret=normalized)

    def _submit_component_task(
        self,
        component_id: str,
        transitional_status: str,
        operation: Callable[[], ComponentState],
    ) -> ComponentState:
        version = self._begin_operation(component_id, transitional_status)
        future = self._dispatcher.submit(operation)
        future.add_done_callback(
            lambda done, cid=component_id, op_version=version: self._complete_component_task(cid, op_version, done)
        )
        return self._state_for(component_id)

    def _begin_operation(self, component_id: str, transitional_status: str) -> int:
        with self._lock:
            version = self._operation_versions.get(component_id, 0) + 1
            self._operation_versions[component_id] = version
            current = self._states.get(component_id, ComponentState(component_id=component_id))
            self._states[component_id] = ComponentState(
                component_id=component_id,
                status=transitional_status,
                pid=current.pid,
                last_error="",
            )
            return version

    def _complete_component_task(self, component_id: str, version: int, future: Future[ComponentState]) -> None:
        try:
            result = future.result()
        except Exception as exc:
            self.logging.log("error", "Component operation failed", component_id=component_id, error=str(exc))
            result = ComponentState(component_id=component_id, status="error", last_error=str(exc))
        with self._lock:
            if self._operation_versions.get(component_id) != version:
                return
            self._states[component_id] = ComponentState(
                component_id=result.component_id,
                status=result.status,
                pid=result.pid,
                last_error=result.last_error,
            )

    def _is_port_open(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    def _terminate_listeners(self, port: int) -> None:
        try:
            result = subprocess.run(
                ["lsof", "-nP", "-iTCP:%d" % port, "-sTCP:LISTEN", "-t"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:
            self.logging.log("warning", "Failed to inspect listener processes", port=port, error=str(exc))
            return
        pids = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                pids.append(int(line))
            except ValueError:
                continue
        tracked = {
            process.pid
            for process in self._processes.values()
            if process is not None and process.poll() is None and process.pid is not None
        }
        for pid in pids:
            if pid <= 0 or pid in tracked or pid == os.getpid():
                continue
            try:
                os.kill(pid, signal.SIGTERM)
                self.logging.log("info", "Stopped stale listener occupying managed port", port=port, pid=pid)
            except ProcessLookupError:
                continue
            except Exception as exc:
                self.logging.log("warning", "Failed to stop stale listener", port=port, pid=pid, error=str(exc))

    def _find_listener_pid(self, port: int, *, process_name: str | None = None) -> int | None:
        try:
            result = subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fpc"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return None
        current_pid: int | None = None
        current_command = ""
        matches: list[int] = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            tag, value = line[0], line[1:]
            if tag == "p":
                try:
                    current_pid = int(value)
                except ValueError:
                    current_pid = None
                current_command = ""
            elif tag == "c":
                current_command = value.strip()
                if current_pid and (process_name is None or current_command == process_name):
                    matches.append(current_pid)
        return matches[0] if matches else None

    def _terminate_matching_listener(self, port: int, *, process_name: str) -> None:
        pid = self._find_listener_pid(port, process_name=process_name)
        if not pid or pid == os.getpid():
            return
        try:
            os.kill(pid, signal.SIGTERM)
            self.logging.log("info", "Stopped matching managed listener", port=port, pid=pid, process_name=process_name)
        except ProcessLookupError:
            return
        except Exception as exc:
            self.logging.log("warning", "Failed to stop matching managed listener", port=port, pid=pid, process_name=process_name, error=str(exc))

    def _component_command(self, component_id: str, *args: str) -> list[str]:
        if getattr(sys, "frozen", False):
            return [str(Path(sys.executable).resolve()), f"--run-{component_id}", *args]
        module_name = {
            "backend": "zapret_hub_mac.runtime.mac_proxy_engine",
            "tg-ws-proxy": "zapret_hub_mac.runtime.tg_ws_proxy_runner",
        }[component_id]
        return [sys.executable, "-m", module_name, *args]

    def _traffic_engine_required(self) -> bool:
        return "traffic-engine" in self.settings.get().enabled_component_ids

    def any_bypass_running(self) -> bool:
        return any(
            state.status in {"running", "starting"}
            for state in self.list_states()
            if state.component_id in {"backend", "tg-ws-proxy", "traffic-engine"}
        )

    def set_traffic_engine(self, engine_id: str) -> None:
        self.set_traffic_engine_async(engine_id).result()

    def set_traffic_engine_async(self, engine_id: str) -> Future[None]:
        return self._dispatcher.submit(self._set_traffic_engine_impl, engine_id)

    def _set_traffic_engine_impl(self, engine_id: str) -> None:
        if engine_id not in {"spoofdpi", "zapret"}:
            raise ValueError(engine_id)
        current = self.settings.get().traffic_engine_id
        if current == engine_id:
            return
        backend_running = self._state_for("backend").status in {"running", "starting"}
        engine_running = self._state_for("traffic-engine").status in {"running", "starting"}
        if backend_running:
            self._stop_backend()
        if engine_running:
            self._stop_selected_traffic_engine()
        self.settings.update(traffic_engine_id=engine_id)
        self.merge.build_runtime_state()
        if engine_running:
            self._start_selected_traffic_engine()
        if backend_running:
            self._start_backend()

    def _start_selected_traffic_engine(self) -> ComponentState:
        self._stop_non_selected_traffic_engine()
        engine_id = self.settings.get().traffic_engine_id
        if engine_id == "zapret":
            return self._start_zapret_macos()
        return self._start_spoofdpi()

    def _stop_selected_traffic_engine(self) -> ComponentState:
        state = self._stop_selected_traffic_engine_runtime()
        return ComponentState(component_id="traffic-engine", status=state.status, pid=state.pid, last_error=state.last_error)

    def _stop_selected_traffic_engine_runtime(self) -> ComponentState:
        engine_id = self.settings.get().traffic_engine_id
        if engine_id == "zapret":
            state = self._stop_zapret_macos()
        else:
            state = self._stop_spoofdpi()
        self._stop_non_selected_traffic_engine()
        return state

    def _stop_non_selected_traffic_engine(self) -> None:
        engine_id = self.settings.get().traffic_engine_id
        if engine_id == "zapret":
            self._stop_spoofdpi()
            return
        self._stop_zapret_macos()

    def _spawn_component(self, command: list[str], log_path: Path) -> subprocess.Popen[bytes]:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        with log_path.open("ab") as log_file:
            return subprocess.Popen(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=False,
                env=env,
            )
