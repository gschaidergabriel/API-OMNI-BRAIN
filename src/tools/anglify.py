#!/usr/bin/env python3
"""Anglify: translate the user-visible German strings of the project to English, mechanically and safely.
Python: only plain string tokens (no f-strings, no docstrings); JS/HTML/JSON: quoted literals. A literal is translated when it is German PROSE (several words, or a capitalised label);
identifiers, enum values, SQL, paths and header names are never touched. Placeholders (%s %d {x} ${x} \\n <tags>) must survive or the translation is rejected.
The map german->english is global, so every file (code, tests, UI) changes consistently.
usage: anglify.py scan [N] | map | apply [--dry]"""
import ast
import io
import json
import os
import re
import sys
import tokenize

import team_lib as L
from team_lib import it, log

ROOT = it.ROOT
PKG = os.path.join(ROOT, "omnipool")
FILES = [os.path.join(PKG, n) for n in sorted(os.listdir(PKG)) if n.endswith((".py", ".js", ".json", ".html")) and n != "radar_quellen.json"]
MAP = os.path.join(ROOT, "team", "anglify_map.json")
GER = set("""der die das den dem des ein eine einen einem einer eines und oder nicht kein keine keinen ist sind wird werden wurde wurden hat haben kann koennen muss muessen soll sollen mit von zu zum zur auf bei nach aus fuer ueber unter vor durch gegen ohne
noch nur auch wenn als wie was wer wo wann warum dann dass weil aber doch schon sehr mehr alle alles jede jeder jedes dieser diese dieses sich es sie wir ihr du ich bitte neu neue neuen alt fehler pruefen speichern abbrechen schluessel anbieter modell modelle
gueltig ungueltig erkannt gefunden geloescht gespeichert verbunden entfernt bereit laeuft verfuegbar aktiv inaktiv hilfe zurueck weiter fertig leer bisher heute gestern jetzt sofort immer nie""".split())
SAFE_SINGLE = set()          # curated single words that are labels (filled from the scan review)
SQL = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|PRAGMA|ALTER|DROP)\b")
JS = re.compile(r"""(?P<q>["'`])(?P<s>(?:\\.|(?!(?P=q))[^\\\n])*)(?P=q)""")


def fold(s):
    return s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


EXCLUDE = ("Geheimcode", "KIRSCHE", "Load-Balancer", "hole_wert", "Anna ist", "Notiz %d", "Wie lautet", "stadt", "Zweitälteste", "Fachlichkeit")      # German probe prompts: they TEST German, they stay German


def is_german(s):
    if len(s) < 3 or SQL.search(s) or "Omnipool" in s and " " not in s or any(x in s for x in EXCLUDE):
        return False
    if re.fullmatch(r"[A-Za-z0-9_]+", s) and ("_" in s or s.islower() or s.isupper()):
        return False                                                    # identifiers / enum values / env names
    if re.fullmatch(r"[a-z0-9_/.-]+", s) or s[:1] in "'\"":
        return False                                                    # routes, paths, fragments
    if re.search(r"\b(AND|NOT IN|COALESCE|WHERE|FROM|ORDER BY|LIMIT)\b", s):
        return False
    if re.match(r"^(https?:|/|#|\.|\{|\[|[A-Z]+-)", s) and " " not in s:
        return False
    words = re.findall(r"[A-Za-zÄÖÜäöüß]+", s)
    if not words:
        return False
    umlaut = bool(re.search("[äöüÄÖÜß]", s))
    hits = sum(fold(w) in GER for w in words)
    if hits == len(words) and len(words) >= 6 and not re.search(r"[.!?:]", s):
        return False                                                    # keyword lists for language detection
    if len(words) == 1:
        return s in SAFE_SINGLE or (umlaut and s[0].isupper())
    return umlaut or hits >= 1


def py_strings(src):
    out, fs = [], 0
    try:
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type == getattr(tokenize, "FSTRING_START", -1):
                fs += 1
            elif t.type == getattr(tokenize, "FSTRING_END", -1):
                fs -= 1
            elif t.type == tokenize.STRING and not fs and not t.string.startswith(('"""', "'''")) and re.match(r"^[\"']", t.string):
                out.append((t.start, t.end, t.string))
    except tokenize.TokenError:
        pass
    return out


def literals(path):
    src = open(path, encoding="utf-8").read()
    res = []
    if path.endswith(".py"):
        for _st, _en, tok in py_strings(src):
            try:
                val = ast.literal_eval(tok)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(val, str) and is_german(val):
                res.append(val)
    elif path.endswith(".json"):
        d = json.loads(src)
        res += [v for v in (d.values() if isinstance(d, dict) else []) if isinstance(v, str) and is_german(v)]
    else:
        res += [m.group("s") for m in JS.finditer(src) if is_german(m.group("s").replace("\\n", " "))]
    return res


UI = ("ui.js", "ui_radar.js", "ui.html")
MAP2 = os.path.join(ROOT, "team", "anglify_map2.json")
MAP3 = os.path.join(ROOT, "team", "anglify_map3.json")


