#!/usr/bin/env bash
set -euo pipefail

# -------------------------------
# Battlesnake Env Doctor 🐍🩺
# -------------------------------

SETUP_HINT="./setup_env.sh"   # update if your setup script is named differently

SUBMODULE_ROOT="${SUBMODULE_ROOT:-submodules}"
BOARD_DIR="${BOARD_DIR:-$SUBMODULE_ROOT/board}"
RULES_DIR="${RULES_DIR:-$SUBMODULE_ROOT/rules}"

# ✅ Hard-coded Battlesnake CLI path check
BS_BIN="/home/runner/workspace/submodules/rules/bin/battlesnake"

PY="${PY:-python3}"
REQ="${REQ:-requirements.txt}"

say()   { printf "%s\n" "$*"; }
info()  { printf "ℹ️  %s\n" "$*"; }
ok()    { printf "✅ %s\n" "$*"; }
warn()  { printf "⚠️  %s\n" "$*"; }
err()   { printf "❌ %s\n" "$*"; }

missing_env=()
fixups_env=()
need_setup=false

# ---------- load .env ----------
if [[ -f .env ]]; then
  info "Loading environment from .env 📄"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  warn "No .env file found. Only REPLIT_URL is required."
fi

# ---------- helpers ----------
is_http_url() { [[ "$1" =~ ^https?://[^/[:space:]]+(/.*)?$ ]]; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }
req_pkg_name() {
  local line="$1"
  line="${line%%#*}"
  line="${line// /}"
  [[ -z "$line" || "$line" == -* ]] && return 1
  local name="${line%%[<>=![]*}"
  [[ -z "$name" ]] && return 1
  printf "%s" "$name"
}

# ---------- ENV: REPLIT_URL ----------
if [[ -z "${REPLIT_URL:-}" ]]; then
  err "REPLIT_URL is missing 🚫"
  missing_env+=("REPLIT_URL")
  fixups_env+=("REPLIT_URL=https://your-replit-subdomain.replit.dev")
  need_setup=true
elif ! is_http_url "$REPLIT_URL"; then
  err "REPLIT_URL malformed: '$REPLIT_URL' (expected http(s)://host) 🛑"
  missing_env+=("REPLIT_URL")
  fixups_env+=("REPLIT_URL=https://your-replit-subdomain.replit.dev")
  need_setup=true
else
  ok "REPLIT_URL set: $REPLIT_URL 🎉"
  REPLIT_URL="${REPLIT_URL%/}"
  info "Derived ENGINE_URL 👉 ${REPLIT_URL}:9000"
  info "Derived BOARD_URL  👉 ${REPLIT_URL}:3000"
fi

echo

# ---------- PYTHON ----------
info "Checking Python setup 🐍"
if ! has_cmd "$PY"; then
  err "Python not found in PATH (expected '$PY')"
  need_setup=true
else
  ok "Python found: $("$PY" -V 2>&1)"
  if [[ -f "$REQ" ]]; then
    missing_pkgs=()
    while IFS= read -r line || [[ -n "$line" ]]; do
      pkg="$(req_pkg_name "$line" || true)"
      [[ -z "$pkg" ]] && continue
      if ! "$PY" -m pip show "$pkg" >/dev/null 2>&1; then
        missing_pkgs+=("$pkg")
      fi
    done < "$REQ"
    if ((${#missing_pkgs[@]})); then
      err "Missing Python packages: ${missing_pkgs[*]} 📦"
      info "Try: pip install -r $REQ"
      need_setup=true
    else
      ok "All Python packages from $REQ appear installed 🎯"
    fi
  else
    warn "No $REQ found; skipping package checks"
  fi
fi

echo

# ---------- GIT SUBMODULES ----------
info "Checking submodules 📦"
[[ -d "$SUBMODULE_ROOT" ]] || { err "Submodules root missing: $SUBMODULE_ROOT"; need_setup=true; }
[[ -d "$BOARD_DIR" ]] || { err "Board submodule missing at: $BOARD_DIR"; need_setup=true; }
[[ -d "$RULES_DIR" ]] || { err "Rules submodule missing at: $RULES_DIR"; need_setup=true; }
[[ -d "$SUBMODULE_ROOT" && -d "$BOARD_DIR" && -d "$RULES_DIR" ]] && ok "All submodules present"

echo

# ---------- GO / BATTLESNAKE CLI ----------
info "Checking Battlesnake CLI binary ⚙️"
if [[ ! -x "$BS_BIN" ]]; then
  err "Battlesnake CLI not found at: $BS_BIN"
  need_setup=true
else
  ok "Battlesnake CLI built"
fi

echo

# ---------- NODE ----------
info "Checking Node.js / npm 🧰"
if has_cmd node; then
  ok "Node: $(node -v)"
else
  err "node not found in PATH"
  need_setup=true
fi

if has_cmd npm; then
  ok "npm: $(npm -v)"
else
  err "npm not found in PATH"
  need_setup=true
fi

if [[ -d "$BOARD_DIR" && -f "$BOARD_DIR/package.json" ]]; then
  if [[ -d "$BOARD_DIR/node_modules" ]]; then
    ok "node_modules present in $BOARD_DIR"
  else
    err "node_modules missing in $BOARD_DIR"
    info "Try: (cd \"$BOARD_DIR\" && npm ci)"
    need_setup=true
  fi
fi

echo

# ---------- SUMMARY ----------
if ((${#missing_env[@]})); then
  err "Environment variables missing/invalid: ${missing_env[*]} ❌"
  say "👉 Add this to your .env:"
  printf "%s\n" "${fixups_env[@]}" | sort -u
  echo
fi

if [[ "$need_setup" == true ]]; then
  err "Some checks failed."
  say "🛠️  Run your setup script to fix this (e.g. ${SETUP_HINT})"
  exit 1
else
  ok "All checks passed — you're good to go! 🚀"
fi
