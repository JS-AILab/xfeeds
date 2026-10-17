#!/bin/bash
# One-time setup on a Mac: checks Hot Aisle every 2 minutes in the background
# (launchd) and plays a loud alert when a 4x or 8x GPU machine is available.
# Run from the folder that has hotaisle_alert.py:  bash install_mac.sh
# Uninstall:  launchctl bootout gui/$(id -u)/com.hotaisle.alert; rm -rf ~/hotaisle ~/Library/LaunchAgents/com.hotaisle.alert.plist
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/hotaisle_alert.py"
DIR="$HOME/hotaisle"
LABEL=com.hotaisle.alert
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$(command -v python3)"

[ -f "$SRC" ] || { echo "hotaisle_alert.py not found next to this script"; exit 1; }
mkdir -p "$DIR" "$HOME/Library/LaunchAgents"
cp "$SRC" "$DIR/hotaisle_alert.py"

if [ ! -f "$DIR/hotaisle.env" ]; then
  echo "Hot Aisle API key and team handle (get them with: ssh admin.hotaisle.app)"
  read -r -s -p "API key: " KEY; echo
  read -r -p "Team handle: " TEAM
  umask 077
  printf 'HOTAISLE_API_KEY=%s\nHOTAISLE_TEAM_HANDLE=%s\n' "$KEY" "$TEAM" > "$DIR/hotaisle.env"
fi

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>$DIR/hotaisle_alert.py</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartInterval</key><integer>120</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DIR/hotaisle.log</string>
  <key>StandardErrorPath</key><string>$DIR/hotaisle.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed. Playing a test alert now..."
"$PY" "$DIR/hotaisle_alert.py" --test
sleep 5
echo
echo "First check (log: $DIR/hotaisle.log):"
tail -n 5 "$DIR/hotaisle.log"
