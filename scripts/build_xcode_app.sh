#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DERIVED="$ROOT/build/xcode"

rm -rf "$DERIVED"
xcodebuild \
  -project "$ROOT/ZapretHubMac.xcodeproj" \
  -scheme "Zapret Hub Mac" \
  -configuration Release \
  -derivedDataPath "$DERIVED" \
  CODE_SIGN_IDENTITY="-" \
  CODE_SIGN_STYLE=Manual \
  build

APP_PATH="$DERIVED/Build/Products/Release/Zapret Hub Mac.app"
"$ROOT/scripts/apply_xcode_icon_assets.sh" "$APP_PATH"
DIST_APP_PATH="$ROOT/dist/Zapret Hub.app"
rm -rf "$DIST_APP_PATH" "$ROOT/dist/Zapret Hub Mac.app" "$ROOT/dist/Zapret Hub" "$ROOT/dist/zapret_hub_mac"
mkdir -p "$ROOT/dist"
rsync -a "$APP_PATH/" "$DIST_APP_PATH/"
plutil -replace CFBundleName -string "Zapret Hub" "$DIST_APP_PATH/Contents/Info.plist" || true
plutil -replace CFBundleDisplayName -string "Zapret Hub" "$DIST_APP_PATH/Contents/Info.plist" || \
  plutil -insert CFBundleDisplayName -string "Zapret Hub" "$DIST_APP_PATH/Contents/Info.plist" || true
codesign --force --deep --sign - "$DIST_APP_PATH"
echo "$APP_PATH"
