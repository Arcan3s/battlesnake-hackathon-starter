#!/usr/bin/env bash
set -euo pipefail

############################################
# Helpers / cleanup
############################################
log()  { printf "\033[1;34m[run]\033[0m %s\n" "$*"; }
die()  { echo "❌ $*" >&2; exit 1; }

BOARD_PID=""
CLI_PID=""

cleanup() {
  set +e
  [[ -n "${CLI_PID:-}"   ]] && kill "$CLI_PID"   2>/dev/null || true
  [[ -n "${BOARD_PID:-}" ]] && kill "$BOARD_PID" 2>/dev/null || true
}
trap cleanup EXIT

############################################
# Load .env (if present) so it can override defaults
############################################
if [[ -f .env ]]; then
  log "Loading environment from .env"
  # Export all variables defined in .env
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

############################################
# Config (override via env or .env)
############################################
SUBMODULE_ROOT="${SUBMODULE_ROOT:-submodules}"
BOARD_DIR="${BOARD_DIR:-$SUBMODULE_ROOT/board}"
RULES_DIR="${RULES_DIR:-$SUBMODULE_ROOT/rules}"
BS_BIN="${BS_BIN:-$PWD/$RULES_DIR/bin/battlesnake}"

BOARD_HOST="${BOARD_HOST:-0.0.0.0}"
BOARD_PORT="${BOARD_PORT:-3010}"

SNAKE_URL="${SNAKE_URL:-http://localhost:8000}"   # your snake API
GAME_NAME="${GAME_NAME:-Python Starter Project}"
WIDTH="${WIDTH:-11}"
HEIGHT="${HEIGHT:-11}"
GAME_MODE="${GAME_MODE:-solo}"                     # e.g. solo, standard, etc.

# Replit/public base; derive full URLs from this.
# In .env: REPLIT_URL=https://your-replit-url.repl.co
REPLIT_URL="${REPLIT_URL:-http://localhost}"

# Known public ports (engine and optional board proxy)
ENGINE_PORT="${ENGINE_PORT:-9000}"
BOARD_PORT_PUBLIC="${BOARD_PORT_PUBLIC:-3000}"

# Build normalized base (strip trailing slash; ensure scheme).
_base="${REPLIT_URL%/}"
if [[ ! "$_base" =~ ^https?:// ]]; then
  _base="https://${_base}"
fi

# Build URLs used by CLI
ENGINE_URL="${_base}:${ENGINE_PORT}"
BOARD_URL="${_base}:${BOARD_PORT_PUBLIC}"

WAIT_STEPS="${WAIT_STEPS:-80}"     # 80 * 0.25s ≈ 20s
WAIT_INTERVAL="${WAIT_INTERVAL:-0.25}"

############################################
# Sanity checks
############################################
[[ -d "$BOARD_DIR" ]] || die "Missing board dir: $BOARD_DIR (did you run setup?)"
[[ -d "$RULES_DIR" ]] || die "Missing rules dir: $RULES_DIR (did you run setup?)"
[[ -x "$BS_BIN"    ]] || die "CLI not found/executable at: $BS_BIN"

log "Using CLI: $("$BS_BIN" --version 2>/dev/null || echo "$BS_BIN")"
log "Derived URLs -> ENGINE_URL: ${ENGINE_URL} | BOARD_URL: ${BOARD_URL}"

############################################
# Start Board UI (local dev server)
############################################
pushd "$BOARD_DIR" >/dev/null

if [[ ! -d node_modules ]]; then
  log "Installing board dependencies"
  npm ci || npm install
fi

if npm run -s | grep -qE '^\s*dev\b'; then
  log "Starting board: npm run dev -- --host ${BOARD_HOST} --port ${BOARD_PORT}"
  npm run dev -- --host "${BOARD_HOST}" --port "${BOARD_PORT}" >/dev/null 2>&1 &
elif npm run -s | grep -qE '^\s*preview\b'; then
  log "Starting board (build + preview)"
  npm run build
  npm run preview -- --host "${BOARD_HOST}" --port "${BOARD_PORT}" >/dev/null 2>&1 &
else
  log "Starting board via vite fallback"
  npx vite --host "${BOARD_HOST}" --port "${BOARD_PORT}" >/dev/null 2>&1 &
fi
BOARD_PID=$!
popd >/dev/null

# Wait for board to listen locally
for _ in $(seq 1 "$WAIT_STEPS"); do
  if curl -fsS "http://127.0.0.1:${BOARD_PORT}" >/dev/null 2>&1; then break; fi
  sleep "$WAIT_INTERVAL"
done
log "Board listening on :${BOARD_PORT} (PID ${BOARD_PID})"

############################################
# Check snake API (optional)
############################################
if curl -fsS "${SNAKE_URL}/ping" >/dev/null 2>&1 || curl -fsS "${SNAKE_URL}" >/dev/null 2>&1; then
  log "Snake detected at ${SNAKE_URL}"
else
  log "⚠️  Could not confirm snake at ${SNAKE_URL}. The game will still start, but moves may fail."
fi

############################################
# Launch local game (engine) via `play`
############################################
# If --board-url is supported, point the CLI at the public board proxy (derived from REPLIT_URL).
BOARD_FLAG=()
if "$BS_BIN" play --help 2>/dev/null | grep -q -- '--board-url'; then
  BOARD_FLAG=(--board-url "${BOARD_URL}")
  log "CLI supports --board-url; using ${BOARD_URL}"
else
  log "CLI does not expose --board-url; relying on --browser to open its default UI"
fi

log "Starting local game via CLI 'play'…"
set -x
"$BS_BIN" play \
  -W "${WIDTH}" -H "${HEIGHT}" \
  --name "${GAME_NAME}" \
  --url "${SNAKE_URL}" \
  -g "${GAME_MODE}" \
  --browser \
  --engine "${ENGINE_URL}" \
  "${BOARD_FLAG[@]}" &
set +x
CLI_PID=$!

echo
log "Open local board directly (dev server): http://localhost:${BOARD_PORT}"
log "Public board (if proxied): ${BOARD_URL}"
log "Game is running; close with Ctrl+C."
echo

wait "$CLI_PID" "$BOARD_PID"
