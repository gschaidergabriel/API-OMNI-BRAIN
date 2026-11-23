#!/bin/bash
# API-OMNI-BRAIN binary: one file, own icon. Heavy step -> mem-guard first, lowprio. PyInstaller runs without the user site (an obsolete 'typing' package there blocks it).
set -e
cd "$(dirname "$0")"
mem-guard || { echo "machine busy (mem-guard), try again later"; exit 75; }
PYTHONNOUSERSITE=1 PYTHONPATH="$HOME/omnipool-build/shim" lowprio -m 3G -c 200 -- python3 -m PyInstaller --noconfirm --clean --onefile --name API-OMNI-BRAIN \
  --distpath dist --workpath "$HOME/omnipool-build/work" --specpath "$HOME/omnipool-build" --paths omnipool/vendor \
  --hidden-import token_check --hidden-import keypool \
  --add-data "$PWD/omnipool/ui.html:omnipool" --add-data "$PWD/omnipool/ui.css:omnipool" --add-data "$PWD/omnipool/ui.js:omnipool" --add-data "$PWD/omnipool/ui_radar.js:omnipool" --add-data "$PWD/omnipool/ui_manual.js:omnipool" --add-data "$PWD/omnipool/manual.json:omnipool" --add-data "$PWD/omnipool/manual:omnipool/manual" \
  --add-data "$PWD/omnipool/assets:omnipool/assets" --add-data "$PWD/omnipool/texte.json:omnipool" --add-data "$PWD/omnipool/radar_quellen.json:omnipool" --add-data "$PWD/omnipool/icon.png:omnipool" \
  --add-data "$PWD/omnipool/vendor/providers_free.json:omnipool/vendor" --add-data "$PWD/omnipool/vendor/providers_free.json:." \
  --exclude-module PySide6 --exclude-module tkinter --exclude-module numpy --exclude-module PIL launch.py
sha256sum dist/API-OMNI-BRAIN | tee dist/API-OMNI-BRAIN.sha256
