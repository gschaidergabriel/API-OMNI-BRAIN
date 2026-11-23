# 04-web-competition (Web Researcher: Competition)
Model: nvidia/minimaxai/minimax-m3.1-flash

**Note on Data Availability:** No retrievable sources or excerpts are available. The assessment is based on my knowledge of comparable tools (LM Studio, Ollama, Jan, OpenRouter, LiteLLM, Continue/Aider) and is to be validated as a hypothesis, not as a verified competitive analysis.

## 1) Key Findings

1. **One Goal, One Button.** LM Studio, Ollama, and Jan feel immediately usable because exactly one primary action is visible; OpenRouter and Open WebUI overwhelm with tables, columns, and filters. Omnipool needs exactly one primary action on "Overview": *Start Free AI*.
2. **Trust comes from Clarity, not Data Volume.** LiteLLM and OpenRouter show status, latency, cost — valuable for pros, but overwhelming as a default. One core statement in plain text plus details on demand combines both.
3. **Setup may Guide, not Condemn.** Assistant flows help novices; Claude-Code/Aider users expect copy-paste configuration. Two equivalent paths (guided/direct) beat a forced wizard.
4. **Connection is the actual Product.** Users think in endpoints, not models. A visible "Connect" matrix (App ↔ Base-URL ↔ Key) is stronger than any model leaderboard.
5. **Radar is only valuable if Event-Driven.** News feeds create reading load. Relevant is: *new free key found → tested → available*.

## 2) Concrete Rules (HTML/CSS/JS, no Frameworks)

1. **Overview:** one primary action + three status tiles (Keys, Models, Connections) with plain-text status and "Fix Problem" link.
2. **Toggle "Simple | Technical"** (localStorage), which only changes density and detail depth, never functions.
3. **Tabs Lazy Load:** Load data only on open; `<details>` for raw data; placeholders instead of permanent spinners.
4. **Status in Plain Text** ("1 key works, 1 is faster for code"); HTTP codes, model IDs, JSON only in details.
5. **Empty States are Actions:** "Add Key", "Find Provider", "Test Automatically".
6. **Routing Preview:** Top 3 with reasoning, manual pinning possible; every switch generates a visible entry in "Events".
7. **Connect Page:** ready-to-use configuration blocks (env, Base-URL, Key) copyable by click; success confirmed via status line.
8. **No Modals on Start**; keyboard operable, visible focus rings, SSE/fetch interval with backoff.

## 3) What NOT to do

- No forced onboarding wizard, no mandatory account, no telemetry prompts in the start flow.
- No nine equivalent tabs on the homepage, no endless feeds.
- No silent key switches or deletions; never claim "free" without verification timestamp.
- No artificial urgency ("only 2 keys left!"), no paid recommendation in the middle of a task.
- No blockade without network: local data must continue to function offline.
