"""API-OMNI-BRAIN server: web UI + JSON API on 127.0.0.1 only, and the connection point for agent harnesses:
  /v1/chat/completions, /v1/models          OpenAI-compatible (Hermes, Grokbot, Crush, Aider, any OpenAI client)
  /v1/messages (+count_tokens)              Anthropic-compatible (Claude Code via ANTHROPIC_BASE_URL)
  /x/<provider>/<path>                      authenticated pass-through with key rotation (video, image, audio, embeddings, search ... any API of a known provider)
Every application gets its own key (derived from the app key) and can be switched off; the UI/API need the header X-Omnipool and a local Host (no cross-site calls)."""
import hashlib
import hmac
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import anbieter as AN
from . import assistent, core, gehirn, integrieren, quarantaene, radar, sicher, selfservice

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.5.0"
STATE = {"lauf": False, "ts": 0.0, "fehler": "", "start": time.time()}
LABEL = {"claude_code": "Claude Code", "hermes": "Hermes Agent", "grokbot": "Grokbot", "crush": "Crush", "aider": "Aider", "openai": 'Other OpenAI-compatible applications'}


def harness_key(app):
    return "op-%s-%s" % (app, hmac.new(core.settings()["app_key"].encode(), app.encode(), hashlib.sha256).hexdigest()[:24])


def app_of_key(k):
    return next((a for a in core.settings()["harness"] if k and hmac.compare_digest(k, harness_key(a))), None)


def base_of(p):
    cp = core.custom().get(p)
    if cp:
        return cp["base"].rstrip("/")
    u = core.chat_url(p) or ((core.TC.PINFO.get(p) or {}).get("check") or {}).get("url", "")
    return re.sub(r"/(chat/completions|models)$", "", u)


def bericht_voll(c):
    """organ report of the brain plus the two newer organs (Radar, Sicherheit)"""
    b = gehirn.bericht(c)
    try:
        r = radar.status(c)
        z = r["zyklus"]
        b["organe"] += [
            {"name": "Radar", "info": '%d sources responding, %d messages, %d APIs in index; Model check 2x per week' % (r["feeds"]["lebendig"], r["nachrichten"], r["apis"]),
             "ts": max([v["zuletzt"] for v in z.values() if v["zuletzt"]] or [None])},
            {"name": 'Security', "info": 'Quarantine sandbox for all external, Tor before keys, %d alerts open, %d dismissed' % (
                len(quarantaene.offene(c)), c.execute("SELECT COUNT(*) FROM meldung").fetchone()[0]), "ts": c.execute("SELECT MAX(ts) FROM meldung").fetchone()[0]}]
    except Exception as e:  # noqa: BLE001
        b["organe"] += [{"name": "Error", "info": str(e)}]
    return b


def tor(base):
    """gate before a key may travel to a new provider address: local/LAN addresses pass, public ones need https and a clean verdict -> (blocked?, verdict)"""
    import ipaddress
    import urllib.parse
    h = (urllib.parse.urlsplit(base).hostname or "").lower()
    try:
        a = ipaddress.ip_address(h)
        lokal = a.is_private or a.is_loopback
    except ValueError:
        lokal = h == "localhost" or h.endswith(".localhost") or h.endswith(".local")
    if lokal:
        return False, {"urteil": "lokal", "gruende": ['local/private address, the key does not leave the machine'], "host": h}
    v = sicher.pruefe(base, True)
    return v["urteil"] != "unauffaellig", v


def starte_lauf(max_modelle=None):
    if STATE["lauf"]:
        return False

    def go():
        STATE.update(lauf=True, fehler="")
        try:
            core.lauf(max_modelle or core.settings()["max_modelle"])
        except Exception as e:  # noqa: BLE001
            STATE["fehler"] = type(e).__name__
        STATE.update(lauf=False, ts=time.time())
    threading.Thread(target=go, daemon=True).start()
    return True


def planer():
    """Planer organ: first run soon after start (bigger when the catalogue is empty), then every lauf_min minutes unless the machine is busy"""
    time.sleep(10)
    while True:
        s = core.settings()
        try:
            leer = core.db().execute("SELECT COUNT(*) FROM modell WHERE n_try>0").fetchone()[0] == 0
            if not core.aus() and not gehirn.busy():
                starte_lauf(20 if leer else s["max_modelle"])
            gehirn.drift(core.db())
            radar.zyklus(core.db(), gehirn.busy())
        except Exception as e:  # noqa: BLE001
            STATE["fehler"] = type(e).__name__
        time.sleep(300 if gehirn.busy() else max(300, s["lauf_min"] * 60))


