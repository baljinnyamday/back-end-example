#!/usr/bin/env bash
set -euo pipefail

# Configuration — adjust as needed
DEBUG_PORT=9222
PROFILE_DIR="$HOME/.cache/playwright-mcp-chrome-profile"
MCP_PORT=8931
OUTPUT_DIR="/Users/baljinnyamdayan/coding/take-home-assignment/agent-mcp/outputs"
VIEWPORT="1920x1080"
# (Optional) path to your Chrome/Chromium executable; leave blank to let MCP pick default
CHROME_EXECUTABLE=""

echo "=== Starting Chrome (with remote debugging) ==="

# Launch Chrome / Chromium with remote debugging enabled, using a persistent profile
if [[ -z "$CHROME_EXECUTABLE" ]]; then
  # Try typical macOS path; change if using Linux or custom
  CHROME_EXECUTABLE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
fi

# Start Chrome in background
"$CHROME_EXECUTABLE" \
  --remote-debugging-port=$DEBUG_PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-popup-blocking \
  --disable-background-networking \
  --disable-sync \
  --disable-translate \
  --disable-extensions \
  --disable-background-networking \
  --start-maximized \
  &

CHROME_PID=$!
echo "Launched Chrome with PID $CHROME_PID, CDP endpoint: http://localhost:$DEBUG_PORT"

# Wait a moment for Chrome to fully start
sleep 2

echo "=== Starting playwright-mcp, connecting to existing browser via CDP ==="
npx @playwright/mcp@latest \
  --cdp-endpoint http://localhost:$DEBUG_PORT \
  --port $MCP_PORT \
  --output-dir "$OUTPUT_DIR" \
  --browser chrome \
  # You can also include other MCP options as needed

MCP_EXIT_CODE=$?

echo "MCP exited with code $MCP_EXIT_CODE"
echo "Killing Chrome (PID $CHROME_PID)"
kill $CHROME_PID || echo "Failed to kill Chrome PID $CHROME_PID"

exit $MCP_EXIT_CODE
