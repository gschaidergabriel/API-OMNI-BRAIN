# API-OMNI-BRAIN
Local API router that routes requests to free models using Thompson sampling over Beta distributions with a pessimistic shrinkage prior, informed by live probes and real traffic outcomes.

API-OMNI-BRAIN is a standalone local application that runs a background daemon on 127.0.0.1:8799 and opens a web interface in its own window. It discovers and validates your own free-tier API keys, probes models with machine-checked tests, classifies incoming requests, and routes them through a Thompson-sampling chooser that mixes probe results with real traffic outcomes. It ships no keys, no trained model, and no external dependencies beyond the binary or Python standard library.

```text
__     ______  _    _            _____  ______ 
\ \   / / __ \| |  | |     /\   |  __ \|  ____|
 \ \_/ / |  | | |  | |    /  \  | |__) | |__   
  \   /| |  | | |  | |   / /\ \ |  _  /|  __|  
   | | | |__| | |__| |  / ____ \| | \ \| |____ 
   |_|  \____/ \____/  /_/    \_\_|  \_\______|
 _____  ______  _____ _____   ____  _   _  _____ _____ ____  _      ______ 
|  __ \|  ____|/ ____|  __ \ / __ \| \ | |/ ____|_   _|  _ \| |    |  ____|
| |__) | |__  | (___ | |__) | |  | |  \| | (___   | | | |_) | |    | |__   
|  _  /|  __|  \___ \|  ___/| |  | | . ` |\___ \  | | |  _ <| |    |  __|  
| | \ \| |____ ____) | |    | |__| | |\  |____) |_| |_| |_) | |____| |____ 
|_|  \_\______|_____/|_|     \____/|_| \_|_____/|_____|____/|______|______|

  ##########################################################################
  #  THE RESPONSIBILITY FOR HOW THIS SOFTWARE IS USED LIES WITH *YOU*.     #
  #                                                                        #
  #  You choose the keys you add, the providers you call, the data you     #
  #  send, the costs you cause, and you must follow each provider's        #
  #  terms. The authors give NO warranty and accept NO liability.          #
  #  Free tiers change or vanish. A scanner result is not a guarantee.     #
  #  Do not use it to abuse services, evade limits, or process data you    #
  #  are not allowed to process. This is not legal or security advice.     #
  ##########################################################################
```

## What it is (and honestly what it is not)

API-OMNI-BRAIN is a standalone local application distributed as:
- A Linux x86_64 binary (glibc ≥ 2.38)
- A Python zipapp (`.pyz`, pure Python ≥ 3.8 standard library, tested on 3.12 only)

It runs a background daemon bound to 127.0.0.1:8799 (header `X-Omnipool: 1` required for `/api`) and opens a web interface in its own window.

**It is not a trained model.** Honest label: well-made scripts + rules + bandit statistics + a strong external model as judge. Planned but not built: two small trained "needles" and a 0.8B model (needs budget and explicit approval).

**It ships no keys.** You add your own free-tier API keys. Keys stay on the machine (local key file or environment), are never logged, never shown in the UI (slot and short hash only), never sent anywhere except to the provider they belong to.

## Install

No keys are shipped. Commands are exactly:

One line (picks the binary or the zipapp for your machine, verifies the checksum, installs a desktop entry and a user service, no root needed):

```bash
curl -fsSL https://raw.githubusercontent.com/gschaidergabriel/API-OMNI-BRAIN/main/install.sh | sh
```

Or from a checkout, or by hand:

```bash
git clone https://github.com/gschaidergabriel/API-OMNI-BRAIN && cd API-OMNI-BRAIN && ./install.sh
```

```bash
chmod +x bin/API-OMNI-BRAIN && bin/API-OMNI-BRAIN --install
```

```bash
python3 bin/API-OMNI-BRAIN.pyz --install
```

Read `install.sh` first if you do not want to pipe a script into a shell; verify with `bin/SHA256SUMS`.

## First five minutes

1. Open the application window (starts automatically on run).
2. Paste a free-tier API token into the Keys & Providers tab; the UI recognises the format and checks it live (nothing is saved before you confirm).
3. Press "Scan and probe now" (top right) and watch the Models tab fill with probe results (code, JSON, German, reasoning, long text, tools).
4. Connect an app: copy the per-app key `op-<app>-<hmac>` from the Connect tab and configure your client (Claude Code, Hermes, Crush, Aider, or any OpenAI/Anthropic-style client) to point at `http://127.0.0.1:8799/v1`.
5. Watch the Overview tab: usage per application and the best model per class update as real traffic arrives; NVIDIA models are preferred when quality is equal.

## What it can do

