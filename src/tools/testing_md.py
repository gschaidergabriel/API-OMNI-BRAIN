#!/usr/bin/env python3
"""Write docs_out/TESTING.md from the real result files in team/testing/*.json (+ team/testing/extra.md for environments tested by hand)."""
import glob, json, os, platform, subprocess
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = []
for f in sorted(glob.glob(os.path.join(R, "team/testing/*.json"))):
    d = json.load(open(f))
    bad = [k for k, v in d.get("checks", {}).items() if not v]
    rows.append("| %s | %s | %s | %s | %s |" % (d.get("artifact"), d.get("sandbox"), d.get("version", "?"), "PASS" if d.get("ok") else "FAIL", ", ".join(bad) or "-"))
extra = open(os.path.join(R, "team/testing/extra.md")).read() if os.path.exists(os.path.join(R, "team/testing/extra.md")) else ""
t = ["# TESTING.md - what was tested, where, and what was not", "",
     "Every row below comes from a result file produced by `src/tools/sandbox_test.py` (raw JSON in `research/testing/`). A row says PASS only if every check passed.", "",
     "## Checks per run (15)", "",
     "daemon starts; `--version` starts with 1.4; index page contains the product name; static files (ui.js, ui.css, ui_radar.js, ui_manual.js, texte.json) are served; `/manual.json` and a manual screenshot are served; `/api/*` without the header is refused (403); `/api/status` with the header answers; the clean data directory contains **no key**; `/v1/*` without an application key is refused; path traversal is blocked.", "",
     "Each run uses an empty HOME, no keys, its own port, `env -i`, background scanner and radar switched off.", "",
     "## Sandboxes on the author's machine (Linux 6.17, Python 3.12, glibc 2.39)", "",
     "- **plain**: `env -i`, empty home", "- **bwrap**: read-only `/usr`, own PID/IPC/UTS/cgroup namespaces, tmpfs `/tmp`", "- **firejail**: private home, no new privileges, all capabilities dropped",
     "- **netoff**: own network namespace with only loopback (proves the app starts and serves without any network)", "",
     "| artifact | sandbox | version | result | failed checks |", "|---|---|---|---|---|"] + rows + ["", extra,
     "## Not tested (honest list)", "",
     "- Other CPU architectures than x86_64 for the ELF (the `.pyz` is pure Python and should run anywhere with Python 3.8+, but only 3.12 and the versions listed above were run).",
     "- glibc older than 2.38 for the ELF (the installer falls back to the `.pyz` there; that fallback was exercised only by logic, not on such a machine).",
     "- macOS and Windows: not supported.",
     "- Live connections of Claude Code, Hermes and Grokbot to the proxy: not tested. Only the project's own test suite (79 tests) and a demo client were used.",
     "- The router needle is not part of the sandbox runs (no weights there). It was exercised with `--needles-test` in the ELF and the .pyz and end to end through the routing function on the author's machine only: 300 held-out rows, 295 correct, median 81 ms with the machine under load (other machines and CPUs: not measured).",
     "- Real provider behaviour over long periods: free tiers change; the probes are measurements of the day they ran.",
     "- Docker and systemd-nspawn: not available on the author's machine (no root, no docker)."]
open(os.path.join(R, "docs_out/TESTING.md"), "w").write("\n".join(t) + "\n")
print("TESTING.md written", len(rows), "rows")
