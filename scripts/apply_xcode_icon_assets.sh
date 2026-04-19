#!/bin/zsh
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/App.app" >&2
  exit 1
fi

APP_PATH="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_PATH="$APP_PATH/Contents/Info.plist"
RESOURCES_DIR="$APP_PATH/Contents/Resources"
ICON_STAGE_DIR="$ROOT/build/xcode_icon_stage"
ASSET_CATALOG="$ROOT/xcode/Assets.xcassets"
FALLBACK_ASSETS_DIR="$ROOT/build/macos_icon_assets/out"

mkdir -p "$RESOURCES_DIR"

if [[ ! -f "$RESOURCES_DIR/Assets.car" ]]; then
  rm -rf "$ICON_STAGE_DIR"
  mkdir -p "$ICON_STAGE_DIR"
  /usr/bin/xcrun actool "$ASSET_CATALOG" \
    --compile "$ICON_STAGE_DIR" \
    --output-format human-readable-text \
    --notices \
    --warnings \
    --output-partial-info-plist "$ICON_STAGE_DIR/Info.plist" \
    --app-icon AppIcon \
    --target-device mac \
    --platform macosx \
    --minimum-deployment-target 15.0 \
    --development-region en \
    --bundle-identifier io.github.goshkow.zapret-hub-mac

  if [[ -f "$ICON_STAGE_DIR/Assets.car" ]]; then
    cp "$ICON_STAGE_DIR/Assets.car" "$RESOURCES_DIR/Assets.car"
  fi
  if [[ -f "$ICON_STAGE_DIR/AppIcon.icns" ]]; then
    cp "$ICON_STAGE_DIR/AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"
  fi
fi

if [[ ! -f "$RESOURCES_DIR/Assets.car" && -f "$FALLBACK_ASSETS_DIR/Assets.car" ]]; then
  cp "$FALLBACK_ASSETS_DIR/Assets.car" "$RESOURCES_DIR/Assets.car"
fi

if [[ ! -f "$RESOURCES_DIR/AppIcon.icns" && -f "$FALLBACK_ASSETS_DIR/AppIcon.icns" ]]; then
  cp "$FALLBACK_ASSETS_DIR/AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"
fi

/usr/libexec/PlistBuddy -c "Set :CFBundleIconName AppIcon" "$PLIST_PATH" || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleIconName string AppIcon" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon" "$PLIST_PATH" || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string AppIcon" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Set :CFBundleExecutable zapret_hub_mac" "$PLIST_PATH" || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleExecutable string zapret_hub_mac" "$PLIST_PATH"

codesign --force --deep --sign - "$APP_PATH"
