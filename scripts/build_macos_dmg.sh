#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Tributary Area Tool.app"
APP_PATH="$ROOT_DIR/dist/$APP_NAME"
DMG_PATH="$ROOT_DIR/dist/TributaryAreaTool-macOS.dmg"
VOLUME_NAME="Tributary Area Tool"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app bundle: $APP_PATH"
  echo "Build it first with: .venv/bin/python scripts/build_desktop.py"
  exit 1
fi

STAGING_DIR="$(mktemp -d "$ROOT_DIR/build/macos-dmg.XXXXXX")"
cleanup() {
  rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

mkdir -p "$STAGING_DIR"
cp -R "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

rm -f "$DMG_PATH"
hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "Created DMG: $DMG_PATH"
