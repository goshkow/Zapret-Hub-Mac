from __future__ import annotations

import sys
from pathlib import Path

from zapret_hub_mac import __version__
from zapret_hub_mac.bootstrap import bootstrap_application
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from zapret_hub_mac.services.updates import ReleaseInfo, UpdateService

try:
    import objc
    from AppKit import NSApp, NSApplicationActivationPolicyAccessory, NSApplicationActivationPolicyProhibited, NSApplicationActivationPolicyRegular, NSImage, NSMakeSize, NSMenu, NSMenuItem, NSSquareStatusItemLength, NSStatusBar
    from Foundation import NSObject

    HAS_NATIVE_STATUS_ITEM = True
except Exception:
    objc = None
    NSApp = None
    NSApplicationActivationPolicyAccessory = None
    NSApplicationActivationPolicyProhibited = None
    NSApplicationActivationPolicyRegular = None
    NSImage = None
    NSMakeSize = None
    NSMenu = None
    NSMenuItem = None
    NSSquareStatusItemLength = None
    NSStatusBar = None
    NSObject = object
    HAS_NATIVE_STATUS_ITEM = False


if HAS_NATIVE_STATUS_ITEM:
    class NativeStatusItemController(NSObject):
        def initWithOpen_quit_languageProvider_iconPath_(self, on_open, on_quit, language_provider, icon_path):
            self = objc.super(NativeStatusItemController, self).init()
            if self is None:
                return None
            self._on_open = on_open
            self._on_quit = on_quit
            self._language_provider = language_provider
            self._icon_path = str(icon_path)
            self._status_item = None
            self._status_image = None
            self._menu = None
            self._open_item = None
            self._quit_item = None
            self.refresh_labels()
            return self

        @objc.python_method
        def _t(self, ru: str, en: str) -> str:
            return ru if self._language_provider() == "ru" else en

        @objc.python_method
        def refresh_labels(self) -> None:
            if self._open_item is not None:
                self._open_item.setTitle_(self._t("Открыть приложение", "Open App"))
            if self._quit_item is not None:
                self._quit_item.setTitle_(self._t("Закрыть полностью", "Quit Completely"))

        @objc.python_method
        def create(self) -> None:
            if self._status_item is not None:
                return
            self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSSquareStatusItemLength)
            self._menu = NSMenu.alloc().init()
            self._open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("", "openAction:", "")
            self._open_item.setTarget_(self)
            self._quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("", "quitAction:", "")
            self._quit_item.setTarget_(self)
            self._menu.addItem_(self._open_item)
            self._menu.addItem_(NSMenuItem.separatorItem())
            self._menu.addItem_(self._quit_item)
            self._status_item.setMenu_(self._menu)
            button = self._status_item.button()
            if button is not None:
                image = NSImage.alloc().initWithContentsOfFile_(self._icon_path)
                if image is not None:
                    image.setSize_(NSMakeSize(16, 16))
                    image.setTemplate_(True)
                    self._status_image = image
                    button.setImage_(image)
                    button.setTitle_("")
                else:
                    button.setTitle_("H")
                button.setToolTip_("Zapret Hub")
            try:
                self._status_item.setVisible_(True)
            except Exception:
                pass
            self.refresh_labels()

        @objc.python_method
        def show(self) -> None:
            self.create()

        @objc.python_method
        def hide(self) -> None:
            try:
                self.destroy()
            except Exception:
                pass

        @objc.python_method
        def destroy(self) -> None:
            if self._status_item is None:
                return
            NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
            self._status_item = None
            self._status_image = None
            self._menu = None
            self._open_item = None
            self._quit_item = None

        def openAction_(self, _sender) -> None:
            QTimer.singleShot(0, self._on_open)

        def quitAction_(self, _sender) -> None:
            QTimer.singleShot(0, self._on_quit)
else:
    class NativeStatusItemController:
        def __init__(self, *args, **kwargs):
            self._on_open = None
            self._on_quit = None

        @classmethod
        def alloc(cls):
            return cls()

        def initWithOpen_quit_languageProvider_iconPath_(self, on_open, on_quit, _language_provider, _icon_path):
            self._on_open = on_open
            self._on_quit = on_quit
            return self

        def refresh_labels(self) -> None:
            return None

        def create(self) -> None:
            return None

        def show(self) -> None:
            return None

        def hide(self) -> None:
            return None

        def destroy(self) -> None:
            return None


def _run_embedded_runtime(flag: str) -> int | None:
    runtime_entrypoints = {
        "--run-backend": "zapret_hub_mac.runtime.mac_proxy_engine",
        "--run-tg-ws-proxy": "zapret_hub_mac.runtime.tg_ws_proxy_runner",
    }
    module_name = runtime_entrypoints.get(flag)
    if module_name is None:
        return None

    if module_name == "zapret_hub_mac.runtime.mac_proxy_engine":
        from zapret_hub_mac.runtime.mac_proxy_engine import main as runtime_main
    else:
        from zapret_hub_mac.runtime.tg_ws_proxy_runner import main as runtime_main

    previous_argv = sys.argv
    try:
        sys.argv = [previous_argv[0], *previous_argv[2:]]
        return int(runtime_main() or 0)
    finally:
        sys.argv = previous_argv


