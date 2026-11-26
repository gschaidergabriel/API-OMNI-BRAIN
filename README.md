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

**Trained parts exist, two of them can steer.** Two small trained models ("needles", 26M parameters: request router and model-capability sorter) and a 0.8B use-case analyst (LoRA on Qwen3.5-0.8B-Base) were trained once on a rented GPU. Held-out results (authors never seen in training; labels = agreement of several judge/teacher models, so this measures imitation of that judgement): router 0.985 vs rule baseline 0.716 (n=880); sorter 0.851 vs 0.643 (n=370), but on 36 real OpenRouter ids 0.972 vs 0.944, i.e. no real difference; analyst caps-F1 0.883 vs 0.465 (n=176). The router needle decides the class of content-classified requests (code, json, de, reason) once the weights are installed (`--needles-install`, setting `needle_router`: off | shadow | active, default active). Explicit model names, tools and very long contexts stay with the rules, and any error, missing numpy/weights, slow pass (machine under load) or start-up falls back to the rules. Pure numpy forward pass, about 40-80 ms per request on a busy machine (2 BLAS threads, weights in `<data>/needles/`); the single-file binary includes numpy. The gate it passed is held-out agreement with teacher labels, not a proven benefit in your own traffic: `GET /api/needles` shows how often it agrees with the rules (labels and timing only, never request text). The sorter is not wired in: 0.80 in the numpy runtime, and on the 71 real model ids of the author's catalogue (2026-11-24) it disagrees with the rule on 9; judged by hand the rule is right in 5, the sorter in 1, both wrong in 3 (`tools/sorter_vs_rule.py` repeats this on your own catalogue) The 0.8B analyst has a runtime since 1.5.0: the single-file binary carries a static CPU llama-server (AVX2, no GPU, no UI), the merged GGUF (Q8_0, 834 MB) is NOT inside the file (a one-file binary is unpacked on every start) and is fetched or copied once with `--analyst-install [FILE]`, check with `--analyst-test`, state at `GET /api/analyst`. Setting `analyst_local`: off | fallback (default: only when the judge model has no key or fails) | prefer (local first). It starts lazily on a free localhost port, stops after 300 s idle, is skipped when the machine is busy and any error falls back to the old path. Measured on the held-out set with the GGUF itself: caps-F1 0.8835 (HF 0.8826), valid JSON 1.0, rule baseline 0.465, median 5.6 s per use case on a loaded 4-core CPU (2.6-4.8 s in the single-file self-test). Not measured yet: the Q4_K_M variant and any benefit in live traffic. The overall label stays honest: scripts + rules + statistics + an external judge, plus one small trained router and an optional local analyst.

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

## Universal Self-Service tools (source-only P0)

The pool exposes the **same tool contract regardless of which AI calls it**:
MCP for capable agent harnesses, OpenAI function-tool JSON Schema, Anthropic
tool-use JSON Schema, and authenticated local HTTP for other tool-enabled models
including Grok, ChatGPT, Claude and local models. No vendor-specific permissions
or key copies are introduced. Discover it at
`/.well-known/omnipool-tools.json`; see [the implementation and threat model](docs/SELF-SERVICE.md).

A connected AI can request a **restricted read-only diagnostic plan**.
Each plan must be approved **separately by the human in a local terminal**;
existing Connect-tab approval alone is insufficient. Every grant is
one-use, expires within five minutes and is bound to the exact local
application, host and plan hash. Only a status and receipt hash are
returned to the AI; detailed host diagnostics remain private and local.

**Not yet supported:** execution of arbitrary/generated scripts, repository
writes, installations, service changes, cross-host state sharing or autonomous
deployments. These require separate sandbox and consent work. A plain text-only
AI without tools cannot execute actions.

This feature is currently **source-only**. The published `bin/` artifacts
have not been rebuilt, and installing the current release does not activate it.
No live OMNIPOOL service has been changed.