# ------------------------------------------------------------------ upstream with failover
def beschaffe(c, cands, body, stream, app, klasse):
    """first candidate that answers: -> (response or parsed json, provider, model, started) or (None, [errors])"""
    fehler = []
    for p, m in cands:
        cur = body
        for versuch in range(2):
            tok = gehirn.key_waehlen(p, m)
            if not tok:
                fehler.append('%s: no free key' % p)
                break
            rq = urllib.request.Request(core.chat_url(p), json.dumps({**cur, "model": m}).encode(),
                                        {**core.auth_kopf(p, tok), "Content-Type": "application/json", "User-Agent": "API-OMNI-BRAIN/1.0"})
            t0 = time.time()
            try:
                r = urllib.request.urlopen(rq, timeout=60 if stream else 120)
                if stream:
                    return r, p, m, t0
                js = json.loads(r.read().decode())
                msg = js["choices"][0]["message"]
                if not (msg.get("content") or msg.get("tool_calls")):
                    if versuch == 0 and js["choices"][0].get("finish_reason") == "length":          # a thinking model spent the whole budget on reasoning: give it room once
                        cur = {**body, "max_tokens": min(8192, max(2048, 6 * int(body.get("max_tokens") or 512)))}
                        continue
                    gehirn.lerne(c, app, klasse, p, m, False, time.time() - t0, status=200)
                    fehler.append('%s/%s: empty response' % (p, m))
                    break
                gehirn.gut(p, m)
                return js, p, m, t0
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    ra = str(e.headers.get("Retry-After", ""))
                    gehirn.limit(p, m, tok, int(ra) if ra.isdigit() else 90)
                    fehler.append("%s/%s: Limit (429)" % (p, m))
                    continue
                elif e.code in (401, 402, 403):
                    gehirn.key_ruhe(tok, 3600)
                else:
                    gehirn.bremse(p, m, e.code)
                    gehirn.lerne(c, app, klasse, p, m, False, time.time() - t0, status=e.code)
                    fehler.append("%s/%s: HTTP %d" % (p, m, e.code))
                    break
                fehler.append('%s: HTTP %d (key idle)' % (p, e.code))
                if versuch == 1:
                    gehirn.bremse(p, m, e.code)
            except Exception as e:  # noqa: BLE001
                gehirn.bremse(p, m, 0)
                gehirn.lerne(c, app, klasse, p, m, False, time.time() - t0, status=0)
                fehler.append("%s/%s: %s" % (p, m, type(e).__name__))
                break
    return None, fehler


def waehle_kandidaten(c, body, klasse):
    ex = str(body.get("model", ""))
    cands = gehirn.kandidaten(c, klasse, 6)
    if "/" in ex and not ex.startswith("omnipool-"):
        p, m = ex.split("/", 1)
        if core.chat_url(p):
            cands = [(p, m)] + [x for x in cands if x != (p, m)]
    return cands