- **Sensor**: finds keys in configured places and checks them (valid / invalid / rate-limited) per provider; a token pasted into the UI is recognised by format and checked live.
- **Catalogue**: reads the model lists of every working provider; unknown OpenAI-compatible providers can be added by URL + token (a safety gate checks the address first).
- **Probes**: small machine-checked tests per model: code, JSON output, German, reasoning, long context, tool calling. A strong judge model (nemotron-3-ultra) scores free-text answers (German).
- **Classifier**: rules that sort an incoming request into a class (code, json, german, reason, long, tool); measured 29/32 on the shipped test set (3 known misses).
- **Chooser**: Thompson sampling over Beta distributions with a pessimistic shrinkage prior (PRIOR_K=6, prior mean 0.85*p0), mixes probe results with real traffic outcomes; NVIDIA preferred when quality is equal; confirmation probes for lucky candidates.
- **Immune system**: circuit breaker per model/provider, key cooldowns, model-exact 429 handling, drift detection (several real failures → re-probe).
- **Planner**: runs a scan only when the machine is not busy.
- **Proxy**: OpenAI-compatible `/v1/chat/completions`, `/v1/models` and Anthropic-compatible `/v1/messages` (+ `count_tokens`) on localhost; per-app keys `op-<app>-<hmac>`; a virtual model `omnipool-auto` routes by class. Works with Claude Code, Hermes, Crush, Aider and any OpenAI/Anthropic-style client (only Claude-Code-style, Hermes and Grokbot connection not tested live yet).
- **Radar**: ~110 news feeds and 10 Hacker-News searches every 2 h (95 of 129 sources alive at first run), an index of ~2600 free-API entries (public-apis list + hand-curated providers), full-text search (SQLite FTS5), twice-weekly model re-check (every 3.4 days), use-case matching (a strong model extracts capabilities, then search + safety verdict). Reddit is blocked on purpose.
- **Safety**: hardened fetch (HTTPS only, public IPs only, pinned IP, redirects re-checked, size caps), URL verdicts (TLS, domain age via RDAP, shorteners, punycode, risky TLDs), a gate before any key travels to a new provider, and a quarantine: every fetched file is written to a private folder and scanned by a sandboxed worker (fresh network namespace if available, rlimits, empty environment, fail-closed); anything not clean is overwritten with zeros and deleted, a popup says so, and there is no release button.

## What it cannot and does not want to do

- It is not an antivirus: the scanner uses signatures and heuristics; "nothing found" is not "proven harmless".
- It does not create accounts, buy anything, handle payments, trade, or move money; it never writes into other programs' configuration (the Connect tab only shows instructions).
- It does not bypass rate limits, quotas, terms of service, CAPTCHAs or paywalls; it does not farm or share keys; it does not crawl behind logins.
- It cannot make a free API reliable: free tiers change, vanish, throttle. Rankings are measurements of today.
- It does not guarantee privacy at the provider: your prompts go to the provider you route to; their policies apply.
- Search is only as good as the index; the judge model is coarse; the vision judge used for UI scoring is noisy (±0.5 on a 10 scale).
- Not tested on other distributions or Python versions than the listed ones.

## Security model

- Daemon binds to 127.0.0.1 only; header `X-Omnipool: 1` required for `/api` endpoints.
- Keys never leave the machine except to their owning provider.
- Quarantine: fetched files scanned in a sandboxed worker (network namespace, rlimits, empty environment, fail-closed); unclean files zeroed and deleted; no release button.
- Hardened fetch: HTTPS only, public IPs only, pinned IP, redirects re-checked, size caps.
- URL verdicts: TLS, domain age via RDAP, shorteners, punycode, risky TLDs.
- Gate before any key travels to a new provider.

## Documentation links

- `docs/MANUAL.md`
- `docs/ORIGIN.md`
- `docs/WHY.md`
- `docs/TESTING.md`
- `research/`

## Requirements and known limits

- Binary: glibc ≥ 2.38 (Linux x86_64)
- Zipapp: Python ≥ 3.8 standard library (tested on 3.12 only)
- Only tested on the listed systems and Python version

## Naming note

Internal package name `omnipool`, header `X-Omnipool`, environment variables `OMNIPOOL_*` stay for compatibility.

```text
__     ______  _    _            _____  ______ 
\ \   / / __ \| |  | |     /\   |  __ \|  ____|
 \ \_/ / |  | | |  | |    /  \  | |__) | |__   
  \   /| |  | | |  | |   / /\ \ |  _  /|  __|  
   | | | |__| | |__| |  / ____ \| | \ \| |____ 
   |_|  \____/ \____/  /_/    \_\_|  \_\______|
 _____  ______  _____ _____   ____  _   _  _____ _____ ____  _      ______ 
|  __ \|  ____|/ ____|  __ \ / __ \| \ | |/ ____|_   _|  _ \| |    |  ____|
| |__) | |__  | (___ | |__) | |  | |  \| | (___   | | | |_) | |    | |__   
|  _  /|  __|  \___ \|  ___/| |  | | . ` |\___ \  | | |  _ <| |    |  __|  
| | \ \| |____ ____) | |    | |__| | |\  |____) |_| |_| |_) | |____| |____ 
|_|  \_\______|_____/|_|     \____/|_| \_|_____/|_____|____/|______|______|

  ##########################################################################
  #  THE RESPONSIBILITY FOR HOW THIS SOFTWARE IS USED LIES WITH *YOU*.     #
  #                                                                        #
  #  You choose the keys you add, the providers you call, the data you     #
  #  send, the costs you cause, and you must follow each provider's        #
  #  terms. The authors give NO warranty and accept NO liability.          #
  #  Free tiers change or vanish. A scanner result is not a guarantee.     #
  #  Do not use it to abuse services, evade limits, or process data you    #
  #  are not allowed to process. This is not legal or security advice.     #
  ##########################################################################
```
