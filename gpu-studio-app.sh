#!/bin/bash
# GPU Studio kao aplikacija: pokrene server, otvori prozor, a kad se prozor zatvori ugasi server.
DIR="$(cd "$(dirname "$0")" && pwd)"
URL="http://localhost:8767"
PROFILE="$HOME/.config/gpu-studio-app"
LOG="/tmp/gpu-studio.log"
BROWSER="$(command -v chromium || command -v chromium-browser || command -v google-chrome)"

if pgrep -u "$USER" -f -- "--user-data-dir=$PROFILE" >/dev/null; then
  exec "$BROWSER" --user-data-dir="$PROFILE" --app="$URL"
fi

if ! curl -s -m1 -o /dev/null "$URL/api/info"; then
  python3 "$DIR/gpu-studio.py" >"$LOG" 2>&1 &
  for i in $(seq 1 40); do curl -s -m1 -o /dev/null "$URL/api/info" && break; sleep 0.25; done
fi

"$BROWSER" --user-data-dir="$PROFILE" --app="$URL" --class=GpuStudio --start-maximized \
  --no-first-run --no-default-browser-check --disable-features=Translate >/dev/null 2>&1

curl -s -m3 "$URL/api/quit" >/dev/null
sleep 0.5
pkill -u "$USER" -f "python3 $DIR/gpu-studio.py" 2>/dev/null
exit 0
