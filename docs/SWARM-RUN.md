# Swarm run: 50 agents, 3 hours, measured

Second polish/bug-fix run (the first was the 3.5 h team run, see TEAM-RUN.md). This time every agent got a small harness of its own.

## Honest summary

- 50 agents = 50 identities (12 roles x 5 perspectives) running on **12 distinct NVIDIA models**. There are not 50 different models; the free NVIDIA catalogue offered 12 usable ones.
- 37 of 50 agents passed their fixed calibration cases and were allowed to edit; 13 stayed reviewer-only.
- 100 findings -> 40 tickets -> 80 peer votes (62 agree, 12 disagree, 6 unclear) -> 31 tickets survived -> 23 were built -> **14 passed every automatic gate, 9 failed** (the swarm rolled those back itself).
- A human-style review of the 14 kept diffs **reverted 7** and **ported 7**. The gates are structural (syntax, 57 unit tests, headless UI measurements); they cannot see semantics. Half of what passed them changed behaviour without fixing a defect.
- Only one cycle fitted into 3 hours: calibration (18 min), findings (17 min), voting (17 min), then about one built ticket per 5 minutes.
- Measured before/after: tests 57/57 both times, console errors 0, overflow 0, blank tabs 0, German strings 0, unused imports 0, nav buttons 10, **contrast failures 4 -> 4 (no change)**. The run did not improve any measured UI metric; the ported changes are small code-hygiene and accessibility fixes.

## What each agent had (mini harness, `tools/minih.py`)

Built on the ideas of [smallH](https://github.com/gschaidergabriel/smallH) (MIT). smallH itself only implements the identity registry (`clay/identitaet.py`, used unchanged); the rest is a minimal own implementation of its design.

| organ | what it does here |
|---|---|
| identity | a `clay_` id (FORK of the run's ORIGIN), checked with `darf_pulsen()` before every pulse |
| mini DB | one SQLite file per agent: `lesson`, `episode`, `calib` |
| retrieval | top lessons by token overlap x weight go into the next prompt (relevance, not truth) |
| evidence guard | a finding only counts if its quoted evidence occurs verbatim in the real file |
| learning | every rejected patch / failed guard / failed gate becomes a lesson; lessons decay (0.97 per pulse), get boosted when the next attempt that used them works, pruned below 0.05 |
| calibration | 2 fixed cases per agent; failing agents lose their edit right (reviewer-only) |

Result of the learning part, honestly: 21 shared lessons at the end (`research/swarm/lessons_shared.json`). The strongest ones are all format errors the agents repeated: copy anchors exactly, answer only the JSON array, never paraphrase a quote. Episodes: 44 ok, 52 failed. There is no evidence in this run that the lessons raised the success rate; one cycle is too short to measure that.

## Pipeline

baseline measure -> calibration -> findings with verbatim quote (guard) -> dedupe to <= 40 tickets -> 2 peer votes by agents on other models -> patch builder (up to 3 tries with feedback) -> diff review by another model -> gates under a lock (apply, syntax, pytest with 3 retries, headless UI measure; roll back if any metric gets worse) -> lessons.

Run on a copy of the project, never on the live install. Files the swarm may not touch: `sicher.py`, `quarantaene.py`, `anbieter.py`, `__main__.py`, `vendor/`.

## Ported (7)

| ticket | file | change |
|---|---|---|
| c0-003 | gehirn.py | circuit-breaker entries are pruned when they expire |
| c0-005 | scan.py | NUL-byte check covers the whole file, not only the first 8 KB |
| c0-007 | ui_radar.js | sandbox preview only sliced when it is a string |
| c0-012 | ui_radar.js | verdict chip handles a verdict without `urteil` |
| c0-014 | ui.css | `--target-width` default moved to `.bar` (neutral) |
| c0-017 | ui.css | visible focus ring for every focusable element |
| c0-018 | server.py | an error while building the Security organ is shown instead of swallowed |

## Reverted (7), with the reason

| ticket | why |
|---|---|
| c0-008 | hides the "Open" link for caution/unchecked results: UX change, not a bug fix |
| c0-011 | `chat()` returned error text as body; callers treat the body as model answer |
| c0-019 | key cool-down only re-armed on a new model: loosens rate-limit protection |
| c0-021 | removed the ranking penalty for fallback-class models |
| c0-027 | adds an unused constant (and from a CSS agent in `scan.py`) |
| c0-031 | tool arguments `""` used to give `{}`, now raises |
| c0-032 | raises when vault lists differ in length: aborts the whole key scan, no defect shown |

## Limits to know

- Shared NVIDIA capacity (another team ran at the same time), so parallelism was capped at 6.
- Gates cannot judge intent. A patch that removed a valid call passed all gates in the smoke test; this is why cross-file checks were added and why every diff was reviewed by hand.
- Data: `research/swarm/` holds the board log, summary, shared lessons and the review notes. The per-agent mini DBs are not published.
