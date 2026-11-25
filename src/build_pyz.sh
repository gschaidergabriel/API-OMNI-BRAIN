#!/bin/bash
# Universal single file: pure Python (stdlib only), runs on every Linux with python3 >= 3.8, any CPU. Output: dist/API-OMNI-BRAIN.pyz
set -e
cd "$(dirname "$0")"
rm -rf /tmp/op-pyz && mkdir -p /tmp/op-pyz dist
cp -r omnipool /tmp/op-pyz/omnipool && find /tmp/op-pyz -name __pycache__ -prune -exec rm -rf {} + ; rm -rf /tmp/op-pyz/omnipool/rt   # the static llama-server is x86-64 only; the pyz stays pure Python (the analyst then needs OMNIPOOL_LLAMA_SERVER or llama-server on PATH)
printf 'from omnipool.__main__ import main\nmain()\n' > /tmp/op-pyz/__main__.py
python3 -m zipapp /tmp/op-pyz -o dist/API-OMNI-BRAIN.pyz -p "/usr/bin/env python3" -c
chmod +x dist/API-OMNI-BRAIN.pyz; sha256sum dist/API-OMNI-BRAIN.pyz | tee dist/API-OMNI-BRAIN.pyz.sha256; ls -la dist/API-OMNI-BRAIN.pyz | cut -c20-60
