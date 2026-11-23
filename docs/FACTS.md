# FACTS (verified against the code and measurements of 2026-11-23; authors may only claim what is listed here)

## What it is
- API-OMNI-BRAIN (internal package name `omnipool`, first called Poolbrain) is a standalone local application: one binary (Linux x86_64, glibc >= 2.38) or one zipapp (`.pyz`, pure Python >= 3.8 stdlib, tested on 3.12 only).
- It runs a background daemon bound to 127.0.0.1:8799 (header `X-Omnipool: 1` required for /api) and opens a web interface in its own window.
- It ships NO keys. The user adds their own free-tier API keys; keys stay on the machine (a local key file / environment), are never logged, never shown in the UI except behind "show key", never sent anywhere except to the provider they belong to.
- It is NOT a trained model. Honest label: well-made scripts + rules + bandit statistics + a strong external model as judge. Planned but NOT built: two small trained "needles" and a 0.8B model (needs budget and explicit approval).

## What it does (organs)
- Sensor: finds keys in configured places and checks them (valid / invalid / rate-limited) per provider; a token pasted into the UI is recognised by format and checked live (nothing is saved before the user confirms).
- Catalogue: reads the model lists of every working provider; unknown OpenAI-compatible providers can be added by URL + token (a safety gate checks the address first).
- Probes: small machine-checked tests per model: code, JSON output, German, reasoning, long context, tool calling. A strong judge model (nemotron-3-ultra) scores free-text answers (German).
- Classifier: rules that sort an incoming request into a class (code, json, german, reason, long, tool); measured 29/32 on the shipped test set (3 known misses).
- Chooser: Thompson sampling over Beta distributions with a pessimistic shrinkage prior (PRIOR_K=6, prior mean 0.85*p0), mixes probe results with real traffic outcomes; NVIDIA preferred when quality is equal; confirmation probes for lucky candidates.
- Immune system: circuit breaker per model/provider, key cooldowns, model-exact 429 handling, drift detection (several real failures -> re-probe).
- Planner: runs a scan only when the machine is not busy.
- Proxy: OpenAI-compatible /v1/chat/completions, /v1/models and Anthropic-compatible /v1/messages (+ count_tokens) on localhost; per-app keys `op-<app>-<hmac>`; a virtual model `omnipool-auto` routes by class. Works with Claude Code, Hermes, Crush, Aider and any OpenAI/Anthropic-style client (only Claude-Code-style, Hermes and Grokbot connection NOT tested live yet).
- Radar: ~110 news feeds and 10 Hacker-News searches every 2 h (95 of 129 sources alive at the first run), an index of ~2600 free-API entries (public-apis list + hand-curated providers), full-text search (SQLite FTS5), twice-weekly model re-check (every 3.4 days), use-case matching (a strong model extracts capabilities, then search + safety verdict). Reddit is blocked on purpose.
- Safety: hardened fetch (https only, public IPs only, pinned IP, redirects re-checked, size caps), URL verdicts (TLS, domain age via RDAP, shorteners, punycode, risky TLDs), a gate before any key travels to a NEW provider, and a quarantine: every fetched file is written to a private folder and scanned by a sandboxed worker (fresh network namespace if available, rlimits, empty environment, fail-closed); anything not clean is overwritten with zeros and deleted, a popup says so, and there is no release button.

## What it cannot / must not do
- It is not an antivirus: the scanner uses signatures and heuristics; "nothing found" is not "proven harmless".
- It does not create accounts, buy anything, handle payments, trade, or move money; it never writes into other programs' configuration (the Connect tab only shows instructions).
- It does not bypass rate limits, quotas, terms of service, CAPTCHAs or paywalls; it does not farm or share keys; it does not crawl behind logins.
- It cannot make a free API reliable: free tiers change, vanish, throttle. Rankings are measurements of today.
- It does not guarantee privacy at the provider: your prompts go to the provider you route to; their policies apply.
- Search is only as good as the index; the judge model is coarse; the vision judge used for UI scoring is noisy (+-0.5 on a 10 scale).
- Not tested on other distributions or Python versions than the listed ones.

## Measurements (all from this repository's data)
- Test suite: 57 passed at the 1.2 release (unit, deep end-to-end with a fake provider, radar, quarantine, UI rules).
- Quarantine test set: EICAR, reverse shell, miner, base64-exec, key stealer, prompt injection, trojan source, ELF, zip blocked; a legitimate API client, markdown and install docs released; quarantine folder empty afterwards.
- Radar first run: 95 of 129 feeds alive, 2617 index entries, 937 news items, 0 scanner false positives on real feeds in 48 s.
- Ranking prior: simulation showed a naive shrinkage (k=2) made a lucky model MORE likely (15 % -> 24 %); k=6 with a pessimistic mean fixed it.
- Improvement loop (free NVIDIA tokens, 22 rounds): whole-file rewrites by models failed the syntax check ~85 % of the time even with a repair call; CSS and text edits succeeded more often; an A/B vision judge moved 5.33 -> 5.75 on six tabs (noisy). Real defects found by the gates: `[object HTMLSpanElement]` in the model table, 269 px horizontal overflow at 420 px width.
- Team run (this repo, research/): a chief model invented an Electron/IPC architecture that does not exist (0 valid tickets) -> archived as a failure; fixed by giving the synthesis the technical reality.
