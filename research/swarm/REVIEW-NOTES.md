# Gabriel-side diff review (Claude), mid-run 21:15
- c0-003 gehirn.frei prune: OK (same semantics + cleanup)
- c0-005 scan.py NUL check whole data: OK (stricter, no loosening)
- c0-007 ui_radar vorschau typeof guard: OK
- c0-008 ui_radar "Open" only for unauffaellig/lokal: REVERT (hides Open for caution/ungeprueft = behaviour/UX change, not a defect fix)
# review 21:40 (Claude)
- c0-011 core.chat URLError/JSONDecodeError -> (0, error text): REVERT. Contract was body "" on failure; server.py analyst() and radar.py would now get error text as "model answer". JSONDecodeError branch is dead (generic except already caught it). No defect fixed.
- c0-012 ui_radar verdict(): `!v || !v.urteil` guard: OK (also the vorschau typeof guard from c0-007).
- c0-006 and c0-010 failed in the gates (rolled back by the swarm itself).
# review 22:05 (Claude)
- c0-014 ui.css --target-width:0% moved from .bar i to .bar: neutral (inherited, same value). keep.
- c0-017 ui.css :focus-visible gets focus-ring for ALL focusables (before: only a list; links/tabs had outline:none and no ring) = a11y fix. keep, check with shots.py.
- c0-018 server.py bericht_voll: silent pass -> adds {"name":"Error","info":str(e)} organ. keep (visible instead of swallowed); str(e) is local-only UI.
- c0-019 gehirn.limit(): KEYCOOL now only when a NEW model 429s after an earlier one; old: re-armed on every 429 once 2 distinct models in 60 s. Loosens rate-limit protection, no defect fixed: REVERT.
- c0-021 gehirn.kandidaten: dropped the -0.15 penalty for fallback-class models = ranking change (intended preference removed): REVERT.
- c0-013, c0-020 failed in gates (self-rolled-back).
# review 22:30 (Claude)
- c0-027 scan.py: adds unused constant READ_LIMIT = MAX (nothing references it): REVERT (noise, from a ui-css agent in scan.py, off-role).
- c0-025, c0-026 failed in gates.
# review 22:58 (Claude) - run ended, 14 kept / 9 failed
- c0-031 server.py tool-call arguments: `json.loads(args) if args is not None else {}`: REVERT. args == "" used to give {} (via `or "{}"`), now raises JSONDecodeError. Regression.
- c0-032 core.scan_keys raises ValueError when len(vault_items) != len(vault_values): REVERT. No defect proven; a legitimate size difference would abort the whole key scan.
- FINAL: port 7 (c0-003, 005, 007, 012, 014, 017, 018); revert 7 (c0-008, 011, 019, 021, 027, 031, 032).
