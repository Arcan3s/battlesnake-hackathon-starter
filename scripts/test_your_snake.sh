#!/usr/bin/env bash
set -euo pipefail

# 1) Load .env if present
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

: "${REPLIT_URL:?REPLIT_URL must be set (e.g., https://your-replit-url.repl.co)}"
BASE="${REPLIT_URL%/}"

port_url() {
  local port="$1"
  if [[ "$port" == "80" || "$port" == "443" ]]; then
    printf "%s" "$BASE"
  else
    printf "%s:%s" "$BASE" "$port"
  fi
}

# Known mappings from your .replit
MAIN_SNAKE_URL="$(port_url 80)"
SNAKE1_URL="$(port_url 3001)"
SNAKE2_URL="$(port_url 3002)"
SNAKE3_URL="$(port_url 3003)"
BOARD_PUBLIC_URL="$(port_url 3010)"
RULES_PUBLIC_URL="$(port_url 9999)"

export BOARD_PUBLIC_URL
export SNAKE_URLS="${MAIN_SNAKE_URL} ${SNAKE1_URL} ${SNAKE2_URL} ${SNAKE3_URL}"

# Game params
export GAME_MODE="${GAME_MODE:-standard}"
export GAME_WIDTH="${GAME_WIDTH:-11}"
export GAME_HEIGHT="${GAME_HEIGHT:-11}"
export GAME_DELAY_MS="${GAME_DELAY_MS:-500}"
export GAME_DURATION_MS="${GAME_DURATION_MS:-10000}"

echo "[env] REPLIT_URL=$REPLIT_URL"
echo "[env] BOARD_PUBLIC_URL=$BOARD_PUBLIC_URL"
echo "[env] SNAKE_URLS=$SNAKE_URLS"

# 2) Run setup_board_rules.sh and capture CLI logs
LOGFILE="$(mktemp)"
bash scripts/setup_board_rules.sh 2>&1 | tee "$LOGFILE" &

# 3) Poll the log for engine port + game id
ENGINE_PORT=""
GAME_ID=""

for _ in $(seq 1 80); do
  if [[ -z "$ENGINE_PORT" ]]; then
    ENGINE_PORT=$(grep -Eo 'engine listening on [0-9]+' "$LOGFILE" | awk '{print $4}' | tail -n1 || true)
  fi
  if [[ -z "$GAME_ID" ]]; then
    GAME_ID=$(grep -Eo 'game id [a-f0-9-]+' "$LOGFILE" | awk '{print $3}' | tail -n1 || true)
  fi
  if [[ -n "$ENGINE_PORT" && -n "$GAME_ID" ]]; then
    break
  fi
  sleep 0.5
done

if [[ -n "$ENGINE_PORT" && -n "$GAME_ID" ]]; then
  ENGINE_URL="$(port_url "$ENGINE_PORT")"
  FINAL_URL="${BOARD_PUBLIC_URL}?engine=${ENGINE_URL}&game=${GAME_ID}&autoplay=true"

  echo
  echo "=========================================================="
  echo "Open this in your browser:"
  echo "👉  $FINAL_URL"
  echo "=========================================================="
else
  echo "❌ Failed to detect engine port or game id. Check logs in $LOGFILE"
fi

wait
