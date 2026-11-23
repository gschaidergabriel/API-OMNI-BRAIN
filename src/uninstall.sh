#!/bin/bash
# Removes menu entry, desktop icon, command and service (also the pre-1.3 "omnipool" names). Your data stays in ~/.local/share/omnipool.
exec "$(dirname "$0")/dist/API-OMNI-BRAIN" --uninstall 2>/dev/null || { systemctl --user disable --now api-omni-brain.service omnipool.service 2>/dev/null; rm -f ~/.local/bin/api-omni-brain ~/.local/bin/omnipool ~/.local/share/applications/api-omni-brain.desktop ~/.local/share/applications/omnipool.desktop ~/Desktop/API-OMNI-BRAIN.desktop ~/Desktop/Omnipool.desktop; echo removed; }