**Credential policy:** No live provider API keys or secrets are shipped or
committed. The existing local key pool (20 free keys reported on one host)
remains under OMNIPOOL's runtime control; the reference code does not read,
copy, export or publish it. `python3 src/tools/check_secrets.py` scans
tracked source/doc files before publication (not binaries or Git history).

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
- `docs/TEAM-RUN.md` (what the free-model teams did and what they broke)
- `docs/SWARM-RUN.md` (50 agents with a mini harness each: what they changed, what was kept, what was reverted)
- `research/`

## Let your agent integrate it (the easy way)

Tell any agent harness (Claude Code, Hermes, Grokbot, Crush, Aider, anything with a shell or HTTP):

> Look at http://127.0.0.1:8799/integrate and integrate API-OMNI-BRAIN into your workflow.

The agent reads the guide, registers itself (`POST /v1/register`, nothing is active yet), tells you to approve it once in the **Connect** tab, and then changes **its own** configuration. API-OMNI-BRAIN never edits another program's settings.
`GET /v1/offer` tells the agent what the pool is good for (routine sub-tasks) and which model leads each class, so it can ask you whether it may hand such work over.
For MCP harnesses: `api-omni-brain --mcp` (tools `pool_ask`, `pool_models`, `pool_offer`). Offline: `api-omni-brain --guide` prints the same guide. Machine-readable: `/.well-known/api-omni-brain.json`.

Tested: registration, approval, denial and use against a fake provider (88 unit tests, 6 of them cover this flow and 9 the assistant) and the MCP server through real JSON-RPC; Claude Code's own health check reports it as connected. Not tested live: full conversations with Claude Code, Hermes and Grokbot.

## Vorstufe (pre-stage, built in)

Before a strong thinker model starts on a task, the Vorstufe takes cognitive load off it. From the senses the caller sends
(task, memory candidates with ids, organs, state, route hint, available tools) it builds one JSON envelope: the intent,
hypotheses AND counter-hypotheses, at most 3 candidates to read in full, the tools needed, what is known and unknown, and a
small world model (facts kept apart by domain, own state, what the message does).

- **Switches itself on.** It is active as soon as OMNI holds a usable key for a provider that serves one of the strong
  Vorstufe models (NVIDIA Nemotron 3 Ultra, Mistral Large 4, Kimi K3.1 Pro, Nemotron 3.5 Super VL, or the same model via
  another provider). No key, no Vorstufe; nothing to configure. `"vorstufe": "aus"` in the settings turns it off by hand.
- **OMNI picks the model** (strength floor, its own ranking and breaker), rotates keys and learns from every outcome.
- `GET /api/vorstufe` says whether it is active and why; `POST /api/vorstufe` with
  `{"runde": "r1"|"reflection"|"negotiation", "name", "kontext", "suggestion"}` returns the cleaned envelope, the raw one and
  a receipt (model, ms, key as 8-char hash). The caller redacts its own input; everything the Vorstufe reads is data, never orders.

## Assistant (chat in the app)

The **Assistant** is the first page of the app: a chat in German or English with sessions (a chat list on the left, "New chat" to start another). Three modes: **Ask** (about your keys, models and applications, or give a task), **Search** (free APIs from the local index, news, your own models; also `/search`, `/api`, `/news` or Ctrl+K) and **Use case** (describe what you want to build, get the matching models and APIs; also `/usecase`). It answers with a free model from your own pool and sees only a short live summary (never a key; a message that looks like a key is neither sent nor stored). Read-only questions (best model per class, models per capability, free APIs from the local index) are answered from the local data. Anything that changes state (scan now, emergency stop, open a tab) is only **proposed**: you press the button. Chats are kept only in your own browser storage on this machine (up to 40 chats), never sent anywhere. It is a free model, weaker than a frontier model.

## Requirements and known limits

- Binary: glibc ≥ 2.38 (Linux x86_64)
- Zipapp: Python ≥ 3.8 standard library (tested on 3.12 only)
- Only tested on the listed systems and Python version

## License

MIT, see `LICENSE`. The licence covers the code; it does not remove your responsibility described above, and it does not grant any rights to third-party services you route to.

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
