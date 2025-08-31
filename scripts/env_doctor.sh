#!/usr/bin/env bash
set -euo pipefail

# -------------------------------
# Battlesnake Env Doctor 🐍🩺
# -------------------------------

say()   { printf "%s\n" "$*"; }
info()  { printf "ℹ️  %s\n" "$*"; }
ok()    { printf "✅ %s\n" "$*"; }
warn()  { printf "⚠️  %s\n" "$*"; }
err()   { printf "❌ %s\n" "$*"; }

missing=()
fixups=()

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

# ---------- validators ----------
is_http_url() {
  local u="${1:-}"
  [[ "$u" =~ ^https?://[^/[:space:]]+(/.*)?$ ]]
}

# ---------- checks ----------
if [[ -z "${REPLIT_URL:-}" ]]; then
  err "REPLIT_URL is missing 🚫"
  missing+=("REPLIT_URL")
  fixups+=("REPLIT_URL=https://your-replit-subdomain.replit.dev")
else
  if ! is_http_url "$REPLIT_URL"; then
    err "REPLIT_URL malformed: '$REPLIT_URL' (expected http(s)://host) 🛑"
    missing+=("REPLIT_URL")
    fixups+=("REPLIT_URL=https://your-replit-subdomain.replit.dev")
  else
    ok "REPLIT_URL set: $REPLIT_URL 🎉"
    REPLIT_URL="${REPLIT_URL%/}"
  fi
fi

# ---------- derived URLs ----------
if [[ -n "${REPLIT_URL:-}" && ${#missing[@]} -eq 0 ]]; then
  ENGINE_URL="${REPLIT_URL}:9000"
  BOARD_URL="${REPLIT_URL}:3000"
  info "Derived ENGINE_URL 👉 $ENGINE_URL"
  info "Derived BOARD_URL  👉 $BOARD_URL"
fi

# ---------- summary ----------
echo
if ((${#missing[@]})); then
  err "Missing or invalid required variable(s): ${missing[*]} ❌"
  echo
  say "👉 Add this line to your .env:"
  printf "%s\n" "${fixups[@]}" | sort -u
  exit 1
else
  ok "Environment looks good 🚀 You're ready to run the game!"
fi
