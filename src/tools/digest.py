#!/usr/bin/env python3
"""compact swarm digest: counts per event, kept/rollback list, model success rates, regressions"""
import collections, json, os, sys, time
R = os.path.expanduser("~/omnipool-swarm/swarm")
ev = [json.loads(l) for l in open(R + "/board.jsonl")]
c = collections.Counter(e["kind"] for e in ev)
print("events", dict(c), "age_min", round((time.time() - ev[0]["t"]) / 60))
for e in ev:
    if e["kind"] in ("kept", "rollback", "failed", "error", "calibration", "tickets", "voted", "cycle", "end"):
        print(time.strftime("%H:%M", time.localtime(e["t"])), e["kind"], {k: str(v)[:70] for k, v in e.items() if k not in ("t", "kind", "metrics")})
vs = collections.Counter(e.get("vote") for e in ev if e["kind"] == "vote")
print("votes", dict(vs), "llm_errors", c.get("llm_error", 0))
