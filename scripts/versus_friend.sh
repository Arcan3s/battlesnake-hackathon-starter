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
# Load .env (if present)
############################################
if [[ -f .env ]]; then
  log "Loading environment from .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

############################################
# CLI args (override env/.env)
############################################
usage() {
  cat <<'USAGE'
Usage:
  ./run.sh [URL] [options]

Positional:
  URL                       Single snake URL (e.g., http://localhost:8000)

Options:
  -u, --url URL             Single snake URL
  -U, --urls "URLS..."      Space- or comma-separated snake URLs
      --ports "8000 5001"   Ports to probe on localhost
      --range A-B           Port range to probe (e.g., 8000-8010)
      --mode MODE           Game mode (solo|standard)
  -h, --help                Show this help
USAGE
}

INPUT_URLS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage; exit 0;;
    -u|--url)
      [[ $# -ge 2 ]] || { echo "Missing value for $1"; usage; exit 1; }
      INPUT_URLS="${INPUT_URLS:+$INPUT_URLS }$2"; shift 2;;
    -U|--urls)
      [[ $# -ge 2 ]] || { echo "Missing value for $1"; usage; exit 1; }
      INPUT_URLS="${INPUT_URLS:+$INPUT_URLS }$2"; shift 2;;
    --ports)
      [[ $# -ge 2 ]] || { echo "Missing value for $1"; usage; exit 1; }
      SNAKE_PORTS="$2"; shift 2;;
    --range)
      [[ $# -ge 2 ]] || { echo "Missing value for $1"; usage; exit 1; }
      DISCOVER_PORT_RANGE="$2"; shift 2;;
    --mode)
      [[ $# -ge 2 ]] || { echo "Missing value for $1"; usage; exit 1; }
      GAME_MODE="$2"; shift 2;;
    http://*|https://*)
      INPUT_URLS="${INPUT_URLS:+$INPUT_URLS }$1"; shift;;
    *)
      echo "Unknown argument: $1"
      usage; exit 1;;
  esac
done

if [[ -n "${INPUT_URLS}" ]]; then
  IFS=', ' read -r -a _cli_urls <<<"$INPUT_URLS"
  SNAKE_URLS="${_cli_urls[*]}"
  if [[ -z "${DISCOVER_PORT_RANGE:-}" && -z "${SNAKE_PORTS:-}" ]]; then
    SNAKE_PORTS=""
    DISCOVER_PORT_RANGE=""
  fi
  if [[ "${#_cli_urls[@]}" -eq 1 && -z "${GAME_MODE:-}" ]]; then
    GAME_MODE="solo"
  fi
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

SNAKE_URL="${SNAKE_URL:-http://localhost:8000}"
SNAKE_URLS="${SNAKE_URLS:-${SNAKE_URLS:-}}"
SNAKE_PORTS="${SNAKE_PORTS:-8000 5001 5002 5003}"
DISCOVER_PORT_RANGE="${DISCOVER_PORT_RANGE:-}"

GAME_NAME="${GAME_NAME:-Python Starter Project}"
WIDTH="${WIDTH:-11}"
HEIGHT="${HEIGHT:-11}"
GAME_MODE="${GAME_MODE:-standard}"

REPLIT_URL="${REPLIT_URL:-http://localhost}"
ENGINE_PORT="${ENGINE_PORT:-9000}"
BOARD_PORT_PUBLIC="${BOARD_PORT_PUBLIC:-3000}"

_base="${REPLIT_URL%/}"
if [[ ! "$_base" =~ ^https?:// ]]; then
  _base="https://${_base}"
fi
ENGINE_URL="${_base}:${ENGINE_PORT}"
BOARD_URL="${_base}:${BOARD_PORT_PUBLIC}"

WAIT_STEPS="${WAIT_STEPS:-80}"
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

for _ in $(seq 1 "$WAIT_STEPS"); do
  if curl -fsS "http://127.0.0.1:${BOARD_PORT}" >/dev/null 2>&1; then break; fi
  sleep "$WAIT_INTERVAL"
done
log "Board listening on :${BOARD_PORT} (PID ${BOARD_PID})"

############################################
# Snake discovery
############################################
declare -a DISCOVERED_URLS=()

if [[ -n "$SNAKE_URLS" ]]; then
  IFS=', ' read -r -a _urls <<<"$SNAKE_URLS"
  for u in "${_urls[@]}"; do
    [[ -n "$u" ]] && DISCOVERED_URLS+=("$u")
  done
fi

if [[ -n "$SNAKE_PORTS" ]]; then
  for p in $SNAKE_PORTS; do
    DISCOVERED_URLS+=("http://localhost:$p")
  done
fi

if [[ -n "$DISCOVER_PORT_RANGE" ]]; then
  range_start="${DISCOVER_PORT_RANGE%-*}"
  range_end="${DISCOVER_PORT_RANGE#*-}"
  if [[ "$range_start" =~ ^[0-9]+$ && "$range_end" =~ ^[0-9]+$ && "$range_end" -ge "$range_start" ]]; then
    for p in $(seq "$range_start" "$range_end"); do
      DISCOVERED_URLS+=("http://localhost:$p")
    done
  fi
fi

DISCOVERED_URLS+=("$SNAKE_URL")

declare -A _seen=()
declare -a CANDIDATE_URLS=()
for u in "${DISCOVERED_URLS[@]}"; do
  key="${u%/}"
  if [[ -n "${_seen[$key]:-}" ]]; then continue; fi
  _seen[$key]=1
  CANDIDATE_URLS+=("$key")
done

is_alive() {
  local url="$1"
  curl -fsS "${url%/}/ping" >/dev/null 2>&1 && return 0
  curl -fsS "${url%/}/"    >/dev/null 2>&1 && return 0
  return 1
}

snake_name_from_root() {
  local url="$1"
  local json
  json="$(curl -fsS "${url%/}/" 2>/dev/null || true)"
  if [[ -z "$json" ]]; then
    echo ""; return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "$json" 2>/dev/null || true
import sys, json
try:
    data = json.loads(sys.argv[1])
    v = data.get("name") or data.get("Name") or ""
    print(v)
except Exception:
    pass
PY
    return 0
  fi
  echo "$json" | grep -oE '"name"\s*:\s*"[^"]+"' | head -n1 | sed -E 's/.*"name"\s*:\s*"([^"]+)".*/\1/' || true
}

declare -a SNAKE_NAMES=()
declare -a SNAKE_URL_ARGS=()
for url in "${CANDIDATE_URLS[@]}"; do
  if is_alive "$url"; then
    name="$(snake_name_from_root "$url")"
    if [[ -z "$name" ]]; then
      hostport="$(echo "$url" | sed -E 's#^https?://##')"
      name="Snake@${hostport}"
    fi
    log "✅ Found snake: ${name}  (${url})"
    SNAKE_NAMES+=("$name")
    SNAKE_URL_ARGS+=("$url")
  else
    log "… no snake at ${url}"
  fi
done

if [[ "${#SNAKE_URL_ARGS[@]}" -eq 0 ]]; then
  log "⚠️  No snakes discovered. The game will still start, but moves may fail."
  SNAKE_NAMES=("Snake@${SNAKE_URL#http://}")
  SNAKE_URL_ARGS=("$SNAKE_URL")
fi

if [[ "${#SNAKE_URL_ARGS[@]}" -ge 2 && "${GAME_MODE}" == "solo" ]]; then
  log "Multiple snakes detected → switching game mode to 'standard'"
  GAME_MODE="standard"
fi

############################################
# Launch local game (engine) via `play`
############################################
BOARD_FLAG=()
if "$BS_BIN" play --help 2>/dev/null | grep -q -- '--board-url'; then
  BOARD_FLAG=(--board-url "${BOARD_URL}")
  log "CLI supports --board-url; using ${BOARD_URL}"
else
  log "CLI does not expose --board-url; relying on --browser"
fi

declare -a SNAKE_ARGS=()
for i in "${!SNAKE_URL_ARGS[@]}"; do
  SNAKE_ARGS+=( --name "${SNAKE_NAMES[$i]}" --url "${SNAKE_URL_ARGS[$i]}" )
done

log "Starting local game via CLI 'play' with ${#SNAKE_URL_ARGS[@]} snake(s)…"
set -x
"$BS_BIN" play \
  -W "${WIDTH}" -H "${HEIGHT}" \
  -g "${GAME_MODE}" \
  --browser \
  --engine "${ENGINE_URL}" \
  "${BOARD_FLAG[@]}" \
  "${SNAKE_ARGS[@]}" &
set +x
CLI_PID=$!

echo
log "Open local board directly: http://localhost:${BOARD_PORT}"
log "Public board (if proxied): ${BOARD_URL}"
log "Game is running; close with Ctrl+C."
echo

wait "$CLI_PID" "$BOARD_PID"
