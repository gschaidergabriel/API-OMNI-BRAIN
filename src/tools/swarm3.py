#!/usr/bin/env python3
"""swarm3.py - 50 NVIDIA agents polish and bug-fix API-OMNI-BRAIN in a COPY of the tree. They measure first, discuss, vote, patch, get reviewed by
a different model, and every change passes objective gates; failures become lessons in each agent's mini DB (minih.py, smallH-inspired).

  measure -> findings (quote must occur verbatim: evidence guard) -> 2 peer votes (other models) -> patch (SEARCH/REPLACE, 3 tries with feedback)
  -> diff review by a third model -> gates (syntax, pytest, headless UI structure: nav buttons, console errors, contrast, overflow, blank tabs,
  German leftovers, unused imports; no metric may get worse) -> keep or roll back.   Free NVIDIA models only, one Chrome at a time, max 6 calls at once.
usage: swarm3.py [--hours 3] [--agents 50] [--parallel 6] [--smoke]"""
import argparse
import ast
import concurrent.futures as cf
import difflib
import json
import os
import random
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cdp  # noqa: E402
import demo  # noqa: E402
import minih  # noqa: E402
import team_lib as L  # noqa: E402
import team_patch as tp  # noqa: E402
from team_lib import it  # noqa: E402

RUN = os.path.join(ROOT, "swarm")
os.makedirs(RUN, exist_ok=True)
EDIT = ("ui.css", "ui.js", "ui_radar.js", "ui_manual.js", "texte.json", "ui.html", "manual.json", "gehirn.py", "server.py", "core.py", "scan.py", "radar.py")
# human-only: sicher.py quarantaene.py anbieter.py __main__.py vendor/ (hardening + installer: no autonomous edits)
ROLES = [
    ("backend-bugs", "server.py core.py", "real bugs in the daemon: crash, wrong status code, race, unhandled input, resource leak, bad JSON handling"),
    ("router", "gehirn.py server.py", "routing, classification and chooser logic: wrong class, bad probability maths, unfair fallback, stuck circuit breaker"),
    ("scanner", "scan.py", "scanner regex errors, false negatives/positives; NEVER propose loosening a rule"),
    ("radar", "radar.py", "feed/index/FTS/scheduler bugs, unsafe fetch handling, time or ordering bugs"),
    ("ui-js", "ui.js", "JS bugs: unhandled promise, wrong state, null access, stale render, innerHTML with data, wrong labels"),
    ("ui-radar", "ui_radar.js", "JS bugs in the radar/search/use-case tabs: same list as ui-js"),
    ("ui-css", "ui.css", "CSS defects: duplicated or dead rules, text contrast below 4.5:1, overflow, missing :focus-visible, broken responsive rules"),
    ("a11y", "ui.js ui.css ui.html", "accessibility: labels, roles, keyboard path, focus, aria-live, contrast, prefers-reduced-motion"),
    ("copy-en", "ui.js texte.json ui_radar.js", "English UI copy: remaining German, inconsistent terms, jargon a beginner cannot parse, claims that are not true"),
    ("manual-truth", "manual.json ui.js", "every sentence of manual.json must be TRUE for the real UI/server; find false, missing or outdated claims"),
    ("onboarding", "ui.js ui.html", "first run: empty states, next-step clarity, beginner not overwhelmed, professional not patronised"),
    ("tests", "server.py core.py gehirn.py", "kind=test only: a missing pytest that would catch a real bug (propose the test idea, not a fix)"),
]
PERSP = ["adversarial fuzzer", "maintainer who must live with this code", "complete beginner", "security reviewer", "performance and reliability engineer"]
GERMAN = re.compile(r"[äöüÄÖÜß]|\b(und|nicht|oder|wird|bitte|keine?n?|für|ist ein|mit dem)\b")
LOCK, GATE = threading.Lock(), threading.Lock()
BOARD = os.path.join(RUN, "board.jsonl")
CALL = {}


