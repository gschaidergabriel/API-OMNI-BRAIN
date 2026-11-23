#!/bin/sh
# API-OMNI-BRAIN installer. No root, no keys, nothing is sent anywhere except the download from this repository.
#   from a checkout:   ./install.sh
#   straight from web: curl -fsSL https://raw.githubusercontent.com/gschaidergabriel/API-OMNI-BRAIN/main/install.sh | sh
# It picks the native binary (Linux x86_64, glibc >= 2.38) or the universal .pyz (python3 >= 3.8), verifies the SHA-256 against SHA256SUMS, and runs "--install"
# (menu entry, desktop icon, ~/.local/bin/api-omni-brain). Use "--service" to also enable the background service. Remove again with: api-omni-brain --uninstall
set -eu
REPO="https://raw.githubusercontent.com/gschaidergabriel/API-OMNI-BRAIN/main"
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo .)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
[ "$(uname -s)" = "Linux" ] || { echo "Linux only."; exit 1; }
glibc_ok() { v="$(ldd --version 2>&1 | head -1 | grep -o '[0-9]*\.[0-9]*$' || true)"; [ -n "$v" ] && [ "$(printf '%s\n2.38\n' "$v" | sort -V | head -1)" = "2.38" ]; }
if [ "$(uname -m)" = "x86_64" ] && glibc_ok; then NAME="API-OMNI-BRAIN"; else
  command -v python3 >/dev/null || { echo "Need python3 >= 3.8 (or an x86_64 system with glibc >= 2.38)."; exit 1; }
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' || { echo "python3 >= 3.8 required."; exit 1; }
  NAME="API-OMNI-BRAIN.pyz"; fi
if [ -f "$HERE/bin/$NAME" ] && [ -f "$HERE/bin/SHA256SUMS" ]; then cp "$HERE/bin/$NAME" "$TMP/$NAME"; cp "$HERE/bin/SHA256SUMS" "$TMP/SHA256SUMS"
else
  fetch() { if command -v curl >/dev/null; then curl -fsSL "$1" -o "$2"; else wget -q "$1" -O "$2"; fi; }
  fetch "$REPO/bin/$NAME" "$TMP/$NAME"; fetch "$REPO/bin/SHA256SUMS" "$TMP/SHA256SUMS"; fi
( cd "$TMP" && grep " $NAME\$" SHA256SUMS | sha256sum -c - ) || { echo "Checksum mismatch - not installing."; exit 1; }
chmod +x "$TMP/$NAME"
"$TMP/$NAME" --install "$@"
echo "Done. Start it from the menu / desktop icon, or run: api-omni-brain"
