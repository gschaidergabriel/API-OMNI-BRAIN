"""In-app assistant: a chat (German or English) about the pool, plus a small allowlist of tasks.
Local only. Nothing is stored. The model never sees a key, and read-only actions are answered from the local DB; anything that changes state is only
PROPOSED (the UI shows a button, the user clicks) and goes through the same endpoints as the normal buttons."""
import json
import re

from . import core, radar

SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{16,}|gsk_[A-Za-z0-9]{16,}|nvapi-[A-Za-z0-9_\-]{16,}|AIza[A-Za-z0-9_\-]{20,}|hf_[A-Za-z0-9]{20,}|op-[a-z0-9_]+-[0-9a-f]{16,}|Bearer\s+[A-Za-z0-9._\-]{20,}|\b(?=[A-Za-z0-9_\-]*[A-Z])(?=[A-Za-z0-9_\-]*\d)[A-Za-z0-9_\-]{40,}\b|\b[0-9a-f]{32,}\b)")
DE = re.compile(r"[äöüß]|\b(und|der|die|das|ich|nicht|wie|was|kann|bitte|zeig\w*|mach\w*|welche\w*|ist|sind|mein\w*|habe|hast|warum|wieso|wo)\b", re.I)
ACTION = re.compile(r"^\s*ACTION:\s*(\{.*\})\s*$", re.M)
READ = ("status", "best", "models", "find_api")                               # answered from the local DB, no click needed
PROPOSE = {"scan": ("lauf", {}), "stop_all": ("aus", {"aus": True}), "resume": ("aus", {"aus": False})}   # need the user's click
TABS = ("Overview", "Keys & Providers", "Models", "Connect", "Settings", "Events")
REFUSE = {"de": "Das sieht nach einem API-Schlüssel aus. Schlüssel gehören nicht in den Chat (er geht an ein Modell eines Anbieters). Trag ihn im Reiter 'Keys & Providers' ein.",
          "en": "That looks like an API key. Keys do not belong in the chat (it goes to a provider's model). Add it in the 'Keys & Providers' tab."}


def lang(text):
    return "de" if DE.search(text or "") else "en"


def lage(c, s):
    keys = c.execute("SELECT provider, status, COUNT(*) FROM key GROUP BY provider, status ORDER BY provider").fetchall()
    best = {k: "%s/%s" % r[0][:2] for k in core.KLASSEN for r in [core.rangfolge(c, k, None, 1)] if r}
    caps = c.execute("SELECT COALESCE(faehigkeit,'chat'), COUNT(*) FROM modell WHERE gone<3 GROUP BY 1").fetchall()
    apps = [a + (" (on)" if v.get("angemeldet") else " (off/pending)") for a, v in s["harness"].items()]
    return json.dumps({"emergency_stop": core.aus(), "keys": ["%s %s x%d" % k for k in keys], "models_by_capability": dict(caps), "best_per_class": best, "applications": apps}, ensure_ascii=False)


def handbuch():
    m = json.loads(core.res("manual.json"))
    return (m["intro"][:600] + "\n" + "\n".join("- %s: %s" % (x["title"], x["summary"][:420]) for x in m["sections"]))[:6000]


def system(c, s, la):
    return ("You are the assistant built into API-OMNI-BRAIN, a local program that tests free API keys and models, ranks them and routes requests of other programs to the best free model. "
            "Answer in the language of the user's last message (%s). Short and concrete. State only what LIVE STATE and MANUAL support; if you do not know, say so. "
            "Never ask for, repeat or guess API keys; to add a key point to the tab 'Keys & Providers'. You are a free model: weaker than a frontier model, say so when a task needs more.\n"
            "TASKS: when the user wants something done, end your reply with exactly one line: ACTION: {\"do\": NAME, \"args\": {...}} with NAME one of "
            "status (live overview), best (args {\"klasse\": code|json|de|reason|long|tool}), models (args {\"faehigkeit\": chat|code|vision|embedding|image|audio|video|ocr|rerank}), "
            "find_api (args {\"q\": short English search words}: look up free APIs in the local index), "
            "scan (scan keys and probe models now), stop_all (emergency stop), resume (undo the stop), open (args {\"tab\": one of %s}). "
            "You can do ONLY these tasks; for everything else in the MANUAL say where the user clicks. Never claim you can do more. Never invent other names.\nLIVE STATE: %s\nMANUAL:\n%s" % ("German" if la == "de" else "English", ", ".join(TABS), lage(c, s), handbuch()))


