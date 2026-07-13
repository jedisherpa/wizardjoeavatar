#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/deploy/macos/com.jedisherpa.wizardjoeavatar.plist"
TARGET="$HOME/Library/LaunchAgents/com.jedisherpa.wizardjoeavatar.plist"
DOMAIN="gui/$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
sed -e "s|__ROOT__|$ROOT|g" -e "s|__HOME__|$HOME|g" "$SOURCE" > "$TARGET"
plutil -lint "$TARGET"
launchctl bootout "$DOMAIN" "$TARGET" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl enable "$DOMAIN/com.jedisherpa.wizardjoeavatar"
launchctl print "$DOMAIN/com.jedisherpa.wizardjoeavatar"
