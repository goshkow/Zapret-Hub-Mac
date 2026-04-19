#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
BUILD="$ROOT/build"
APP_NAME="Zapret Hub.app"
APP_PATH="$DIST/$APP_NAME"
APP_ICON="$APP_PATH/Contents/Resources/AppIcon.icns"
VOL_NAME="Zapret Hub 1.0.0b"
DMG_NAME="Zapret_Hub_1.0.0b.dmg"
DMG_FINAL="$DIST/$DMG_NAME"
STAGE_DIR="$BUILD/dmg_stage"
DMG_RW="$BUILD/${DMG_NAME:r}_rw.dmg"
MOUNT_POINT="$BUILD/dmg_mount"
INSTRUCTION_NAME="Инструкция.txt"

"$ROOT/scripts/build_xcode_app.sh"

rm -rf "$STAGE_DIR" "$DMG_FINAL" "$DMG_RW" "$MOUNT_POINT"
mkdir -p "$STAGE_DIR"

cat > "$STAGE_DIR/$INSTRUCTION_NAME" <<'EOF'
Установка: перетащите приложение Zapret Hub.app в папку Applications.

Если macOS выдаёт предупреждение, что приложение повреждено или не может быть открыто, откройте Терминал и выполните команду для снятия ограничений безопасности:
sudo xattr -r -d com.apple.quarantine /Applications/Zapret Hub.app
EOF

cp -R "$APP_PATH" "$STAGE_DIR/$APP_NAME"
ln -s /Applications "$STAGE_DIR/Applications"

hdiutil create \
  -quiet \
  -volname "$VOL_NAME" \
  -srcfolder "$STAGE_DIR" \
  -fs HFS+ \
  -format UDRW \
  "$DMG_RW"

mkdir -p "$MOUNT_POINT"
hdiutil attach \
  -quiet \
  -readwrite \
  -mountpoint "$MOUNT_POINT" \
  "$DMG_RW"

cp "$APP_ICON" "$MOUNT_POINT/.VolumeIcon.icns"
SetFile -a C "$MOUNT_POINT"
sync
hdiutil detach -quiet "$MOUNT_POINT"

hdiutil convert \
  -quiet \
  "$DMG_RW" \
  -format UDZO \
  -imagekey zlib-level=9 \
  -o "$DMG_FINAL"

python3 - <<EOF
from Cocoa import NSImage, NSWorkspace

icon_path = r"$APP_ICON"
target_path = r"$DMG_FINAL"
image = NSImage.alloc().initWithContentsOfFile_(icon_path)
if image:
    NSWorkspace.sharedWorkspace().setIcon_forFile_options_(image, target_path, 0)
EOF

echo "$DMG_FINAL"
