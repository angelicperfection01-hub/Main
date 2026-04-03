#!/usr/bin/env bash
# Start the Author Agent Network with a public Cloudflare URL.
# Usage: ./start.sh

set -e
cd "$(dirname "$0")"

# Check .env exists
if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.author.example to .env and add your ANTHROPIC_API_KEY."
  exit 1
fi

# Check ANTHROPIC_API_KEY is set
if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
  echo "WARNING: ANTHROPIC_API_KEY doesn't look set in .env — agents may fail."
fi

PORT=5000

echo "Starting Flask app on port $PORT..."
python web/app.py &
FLASK_PID=$!

# Wait for Flask to be ready
for i in $(seq 1 15); do
  if curl -sf "http://localhost:$PORT" > /dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo ""
echo "Starting Cloudflare tunnel..."
echo "Your public URL will appear below — open it in any browser."
echo "──────────────────────────────────────────────────────────"

# Trap Ctrl+C to kill both processes cleanly
cleanup() {
  echo ""
  echo "Shutting down..."
  kill $FLASK_PID 2>/dev/null
  exit 0
}
trap cleanup INT TERM

cloudflared tunnel --url "http://localhost:$PORT" --no-autoupdate 2>&1 | \
  grep --line-buffered -E "trycloudflare|Your quick Tunnel|https://"
