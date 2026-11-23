#!/usr/bin/env python3
"""Team 3: five documentation roles with DYNAMIC model assignment (free NVIDIA tokens through the local proxy).
Roles: historian (origin + creation), essayist (why this is necessary), manual (manual text + manual.json), reviewer (fact-check against docs_src/facts.md), release (README).
Dynamic = per task two different models write a candidate, a third model judges them blind, the win statistics (team/models3.json) decide who is asked first next time.
Facts the authors may use: docs_src/facts.md + the measured data pack. Output goes to docs_out/ (the repo builder copies it).
usage: team3.py [all|origin|why|manual|readme|translate]"""
import json
import os
import random
import re
import subprocess
import sys
import time

import team_lib as L
from team_lib import it, log

ROOT = it.ROOT
OUT = os.path.join(ROOT, "docs_out")
STATS = os.path.join(ROOT, "team", "models3.json")
FACTS = open(os.path.join(ROOT, "docs_src", "facts.md")).read()
STYLE = ("Write in clear, plain, precise ENGLISH. Honest tone: say what works, what was measured, what failed. No hype, no marketing superlatives, no claims beyond the FACTS. "
         "Opinions are allowed only when labelled as the author's position. No emojis.")


def load():
    try:
        return json.load(open(STATS))
    except (OSError, ValueError):
        return {}


def choose(role, models, n=2):
    st = load().get(role, {})
    sc = {m: (st.get(m, [0, 0])[0] + 1.0) / (st.get(m, [0, 0])[1] + 2.0) + random.random() * 0.25 for m in models}
    return sorted(models, key=lambda m: -sc[m])[:n]


def record(role, win, lose):
    d = load()
    r = d.setdefault(role, {})
    for m, w in ((win, 1), (lose, 0)):
        a = r.setdefault(m, [0, 0])
        a[0] += w
        a[1] += 1
    json.dump(d, open(STATS, "w"), indent=1)


def duel(role, prompt, models, max_tokens=7000, check=None):
    """two different models write, a third judges blind; returns the winning text"""
    a, b = choose(role, models, 2)
    ta, ma = L.ask([a], prompt, max_tokens, 290)
    tb, mb = L.ask([b], prompt, max_tokens, 290)
    cands = [(t, m) for t, m in ((ta, ma), (tb, mb)) if t and (check is None or check(t))]
    if not cands:
        t, m = L.ask([x for x in models if x not in (a, b)], prompt, max_tokens, 290)
        return t, m
    if len(cands) == 1:
        return cands[0]
    judge = next((m for m in models if m not in (a, b)), models[0])
    j, _ = L.ask([judge], "Two candidate texts answer the same task. Judge ONLY quality: accuracy against the FACTS, honesty (no overclaiming), clarity, completeness. Answer with a single letter A or B and one short reason.\n"
                 "TASK:\n%s\n\nFACTS:\n%s\n\n=== A ===\n%s\n\n=== B ===\n%s" % (prompt[:1500], FACTS[:4000], cands[0][0][:6000], cands[1][0][:6000]), 300)
    win = 1 if re.match(r"\W*B\b", j or "") else 0
    record(role, cands[win][1], cands[1 - win][1])
    log(art="duell", rolle=role, sieger=cands[win][1], verlierer=cands[1 - win][1])
    return cands[win]


def review(text, what, models):
    """reviewer role: list claims not supported by FACTS, then the writer-model fixes them"""
    r, m = L.ask(choose("reviewer", models, 1), "You are a strict fact-checker. List every sentence in the TEXT that claims something not supported by the FACTS or overclaims (hype, guarantees, 'revolutionary', unsupported numbers). "
                 "Answer ONLY with a ```json list of {\"sentence\":\"\",\"problem\":\"\"}; empty list if none.\nFACTS:\n%s\n\nTEXT:\n%s" % (FACTS, text[:12000]), 3000)
    issues = L.jsonblock(r) if r else None
    log(art="review", was=what, modell=m, probleme=len(issues) if isinstance(issues, list) else None)
    if not issues:
        return text
    t, _ = L.ask(choose("release", models, 1), "Revise the TEXT: remove or soften every flagged sentence so that it matches the FACTS exactly; keep structure, headings and everything else. Output the complete revised text only.\n"
                 "FLAGGED:\n%s\n\nFACTS:\n%s\n\nTEXT:\n%s" % (json.dumps(issues, ensure_ascii=False)[:4000], FACTS, text), 8000)
    return t or text


