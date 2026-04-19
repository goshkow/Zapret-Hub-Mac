# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPEC).resolve().parent.parent
generated_icon = project_root / "build" / "macos_icon_assets" / "out" / "AppIcon.icns"
bundle_icon = generated_icon if generated_icon.exists() else project_root / "resources" / "ui_assets" / "icons" / "app.icns"

a = Analysis(
    [str(project_root / "src" / "zapret_hub_mac" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(project_root / "resources"), "resources"),
    ],
    hiddenimports=[
        "objc",
        "Cocoa",
        "AppKit",
        "Foundation",
        "zapret_hub_mac.runtime.mac_proxy_engine",
        "zapret_hub_mac.runtime.tg_ws_proxy_runner",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="zapret_hub_mac",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="Zapret Hub",
)
app = BUNDLE(
    coll,
    name="Zapret Hub.app",
    icon=str(bundle_icon),
    bundle_identifier="io.github.goshkow.zapret-hub-mac",
    info_plist={
        "CFBundleIconName": "AppIcon",
        "CFBundleIconFile": "AppIcon",
    },
)
