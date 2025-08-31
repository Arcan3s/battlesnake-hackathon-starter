#!/usr/bin/env bash
set -euo pipefail

# -------------------------------
# Battlesnake Env Doctor 🐍🩺
# -------------------------------

SETUP_HINT="Run Environment Setup ./scripts/setup_submodules.sh"   # update if your setup script is named differently

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
is_http_url() { [[ "${1:-}" =~ ^https?://[^/[:space:]]+(/.*)?$ ]]; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }

# returns 0 if dir has at least one non-dot entry (not counting .git contents)
dir_nonempty() {
  local d="$1"
  [[ -d "$d" ]] || return 1
  # exclude '.' '..' and empty .git file/dir noise; fail if truly empty
  shopt -s nullglob dotglob
  local entries=("$d"/*)
  shopt -u nullglob dotglob
  # If only .git exists and it's empty, treat as empty
  if (( ${#entries[@]} == 0 )); then
    return 1
  fi
  return 0
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
    # Fast/forgiving check: ensure each named package is present
    while IFS= read -r line || [[ -n "$line" ]]; do
      line="${line%%#*}"; line="${line// /}"
      [[ -z "$line" || "$line" == -* ]] && continue
      pkg="${line%%[<>=![]*}"
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

# ---------- GIT SUBMODULES (existence + non-empty + key files) ----------
info "Checking submodules 📦"

# Root exists & non-empty?
if [[ ! -d "$SUBMODULE_ROOT" ]]; then
  err "Submodules root missing: $SUBMODULE_ROOT"
  need_setup=true
elif ! dir_nonempty "$SUBMODULE_ROOT"; then
  err "Submodules root exists but is empty: $SUBMODULE_ROOT"
  need_setup=true
else
  ok "Submodules root present: $SUBMODULE_ROOT"
fi

# Board submodule strict checks
if [[ ! -d "$BOARD_DIR" ]]; then
  err "Board submodule missing: $BOARD_DIR"
  need_setup=true
elif ! dir_nonempty "$BOARD_DIR"; then
  err "Board submodule is empty: $BOARD_DIR"
  need_setup=true
else
  if [[ -f "$BOARD_DIR/package.json" ]]; then
    ok "Board has package.json ✅"
  else
    err "Board missing package.json at $BOARD_DIR/package.json"
    need_setup=true
  fi
  if [[ -d "$BOARD_DIR/src" ]] && dir_nonempty "$BOARD_DIR/src"; then
    ok "Board src/ present and non-empty ✅"
  else
    err "Board src/ missing or empty at $BOARD_DIR/src"
    need_setup=true
  fi
fi

# Rules submodule strict checks
if [[ ! -d "$RULES_DIR" ]]; then
  err "Rules submodule missing: $RULES_DIR"
  need_setup=true
elif ! dir_nonempty "$RULES_DIR"; then
  err "Rules submodule is empty: $RULES_DIR"
  need_setup=true
else
  if [[ -f "$RULES_DIR/go.mod" ]]; then
    ok "Rules has go.mod ✅"
  else
    err "Rules missing go.mod at $RULES_DIR/go.mod"
    need_setup=true
  fi
fi

# Optional: show submodule status if git exists
if has_cmd git; then
  info "git submodule status:"
  git submodule status || warn "Could not read submodule status"
fi

echo

# ---------- GO / BATTLESNAKE CLI ----------
info "Checking Battlesnake CLI binary ⚙️"
if [[ ! -x "$BS_BIN" ]]; then
  err "Battlesnake CLI not found or not executable at: $BS_BIN"
  warn "Try building it inside the rules submodule (e.g., make build or go build)"
  need_setup=true
else
  ok "Battlesnake CLI built at $BS_BIN ✅"
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
  if [[ -d "$BOARD_DIR/node_modules" ]] && dir_nonempty "$BOARD_DIR/node_modules"; then
    ok "node_modules present in $BOARD_DIR ✅"
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
  say "   - git submodule update --init --recursive"
  say "   - pip install -r ${REQ}"
  say "   - build Battlesnake CLI in rules (creates ${BS_BIN})"
  say "   - (cd ${BOARD_DIR} && npm ci)"
  exit 1
else
  ok "All checks passed — you're good to go! 🚀"
fi
