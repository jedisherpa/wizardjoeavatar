#!/bin/sh
set -eu

TARGET="$HOME/Library/LaunchAgents/com.jedisherpa.wizardjoeavatar.plist"
launchctl bootout "gui/$(id -u)" "$TARGET"
