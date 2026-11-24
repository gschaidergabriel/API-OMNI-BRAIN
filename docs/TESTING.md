# TESTING.md - what was tested, where, and what was not

Every row below comes from a result file produced by `src/tools/sandbox_test.py` (raw JSON in `research/testing/`). A row says PASS only if every check passed.

## Checks per run (15)

daemon starts; `--version` starts with 1.4; index page contains the product name; static files (ui.js, ui.css, ui_radar.js, ui_manual.js, texte.json) are served; `/manual.json` and a manual screenshot are served; `/api/*` without the header is refused (403); `/api/status` with the header answers; the clean data directory contains **no key**; `/v1/*` without an application key is refused; path traversal is blocked.

Each run uses an empty HOME, no keys, its own port, `env -i`, background scanner and radar switched off.

## Sandboxes on the author's machine (Linux 6.17, Python 3.12, glibc 2.39)

- **plain**: `env -i`, empty home
- **bwrap**: read-only `/usr`, own PID/IPC/UTS/cgroup namespaces, tmpfs `/tmp`
- **firejail**: private home, no new privileges, all capabilities dropped
- **netoff**: own network namespace with only loopback (proves the app starts and serves without any network)

| artifact | sandbox | version | result | failed checks |
|---|---|---|---|---|
| API-OMNI-BRAIN | bwrap | API-OMNI-BRAIN 1.4.0 | PASS | - |
| API-OMNI-BRAIN | firejail | API-OMNI-BRAIN 1.4.0 | PASS | - |
| API-OMNI-BRAIN | netoff | API-OMNI-BRAIN 1.4.0 | PASS | - |
| API-OMNI-BRAIN | plain | API-OMNI-BRAIN 1.4.0 | PASS | - |
| API-OMNI-BRAIN.pyz | bwrap | API-OMNI-BRAIN 1.4.0 | PASS | - |
| API-OMNI-BRAIN.pyz | firejail | API-OMNI-BRAIN 1.4.0 | PASS | - |
| API-OMNI-BRAIN.pyz | netoff | API-OMNI-BRAIN 1.4.0 | PASS | - |
| API-OMNI-BRAIN.pyz | plain | API-OMNI-BRAIN 1.4.0 | PASS | - |

## Second environment: the "gpt-sandbox" VM (Ubuntu 26.04, Linux 7.0, Python 3.14.4, glibc 2.43)

A KVM virtual machine on the author's machine that has internet access but no keys and a different Python and glibc than the host. It is the sandbox the author's ChatGPT bridge uses. **Honest note:** ChatGPT's own built-in code interpreter has no internet access and cannot download the app, so the job was run in this VM by the author's assistant over SSH, not typed by ChatGPT itself. In a fresh temporary HOME:

1. The one-line installer from `raw.githubusercontent.com` ran: checksum OK, ELF chosen, menu entry and `api-omni-brain` launcher created.
2. `sha256sum -c bin/SHA256SUMS` on a fresh `git clone`: both files OK.
3. `api-omni-brain --version` and `python3 -I API-OMNI-BRAIN.pyz --version`: `API-OMNI-BRAIN 1.3.0`.
4. The 15-check harness, **plain** sandbox, ELF and zipapp: PASS / PASS (`research/testing/vm/`).
5. **Not run there:** `bwrap` and `firejail` are not installed in the VM, and `unshare -rn` is not permitted for that user, so those three sandbox kinds were skipped (not counted as passes).

## Third environment: the author's PC, real install

The same one-line installer was run on the author's own machine (real HOME, replacing a previous Omnipool 1.2.0 install, which was backed up first): installed binary hash equals the hash in `SHA256SUMS`; the user service `api-omni-brain.service` came up; `/`, `/manual.json`, `/manual/overview.png` and `/ui_manual.js` answer 200; `/api/ping` answers version 1.3.0.


## Not tested (honest list)

- Other CPU architectures than x86_64 for the ELF (the `.pyz` is pure Python and should run anywhere with Python 3.8+, but only 3.12 and the versions listed above were run).
- glibc older than 2.38 for the ELF (the installer falls back to the `.pyz` there; that fallback was exercised only by logic, not on such a machine).
- macOS and Windows: not supported.
- Live connections of Claude Code, Hermes and Grokbot to the proxy: not tested. Only the project's own test suite (79 tests) and a demo client were used.
- The router needle is not part of the sandbox runs (no weights there). It was exercised with `--needles-test` in the ELF and the .pyz and end to end through the routing function on the author's machine only: 300 held-out rows, 295 correct, median 81 ms with the machine under load (other machines and CPUs: not measured).
- Real provider behaviour over long periods: free tiers change; the probes are measurements of the day they ran.
- Docker and systemd-nspawn: not available on the author's machine (no root, no docker).
