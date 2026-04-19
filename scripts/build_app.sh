#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ICON_BUILD_DIR="$ROOT/build/macos_icon_assets"
ASSET_INPUT_DIR="$ICON_BUILD_DIR/AppAssets.xcassets"
ASSET_OUTPUT_DIR="$ICON_BUILD_DIR/out"
APP_BUNDLE="$ROOT/dist/Zapret Hub.app"
APP_RESOURCES="$APP_BUNDLE/Contents/Resources"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/zapret_hub_mac"
LAUNCH_LOG="$ICON_BUILD_DIR/launch_check.log"
PYTHON_BIN="$ROOT/.venv/bin/python"
export PYINSTALLER_CONFIG_DIR="$ROOT/build/pyinstaller-config"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

mkdir -p "$ICON_BUILD_DIR"
mkdir -p "$PYINSTALLER_CONFIG_DIR"
"$PYTHON_BIN" "$ROOT/scripts/build_macos_icons.py"

rm -rf "$ASSET_OUTPUT_DIR"
mkdir -p "$ASSET_OUTPUT_DIR"
xcrun actool \
  --compile "$ASSET_OUTPUT_DIR" \
  --platform macosx \
  --target-device mac \
  --minimum-deployment-target 15.0 \
  --app-icon AppIcon \
  --output-partial-info-plist "$ICON_BUILD_DIR/Info.plist" \
  "$ASSET_INPUT_DIR"

"$PYTHON_BIN" -m PyInstaller -y packaging/zapret_hub_mac.spec

cp "$ASSET_OUTPUT_DIR/Assets.car" "$APP_RESOURCES/Assets.car"
cp "$ASSET_OUTPUT_DIR/AppIcon.icns" "$APP_RESOURCES/AppIcon.icns"

/usr/libexec/PlistBuddy -c "Set :CFBundleIconName AppIcon" "$APP_BUNDLE/Contents/Info.plist" || /usr/libexec/PlistBuddy -c "Add :CFBundleIconName string AppIcon" "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon" "$APP_BUNDLE/Contents/Info.plist" || /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string AppIcon" "$APP_BUNDLE/Contents/Info.plist"

codesign --force --deep --sign - "$APP_BUNDLE"

rm -f "$LAUNCH_LOG"
"$APP_BINARY" >"$LAUNCH_LOG" 2>&1 &
APP_PID=$!
sleep 2
if kill -0 "$APP_PID" 2>/dev/null; then
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
fi

if rg -n "Traceback|Failed to execute script|BadPrototypeError|PYI-[0-9]+:ERROR" "$LAUNCH_LOG" >/dev/null; then
  cat "$LAUNCH_LOG"
  exit 1
fi

rm -rf "$ROOT/dist/Zapret Hub Mac.app" "$ROOT/dist/Zapret Hub" "$ROOT/dist/zapret_hub_mac"