# ------------------------------------------------------------------ Anthropic <-> OpenAI
def a2o(b):
    msgs, sysm = [], b.get("system")
    if sysm:
        msgs.append({"role": "system", "content": sysm if isinstance(sysm, str) else " ".join(x.get("text", "") for x in sysm if isinstance(x, dict))})
    for m in b.get("messages") or []:
        c = m.get("content")
        if isinstance(c, str):
            msgs.append({"role": m["role"], "content": c})
            continue
        txt, calls = [], []
        for x in c or []:
            t = x.get("type")
            if t == "text":
                txt.append(x.get("text", ""))
            elif t == "tool_use":
                calls.append({"id": x["id"], "type": "function", "function": {"name": x["name"], "arguments": json.dumps(x.get("input", {}))}})
            elif t == "tool_result":
                cc = x.get("content")
                msgs.append({"role": "tool", "tool_call_id": x["tool_use_id"], "content": cc if isinstance(cc, str) else " ".join(y.get("text", "") for y in cc or [] if isinstance(y, dict))})
            elif t == "image":
                txt.append("[Bild]")
        if txt or calls:
            msgs.append({"role": m["role"], "content": "\n".join(txt) or None, **({"tool_calls": calls} if calls else {})})
    o = {"messages": msgs, "max_tokens": b.get("max_tokens", 1024), "model": b.get("model", "omnipool-auto")}
    for k in ("temperature", "top_p"):
        if k in b:
            o[k] = b[k]
    if b.get("stop_sequences"):
        o["stop"] = b["stop_sequences"]
    if b.get("tools"):
        o["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t.get("input_schema", {"type": "object"})}} for t in b["tools"]]
        tc = b.get("tool_choice") or {}
        o["tool_choice"] = {"auto": "auto", "any": "required"}.get(tc.get("type"), {"type": "function", "function": {"name": tc.get("name")}} if tc.get("type") == "tool" else "auto")
    return o


def o2a(js, name):
    msg, ch = js["choices"][0]["message"], js["choices"][0]
    blocks = [{"type": "text", "text": msg["content"]}] if msg.get("content") else []
    for tc in msg.get("tool_calls") or []:
        try:
            inp = json.loads(tc["function"].get("arguments") or "{}")
        except ValueError:
            inp = {}
        blocks.append({"type": "tool_use", "id": tc.get("id") or "toolu_" + os.urandom(6).hex(), "name": tc["function"]["name"], "input": inp})
    u = js.get("usage") or {}
    stop = {"tool_calls": "tool_use", "length": "max_tokens"}.get(ch.get("finish_reason"), "end_turn")
    return {"id": "msg_" + os.urandom(8).hex(), "type": "message", "role": "assistant", "model": name, "content": blocks or [{"type": "text", "text": ""}], "stop_reason": stop,
            "stop_sequence": None, "usage": {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0)}}


def sse(msg):
    """Anthropic stream events built from a finished message (failover stays simple: the upstream call is never streamed here)"""
    ev = [("message_start", {"type": "message_start", "message": {**msg, "content": [], "stop_reason": None, "usage": {"input_tokens": msg["usage"]["input_tokens"], "output_tokens": 0}}})]
    for i, b in enumerate(msg["content"]):
        if b["type"] == "text":
            ev += [("content_block_start", {"type": "content_block_start", "index": i, "content_block": {"type": "text", "text": ""}}),
                   ("content_block_delta", {"type": "content_block_delta", "index": i, "delta": {"type": "text_delta", "text": b["text"]}})]
        else:
            ev += [("content_block_start", {"type": "content_block_start", "index": i, "content_block": {"type": "tool_use", "id": b["id"], "name": b["name"], "input": {}}}),
                   ("content_block_delta", {"type": "content_block_delta", "index": i, "delta": {"type": "input_json_delta", "partial_json": json.dumps(b["input"])}})]
        ev.append(("content_block_stop", {"type": "content_block_stop", "index": i}))
    ev += [("message_delta", {"type": "message_delta", "delta": {"stop_reason": msg["stop_reason"], "stop_sequence": None}, "usage": {"output_tokens": msg["usage"]["output_tokens"]}}),
           ("message_stop", {"type": "message_stop"})]
    return "".join("event: %s\ndata: %s\n\n" % (n, json.dumps(d)) for n, d in ev).encode()


