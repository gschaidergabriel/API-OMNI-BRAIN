# ORIGIN.md

## 1. The problem

Free AI API tiers multiply. Keys scatter across environment variables, local files, browser extensions, and pasted strings. Providers appear, change models, and vanish without notice. Quality varies wildly: some models hallucinate, some refuse code, some truncate context. No single dashboard shows what works *today* for a given task. The user wants one local endpoint that picks the best available model for each request, keeps keys on the machine, and survives provider churn.

## 2. The first idea (planned, NOT built)

**Name:** Poolbrain  
**Architecture:** Two small trained "needle" models (classifier + ranker) + a 0.8 B parameter generative model for local fallback.  
**Status:** Never built.  
**Reason:** Required training compute, labelled data, and an explicit budget/approval cycle that did not exist. The project proceeded with zero training budget.

## 3. What was actually built instead (organs)

The system grew as a collection of independent, testable organs. Each organ solves one concrete sub-problem.

| Organ | Purpose | Key detail |
|-------|---------|------------|
| **Sensor** | Discovers keys in configured locations; validates each key against its provider (valid / invalid / rate‑limited). Live check for pasted tokens; nothing saved before user confirms. |
| **Catalogue** | Pulls model lists from every working provider. Unknown OpenAI‑compatible providers can be added by URL + token; a safety gate checks the address first. |
| **Probes** | Runs small machine‑checked tests per model: code, JSON, German, reasoning, long context, tool calling. A strong judge model (nemotron‑3‑ultra) scores free‑text German answers. |
| **Classifier** | Rule‑based request router → class (code, json, german, reason, long, tool). Measured 29/32 on shipped test set (3 known misses). |
| **Chooser** | Thompson sampling over Beta distributions with pessimistic shrinkage prior (PRIOR_K=6, prior mean 0.85·p₀). Mixes probe results with real traffic outcomes. NVIDIA preferred when quality equal. Confirmation probes for lucky candidates. |
| **Immune system** | Circuit breaker per model/provider, key cooldowns, model‑exact 429 handling, drift detection (several real failures → re‑probe). |
| **Planner** | Runs background scans only when the machine is not busy. |
| **Proxy** | OpenAI‑compatible `/v1/chat/completions`, `/v1/models` and Anthropic‑compatible `/v1/messages` (+ `count_tokens`) on localhost. Per‑app keys `op-<app>-<hmac>`. Virtual model `omnipool-auto` routes by class. Built to the OpenAI and Anthropic wire formats and tested with the project's own test suite and a demo client. *Claude Code, Hermes and Grokbot have NOT been tested live against it.* |
| **Radar** | ~110 news feeds + 10 Hacker‑News searches every 2 h. Index of ~2600 free‑API entries (public‑apis list + hand‑curated). SQLite FTS5 full‑text search. Model re‑check every 3.4 days. Use‑case matching via strong model extraction + search + safety verdict. Reddit blocked on purpose. |
| **Safety** | Hardened fetch (HTTPS only, public IPs only, pinned IP, redirects re‑checked, size caps). URL verdicts (TLS, domain age via RDAP, shorteners, punycode, risky TLDs). Gate before any key travels to a NEW provider. Quarantine: every fetched file written to private folder, scanned by sandboxed worker (fresh network namespace if available, rlimits, empty environment, fail‑closed). Unclean files overwritten with zeros and deleted; popup informs user; no release button. |

## 4. How it was built

- **Human director** steering AI agents, not the reverse.
- **Free NVIDIA tokens** used for improvement loops (see §5).
- **Gates** every change must pass:
  1. Syntax check
  2. Unit + deep end‑to‑end tests (fake provider)
  3. Headless‑browser UI check
  4. Vision judge (A/B scoring on 6 tabs)
- **Design‑research team**: ten model "entities" assigned distinct personas (architect, UX, security, performance, etc.) to explore design space.
- **Five coding roles** that fuzz, attack, and patch each other's output:
  1. Generator
  2. Fuzzer
  3. Attacker (adversarial inputs)
  4. Patcher
  5. Verifier
- **Supervising agent** coordinates the loop, enforces gates, logs every round.

## 5. Measurements and failures

### Improvement loop (22 rounds, free NVIDIA tokens)

| Metric | Value |
|--------|-------|
| Rounds logged | 22 |
| Accepted | 11 |
| Rejected | 11 |
| Rejection reason: Syntax | 10 |
| Rejection reason: Gates | 1 |
| Rejection reason: keine Datei | 0 |
| Rejection reason: llm | 0 |
| Rejection reason: Größe | 0 |

- **Whole‑file rewrites** by models failed the syntax check **~85 % of the time** even with a repair call.
- **CSS and text edits** succeeded more often.
- **A/B vision judge** moved average score from **5.33 → 5.75** on six tabs (noisy, ±0.5 on a 10‑point scale).
- **Real defects caught by gates**:
  - `[object HTMLSpanElement]` rendered in model table.
  - 269 px horizontal overflow at 420 px viewport width.

### Ranking prior simulation

| Prior K | Prior mean | Lucky‑model selection probability |
|---------|------------|-----------------------------------|
| 2 (naive) | — | 15 % → 24 % (worse) |
| 6 (pessimistic) | 0.85·p₀ | Fixed (probability reduced to expected) |

### Test suite (release 1.2)

| Category | Passed |
|----------|--------|
| Unit, deep e2e (fake provider), radar, quarantine, UI rules | 57 / 57 |

### Quarantine test set

| Sample type | Result |
|-------------|--------|
| EICAR, reverse shell, miner, base64‑exec, key stealer, prompt injection, trojan source, ELF, zip | Blocked |
| Legitimate API client, markdown, install docs | Released |
| Quarantine folder after run | Empty |

### Radar first run

| Metric | Value |
|--------|-------|
| Feeds alive / total | 95 / 129 |
| Index entries | 2617 |
| News items fetched | 937 |
| Scanner false positives on real feeds (48 s) | 0 |

### Classifier accuracy

| Test set size | Correct | Known misses |
|---------------|---------|--------------|
| 32 | 29 | 3 |

### Invented‑Electron failure (research/ team run)

- Chief model invented an Electron/IPC architecture that does not exist in the codebase.
- Produced **0 valid tickets**.
- Archived as a failure.
- Fixed by feeding the synthesis step the actual technical reality (file tree, existing modules, build scripts).

### 85 % rewrite failure

- Whole‑file rewrites by coding models failed syntax gate ~85 % of attempts.
- Mitigation: restricted agents to diff‑style patches + mandatory repair call; CSS/text edits kept higher success rate.

## 6. Honest label

**API‑OMNI‑BRAIN is scripts + rules + bandit statistics + a strong external model as judge.**  
It is **not a trained model**. The planned "two needles + 0.8 B model" was never built (see §2). All routing, ranking, and quality decisions are deterministic code, statistical bandits, and an outside LLM (nemotron‑3‑ultra) used only as a scorer for probe answers. No weights are learned on the user's machine.