def lies(c, do, a):
    if do == "status":
        return lage(c, core.settings())
    if do == "best":
        k = a.get("klasse") if a.get("klasse") in core.KLASSEN else "reason"
        return json.dumps([{"model": "%s/%s" % (p, m), "score": round(pr, 2)} for p, m, pr, _n, _l in core.rangfolge(c, k, None, 5)])
    if do == "find_api":
        r = radar.suche(c, str(a.get("q", ""))[:80], 6, True)
        return json.dumps([{"name": x["name"], "what": x["beschr"][:90], "auth": x["auth"], "verdict": (x.get("sicher") or {}).get("urteil")} for x in r["apis"]], ensure_ascii=False)
    f = a.get("faehigkeit") if isinstance(a.get("faehigkeit"), str) else "chat"
    rows = c.execute("SELECT provider, model, status FROM modell WHERE COALESCE(faehigkeit,'chat')=? AND gone<3 AND status!='nicht_verfuegbar' LIMIT 12", (f,)).fetchall()
    return json.dumps(["%s/%s (%s)" % r for r in rows])


def chat(c, messages, ask):
    """messages: [{role, content}] from the UI; ask(body, klasse) -> (answer text, 'provider/model') or (None, errors). -> dict for the UI"""
    msgs = [{"role": "assistant" if m.get("role") == "assistant" else "user", "content": str(m.get("content", ""))[:2000]} for m in (messages or [])[-10:] if m.get("content")]
    if not msgs or msgs[-1]["role"] != "user":
        raise ValueError("last message must be from the user")
    la = lang(msgs[-1]["content"])
    if any(SECRET.search(m["content"]) for m in msgs if m["role"] == "user"):
        return {"reply": REFUSE[la], "model": None, "proposal": None}
    s = core.settings()
    body = {"messages": [{"role": "system", "content": system(c, s, la)}] + msgs, "max_tokens": 3000}
    text, who = ask(body, "de" if la == "de" else "reason")
    if text is None:
        why = "; ".join(who[:3]) or ("Noch kein Key eingetragen (Reiter 'Keys & Providers')." if la == "de" else "No key added yet (tab 'Keys & Providers').")
        return {"reply": ("Kein freies Modell erreichbar: " if la == "de" else "No free model reachable: ") + why, "model": None, "proposal": None}
    m = ACTION.search(text)
    text = ACTION.sub("", text).strip()
    proposal, do, a = None, None, {}
    try:
        act = json.loads(m.group(1)) if m else None
    except ValueError:
        act = None
    if isinstance(act, dict):
        do, a = act.get("do"), act.get("args") if isinstance(act.get("args"), dict) else {}
        if do in READ:
            body["messages"] += [{"role": "assistant", "content": text or do}, {"role": "user", "content": "RESULT of %s (local data): %s\nNow answer my question from this result. If I also asked for a state-changing task (scan, stop_all, resume, open), end with that ONE ACTION line, otherwise none." % (do, lies(c, do, a))}]
            t2, who2 = ask(body, "de" if la == "de" else "reason")
            if t2:
                m2 = ACTION.search(t2)
                text, who = ACTION.sub("", t2).strip(), who2
                try:
                    act = json.loads(m2.group(1)) if m2 else None
                except ValueError:
                    act = None
                do, a = (act.get("do"), act.get("args") if isinstance(act.get("args"), dict) else {}) if isinstance(act, dict) else (None, {})
                if do in READ:                                      # no chains: a second read is ignored
                    do = None
    if do in PROPOSE:
        proposal = {"api": PROPOSE[do][0], "body": PROPOSE[do][1], "label": do}
    elif do == "open" and a.get("tab") in TABS:
        proposal = {"tab": a["tab"], "label": a["tab"]}
    return {"reply": text, "model": who, "proposal": proposal}
