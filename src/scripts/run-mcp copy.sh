#!/usr/bin/env bash
set -euo pipefail

# Configuration
DEBUG_PORT=9222
PROFILE_DIR="$HOME/.cache/playwright-mcp-chrome-profile"
MCP_PORT=8931
OUTPUT_DIR="$HOME/coding/take-home-assignment/agent-mcp/outputs"
HEADLESS=false  # Set to false for headed mode
CHROME_EXECUTABLE=""

# Cleanup function to ensure Chrome is killed on script exit
cleanup() {
    local exit_code=$?
    if [[ -n "${CHROME_PID:-}" ]] && kill -0 "$CHROME_PID" 2>/dev/null; then
        echo "Cleaning up: Killing Chrome (PID $CHROME_PID)"
        kill "$CHROME_PID" 2>/dev/null || true
        # Give it a moment, then force kill if needed
        sleep 1
        kill -9 "$CHROME_PID" 2>/dev/null || true
    fi
    exit $exit_code
}

trap cleanup EXIT INT TERM

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
mkdir -p "$PROFILE_DIR"

echo "=== Starting Chrome (with remote debugging) ==="

# Auto-detect Chrome executable if not specified
if [[ -z "$CHROME_EXECUTABLE" ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        CHROME_EXECUTABLE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - try common locations
        for path in \
            "/usr/bin/google-chrome" \
            "/usr/bin/chromium-browser" \
            "/usr/bin/chromium"; do
            if [[ -x "$path" ]]; then
                CHROME_EXECUTABLE="$path"
                break
            fi
        done
    fi
fi

# Verify Chrome executable exists
if [[ ! -x "$CHROME_EXECUTABLE" ]]; then
    echo "ERROR: Chrome executable not found at: $CHROME_EXECUTABLE"
    exit 1
fi

# Build Chrome arguments
CHROME_ARGS=(
    "--remote-debugging-port=$DEBUG_PORT"
    "--user-data-dir=$PROFILE_DIR"
    "--no-first-run"
    "--no-default-browser-check"
    "--disable-popup-blocking"
    "--disable-background-networking"
    "--disable-sync"
    "--disable-translate"
    "--disable-extensions"
    "--start-maximized"
    "--disable-dev-shm-usage"  # Prevents crashes in Docker/low memory
    "--no-sandbox"  # May be needed in containerized environments
)

# Add headless flags if enabled
if [[ "$HEADLESS" == true ]]; then
    CHROME_ARGS+=(
        "--headless=new"  # Uses new headless mode (Chrome 109+)
        "--disable-gpu"
        "--window-size=1920,1080"
    )
    echo "Running in HEADLESS mode"
else
    echo "Running in HEADED mode"
fi

# Start Chrome in background
"$CHROME_EXECUTABLE" "${CHROME_ARGS[@]}" > /dev/null 2>&1 &
CHROME_PID=$!

echo "Launched Chrome with PID $CHROME_PID, CDP endpoint: http://localhost:$DEBUG_PORT"

# Wait for Chrome to be ready (check if debug port is listening)
echo "Waiting for Chrome to be ready..."
for i in {1..30}; do
    if curl -s "http://localhost:$DEBUG_PORT/json/version" > /dev/null 2>&1; then
        echo "Chrome is ready!"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "ERROR: Chrome failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

echo "=== Starting playwright-mcp, connecting to existing browser via CDP ==="

# Run MCP server
npx @playwright/mcp@latest \
  --cdp-endpoint "http://localhost:$DEBUG_PORT" \
  --port "$MCP_PORT" \
  --output-dir "$OUTPUT_DIR" \
  --browser chrome

MCP_EXIT_CODE=$?
echo "MCP exited with code $MCP_EXIT_CODE"

exit $MCP_EXIT_CODE