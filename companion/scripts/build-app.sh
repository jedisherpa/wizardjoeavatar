#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
COMPANION_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
TARGET_DIR=${WIZARD_COMPANION_TARGET_DIR:-"$HOME/Library/Caches/Wizard Joe Companion/build-target"}
TAURI="$COMPANION_DIR/node_modules/.bin/tauri"
APP_PATH="$TARGET_DIR/release/bundle/macos/Wizard Joe Companion.app"

if [ ! -x "$TAURI" ]; then
  printf 'Tauri CLI is unavailable; run npm ci in %s\n' "$COMPANION_DIR" >&2
  exit 1
fi

# File Provider workspaces may reattach Finder metadata after signing. Cargo's
# generated bundle therefore lives in a stable local cache unless explicitly
# overridden by the release operator.
mkdir -p "$TARGET_DIR"
CARGO_TARGET_DIR="$TARGET_DIR" "$TAURI" build --bundles app
WIZARD_COMPANION_APP_PATH="$APP_PATH" "$SCRIPT_DIR/adhoc-sign-app.sh"

printf 'Companion app ready: %s\n' "$APP_PATH"