def relaxed(path):
    """UI files, second pass: every literal that could be visible text; the model decides (returns only what is German)"""
    src = open(path, encoding="utf-8").read()
    out = []
    for m in JS.finditer(src):
        s = m.group("s")
        if len(s) < 3 or not re.search(r"[A-Za-zÄÖÜäöüß]{3}", s) or re.fullmatch(r"[a-z0-9_/.:#-]+", s) or re.search(r"[;{}]\s*$|^[.#<]|=>|\bvar\(--|rgba?\(", s) or "px" in s and ":" in s:
            continue
        out.append(s)
    return out


def relaxed_py(path):
    out = []
    for _st, _en, tok in py_strings(open(path, encoding="utf-8").read()):
        try:
            v = ast.literal_eval(tok)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(v, str) or len(v) < 4 or not re.search(r"[A-Za-zÄÖÜäöüß]{3}", v) or SQL.search(v) or re.fullmatch(r"[a-z0-9_/.:#, -]+", v) or re.search(r"\\[bdwsBDWS]|\(\?|\|", v):
            continue
        if v.startswith(("/", "http", "{", "[", "'", '"')) or any(x in v for x in EXCLUDE):
            continue
        out.append(v)
    return out


def collect():
    seen, per = {}, {}
    for p in FILES:
        for s in literals(p):
            seen[s] = seen.get(s, 0) + 1
            per.setdefault(p, set()).add(s)
    return seen, per


def tokens_of(s):
    return sorted(re.findall(r"%[-0-9.]*[sdif]|\$\{[^}]*\}|\{[A-Za-z_0-9]*\}|<[^>]+>|\\n|\\t|&\w+;", s))


def valid(de, en):
    return isinstance(en, str) and en.strip() != "" and tokens_of(de) == tokens_of(en) and en.count("\n") == de.count("\n") and not re.search("[äöüß]", en) and len(en) < 3 * len(de) + 40


def translate(batch, models):
    prompt = ("Translate these German user-interface strings of a software tool (API key manager / model router) into natural, concise English. Keep placeholders EXACTLY as they are (percent-s, percent-d, braces, dollar-braces, backslash-n, HTML tags). "
              "Keep technical names (Omnipool, API, OpenAI, Claude Code, NVIDIA ...). Register: friendly, plain, no marketing. Answer ONLY with one ```json object mapping each German string to its English translation.\n%s" % json.dumps(batch, ensure_ascii=False))
    got = {}
    for m in models:
        t, mm = L.ask([m], prompt, 8000, 240)
        j = L.jsonblock(t) if t else None
        if isinstance(j, dict):
            ok = {k: v for k, v in j.items() if k in batch and valid(k, v)}
            log(art="anglify", modell=mm, angefragt=len(batch), gueltig=len(ok))
            for k, v in ok.items():
                got.setdefault(k, v)
        if len(got) == len(batch):
            break
    return got


def apply_py(src, mp):
    lines = src.splitlines(keepends=True)
    edits = []
    for st, en, tok in py_strings(src):
        try:
            val = ast.literal_eval(tok)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(val, str) and val in mp and st[0] == en[0]:
            edits.append((st, en, repr(mp[val])))
    for st, en, rep in sorted(edits, reverse=True):
        ln = lines[st[0] - 1]
        lines[st[0] - 1] = ln[:st[1]] + rep + ln[en[1]:]
    return "".join(lines)


