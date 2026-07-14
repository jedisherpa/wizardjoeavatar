#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/deploy/macos/com.jedisherpa.wizardjoeavatar.plist"
TARGET="$HOME/Library/LaunchAgents/com.jedisherpa.wizardjoeavatar.plist"
CONFIG_DIR="$HOME/Library/Application Support/WizardJoeAvatar"
CONNECTOR_CONFIG="$CONFIG_DIR/prism-connector.env"
DOMAIN="gui/$(id -u)"

umask 077
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs" "$CONFIG_DIR"

CONNECTOR_TOKEN=""
if [ -f "$CONNECTOR_CONFIG" ]; then
  CONNECTOR_TOKEN=$(sed -n 's/^PRISM_WIZARD_CONNECTOR_TOKEN=//p' "$CONNECTOR_CONFIG" | head -n 1)
fi
case "$CONNECTOR_TOKEN" in
  ''|*[!0-9a-f]*) CONNECTOR_TOKEN=$(openssl rand -hex 32) ;;
esac
if [ "${#CONNECTOR_TOKEN}" -ne 64 ]; then
  CONNECTOR_TOKEN=$(openssl rand -hex 32)
fi

cat > "$CONNECTOR_CONFIG" <<EOF
PRISM_WIZARD_CONNECTOR_ENABLED=1
PRISM_WIZARD_BASE_URL=http://127.0.0.1:8765
PRISM_WIZARD_CONNECTOR_TOKEN=$CONNECTOR_TOKEN
EOF
chmod 600 "$CONNECTOR_CONFIG"

sed \
  -e "s|__ROOT__|$ROOT|g" \
  -e "s|__HOME__|$HOME|g" \
  -e "s|__CONNECTOR_TOKEN__|$CONNECTOR_TOKEN|g" \
  "$SOURCE" > "$TARGET"
chmod 600 "$TARGET"
plutil -lint "$TARGET"
launchctl bootout "$DOMAIN" "$TARGET" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl enable "$DOMAIN/com.jedisherpa.wizardjoeavatar"
launchctl print "$DOMAIN/com.jedisherpa.wizardjoeavatar" >/dev/null
printf 'Wizard Joe is running at http://127.0.0.1:8765/\n'
printf 'Prism GT connector configuration installed for normal desktop launches.\n'
