#!/usr/bin/env python3
"""Compare the trained capability sorter with the rule (anbieter.infer) on the real model ids in your catalogue; prints every disagreement so a human can judge who is right.
usage: sorter_vs_rule.py SORTER.NPZ NEEDLE.MODEL [omnipool.db]   (weights: GitHub release needles-v1; needs numpy)"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from omnipool.needle_rt import Needle  # noqa: E402

CL = "chat code vision embedding rerank audio image video safety ocr other".split()
TOOLS = json.dumps([{"name": "classify_model", "description": "capability of an API model id", "parameters": {"capability": {"type": "string", "description": "chat, code, vision, embedding, rerank, audio, image, video, safety, ocr or other", "required": True}}}])
ANS = {c: json.dumps([{"arguments": {"capability": c}, "name": "classify_model"}], separators=(",", ":"), sort_keys=True) for c in CL}
EN = {"bild": "image", "sicherheit": "safety", "suche": "other"}                        # the rule's German labels -> the sorter's labels


def main():
    npz, model = sys.argv[1], sys.argv[2]
    db = sys.argv[3] if len(sys.argv) > 3 else os.path.expanduser("~/.local/share/omnipool/omnipool.db")
    n = Needle(npz, model)
    rows = sqlite3.connect(db).execute("SELECT provider, model, faehigkeit FROM modell").fetchall()
    diff = []
    for p, m, f in rows:
        sc = n.score(m, TOOLS, ANS)
        s, r = max(sc, key=sc.get), EN.get(f, f)
        if s != r:
            diff.append((p, m, r, s))
    print("%d ids, agree on %d, differ on %d (rule vs sorter):" % (len(rows), len(rows) - len(diff), len(diff)))
    for p, m, r, s in diff:
        print("  %-10s %-55s rule=%-10s sorter=%s" % (p, m, r, s))
    print("Judge each difference yourself; the labels of the held-out set are teacher votes, not truth.")


if __name__ == "__main__":
    main()
