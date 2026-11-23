#!/bin/bash
# Developer install from a source checkout: builds nothing, just installs ./dist/API-OMNI-BRAIN (run ./build.sh first). End users: use the root install.sh of the repository.
set -e
cd "$(dirname "$0")"
BIN="$PWD/dist/API-OMNI-BRAIN"; [ -x "$BIN" ] || { echo "run ./build.sh first"; exit 1; }
"$BIN" --install "$@"