def data_pack():
    """measured data of the build, sanitised (no paths, no keys)"""
    p = os.path.join(ROOT, "iter", "log.jsonl")
    rounds = [json.loads(x) for x in open(p) if x.strip()] if os.path.exists(p) else []
    acc = [r for r in rounds if r.get("art") == "runde" and r.get("ok")]
    rej = [r for r in rounds if r.get("art") == "runde" and not r.get("ok")]
    return "Improvement loop log (iter/log.jsonl): %d rounds logged, %d accepted, %d rejected; rejection reasons: %s" % (
        len(acc) + len(rej), len(acc), len(rej), json.dumps({k: sum(1 for r in rej if (r.get("grund") or "").startswith(k)) for k in ("Syntax", "Gates", "keine Datei", "llm", "Groesse")}))


def write(name, text):
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, name), "w").write(text.strip() + "\n")
    log(art="doku", datei=name, bytes=len(text))


def origin(models):
    prompt = (STYLE + "\nWrite docs/ORIGIN.md: how API-OMNI-BRAIN came to be and how it was built. Sections: 1. The problem (many free AI API tiers, keys scattered, models appear and vanish, quality unknown). "
              "2. The first idea (a 'Poolbrain': two small trained needles + a 0.8B model - planned, NOT built, and why: budget/approval) 3. What was actually built instead (organs, from FACTS) "
              "4. How it was built: a human directing AI agents; free NVIDIA tokens for improvement loops; gates (syntax, tests, headless-browser UI check, vision judge); a team of ten model 'entities' for design research; "
              "five coding roles that fuzz/attack/patch; a supervising agent. 5. Measurements and failures (use the FACTS and the DATA; include the invented-Electron failure and the 85 percent rewrite failure). "
              "6. Honest label: scripts + rules + statistics + external judge, not a trained model. Use tables where numbers appear.\nDATA:\n%s\n\nFACTS:\n%s" % (data_pack(), FACTS))
    t, m = duel("historian", prompt, models, 7000)
    write("ORIGIN.md", review(t, "ORIGIN", models))


def why(models):
    prompt = (STYLE + "\nWrite docs/WHY.md: why this is a necessary development. Thesis (label it as the author's position): AI access is being concentrated; large-scale data collection benefits when every user routes everything through one vendor, one account, one telemetry stream. "
              "A local, user-owned layer that (a) keeps keys on the user's machine, (b) measures quality itself instead of trusting claims, (c) can switch providers in seconds as free tiers appear and vanish, (d) sends nothing anywhere except the provider the user chose, "
              "is exactly what bulk data collection does not want and what users urgently need: independence, comparability, and the ability to leave. "
              "Structure: Position / What users lose without it / What this tool does about it (only from FACTS, concrete) / What it does NOT solve (be blunt: provider-side logging, free tiers ending, quality limits) / Responsible use. "
              "Argue calmly; no accusations against named companies; no conspiracy tone; separate evidence from opinion.\nFACTS:\n%s" % FACTS)
    t, m = duel("essayist", prompt, models, 6000)
    write("WHY.md", review(t, "WHY", models))


def manual(models):
    tabs = [("overview", "Overview", "the first screen: status chips, the next step, what each number means"), ("keys", "Keys & Providers", "paste a token, automatic recognition, live check, saving; adding an unknown provider by URL; the safety gate"),
            ("models", "Models", "the catalogue, classes (code, JSON, German, reasoning, long, tool), sorting, filters, status"), ("connect", "Connect", "connect Claude Code, Hermes, Crush, Aider or any OpenAI/Anthropic client; the app key; copy buttons; switch on/off"),
            ("settings", "Settings", "scan interval, preferences, priorities"), ("events", "Events", "what the event log shows"), ("radar", "Radar", "news, the safety popup, what 'quarantined' means"),
            ("search", "API Search", "searching the free-API index, safety verdicts"), ("usecases", "Use cases", "describe what you want to do, get matching free APIs")]
    prompt = (STYLE + "\nWrite the in-app MANUAL as JSON for this web app. Output ONE ```json object: {\"intro\":\"2-3 sentences\",\"sections\":[{\"id\":\"overview\",\"title\":\"\",\"summary\":\"1-2 sentences\",\"steps\":[\"short imperative steps\"],"
              "\"can\":[\"what this tab can do\"],\"cannot\":[\"what it cannot and must not do\"]}],\"global_cannot\":[\"things the whole app cannot do and does not want to do (8-12 items, from FACTS)\"],\"responsibility\":\"3-4 sentences: the user is responsible for use\"}. "
              "One section per tab, ids and order exactly: %s. Every tab must have at least 2 cannot-items. Never mention features that are not in FACTS.\nTAB NOTES:\n%s\n\nFACTS:\n%s" % (", ".join(t[0] for t in tabs), "\n".join("- %s (%s): %s" % t for t in tabs), FACTS))
    ok = lambda t: isinstance(L.jsonblock(t), dict) and len(L.jsonblock(t).get("sections", [])) >= 8                  # noqa: E731
    t, m = duel("manual", prompt, models, 9000, ok)
    j = L.jsonblock(t) if t else None
    if not isinstance(j, dict):
        raise SystemExit("manual: no valid JSON")
    for s in j.get("sections", []):
        s["image"] = s["id"] + ".png"
    os.makedirs(OUT, exist_ok=True)
    json.dump(j, open(os.path.join(OUT, "manual.json"), "w"), ensure_ascii=False, indent=1)
    log(art="doku", datei="manual.json", modell=m, sektionen=len(j["sections"]))