def run() -> int:
    runtime_exit_code = _run_embedded_runtime(sys.argv[1]) if len(sys.argv) > 1 else None
    if runtime_exit_code is not None:
        return runtime_exit_code

    from zapret_hub_mac.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Zapret Hub")
    app.setQuitOnLastWindowClosed(False)
    context = bootstrap_application()
    updates = UpdateService(context.logging, current_version=__version__, owner="goshkow", repo="Zapret-Hub-Mac")
    bundle_icon = None
    if getattr(sys, "frozen", False):
        bundle_icon = Path(sys.executable).resolve().parent.parent / "Resources" / "AppIcon.icns"
    icon_path = bundle_icon if bundle_icon and bundle_icon.exists() else context.paths.resources_dir / "ui_assets" / "icons" / "app.icns"
    if not icon_path.exists():
        icon_path = context.paths.resources_dir / "ui_assets" / "icons" / "app.png"
    app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
    window = MainWindow(context)
    if sys.platform != "darwin" and not app_icon.isNull():
        app.setWindowIcon(app_icon)
    if sys.platform != "darwin" and not app_icon.isNull():
        window.setWindowIcon(app_icon)
    shutdown_started = False
    updates_timer = QTimer()
    updates_timer.setInterval(5 * 60 * 60 * 1000)

    def _show_update_notice(release: ReleaseInfo) -> None:
        shown_tag = context.settings.get().last_update_prompt_tag.strip().lower()
        release_tag = release.tag_name.strip().lower()
        if shown_tag == release_tag:
            return
        if not window.isVisible():
            window.show_from_tray()
        window.prompt_update_available(release.tag_name, release.name, release.html_url)
        context.settings.update(last_update_prompt_tag=release.tag_name)

    def _check_updates() -> None:
        if not context.settings.get().check_updates_on_start:
            return
        future = updates.check_for_updates_async()

        def _on_done(done) -> None:
            try:
                release = done.result()
            except Exception as exc:
                context.logging.log("warning", "Update check failed", error=str(exc))
                return
            if release is None:
                return
            QTimer.singleShot(0, lambda rel=release: _show_update_notice(rel))

        future.add_done_callback(_on_done)

    def activate_regular() -> None:
        if HAS_NATIVE_STATUS_ITEM and NSApp is not None:
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            NSApp.activateIgnoringOtherApps_(True)

    def activate_accessory() -> None:
        if HAS_NATIVE_STATUS_ITEM and NSApp is not None:
            policy = NSApplicationActivationPolicyAccessory
            if policy is None:
                policy = NSApplicationActivationPolicyProhibited
            NSApp.setActivationPolicy_(policy)

    def shutdown_runtime() -> None:
        nonlocal shutdown_started
        if shutdown_started:
            return
        shutdown_started = True
        updates_timer.stop()
        updates.shutdown()
        try:
            context.processes.stop_all_async()
        except Exception:
            pass

    def full_quit() -> None:
        shutdown_runtime()
        try:
            if getattr(app, "_native_status_item", None) is not None:
                app._native_status_item.destroy()
        except Exception:
            pass
        window._force_quit = True
        app.quit()

    window.set_activation_policy_handlers(activate_regular, activate_accessory)
    app.aboutToQuit.connect(shutdown_runtime)

    def init_tray():
        if not HAS_NATIVE_STATUS_ITEM or NSStatusBar is None:
            return None
        existing = getattr(app, "_native_status_item", None)
        if existing is not None:
            return existing
        tray = NativeStatusItemController.alloc().initWithOpen_quit_languageProvider_iconPath_(
            window.show_from_tray,
            full_quit,
            lambda: context.settings.get().language,
            context.paths.resources_dir / "ui_assets" / "icons" / "tray_h_template.png",
        )
        app._native_status_item = tray
        window.set_tray_icon(tray)
        window.set_tray_menu_updater(tray.refresh_labels)
        return tray

    window.set_tray_initializer(init_tray)

    launch_hidden = "--launch-hidden" in sys.argv and context.settings.get().launch_hidden
    if launch_hidden and window.hide_to_tray():
        activate_accessory()
    else:
        window.show()
        activate_regular()
        QTimer.singleShot(0, window.raise_)
        QTimer.singleShot(0, window.activateWindow)
    QTimer.singleShot(1200, _check_updates)
    updates_timer.timeout.connect(_check_updates)
    updates_timer.start()
    if context.settings.get().auto_run_components:
        context.processes.start_enabled_components()
    return app.exec()