def apply_js(src, mp):
    def sub(m):
        s, q = m.group("s"), m.group("q")
        if s not in mp:
            return m.group(0)
        en = mp[s]
        en = re.sub(r"(?<!\\)" + re.escape(q), "\\" + q, en)
        return q + en + q
    return JS.sub(sub, src)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    seen, per = collect()
    if cmd == "scan":
        print(len(seen), "distinct German literals in", len(per), "files")
        for p, s in per.items():
            print(os.path.relpath(p, ROOT), len(s))
        for s in list(seen)[:int(sys.argv[2]) if len(sys.argv) > 2 else 40]:
            print("  ", repr(s)[:110])
        return
    mp = json.load(open(MAP)) if os.path.exists(MAP) else {}
    if cmd == "map2":
        m2 = json.load(open(MAP2)) if os.path.exists(MAP2) else {}
        cand = []
        for n in UI:
            for x in relaxed(os.path.join(PKG, n)):
                if x not in m2 and x not in cand:
                    cand.append(x)
        models = [m for m in L.pool() if any(x in m for x in ("mistral-large", "ultra", "step-5", "glm-5.3", "minimax"))]
        for i in range(0, len(cand), 40):
            b, k = cand[i:i + 40], (i // 40) % len(models)
            prompt = ("Below are string literals extracted from a web UI's JavaScript/HTML. Some are German user-visible text (possibly mixed with English), others are English, code, identifiers or CSS. "
                      "Return ONE ```json object mapping ONLY the strings that contain German to their natural English translation (concise, friendly, plain). Keep placeholders, ${...}, %s, HTML tags and punctuation exactly. "
                      "Do not include strings that are already fully English. Keep product/technical names.\n@@").replace("@@", json.dumps(b, ensure_ascii=False))
            got = {}
            for m in models[k:] + models[:k]:
                t, mm = L.ask([m], prompt, 8000, 240)
                j = L.jsonblock(t) if t else None
                if isinstance(j, dict):
                    got = {a: v for a, v in j.items() if a in b and valid(a, v)}
                    log(art="anglify2", modell=mm, angefragt=len(b), geaendert=len(got))
                    break
            m2.update({x: got.get(x, x) for x in b})
            json.dump(m2, open(MAP2, "w"), ensure_ascii=False, indent=1)
            print("batch2", i // 40 + 1, "/", (len(cand) + 39) // 40, "changed so far", sum(1 for a, v in m2.items() if a != v), flush=True)
        print("untranslated: done")
        return
    if cmd == "map3":
        m3 = json.load(open(MAP3)) if os.path.exists(MAP3) else {}
        cand = []
        for n in sorted(os.listdir(PKG)):
            if n.endswith(".py"):
                for x in relaxed_py(os.path.join(PKG, n)):
                    if x not in m3 and x not in cand:
                        cand.append(x)
        print("py candidates", len(cand), flush=True)
        models = [m for m in L.pool() if any(x in m for x in ("mistral-large", "ultra", "step-5", "glm-5.3", "minimax"))]
        for i in range(0, len(cand), 40):
            b, k = cand[i:i + 40], (i // 40) % len(models)
            prompt = ("Below are string literals from a Python program. Some are German text shown to users or written to logs/popups (possibly ASCII-transliterated: ae oe ue ss), others are English, code, identifiers, enum values or protocol words. "
                      "Return ONE ```json object mapping ONLY the strings that are German user/log-visible text to a natural English translation. Keep placeholders (%s %d %.0f %%), braces, backslash-n and punctuation EXACTLY. "
                      "Do NOT include strings that are already English, single identifier-like words (they are data keys), or German prompts meant for a language model.\n@@").replace("@@", json.dumps(b, ensure_ascii=False))
            got = {}
            for m in models[k:] + models[:k]:
                t, mm = L.ask([m], prompt, 8000, 240)
                j = L.jsonblock(t) if t else None
                if isinstance(j, dict):
                    got = {a: v for a, v in j.items() if a in b and valid(a, v)}
                    log(art="anglify3", modell=mm, angefragt=len(b), geaendert=len(got))
                    break
            m3.update({x: got.get(x, x) for x in b})
            json.dump(m3, open(MAP3, "w"), ensure_ascii=False, indent=1)
            print("batch3", i // 40 + 1, "/", (len(cand) + 39) // 40, "changed so far", sum(1 for a, v in m3.items() if a != v), flush=True)
        return
    if cmd == "apply2":
        m2 = json.load(open(MAP2))
        if os.path.exists(MAP3):
            m2.update(json.load(open(MAP3)))
        for n in UI:
            p = os.path.join(PKG, n)
            src = open(p, encoding="utf-8").read()
            new = apply_js(src, {a: v for a, v in m2.items() if a != v})
            if new != src:
                print("changed", n)
                open(p, "w", encoding="utf-8").write(new)
        for n in sorted(os.listdir(PKG)):
            if n.endswith(".py"):
                p = os.path.join(PKG, n)
                src = open(p, encoding="utf-8").read()
                new = apply_py(src, {a: v for a, v in m2.items() if a != v})
                if new != src:
                    print("changed", n)
                    open(p, "w", encoding="utf-8").write(new)
        return
    if cmd == "map":
        models = [m for m in L.pool() if any(x in m for x in ("mistral-large", "ultra", "step-5", "glm-5.3", "minimax"))]
        todo = [s for s in seen if s not in mp]
        for i in range(0, len(todo), 30):
            k = (i // 30) % len(models)
            mp.update(translate(todo[i:i + 30], models[k:] + models[:k]))
            json.dump(mp, open(MAP, "w"), ensure_ascii=False, indent=1)
            print("batch", i // 30 + 1, "/", (len(todo) + 29) // 30, "map", len(mp), flush=True)
        print("untranslated:", [s for s in seen if s not in mp][:20])
    elif cmd == "apply":
        for p in per:
            src = open(p, encoding="utf-8").read()
            if p.endswith(".py"):
                new = apply_py(src, mp)
            elif p.endswith(".json"):
                d = json.loads(src)
                new = json.dumps({k: mp.get(v, v) if isinstance(v, str) else v for k, v in d.items()}, ensure_ascii=False, indent=1) + "\n"
            else:
                new = apply_js(src, mp)
            if new != src:
                print(("would change " if "--dry" in sys.argv else "changed ") + os.path.relpath(p, ROOT))
                if "--dry" not in sys.argv:
                    open(p, "w", encoding="utf-8").write(new)


if __name__ == "__main__":
    main()
