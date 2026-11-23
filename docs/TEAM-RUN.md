# TEAM-RUN.md - what the free-model teams did, and what they broke

Run of 2026-11-23, 3.5 hours, free NVIDIA models through a local proxy (raw data: `team/log.jsonl`, `team/REPORT.md`, `team/AUFSEHER.md`).

## Numbers (from the log)
- UI design tournament: 24 rounds, 19 winners (vision-judge scores 6.67-7.33 on a 10 point scale; steps of 0.33, so noise is about one step).
- Code hardening rounds (fuzz, scanner attack, classifier, inbox): 11 rounds, **1 accepted**. 70 candidate patches were rejected, mostly because the free models quoted a `SEARCH` anchor that does not occur exactly once in the file.
- Reviewer (nemotron-3-ultra) rejected several patches rightly: one loosened the `zerstoerer`/`pipe_sh` scanner rules, one had a regex precedence error, one "fixed" a 500 by returning 400 without a real fix.
- Orchestration bug: the status writer tried to serialise a daemon object (11 `TypeError` log lines). Fixed afterwards.

## What the tournament broke (found by a human-style review of the result)
- **The tab bar disappeared.** A winning CSS patch changed `nav{display:flex}` to `nav{display:none}`. The automatic gates (syntax, tests, element count, vision judge) did not catch it, because the judge scored the visible page and never missed the navigation. Fixed by hand.
- Header got a fixed `height:40px` and lost the `h1` rule: logo and title overlapped the hero card. Fixed by hand.
- 20+ duplicated CSS rules and unused `.status-*` styles piled up (cleaned by an exact-duplicate pass).
- A rename leftover: designers wrote the old product name into hero text and a CSS `::before` string. Fixed by hand.
- Raw database values (`neu`, `fehler`, `keine_klasse`, `sicherheit`) were shown as badges; event icons showed a warning sign for every event because the code compared against a value that never occurs. Fixed by hand.

## Lessons (opinion, based on the above)
1. Free models are useful as a source of candidates and as reviewers, not as unsupervised committers. 1 of 11 code rounds landed.
2. A visual judge that only scores what it sees cannot notice what is missing. Gates need structural assertions (e.g. "nav has 9 visible buttons"). That assertion now exists in the manual-screenshot step and should move into the UI gate.
3. Every autonomous patch loop needs a human-readable diff review before release. This release got one.