# ------------------------------------------------------------------ HTTP
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "API-OMNI-BRAIN"

    def log_message(self, *a):
        pass

    def senden(self, code, obj, typ="application/json", extra=None):
        data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 8 << 20:
            raise ValueError('Request too large')
        raw = self.rfile.read(n) if n else b""
        return raw

    def json_body(self):
        raw = self.body()
        return json.loads(raw.decode()) if raw else {}

    def lokal(self):
        return self.headers.get("Host", "").rsplit(":", 1)[0].strip("[]") in ("127.0.0.1", "localhost", "::1")

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def do_DELETE(self):
        self.route("DELETE")

    def angemeldet(self):
        return [{"name": a, "status": "approved" if v.get("an") else "pending" if v.get("angemeldet") else "off", "scope": v.get("scope", [])} for a, v in core.settings()["harness"].items() if v.get("angemeldet") or v.get("an")]

    def key_of_request(self):
        return (self.headers.get("Authorization") or "").replace("Bearer ", "").strip() or self.headers.get("x-api-key", "")

    def registrieren(self, base):
        """a harness asks to be connected: it gets its key at once, but the application stays OFF until the user approves it in the UI"""
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self.senden(415, {"error": 'Content-Type must be application/json'})
        d = self.json_body()
        name = integrieren.clean_name(d.get("name"))
        if not name:
            return self.senden(400, {"error": 'name missing (a-z, 0-9, _)'})
        s = core.settings()
        if name not in s["harness"] and len(s["harness"]) >= 20:
            return self.senden(429, {"error": 'too many applications; remove unused ones in the Connect tab'})
        scope = [str(x)[:40] for x in (d.get("scope") if isinstance(d.get("scope"), list) else [])][:6]
        e = s["harness"].get(name) or {"an": False, "klasse": "auto"}
        if not e.get("an") and not e.get("angemeldet"):
            core.save_settings({**s, "harness": {**s["harness"], name: {**e, "an": False, "angemeldet": time.time(), "scope": scope}}})
        st = "approved" if e.get("an") else "pending"
        return self.senden(200, {"name": name, "key": harness_key(name), "status": st, "approve": base + "/#connect",
                                 "poll": base + "/v1/register/" + name, "next": "Tell your user to approve this application in API-OMNI-BRAIN (Connect tab, one click), then use the key."})

    def reg_status(self, name):
        name = integrieren.clean_name(name)
        e = core.settings()["harness"].get(name)
        if not e or not hmac.compare_digest(self.key_of_request(), harness_key(name)):
            return self.senden(401, {"error": "unknown application or wrong key"})
        return self.senden(200, {"name": name, "status": "approved" if e.get("an") else "pending" if e.get("angemeldet") else "denied"})

    def route(self, meth):
        try:
            if not self.lokal():
                return self.senden(403, {"error": 'local only'})
            path = self.path.split("?")[0]
            if meth == "GET" and path in ("/", "/index.html"):
                return self.senden(200, core.res("ui.html"), "text/html; charset=utf-8")
            if meth == "GET" and path in ("/icon.png", "/favicon.ico"):
                return self.senden(200, core.res("icon.png"), "image/png")
            if meth == "GET" and re.fullmatch(r"/manual/[a-z0-9_-]{1,40}\.png", path):                       # manual screenshots (whitelisted names only)
                try:
                    return self.senden(200, core.res(path[1:]), "image/png")
                except (OSError, FileNotFoundError):
                    return self.senden(404, {"error": "unknown"})
            if meth == "GET" and path in ("/ui.css", "/ui.js", "/ui_radar.js", "/ui_assistant.js", "/ui_manual.js", "/texte.json", "/manual.json"):
                return self.senden(200, core.res(path[1:]), {"css": "text/css", "js": "text/javascript", "json": "application/json"}[path.rsplit(".", 1)[1]] + "; charset=utf-8")
            base = "http://127.0.0.1:%d" % self.server.server_address[1]
            if meth == "GET" and path in ("/integrate", "/integrate.md", "/llms.txt"):
                return self.senden(200, integrieren.guide(base, VERSION, integrieren.snippets(base)).encode(), "text/markdown; charset=utf-8")
            if meth == "GET" and path == "/.well-known/api-omni-brain.json":
                return self.senden(200, integrieren.manifest(base, VERSION))
            if meth == "GET" and path == "/.well-known/omnipool-tools.json":
                return self.senden(200, selfservice.standard_manifest(base))
            if meth == "GET" and path == "/v1/offer":
                return self.senden(200, integrieren.offer(core.db(), base, self.angemeldet()))
            if meth == "POST" and path == "/v1/register":
                return self.registrieren(base)
            if meth == "GET" and path.startswith("/v1/register/"):
                return self.reg_status(path[13:])
            if path.startswith("/api/"):
                if self.headers.get("X-Omnipool") != "1":
                    return self.senden(403, {"error": 'Header X-Omnipool missing'})
                return self.api(meth, path[5:])
            if path.startswith("/v1/") or path.startswith("/x/"):
                return self.harness(meth, path)
            self.senden(404, {"error": "unbekannt"})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except ValueError as e:
            self.close_connection = True
            self.senden(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            try:
                self.senden(500, {"error": type(e).__name__})
            except OSError:
                pass

    # ---------------- UI API
    def api(self, meth, p):
        c, s = core.db(), core.settings()
        if p == "ping":
            return self.senden(200, {"ok": True, "version": VERSION})
        if p == "analyst":
            from . import analyst
            return self.senden(200, analyst.stand())
        if p == "needles":
            from . import schatten
            return self.senden(200, schatten.stand())
        if p == "status":
            rows = c.execute("SELECT slot, provider, hash8, status, n_models, checked FROM key ORDER BY provider, slot").fetchall()
            hs = {a: {**v, "label": LABEL.get(a, a), "key": harness_key(a)} for a, v in s["harness"].items()}
            return self.senden(200, {
                "version": VERSION, "aus": core.aus(), "busy": gehirn.busy(), "lauf": {"laeuft": STATE["lauf"], "ts": STATE["ts"], "fehler": STATE["fehler"]},
                "keys": [dict(zip(("slot", "provider", "hash8", "status", "n_models", "checked"), r), aus=r[0] in s["slot_aus"]) for r in rows],
                "modelle": c.execute("SELECT COUNT(*) FROM modell").fetchone()[0], "geprobt": c.execute("SELECT COUNT(*) FROM modell WHERE n_try>0").fetchone()[0],
                "faehigkeiten": c.execute("SELECT COALESCE(faehigkeit,'chat'), COUNT(*) FROM modell GROUP BY 1").fetchall(),
                "wahl": {k: core.rangfolge(c, k, None, 5) for k in core.KLASSEN}, "bericht": bericht_voll(c),
                "einstellungen": {k: v for k, v in s.items() if k not in ("app_key", "harness")}, "harness": hs, "keys_file": core.keys_file(),
                "anbieter": [{"id": i, "label": core.TC.PROVIDERS[i][0], "art": "eingebaut"} for i in core.TC.FREE] +
                            [{"id": i, "label": v["label"], "art": "eigener", "faehigkeiten": v.get("faehigkeiten")} for i, v in core.custom().items()],
                "meldungen": quarantaene.offene(c), "url": "http://127.0.0.1:%d" % self.server.server_address[1]})
        if p == "modelle":
            rows = c.execute("SELECT provider, model, COALESCE(faehigkeit,'chat'), status, gone, n_try, probed FROM modell ORDER BY provider, model").fetchall()
            kl = {}
            for pr, m, k, ok, n in c.execute("SELECT provider, model, klasse, ok_n, n FROM klasse"):
                kl.setdefault((pr, m), {})[k] = [round(ok, 1), round(n, 1)]
            return self.senden(200, [{"provider": r[0], "model": r[1], "faehigkeit": r[2], "status": r[3], "gone": r[4], "n_try": r[5], "probed": r[6], "klassen": kl.get((r[0], r[1]), {})}
                                     for r in rows])
        if meth != "POST":
            return self.senden(404, {"error": "unbekannt"})
        d = self.json_body()
        if p == "chat":
            def frage(body, klasse):
                r = beschaffe(c, waehle_kandidaten(c, {"model": "omnipool-auto"}, klasse), body, False, "assistant", klasse)
                return (None, r[1]) if r[0] is None else (r[0]["choices"][0]["message"].get("content") or "", "%s/%s" % (r[1], r[2]))
            return self.senden(200, assistent.chat(c, d.get("messages"), frage))
        if p == "lauf":
            return self.senden(200, {"gestartet": starte_lauf(int(d.get("max", 0)) or None)})
        if p == "token/check":
            tok, prov = str(d.get("token", "")).strip(), d.get("provider", "auto")
            if prov in core.custom():
                r = AN.check(core.custom()[prov], tok)
                return self.senden(200, {"ok": r["ok"], "provider": prov, "hash8": core.token_hash(tok), "modelle": len(r["models"]), "status": r["status"]})
            r = core.TC.check(prov, tok)
            if r.get("provider") == "auto" or (prov == "auto" and not r.get("provider")):
                return self.senden(200, {"ok": False, "unbekannt": True, "hash8": r.get("hash8"), "fehler": r.get("error")})
            return self.senden(200, {"ok": r["ok"], "provider": r["provider"], "hash8": r["hash8"], "modelle": len(r.get("models") or []), "status": r.get("status"), "fehler": r.get("error"),
                                     "hinweis": r.get("extra")})
        if p == "token/save":
            tok, prov = str(d.get("token", "")).strip(), d.get("provider")
            if prov in core.custom():
                slot = AN.key_save(prov, tok)
                res = {"slot": slot, "hash8": core.token_hash(tok), "duplicate": False}
            else:
                core.keys_file()
                res = core.TC.save(prov, tok)
            starte_lauf()
            return self.senden(200, res)
        if p == "token/remove":
            ok = AN.key_remove(d["slot"], d["hash8"]) if d.get("eigener") else bool(core.TC.remove(d["slot"], d["hash8"]))
            c.execute("DELETE FROM key WHERE slot=?", (d["slot"],))
            c.commit()
            return self.senden(200, {"entfernt": ok})
        if p in ("anbieter/entdecke", "anbieter/speichern"):
            base = str(d.get("base") or (d.get("profile") or {}).get("base", ""))
            gesperrt, v = tor(base)
            if gesperrt and not (v["urteil"] == "vorsicht" and d.get("bestaetigt") is True):
                return self.senden(200, {"gesperrt": True, "sicherheit": v, "frage": "The key is not sent. With 'caution' you can explicitly consent using confirmed=true." if v["urteil"] == "vorsicht" else 'Blocked: this provider is not secure enough for a key.'})
        if p == "anbieter/entdecke":
            def analyst(prompt):
                tk = core.tokens_of(core.JUDGE[0])
                return core.chat(core.JUDGE[0], core.JUDGE[1], prompt, tk[0], 300, 60)[1] if tk else ""
            return self.senden(200, AN.entdecke(str(d.get("base", "")), str(d.get("token", "")).strip(), d.get("label") or None, analyst))
        if p == "anbieter/speichern":
            pr = d["profile"]
            if not re.match(r"^[a-z0-9]{1,20}$", pr.get("id", "")) or pr["id"] in core.TC.PROVIDERS:
                raise ValueError('Invalid or already assigned identifier')
            AN.speichere(pr)
            slot = AN.key_save(pr["id"], str(d.get("token", "")).strip())
            core.ereignis(c, "neuer_anbieter", '%s (%s) created, capabilities %s' % (pr["id"], pr["base"], ",".join(pr.get("faehigkeiten", []))))
            c.commit()
            starte_lauf()
            return self.senden(200, {"slot": slot})
        if p == "meldungen":
            return self.senden(200, quarantaene.offene(c))
        if p == "meldungen/gelesen":
            quarantaene.gelesen(c, [int(i) for i in d.get("ids", [])][:100])
            return self.senden(200, {"ok": True})
        if p == "radar/datei":
            url = quarantaene.github_roh(str(d.get("url", ""))[:600])
            g = quarantaene.laden(c, url, None, still=False, max_bytes=1 << 20)
            if not g["ok"]:
                return self.senden(200, {k: v for k, v in g.items() if k != "daten"})
            return self.senden(200, {"ok": True, "urteil": "sauber", "netz_isoliert": g["netz_isoliert"], "vorschau": g["daten"].decode("utf-8", "replace")[:6000], "bytes": len(g["daten"])})
        if p == "radar/status":
            return self.senden(200, radar.status(c))
        if p == "radar/news":
            return self.senden(200, {"news": radar.nachrichten(c, min(int(d.get("n", 40)), 100), bool(d.get("gratis")), str(d.get("q", ""))[:200]), "status": radar.status(c)})
        if p == "radar/suche":
            return self.senden(200, radar.suche(c, str(d.get("q", ""))[:200], 12, True))
        if p == "radar/usecase":
            return self.senden(200, radar.usecase(c, str(d.get("text", ""))[:1200]))
        if p == "radar/pruefe":
            return self.senden(200, radar.urteile(c, [str(d.get("url", ""))[:500]], 12))
        if p == "radar/aktualisiere":
            was = d.get("was")
            fn = {"feeds": radar.feeds_aktualisieren, "index": radar.index_aktualisieren, "modellcheck": radar.modellcheck, "entdeckung": radar.entdecke_feeds}.get(was)
            if not fn:
                raise ValueError("unbekannt")

            def go():
                try:
                    fn(core.db()) if was != "feeds" else fn(core.db(), nur_faellige=False)
                except Exception as e:  # noqa: BLE001
                    core.ereignis(core.db(), "radar_fehler", "%s: %s" % (was, type(e).__name__))
            threading.Thread(target=go, daemon=True).start()
            return self.senden(200, {"gestartet": was})
        if p == "settings":
            n = {**s}
            for k, lo, hi in (("lauf_min", 5, 1440), ("max_modelle", 1, 40), ("port", 1024, 65535)):
                if k in d:
                    n[k] = max(lo, min(hi, int(d[k])))
            if "melden" in d:
                n["melden"] = bool(d["melden"])
            if isinstance(d.get("vorrang"), dict):
                n["vorrang"] = {str(k): max(0.0, min(0.5, float(v))) for k, v in d["vorrang"].items()}
            if "keys_file" in d:
                kf = os.path.expanduser(str(d["keys_file"]))
                n["keys_file"] = kf if (not kf or os.path.isdir(os.path.dirname(kf) or ".")) else s["keys_file"]
            if "slot" in d:
                aus_ = set(s["slot_aus"])
                (aus_.add if d.get("aus") else aus_.discard)(d["slot"])
                n["slot_aus"] = sorted(aus_)
            if "harness" in d:
                a = re.sub(r"[^a-z0-9_]", "", str(d["harness"]["name"]).lower())[:24]
                if a:
                    n["harness"] = {**s["harness"], a: {**s["harness"].get(a, {}), "an": bool(d["harness"].get("an")), "klasse": d["harness"].get("klasse", "auto") if d["harness"].get("klasse", "auto") in ("auto",) + core.KLASSEN else "auto"}}
            if "harness" in d and d["harness"].get("ablehnen") and a in n["harness"]:
                n["harness"][a] = {k: v for k, v in n["harness"][a].items() if k not in ("angemeldet", "scope")}
            core.save_settings(n)
            return self.senden(200, {"ok": True})
        if p == "aus":
            os.makedirs(core.STATE, exist_ok=True)
            f = os.path.join(core.STATE, "AUS")
            (open(f, "w").close() if d.get("aus") else (os.path.exists(f) and os.remove(f)))
            return self.senden(200, {"aus": core.aus()})
        self.senden(404, {"error": "unbekannt"})

    # ---------------- harness side
    def harness(self, meth, path):
        k = (self.headers.get("Authorization") or "").replace("Bearer ", "").strip() or self.headers.get("x-api-key", "")
        app = app_of_key(k)
        if not app:
            return self.senden(401, {"error": {"type": "authentication_error", "message": 'API-OMNI-BRAIN key unknown (see Connect tab)'}})
        hs = core.settings()["harness"][app]
        if not hs.get("an") or core.aus():
            return self.senden(403, {"error": {"type": "permission_error", "message": 'Application not authorized in API-OMNI-BRAIN'}})
        # Shared HTTP tool contract for any tool-capable AI. The existing
        # per-application key/Connect-tab approval above is mandatory.
        # A second, per-plan LOCAL human approval is required before execution.
        if path.startswith("/v1/selfservice/"):
            try:
                if path == "/v1/selfservice/capabilities" and meth == "GET":
                    return self.senden(200, selfservice.capabilities())
                if path == "/v1/selfservice/plans" and meth == "POST":
                    data = self.json_body()
                    if not isinstance(data, dict) or set(data) != {"actions"}:
                        raise selfservice.Denied("invalid tool plan")
                    return self.senden(201, selfservice.propose(app, data["actions"]))
                match = re.fullmatch(r"/v1/selfservice/plans/([0-9a-f]{24})", path)
                if match and meth == "GET":
                    return self.senden(200, selfservice.status(app, match.group(1)))
                match = re.fullmatch(r"/v1/selfservice/execute/([0-9a-f]{24})", path)
                if match and meth == "POST":
                    # No approval route is exposed to an AI or other HTTP client.
                    return self.senden(200, selfservice.execute(app, match.group(1)))
                return self.senden(404, {"error": "unknown selfservice operation"})
            except selfservice.Denied:
                return self.senden(403, {"error": "selfservice denied: approval or policy"})
            except FileExistsError:
                return self.senden(409, {"error": "approval already consumed"})
        c = core.db()
        if path == "/v1/models":
            ids = ["omnipool-auto"] + ["omnipool-" + x for x in core.KLASSEN]
            ids += ["%s/%s" % r for r in c.execute("SELECT provider, model FROM modell WHERE status='ok' AND COALESCE(faehigkeit,'chat')='chat' ORDER BY provider, model LIMIT 300")]
            return self.senden(200, {"object": "list", "data": [{"id": i, "object": "model", "owned_by": "omnipool"} for i in ids]})
        if path.startswith("/x/"):
            return self.durchreichen(meth, path, app)
        b = self.json_body()
        if path == "/v1/messages/count_tokens":
            return self.senden(200, {"input_tokens": len(json.dumps(b)) // 4})
        anth = path == "/v1/messages"
        if path not in ("/v1/chat/completions", "/v1/messages"):
            return self.senden(404, {"error": "unbekannt"})
        ob = a2o(b) if anth else b
        stream = bool(b.get("stream"))
        klasse, _why = gehirn.klassifiziere(ob, hs.get("klasse", "auto"))
        cands = waehle_kandidaten(c, ob, klasse)
        if not cands:
            return self.senden(503, {"error": {"type": "overloaded_error", "message": 'Catalog empty: initial run still in progress or no key (see API-OMNI-BRAIN)'}})
        r = beschaffe(c, cands, {k: v for k, v in ob.items() if k != "stream"} if anth else ob, stream and not anth, app, klasse)
        if r[0] is None:
            return self.senden(502, {"error": {"type": "api_error", "message": 'All candidates failed: ' + "; ".join(r[1][:6])}})
        res, p, m, t0 = r
        route = {"X-Omnipool-Route": "%s/%s" % (p, m), "X-Omnipool-Klasse": klasse}
        if stream and not anth:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            for kk, v in route.items():
                self.send_header(kk, v)
            self.end_headers()
            self.close_connection = True
            ok = False
            try:
                for ln in res:
                    self.wfile.write(ln)
                    self.wfile.flush()
                    ok = ok or b"[DONE]" in ln
            except OSError:
                pass
            gehirn.lerne(c, app, klasse, p, m, ok, time.time() - t0)
            return
        u = res.get("usage") or {}
        gehirn.lerne(c, app, klasse, p, m, True, time.time() - t0, u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        if anth:
            msg = o2a(res, b.get("model", "omnipool-auto"))
            return self.senden(200, sse(msg), "text/event-stream", route) if stream else self.senden(200, msg, extra=route)
        self.senden(200, res, extra=route)

    def durchreichen(self, meth, path, app):
        """/x/<provider>/<rest>: the request goes to the provider's own API with one of its keys; the answer is relayed unchanged"""
        parts = path.split("/", 3) + ["", ""]
        prov, rest = parts[2], parts[3]
        if prov not in core.custom() and prov not in core.TC.FREE:
            return self.senden(404, {"error": 'Unknown provider'})
        if ".." in rest or "//" in rest or not core.tokens_of(prov):
            return self.senden(400, {"error": 'Path or key invalid'})
        raw = self.body() if meth in ("POST", "PUT") else None
        for _ in range(2):
            tok = gehirn.key_waehlen(prov, "x:" + rest.split("/")[0])
            if not tok:
                break
            url = base_of(prov) + "/" + rest + (("?" + self.path.split("?", 1)[1]) if "?" in self.path else "")
            rq = urllib.request.Request(url, raw, {**core.auth_kopf(prov, tok), "Content-Type": self.headers.get("Content-Type", "application/json"), "User-Agent": "API-OMNI-BRAIN/1.0"}, method=meth)
            t0 = time.time()
            try:
                r = urllib.request.urlopen(rq, timeout=300)
                code, hdr = r.status, r.headers
            except urllib.error.HTTPError as e:
                r, code, hdr = e, e.code, e.headers
                if code in (429, 401, 403):
                    gehirn.limit(prov, "x:" + rest.split("/")[0], tok) if code == 429 else gehirn.key_ruhe(tok, 3600)
                    continue
            except Exception:  # noqa: BLE001
                return self.senden(502, {"error": 'Provider unreachable'})
            self.send_response(code)
            self.send_header("Content-Type", hdr.get("Content-Type", "application/octet-stream"))
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            n = 0
            try:
                for chunk in iter(lambda: r.read(65536), b""):
                    n += len(chunk)
                    self.wfile.write(chunk)
            except OSError:
                pass
            gehirn.lerne(core.db(), app, "x:" + prov, prov, rest.split("/")[0] or "-", code < 400, time.time() - t0, 0, n // 4, code)
            return
        self.senden(429, {"error": "All of the provider's keys are currently idle"})


def serve(port=None):
    port = port or core.settings()["port"]
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.daemon_threads = True
    threading.Thread(target=planer, daemon=True).start()
    srv.serve_forever()
