# WHY.md - why this tool has to exist

**Read this first:** sections marked **[Position]** are the author's opinion and argument. Sections marked **[Fact]** can be checked in this repository (code, tests, `research/`). Opinion is not dressed up as fact.

## [Position] The problem is structural, not technical

Whoever sits between you and the model sees everything: every prompt, every correction, every half-finished thought, with your account, your timing and your habits attached. A single vendor, a single key and a single endpoint make that vantage point complete. Free tiers make it worse in a quiet way: they are free because the traffic is the product. Millions of people paying with their working questions is exactly what large-scale data collection wants, and exactly what a user cannot see from inside one vendor's app.

The author's argument: **choice is the only counterweight an individual user has.** If you can send the next request to a different provider in one click (or automatically), no single provider can treat your traffic as captive. Big data's business model needs the opposite: one funnel, one profile, no easy exit. A local, user-owned routing layer is the cheapest way to take that funnel apart. That is why this is a *necessary* development and not a convenience feature.

## [Position] Why it has to be local, and why it has to measure

- **Local:** a hosted router would just be another funnel. The daemon listens on `127.0.0.1` only, keeps keys in a local file and sends a request only to the provider the router chose for it.
- **Measuring:** "which free model is good today" cannot be answered by trusting a provider's marketing. The app probes models itself with machine-checked tests and keeps statistics from your own traffic. Rankings are measurements of today, not promises.
- **Spread:** because the router spreads requests over many providers by measured quality, no single provider sees the whole picture of what you do.

## [Fact] What the app does about it (verifiable in `src/`)

- Ships no keys (binary, zipapp and repository are scanned for key patterns before every publish, see `docs/TESTING.md`).
- Binds to `127.0.0.1`; UI and API calls need a header or a per-application key; each application key can be switched off.
- Probes models (code, JSON, German, reasoning, long text, tool calling), ranks them with Thompson sampling, keeps a per-model circuit breaker and key cooldowns.
- Adds unknown OpenAI-compatible providers only after a safety gate (URL verdict, no key sent before you confirm).
- Uses only free providers; paid providers and models are excluded in code.

## [Fact] What it does NOT solve

- **Provider-side logging.** The provider you route to still sees that prompt. Spreading reduces how much any one provider sees; it does not make a prompt private. Do not send what you must not disclose.
- **Free-tier instability.** Tiers change, throttle and vanish. Rankings can be stale within days.
- **Quality ceiling.** Free models are considerably weaker than frontier models. The judge model and the vision judge used during development are coarse (about plus/minus 0.5 on a 10 point scale).
- **Anonymity.** Your IP and your keys identify you to each provider. This is not an anonymity tool and does not try to be one.
- **Telemetry honesty.** The app itself sends no telemetry. An optional report to the author's own evaluation system exists in the settings and is only available on the author's machines.

## [Position] What we need instead

We need tools that make the user the router: local, inspectable, boring to audit, small enough to read in an afternoon, and honest about what they cannot do. This repository is one such attempt, with its design process, its failures (see `research/`) and its limits documented in the open.

## Responsible use

The responsibility for how this software is used lies with **you**. Use your own keys, follow each provider's terms, do not use it to evade limits or abuse services, and do not send data you are not allowed to send.
