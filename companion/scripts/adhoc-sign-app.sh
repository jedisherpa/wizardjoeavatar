#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
COMPANION_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
APP_PATH=${WIZARD_COMPANION_APP_PATH:-"$COMPANION_DIR/src-tauri/target/release/bundle/macos/Wizard Joe Companion.app"}

if [ ! -d "$APP_PATH/Contents" ]; then
  printf 'Companion bundle not found: %s\n' "$APP_PATH" >&2
  exit 1
fi

# Local ad-hoc signing creates the resource envelope macOS requires when the
# unsigned development artifact is launched from Applications. Public release
# signing and notarization remain separate, credentialed release steps.
if [ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PATH/Contents/Info.plist")" != "com.jedisherpa.wizardjoecompanion" ]; then
  printf 'Refusing to sign an unexpected application bundle: %s\n' "$APP_PATH" >&2
  exit 1
fi

STAGE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/wizard-joe-companion-sign.XXXXXX")
trap 'rm -rf "$STAGE_DIR"' EXIT HUP INT TERM
STAGED_APP="$STAGE_DIR/Wizard Joe Companion.app"

# The repository may live in a File Provider directory that immediately adds
# Finder metadata rejected by codesign. Sign a metadata-free staging copy, then
# replace only the known generated Companion artifact with that verified copy.
ditto --norsrc --noextattr "$APP_PATH" "$STAGED_APP"
xattr -cr "$STAGED_APP"
codesign --force --deep --sign - --timestamp=none "$STAGED_APP"
codesign --verify --deep --strict --verbose=2 "$STAGED_APP"

rm -rf "$APP_PATH"
ditto --norsrc --noextattr "$STAGED_APP" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

printf 'Ad-hoc local bundle verified: %s\n' "$APP_PATH"
