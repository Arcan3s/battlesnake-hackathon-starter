#!/usr/bin/env bash
set -euo pipefail

# --- Config ---
SUBMODULE_ROOT="${SUBMODULE_ROOT:-submodules}"
BOARD_DIR="${BOARD_DIR:-$SUBMODULE_ROOT/board}"
RULES_DIR="${RULES_DIR:-$SUBMODULE_ROOT/rules}"
GO_BIN="${HOME}/go/bin"
BS_BIN="$PWD/$RULES_DIR/bin/battlesnake"

log() { printf "\033[1;34m[setup]\033[0m %s\n" "$*"; }
die() { echo "❌ $*" >&2; exit 1; }

# --- Sanity ---
[[ -d "$SUBMODULE_ROOT" ]] || die "Missing '$SUBMODULE_ROOT' folder."
[[ -d "$BOARD_DIR" ]]      || die "Missing board submodule path '$BOARD_DIR'."
[[ -d "$RULES_DIR" ]]      || die "Missing rules submodule path '$RULES_DIR'."

# --- Submodules ---
log "Initializing/updating submodules"
git submodule update --init --recursive "$BOARD_DIR" "$RULES_DIR"

# Optional: bump to latest remote branch commits (set UPDATE_TO_REMOTE=1)
if [[ "${UPDATE_TO_REMOTE:-0}" == "1" ]]; then
  log "Bumping submodules to latest remote"
  git submodule update --remote --merge "$BOARD_DIR" "$RULES_DIR"
  git add "$BOARD_DIR" "$RULES_DIR"
  git commit -m "Update board/rules submodules to latest" || true
fi

# --- Build Rules CLI ---
export PATH="$PWD/$RULES_DIR/bin:$PATH:$GO_BIN"
log "Building Rules CLI from '$RULES_DIR'"
pushd "$RULES_DIR" >/dev/null
  go mod download
  mkdir -p bin
  go build -o bin/battlesnake ./cli/battlesnake
popd >/dev/null
[[ -x "$BS_BIN" ]] || die "CLI not found/executable at $BS_BIN"
log "Rules CLI ready: $("$BS_BIN" --version 2>/dev/null || echo "$BS_BIN")"

# --- Install Board deps (cacheable) ---
log "Installing Board dependencies in '$BOARD_DIR' (npm ci || npm install)"
pushd "$BOARD_DIR" >/dev/null
  npm ci || npm install
popd >/dev/null

# --- Summary ---
echo
log "Pinned SHAs:"
printf "  board: %s\n" "$(git -C "$BOARD_DIR" rev-parse --short HEAD)"
printf "  rules: %s\n" "$(git -C "$RULES_DIR" rev-parse --short HEAD)"
log "Setup complete."

chmod +x scripts/versus_friend.sh