def post(ev, **kw):
    with LOCK:
        open(BOARD, "a").write(json.dumps({"t": round(time.time()), "kind": ev, **kw}, ensure_ascii=False) + "\n")


def safe(fn, default):
    def run(*a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            post("error", where=getattr(fn, "__name__", "fn"), err="%s: %s" % (type(e).__name__, str(e)[:160]))
            return default
    return run


def held():
    while os.path.exists(os.path.join(RUN, "HOLD")) and not os.path.exists(os.path.join(RUN, "STOP")):
        time.sleep(20)
    return os.path.exists(os.path.join(RUN, "STOP"))


# ------------------------------------------------------------------ models
def models():
    base = list(L.pool())
    extra = ["nvidia/mistralai/mistral-large-4-1t-a52b", "nvidia/nvidia/nemotron-3-ultra-550b-a55b", "nvidia/moonshotai/kimi-k3.1-pro", "nvidia/stepfun-ai/step-5-preview",
             "nvidia/z-ai/glm-5.3-flash", "nvidia/google/gemma-4-31b-it", "nvidia/meta/muse-glimmer-30b"]
    return base + [m for m in extra if m not in base]


def ask(agent, prompt, mx=4000, timeout=300, avoid=()):
    """own model first, then the best-scoring others (running success rate); the answering model is recorded"""
    ms = [agent.model] + sorted((m for m in ALL if m != agent.model and m not in avoid), key=lambda m: -(CALL.get(m, [1, 2])[0] / CALL.get(m, [1, 2])[1]))[:2]
    for m in ms:
        text, used = None, None
        try:
            t, _route = it.llm(m, [{"role": "user", "content": prompt}], mx, timeout)
            if t and t.strip():
                text, used = t, m
        except Exception as e:  # noqa: BLE001
            post("llm_error", model=m, err=type(e).__name__)
        s = CALL.setdefault(m, [1, 2])
        s[1] += 1
        if text:
            s[0] += 1
            return text, used
    return None, None


# ------------------------------------------------------------------ measuring
CONTRAST = """(()=>{const L=c=>{const m=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*m[0]+.7152*m[1]+.0722*m[2]};
const bg=e=>{while(e){const c=getComputedStyle(e).backgroundColor,m=c.match(/[\\d.]+/g);if(m&&(m.length<4||+m[3]>.5))return c;e=e.parentElement}return 'rgb(10,10,12)'};
let bad=0,n=0;for(const e of document.querySelectorAll('#main *,header *,nav *')){if(![...e.childNodes].some(x=>x.nodeType==3&&x.textContent.trim()))continue;const s=getComputedStyle(e);
if(s.visibility==='hidden'||s.display==='none'||+s.opacity===0||s.webkitTextFillColor==='rgba(0, 0, 0, 0)'||s.color==='rgba(0, 0, 0, 0)')continue;
const a=L(s.color),b=L(bg(e)),r=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);n++;if(r<4.5)bad++}return [bad,n]})()"""


def unused_imports(src):
    try:
        t = ast.parse(src)
    except SyntaxError:
        return 0
    names = {(a.asname or a.name).split(".")[0] for n in ast.walk(t) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    used = {n.id for n in ast.walk(t) if isinstance(n, ast.Name)} | {n.value.id for n in ast.walk(t) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    return len(names - used - {"*"})


def measure(port):
    m = {"nav": 0, "errors": 0, "overflow": 0, "contrast_bad": 0, "blank_tabs": 0, "tabs": {}}
    c = cdp.Chrome(1280, 860)
    try:
        c.goto("http://127.0.0.1:%d/" % port, 3.0)
        m["nav"] = c.js("[...document.querySelectorAll('nav button')].filter(b=>b.offsetHeight>0).length") or 0
        for i in range(int(m["nav"])):
            c.js("document.querySelectorAll('nav button')[%d].click()" % i)
            time.sleep(1.0)
            ln = c.js("document.querySelector('#main').innerText.length") or 0
            bad, n = c.js(CONTRAST) or [0, 0]
            m["tabs"][i] = ln
            m["blank_tabs"] += ln < 40
            m["contrast_bad"] += bad
            m["overflow"] += bool(c.js("document.documentElement.scrollWidth>window.innerWidth+2"))
        m["errors"] = len(c.errors)
    finally:
        c.close()
    ui = "\n".join(it.rd(n) for n in ("ui.js", "ui_radar.js", "ui_manual.js", "texte.json", "manual.json", "ui.html"))
    m["german"] = sum(1 for s in re.findall(r'"([^"\n]{6,})"', ui) if GERMAN.search(s))
    m["unused_imports"] = sum(unused_imports(it.rd(n)) for n in EDIT if n.endswith(".py"))
    for _try in range(3):                                   # one test is timing-sensitive under load: retry before calling it a regression
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-rf", "tests"], cwd=ROOT, capture_output=True, text=True, timeout=300)
        ok = r.returncode == 0
        if ok:
            break
        post("test_retry", n=_try, fail=[ln for ln in r.stdout.splitlines() if ln.startswith("FAILED")][:2])
    m["tests_ok"] = ok
    m["tests_tail"] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    return m


WORSE = ("errors", "overflow", "contrast_bad", "blank_tabs", "german", "unused_imports")


def regressions(base, now):
    r = [k for k in WORSE if now[k] > base[k]]
    if now["nav"] < base["nav"]:
        r.append("nav")
    if not now["tests_ok"]:
        r.append("tests")
    return r


# ------------------------------------------------------------------ agents
CAL = [("anchor", "In this text change the number 1 to 2 and answer ONLY with one SEARCH/REPLACE block in the format "
        "<<<<<<< SEARCH file=x.py\\n(old lines)\\n=======\\n(new lines)\\n>>>>>>> REPLACE\\n\\nTEXT:\\nalpha = 10\\nbeta = 1\\ngamma = 11\\n",
        lambda a: tp.apply({"x.py": "alpha = 10\nbeta = 1\ngamma = 11\n"}, tp.parse(a), ("x.py",), 2)[0]["x.py"] == "alpha = 10\nbeta = 2\ngamma = 11\n"),
       ("quote", "Quote verbatim, in one line and nothing else, the line of this text that defines the function 'sweep':\\n\\nimport os\\ndef sweep(path, depth=2):\\n    return os.listdir(path)\\n",
        lambda a: "def sweep(path, depth=2):" in a)]


def build_agents(n, tag):
    ms = models()
    reg = os.path.join(RUN, "register.db")
    origin = minih.new_origin(reg)
    ag = []
    for i in range(n):
        role = ROLES[i % len(ROLES)]
        a = minih.Mini(RUN, "a%02d-%s" % (i + 1, role[0]), role, ms[i % len(ms)], origin, reg)
        a.persp = PERSP[(i // len(ROLES)) % len(PERSP)]
        ag.append(a)
    return ag, ms


def calibrate(a):
    return a.calibrate([(cid, p.replace("\\n", "\n"), chk) for cid, p, chk in CAL], lambda p: (ask(a, p, 500, 200)[0] or ""))


def chunks(name, size=11000):
    lines, out, cur = it.rd(name).splitlines(), [], ""
    for ln in lines:
        if len(cur) + len(ln) > size and cur:
            out.append(cur)
            cur = ""
        cur += ln + "\n"
    return out + [cur] if cur else out


def context_for(a, cyc):
    parts, quotes = [], {}
    for f in a.role[1].split():
        cs = chunks(f)
        k = (int(a.name[1:3]) + cyc) % max(1, len(cs))
        parts.append("=== FILE %s (part %d of %d) ===\n%s" % (f, k + 1, len(cs), cs[k][:12000]))
        quotes[f] = cs[k]
    return "\n".join(parts), quotes


def findings(a, cyc, m):
    ctx, files = context_for(a, cyc)
    if not a.alive():
        return []
    lessons = a.recall(a.role[0] + " " + a.role[2])
    prompt = ("You are agent %s of a 50-agent swarm that polishes and bug-fixes API-OMNI-BRAIN (local free-API router, Python daemon + vanilla JS web UI). Perspective: %s. Focus: %s.\n"
              "MEASUREMENTS FIRST (do not contradict them): tabs=%s nav_buttons=%s contrast_failures=%s overflow_tabs=%s german_strings=%s unused_imports=%s tests=%s.\n"
              "Your past lessons (relevance, not truth):\n%s\n\n%s\n\n"
              "Find up to 4 REAL defects in the part shown. Rules: every finding needs a verbatim QUOTE of >=1 full line copied from the file text above WITHOUT any prefix; "
              "findings whose quote does not occur verbatim are thrown away and counted against you. No style nitpicks, no rewrites, nothing that loosens security. Say how it can be measured. "
              "Answer ONLY JSON: [{\"file\":\"...\",\"quote\":\"...\",\"claim\":\"what is wrong, 1-2 sentences\",\"severity\":1-5,\"kind\":\"bug|polish|test\",\"fix_idea\":\"...\",\"measure\":\"how to check it\"}]"
              % (a.name, a.persp, a.role[2], m["tabs"] and len(m["tabs"]), m["nav"], m["contrast_bad"], m["overflow"], m["german"], m["unused_imports"], m["tests_tail"], lessons or "(none yet)", ctx))
    text, used = ask(a, prompt, 3500)
    fs = L.jsonblock(text) if text else None
    if not isinstance(fs, list):
        a.outcome(a.role[0], "findings", False, "no JSON")
        a.learn("format", "answer ONLY the JSON array, no prose, quotes copied exactly")
        return []
    ok, bad = a.guard(fs, files if len(files) else {})
    for b in bad:
        a.learn("guard", "a quote was not verbatim in %s: never paraphrase, copy the whole line" % b.get("file"))
    a.outcome(a.role[0], "findings %d ok %d bad" % (len(ok), len(bad)), bool(ok), "model " + str(used))
    for f in ok:
        f["agent"], f["model"] = a.name, used
        f["kind"] = f.get("kind") if f.get("kind") in ("bug", "polish", "test") else "bug"
        if a.role[0] != "tests" and f["kind"] == "test":
            f["kind"] = "bug"
        post("finding", agent=f["agent"], model=f["model"], file=f.get("file"), claim=f.get("claim"), severity=f.get("severity"), tkind=f["kind"])
    return ok


def xref(text, files):
    """cross-check names a claim talks about against ALL files (a claim 'X is not defined' often only saw one chunk)"""
    out = []
    for name in sorted(set(re.findall(r"\b([A-Za-z_]\w{2,})\s*\(", text or "")))[:8]:
        pat = re.compile(r"(function\s+%s\b|def\s+%s\b|(?:const|let|var)\s+%s\s*=|\b%s\s*[:=]\s*(?:async\s*)?(?:function|\())" % ((re.escape(name),) * 4))
        for fn, src in files.items():
            m = pat.search(src)
            if m:
                out.append("%s is defined in %s line %d" % (name, fn, src.count("\n", 0, m.start()) + 1))
                break
    return "CROSS-CHECK over all files: " + ("; ".join(out) if out else "no definitions found for the called names")


def vote(f, reviewers, files_now):
    src = files_now.get(f["file"], "")
    i = src.find(f["quote"].strip().splitlines()[0]) if f.get("quote") else -1
    ex = src[max(0, i - 700): i + 1100] if i >= 0 else ""
    votes = []
    for r in reviewers:
        p = ("You are agent %s, reviewer. Another agent claims a defect in API-OMNI-BRAIN. Decide from the code, not from trust.\nFILE %s excerpt:\n%s\n\nCLAIM: %s\nQUOTE: %s\nFIX IDEA: %s\n"
             "%s\nIs the claim TRUE, does the fix idea not weaken security or break behaviour, and is it worth a patch? Answer ONLY JSON {\"vote\":\"agree|disagree|unclear\",\"reason\":\"1-2 sentences naming the code\"}"
             % (r.name, f["file"], ex, f.get("claim"), f.get("quote"), f.get("fix_idea"), xref(f.get("claim", "") + " " + f.get("quote", ""), files_now)))
        text, used = ask(r, p, 600, 240, avoid=(f.get("model"),))
        j = L.jsonblock(text) if text else None
        v = (j or {}).get("vote") if isinstance(j, dict) else None
        votes.append(v if v in ("agree", "disagree", "unclear") else "unclear")
        post("vote", ticket=f.get("id"), by=r.name, model=used, vote=votes[-1], reason=str((j or {}).get("reason"))[:200] if isinstance(j, dict) else "")
    return votes


def excerpt(f, files):
    src = files[f["file"]]
    q = f["quote"].strip().splitlines()[0].strip()
    i = src.find(q)
    if i < 0:
        return None
    a, b = src.rfind("\n", 0, max(0, i - 1800)) + 1, src.find("\n", min(len(src), i + 2200))
    return src[a: b if b > 0 else len(src)]


def close_hint(old_first, src):
    cands = difflib.get_close_matches(old_first.strip(), [ln.strip() for ln in src.splitlines()], 1, 0.6)
    return cands[0] if cands else ""


def build(f, builder, reviewers, base, state):
    """returns True when the change is kept"""
    tid = f["id"]
    if f["kind"] == "test":
        return build_test(f, builder, state)
    feedback = ""
    for att in range(3):
        files = L.read_all(EDIT)
        ex = excerpt(f, files)
        if not ex:
            post("drop", ticket=tid, why="quote no longer present (changed by another ticket)")
            return False
        lessons = builder.recall(f.get("claim", "") + " " + f["file"])
        p = ("You are agent %s. Fix ONE defect in %s with the smallest possible change. Lessons from your own past failures:\n%s\n\nDEFECT: %s\nFIX IDEA: %s\n\nFILE EXCERPT (exact text, copy anchors from here):\n%s\n\n"
             "Answer with SEARCH/REPLACE blocks only (max 3), format:\n<<<<<<< SEARCH file=%s\n(old text copied EXACTLY, unique in the file, 3+ lines of context)\n=======\n(new text)\n>>>>>>> REPLACE\n"
             "No prose. Do not weaken validation, scanner rules or security checks.%s"
             % (builder.name, f["file"], lessons or "(none)", f.get("claim", "") + "\n" + xref(f.get("claim", "") + " " + f.get("quote", ""), files), f.get("fix_idea"), ex, f["file"], feedback))
        text, used = ask(builder, p, 3500, 300)
        patches = tp.parse(text or "")
        new, bad = tp.apply(files, patches, EDIT, 3)
        if bad:
            hint = close_hint(patches[0][1].splitlines()[0], files.get(patches[0][0], "")) if patches and patches[0][1].strip() else ""
            builder.learn("patch-anchor", "SEARCH text must be copied exactly (indent, quotes) and occur once: %s" % bad[0][:120])
            builder.outcome(tid, "patch try %d" % att, False, bad[0])
            feedback = "\n\nYour last answer was rejected: %s. %s" % (bad[0][:200], ("Closest real line: " + hint) if hint else "")
            continue
        ch = tp.changed(files, new)
        syn = [L.syntax(n, new[n]) for n in ch]
        if any(not ok for ok, _w in syn):
            why = next(w for ok, w in syn if not ok)
            builder.learn("syntax", "your patch broke syntax: %s" % why[:150])
            builder.outcome(tid, "syntax", False, why)
            feedback = "\n\nYour patch produced a syntax error: %s" % why[:200]
            continue
        diff = "".join(difflib.unified_diff(*[files[n].splitlines(True) for n in ch[:1]] + [new[n].splitlines(True) for n in ch[:1]], "a/" + ch[0], "b/" + ch[0], n=3))[:4500]
        rv_votes = []
        for r in reviewers[:1]:
            rp = ("You are agent %s, code reviewer. DEFECT claimed: %s\nDIFF:\n%s\n\nDoes the diff fix the defect, avoid new bugs, and avoid loosening any rule or security check? "
                  "%s\nAnswer ONLY JSON {\"ok\":true|false,\"reason\":\"short\"}" % (r.name, f.get("claim"), diff, xref(diff, files)))
            t2, u2 = ask(r, rp, 500, 240, avoid=(used,))
            j = L.jsonblock(t2) if t2 else None
            rv_votes.append(bool(isinstance(j, dict) and j.get("ok")))
            post("review", ticket=tid, by=r.name, model=u2, ok=rv_votes[-1], reason=str((j or {}).get("reason"))[:200] if isinstance(j, dict) else "")
        if not all(rv_votes):
            builder.learn("review", "reviewer rejected the diff for: %s" % str(j.get("reason") if isinstance(j, dict) else "no verdict")[:150])
            builder.outcome(tid, "review", False, "rejected")
            feedback = "\n\nA reviewer rejected your diff: %s" % (j.get("reason") if isinstance(j, dict) else "")
            continue
        with GATE:
            cur = L.read_all(EDIT)
            new2, bad2 = tp.apply(cur, patches, EDIT, 3)
            if bad2:
                continue
            L.write_all(new2, only=ch)
            if any(n.endswith(".py") for n in ch):
                state["d"].stop()
                state["d"] = demo.start()[0]
            now = measure(state["d"].port)
            reg = regressions(base, now)
            if reg:
                L.write_all(cur, only=ch)
                if any(n.endswith(".py") for n in ch):
                    state["d"].stop()
                    state["d"] = demo.start()[0]
                builder.learn("gate", "a patch made %s worse; keep changes narrower and re-check %s" % (",".join(reg), f["file"]))
                builder.outcome(tid, "gate", False, "regressed " + ",".join(reg))
                post("rollback", ticket=tid, file=f["file"], why=reg)
                feedback = "\n\nYour patch was rolled back because it made these metrics worse: %s" % ",".join(reg)
                continue
            for k in WORSE:
                base[k] = min(base[k], now[k])
            base["nav"], base["tests_ok"] = max(base["nav"], now["nav"]), now["tests_ok"]
        builder.outcome(tid, "kept", True, f["file"])
        post("kept", ticket=tid, file=f["file"], agent=builder.name, model=used, metrics={k: now[k] for k in WORSE})
        return True
    post("failed", ticket=tid, file=f["file"], agent=builder.name)
    return False


def build_test(f, builder, state):
    files = L.read_all(EDIT)
    ex = excerpt(f, files) or ""
    p = ("You are agent %s. Write ONE small pytest file for API-OMNI-BRAIN that would catch this defect: %s\nIdea: %s\nCode excerpt (%s):\n%s\n\nExisting tests use the demo daemon in tests/; keep yours "
         "self-contained (import from omnipool, no network, no files outside tmp_path). Answer ONLY a python code block whose first line is `# FILE: tests/test_swarm_%s.py`."
         % (builder.name, f.get("claim"), f.get("fix_idea"), f["file"], ex, f["id"]))
    text, used = ask(builder, p, 2500, 300)
    m = re.search(r"```(?:python)?\s*\n# FILE: (tests/test_swarm_\w+\.py)\n(.*?)```", text or "", re.S)
    if not m:
        builder.learn("format", "tests: first line of the code block must be '# FILE: tests/test_swarm_<id>.py'")
        builder.outcome(f["id"], "test", False, "format")
        return False
    path = os.path.join(ROOT, m.group(1))
    with GATE:
        open(path, "w").write(m.group(2))
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", path], cwd=ROOT, capture_output=True, text=True, timeout=200)
        good = r.returncode == 0 and "passed" in r.stdout
        if not good:
            os.remove(path)
    builder.outcome(f["id"], "test", good, r.stdout[-150:])
    if not good:
        builder.learn("test", "your test did not pass on the CURRENT code: %s" % r.stdout[-120:].replace("\n", " "))
    post("kept" if good else "failed", ticket=f["id"], file=m.group(1), agent=builder.name, model=used)
    return good


# ------------------------------------------------------------------ run
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=3)
    ap.add_argument("--agents", type=int, default=50)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    global ALL
    deadline = time.time() + a.hours * 3600
    agents, ALL = build_agents(a.agents, "run")
    post("start", agents=len(agents), models=len(ALL), hours=a.hours)
    state = {"d": demo.start()[0]}
    base = measure(state["d"].port)
    post("baseline", **{k: v for k, v in base.items() if k != "tabs"})
    ex = cf.ThreadPoolExecutor(a.parallel)
    cyc = 0
    while time.time() < deadline - 900 and not held():
        post("cycle", n=cyc)
        cal = list(ex.map(safe(calibrate, (0, 1)), agents))
        post("calibration", passed=sum(1 for c in cal if c[0] == c[1]), of=len(cal))
        raw = []
        for fs in ex.map(safe(lambda ag: findings(ag, cyc, base), []), agents):
            raw += fs
        seen, tickets = set(), []
        for f in sorted(raw, key=lambda x: -int(x.get("severity") or 1)):
            k = (f["file"], re.sub(r"\s+", " ", f["quote"])[:80])
            if k not in seen:
                seen.add(k)
                f["id"] = "c%d-%03d" % (cyc, len(tickets) + 1)
                tickets.append(f)
        tickets = tickets[:(6 if a.smoke else 40)]
        files_now = L.read_all(EDIT)
        post("tickets", n=len(tickets), raw=len(raw))
        rng = random.Random(cyc)

        def vote_job(f):
            pool = [x for x in agents if x.model != f["model"] and x.name != f["agent"]]
            return f, vote(f, rng.sample(pool, 2) if len(pool) >= 2 else pool, files_now)
        keep = [f for f, v in ex.map(safe(vote_job, (None, [])), tickets) if f and v.count("agree") >= 1 and v.count("disagree") == 0]
        post("voted", kept=len(keep), of=len(tickets))
        for f in keep:
            if time.time() > deadline - 600 or held():
                break
            same = [x for x in agents if x.role[0] == ("tests" if f["kind"] == "test" else x.role[0]) and x.can_edit and x.alive()]
            fits = [x for x in same if f["file"] in x.role[1].split()] or [x for x in agents if x.can_edit] or agents
            builder = rng.choice(fits)
            reviewers = [x for x in agents if x.model != builder.model and x.name != builder.name]
            safe(build, False)(f, builder, rng.sample(reviewers, min(2, len(reviewers))), base, state)
            L.status(swarm=cyc, ticket=f["id"])
        cyc += 1
        if a.smoke:
            break
    final = measure(state["d"].port)
    state["d"].stop()
    n = minih.merge_shared(RUN, agents)
    post("end", **{k: v for k, v in final.items() if k != "tabs"}, lessons=n)
    stats = sorted((x.stats() for x in agents), key=lambda s: -s["ok"])
    json.dump({"baseline": base, "final": final, "agents": stats, "models": {m: CALL[m] for m in CALL}}, open(os.path.join(RUN, "summary.json"), "w"), indent=1, default=str)
    print("done", len(agents), "agents,", n, "lessons")


if __name__ == "__main__":
    main()
