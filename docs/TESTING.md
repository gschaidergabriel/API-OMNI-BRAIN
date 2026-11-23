# TESTING.md - what was tested, where, and what was not

Every row below comes from a result file produced by `src/tools/sandbox_test.py` (raw JSON in `research/testing/`). A row says PASS only if every check passed.

## Checks per run (15)

daemon starts; `--version` starts with 1.3; index page contains the product name; static files (ui.js, ui.css, ui_radar.js, ui_manual.js, texte.json) are served; `/manual.json` and a manual screenshot are served; `/api/*` without the header is refused (403); `/api/status` with the header answers; the clean data directory contains **no key**; `/v1/*` without an application key is refused; path traversal is blocked.

Each run uses an empty HOME, no keys, its own port, `env -i`, background scanner and radar switched off.

## Sandboxes on the author's machine (Linux 6.17, Python 3.12, glibc 2.39)

- **plain**: `env -i`, empty home
- **bwrap**: read-only `/usr`, own PID/IPC/UTS/cgroup namespaces, tmpfs `/tmp`
- **firejail**: private home, no new privileges, all capabilities dropped
- **netoff**: own network namespace with only loopback (proves the app starts and serves without any network)

| artifact | sandbox | version | result | failed checks |
|---|---|---|---|---|
| API-OMNI-BRAIN | bwrap | API-OMNI-BRAIN 1.3.0 | PASS | - |
| API-OMNI-BRAIN | firejail | API-OMNI-BRAIN 1.3.0 | PASS | - |
| API-OMNI-BRAIN | netoff | API-OMNI-BRAIN 1.3.0 | PASS | - |
| API-OMNI-BRAIN | plain | API-OMNI-BRAIN 1.3.0 | PASS | - |
| API-OMNI-BRAIN.pyz | bwrap | API-OMNI-BRAIN 1.3.0 | PASS | - |
| API-OMNI-BRAIN.pyz | firejail | API-OMNI-BRAIN 1.3.0 | PASS | - |
| API-OMNI-BRAIN.pyz | netoff | API-OMNI-BRAIN 1.3.0 | PASS | - |
| API-OMNI-BRAIN.pyz | plain | API-OMNI-BRAIN 1.3.0 | PASS | - |


## Not tested (honest list)

- Other CPU architectures than x86_64 for the ELF (the `.pyz` is pure Python and should run anywhere with Python 3.8+, but only 3.12 and the versions listed above were run).
- glibc older than 2.38 for the ELF (the installer falls back to the `.pyz` there; that fallback was exercised only by logic, not on such a machine).
- macOS and Windows: not supported.
- Live connections of Claude Code, Hermes and Grokbot to the proxy: not tested. Only the project's own test suite (57 tests) and a demo client were used.
- Real provider behaviour over long periods: free tiers change; the probes are measurements of the day they ran.
- Docker and systemd-nspawn: not available on the author's machine (no root, no docker).
