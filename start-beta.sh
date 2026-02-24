#!/bin/bash
# Start Slide Guide Generator + Dev Tunnel for beta testing
# Close this terminal window to stop both services.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
DEVTUNNEL="$HOME/bin/devtunnel"
STREAMLIT="$DIR/venv/bin/streamlit"
TUNNEL_ID="slide-guide"
PORT=8501

# --- Cleanup on exit ---
cleanup() {
    echo ""
    echo "Shutting down..."
    [[ -n "$TUNNEL_PID" ]] && kill "$TUNNEL_PID" 2>/dev/null
    [[ -n "$STREAMLIT_PID" ]] && kill "$STREAMLIT_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Stopped."
}
trap cleanup EXIT

# --- Free the port if something else is using it ---
EXISTING_PID=$(lsof -ti :"$PORT" 2>/dev/null || true)
if [[ -n "$EXISTING_PID" ]]; then
    echo "Port $PORT in use (PID $EXISTING_PID) — stopping it..."
    kill "$EXISTING_PID" 2>/dev/null
    sleep 1
fi

# --- Start Streamlit ---
echo "Starting Streamlit on port $PORT..."
"$STREAMLIT" run "$DIR/app.py" \
    --server.port "$PORT" \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!
sleep 2

# --- Start Dev Tunnel (port is already configured on the tunnel) ---
echo "Starting dev tunnel ($TUNNEL_ID)..."
"$DEVTUNNEL" host "$TUNNEL_ID" &
TUNNEL_PID=$!
sleep 3

# --- Show info ---
TUNNEL_URL=$("$DEVTUNNEL" show "$TUNNEL_ID" 2>/dev/null | grep -oP 'https://\S+')
echo ""
echo "================================================"
echo "  Slide Guide Generator — Beta Server Running"
echo "================================================"
echo "  Local:  http://localhost:$PORT"
echo "  Tunnel: $TUNNEL_URL"
echo ""
echo "  Share the tunnel URL with your colleagues."
echo "  Close this window to stop everything."
echo "================================================"
echo ""

# --- Wait and show activity ---
wait "$STREAMLIT_PID"
