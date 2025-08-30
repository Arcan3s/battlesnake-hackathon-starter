#!/usr/bin/env bash
set -euo pipefail

############################################
# Config (env overrides welcome)
############################################
SUBMODULE_ROOT="${SUBMODULE_ROOT:-submodules}"
BOARD_DIR="${BOARD_DIR:-$SUBMODULE_ROOT/board}"
RULES_DIR="${RULES_DIR:-$SUBMODULE_ROOT/rules}"

BOARD_PORT="${BOARD_PORT:-3010}"          # board dev/preview port
BOARD_HOST="${BOARD_HOST:-0.0.0.0}"
BOARD_PUBLIC_URL="${BOARD_PUBLIC_URL:-http://localhost:${BOARD_PORT}}"

# Where the CLI binary will be placed
BS_BIN="$PWD/$RULES_DIR/bin/battlesnake"
GO_BIN="${HOME}/go/bin"

# Optional: run a demo game if SNAKE_URL is set (or SNAKE_URLS space-separated)
SNAKE_URLS="${SNAKE_URLS:-${SNAKE_URL:-}}"
GAME_WIDTH="${GAME_WIDTH:-11}"
GAME_HEIGHT="${GAME_HEIGHT:-11}"
GAME_DELAY_MS="${GAME_DELAY_MS:-500}"     # visual delay
GAME_DURATION_MS="${GAME_DURATION_MS:-10000}"
GAME_MODE="${GAME_MODE:-solo}"            # solo|standard|royale|squad

WAIT_STEPS=80
WAIT_INTERVAL=0.25

log() { printf "\033[1;34m[setup]\033[0m %s\n" "$*"; }
die() { echo "❌ $*" >&2; exit 1; }

BOARD_PID=""
CLI_PID=""
cleanup() {
  set +e
  [[ -n "${CLI_PID:-}"   ]] && kill "$CLI_PID"   2>/dev/null || true
  [[ -n "${BOARD_PID:-}" ]] && kill "$BOARD_PID" 2>/dev/null || true
}
trap cleanup EXIT

############################################
# 1) Ensure submodules (board & rules)
############################################
ensure_submodules() {
  if [[ ! -d "$BOARD_DIR" || ! -d "$RULES_DIR" ]]; then
    die "Expected submodules at '$BOARD_DIR' and '$RULES_DIR'."
  fi

  local needs_init=0
  [[ ! -e "$BOARD_DIR/.git" ]] && needs_init=1
  [[ ! -e "$RULES_DIR/.git" ]] && needs_init=1

  if [[ $needs_init -eq 1 ]]; then
    log "Initializing submodules"
    git submodule update --init --recursive "$BOARD_DIR" "$RULES_DIR"
  else
    log "Updating submodules to recorded commits"
    git submodule update --recursive "$BOARD_DIR" "$RULES_DIR"
  fi
}
ensure_submodules

############################################
# 2) Build Rules CLI from submodule
############################################
export PATH="$PWD/$RULES_DIR/bin:$PATH:$GO_BIN"

log "Building Battlesnake CLI from '$RULES_DIR'"
pushd "$RULES_DIR" >/dev/null
  go mod download
  mkdir -p bin
  go build -o bin/battlesnake ./cli/battlesnake
popd >/dev/null

[[ -x "$BS_BIN" ]] || die "CLI not found/executable at $BS_BIN"
log "CLI ready: $("$BS_BIN" --version 2>/dev/null || echo "$BS_BIN")"

############################################
# 3) Start Board UI from submodule
############################################
pushd "$BOARD_DIR" >/dev/null
  # Get deps; ci falls back to install for non-CI envs
  npm ci || npm install

  if npm run -s | grep -qE '^\s*dev\b'; then
    log "Starting board: npm run dev -- --host $BOARD_HOST --port $BOARD_PORT"
    npm run dev -- --host "$BOARD_HOST" --port "$BOARD_PORT" &
  elif npm run -s | grep -qE '^\s*preview\b'; then
    log "Building then previewing board"
    npm run build
    npm run preview -- --host "$BOARD_HOST" --port "$BOARD_PORT" &
  else
    log "Starting board via vite fallback"
    npx vite --host "$BOARD_HOST" --port "$BOARD_PORT" &
  fi
  BOARD_PID=$!
popd >/dev/null

# Wait for board to come up
for _ in $(seq 1 "$WAIT_STEPS"); do
  if curl -fsS "http://localhost:${BOARD_PORT}" >/dev/null 2>&1; then break; fi
  sleep "$WAIT_INTERVAL"
done
log "Board listening on :$BOARD_PORT (public: $BOARD_PUBLIC_URL)"

############################################
# 4) (Optional) Run a local game using CLI
############################################
if [[ -n "$SNAKE_URLS" ]]; then
  log "Starting game via CLI ($GAME_MODE ${GAME_WIDTH}x${GAME_HEIGHT}, delay ${GAME_DELAY_MS}ms)…"
  # Build args: one or many snakes
  CLI_ARGS=( play -W "$GAME_WIDTH" -H "$GAME_HEIGHT" -g "$GAME_MODE" -D "$GAME_DELAY_MS" --board-url "$BOARD_PUBLIC_URL" --browser --duration "$GAME_DURATION_MS" )
  # Turn each URL into a --url arg (name is optional; board shows URLs)
  for url in $SNAKE_URLS; do
    CLI_ARGS+=( --url "$url" )
  done
  # Example: add simple names if provided as NAME=url pairs (NAME@URL also supported)
  # Not implemented by default to keep it generic.

  "${BS_BIN}" "${CLI_ARGS[@]}" &
  CLI_PID=$!
  wait "$CLI_PID"
else
  log "Skipping game start (no SNAKE_URLS provided)."
  log "Tip: run with SNAKE_URLS='http://localhost:8000 http://localhost:8001' to auto-start."
  wait "$BOARD_PID"
fi
