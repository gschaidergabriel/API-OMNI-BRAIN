#!/usr/bin/env python3
"""Compact state of the team program for the supervising agent (target: <= 1500 characters, so a check costs few tokens). usage: aufseher_digest.py [--min 30]"""
import collections
import json
import os
import subprocess
import sys
import time

TEAM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "team")
now, win = time.time(), 60 * (int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 30)
rows = []
try:
    for ln in open(os.path.join(TEAM, "log.jsonl")):
        try:
            rows.append(json.loads(ln))
        except ValueError:
            pass
except OSError:
    pass
rec = [r for r in rows if now - r["t"] < win]
alive = subprocess.run("ps -eo args | grep -c '[p]ython3 tools/team.py'", shell=True, capture_output=True, text=True).stdout.strip()
try:
    st = json.load(open(os.path.join(TEAM, "STATUS.json")))
except (OSError, ValueError):
    st = {}
out = ["LEBT=%s phase=%s stand=%s ticket=%s score=%s letzte_aktivitaet=vor %dmin%s" % ("ja" if alive != "0" else "NEIN", st.get("phase"), json.dumps(st.get("stand")), st.get("ticket"), st.get("score"),
       (now - rows[-1]["t"]) / 60 if rows else -1, "  STILLSTAND?" if rows and now - rows[-1]["t"] > 900 and alive != "0" else "")]
out.append("Log %dmin: %s" % (win // 60, dict(collections.Counter(r.get("art") for r in rec))))
sc = [(r.get("ticket"), r.get("score"), r.get("ref")) for r in rows if r.get("art") == "sieger"][-5:]
if sc:
    out.append("Sieger(ticket,score,ref): %s" % sc)
bad = collections.Counter((r.get("info") or "")[:40] for r in rec if r.get("art") == "kandidat" and not r.get("ok"))
if bad:
    out.append("Kandidaten-Fehlgruende: %s" % dict(bad.most_common(4)))
for r in [r for r in rec if r.get("art") in ("runde_code", "fehler", "zerleger", "tester", "intelligenz", "pruefer")][-5:]:
    out.append("%s: %s" % (r.get("art"), {k: v for k, v in r.items() if k not in ("t", "art")}))
q = {n: len(json.load(open(os.path.join(TEAM, n)))) for n in ("tickets.json", "bugs.json") if os.path.exists(os.path.join(TEAM, n))}
out.append("Postfach: %s  Entitaeten-Berichte: %d/10" % (q or "leer", len(os.listdir(os.path.join(TEAM, "briefs"))) if os.path.isdir(os.path.join(TEAM, "briefs")) else 0))
print("\n".join(out)[:1700])