def readme(models):
    fig = subprocess.run(["figlet", "-f", "big", "-w", "78", "YOU ARE"], capture_output=True, text=True).stdout.rstrip() + "\n" + subprocess.run(["figlet", "-f", "big", "-w", "78", "RESPONSIBLE"], capture_output=True, text=True).stdout.rstrip()
    box = ("```text\n" + fig + "\n\n"
           "  ##########################################################################\n"
           "  #  THE RESPONSIBILITY FOR HOW THIS SOFTWARE IS USED LIES WITH *YOU*.     #\n"
           "  #                                                                        #\n"
           "  #  You choose the keys you add, the providers you call, the data you     #\n"
           "  #  send, the costs you cause, and you must follow each provider's        #\n"
           "  #  terms. The authors give NO warranty and accept NO liability.          #\n"
           "  #  Free tiers change or vanish. A scanner result is not a guarantee.     #\n"
           "  #  Do not use it to abuse services, evade limits, or process data you    #\n"
           "  #  are not allowed to process. This is not legal or security advice.     #\n"
           "  ##########################################################################\n```")
    prompt = (STYLE + "\nWrite README.md for the GitHub repository API-OMNI-BRAIN. Do NOT write the responsibility box (it is inserted by the tool at the marker line <<BOX>>; put the line <<BOX>> right after the one-paragraph introduction and again at the very end). "
              "Sections: title + tagline, one-paragraph introduction, <<BOX>>, What it is (and honestly what it is not: scripts + statistics, not a trained model), Install (the binary and the .pyz; no keys are shipped; commands are exactly: "
              "`chmod +x API-OMNI-BRAIN && ./API-OMNI-BRAIN` and `python3 API-OMNI-BRAIN.pyz --install`; install.sh at repo root does a checksum-verified install), First five minutes (5 numbered steps: open, paste a token, check, connect an app, watch the ranking), "
              "What it can do (bullets), What it cannot and does not want to do (bullets), Security model (short), Documentation links (docs/MANUAL.md, docs/ORIGIN.md, docs/WHY.md, docs/TESTING.md, research/), Requirements and known limits (glibc >= 2.38 for the binary, "
              "only tested on the listed systems), Naming note (internal package name `omnipool`, header X-Omnipool, env OMNIPOOL_* stay for compatibility), <<BOX>>.\nFACTS:\n%s" % FACTS)
    t, m = duel("release", prompt, models, 7000, lambda t: "<<BOX>>" in t)
    t = review(t, "README", models)
    t = t if "<<BOX>>" in t else t + "\n<<BOX>>\n"
    t = t.replace("<<BOX>>", box)
    write("README.md", t)


def translate(models):
    """the ten German design briefs and the archived failed design (research data) -> English"""
    od = os.path.join(OUT, "research", "design-briefs")
    os.makedirs(od, exist_ok=True)
    src = [os.path.join(ROOT, "team", "briefs", f) for f in sorted(os.listdir(os.path.join(ROOT, "team", "briefs")))] + [os.path.join(ROOT, "team", "DESIGN-v1-invented-electron.md")]
    for p in src:
        dst = os.path.join(od, os.path.basename(p))
        if os.path.exists(dst):
            continue
        t, m = L.ask(choose("translator", models, 2), "Translate this German research brief into English. Keep the Markdown structure and the technical terms; add nothing. Output the translation only.\n\n" + open(p).read()[:14000], 9000, 280)
        if t:
            open(dst, "w").write(t.strip() + "\n")
        log(art="doku", datei=os.path.basename(p), modell=m, ok=bool(t))


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    models = L.pool()
    for name, fn in (("origin", origin), ("why", why), ("manual", manual), ("readme", readme), ("translate", translate)):
        if what in ("all", name):
            fn(models)
            print("done", name, flush=True)


if __name__ == "__main__":
    main()
