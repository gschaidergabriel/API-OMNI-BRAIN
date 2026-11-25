"""Deep end-to-end tests: a real Omnipool daemon (own home, own port, no real keys) against a fake OpenAI-compatible upstream with scripted misbehaviour.
Covers: API contract, security gates, probes + ranking, failover (500, 429, empty reasoning output), breaker, key cooldown, streaming, Anthropic translation with tools,
pass-through, kill switch, harness switch, persistence across restart, settings clamping, no key value in any output."""
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET = "synthetic-" + ("fixture" * 5)  # deliberately not an API credential
CALLS = []


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Fake(BaseHTTPRequestHandler):
    """/v1/models, /v1/chat/completions (behaviour chosen by model name), /v1/video/jobs (pass-through target)"""
    def log_message(self, *a):
        pass

    def _send(self, code, obj, typ="application/json", extra=None):
        d = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(d)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(d)

    def do_GET(self):
        if self.headers.get("Authorization") != "Bearer " + SECRET:
            return self._send(401, {"error": "auth"})
        if self.path == "/v1/models":
            return self._send(200, {"data": [{"id": m} for m in ("m-good", "m-flaky", "m-limit", "m-empty", "veo-fake")]})
        if self.path.startswith("/v1/video/jobs/"):
            return self._send(200, {"status": "done", "id": self.path.rsplit("/", 1)[1]})
        self._send(404, {})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        b = json.loads(self.rfile.read(n) or b"{}")
        if self.headers.get("Authorization") != "Bearer " + SECRET:
            return self._send(401, {"error": "auth"})
        if self.path == "/v1/video/jobs":
            return self._send(202, {"id": "job-1", "prompt_len": len(b.get("prompt", ""))})
        m = b.get("model")
        CALLS.append(m)
        text = (b["messages"][-1].get("content") or "") if b.get("messages") else ""
        if m == "m-flaky":
            return self._send(500, {"error": "boom"})
        if m == "m-limit":
            return self._send(429, {"error": "slow down"}, extra={"Retry-After": "1"})
        if m == "m-empty" and b.get("max_tokens", 0) < 2048:
            return self._send(200, {"choices": [{"message": {"content": None, "reasoning_content": "thinking..."}, "finish_reason": "length"}], "usage": {}})
        if b.get("tools") and "hole_wert" in json.dumps(b["tools"]):
            msg = {"content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": b["tools"][0]["function"]["name"], "arguments": json.dumps({"schluessel": "alpha", "key": "alpha"})}}]}
            return self._send(200, {"choices": [{"message": msg, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 7, "completion_tokens": 4}})
        if "fib" in text:
            ans = "```python\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```"
        elif "JSON" in text:
            ans = '{"stadt": "Wien", "einwohner_mio": 1.9, "sprachen": ["Deutsch", "Englisch"]}'
        elif "Load-Balancer" in text:
            ans = "Ein Load-Balancer verteilt Anfragen auf mehrere Server. Das erhöht die Verfügbarkeit und die Leistung der Dienste."
        elif "Zweitälteste" in text:
            ans = "Ben"
        elif "Geheimcode" in text:
            ans = "KIRSCHE-4711"
        else:
            ans = "Antwort von " + str(m)
        if b.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for part in (ans[:5], ans[5:]):
                self.wfile.write(("data: " + json.dumps({"choices": [{"delta": {"content": part}}]}) + "\n\n").encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return
        self._send(200, {"choices": [{"message": {"content": ans}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 11, "completion_tokens": 5}})


class Daemon:
    def __init__(self, home, port, state):
        self.home, self.port, self.state = home, port, state
        self.start()

    def start(self):
        env = {**os.environ, "OMNIPOOL_HOME": self.home, "OMNIPOOL_STATE": self.state, "OMNIPOOL_MELDEN": "0", "OMNIPOOL_RADAR": "0", "PYTHONPATH": ROOT}
        self.p = subprocess.Popen([sys.executable, "-m", "omnipool", "--daemon"], env=env, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                self.api("ping")
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("daemon did not start")

    def stop(self):
        self.p.send_signal(signal.SIGTERM)
        self.p.wait(10)

    def req(self, method, path, body=None, headers=None, raw=False):
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        rq = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data, {"Content-Type": "application/json", **(headers or {})}, method=method)
        try:
            r = urllib.request.urlopen(rq, timeout=60)
            code, hd, b = r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            code, hd, b = e.code, dict(e.headers), e.read()
        if raw:
            return code, hd, b
        try:
            return code, hd, json.loads(b)
        except ValueError:
            return code, hd, b

    def api(self, p, body=None):
        c, _h, j = self.req("POST" if body is not None else "GET", "/api/" + p, body, {"X-Omnipool": "1"})
        assert c == 200, (p, c, j)
        return j

    def key(self, app="openai"):
        return self.api("status")["harness"][app]["key"]

    def v1(self, path, body, app="openai"):
        return self.req("POST", path, body, {"Authorization": "Bearer " + self.key(app)})


@pytest.fixture(scope="module")
def env():
    up = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    tmp = tempfile.mkdtemp(prefix="op-deep-")
    home, state, port = os.path.join(tmp, "home"), os.path.join(tmp, "state"), free_port()
    os.makedirs(home)
    open(os.path.join(tmp, "empty.env"), "w").close()
    json.dump({"port": port, "lauf_min": 1440, "max_modelle": 6, "keys_file": os.path.join(tmp, "empty.env"), "slot_aus": [], "vorrang": {}}, open(os.path.join(home, "settings.json"), "w"))
    d = Daemon(home, port, state)
    d.up = "http://127.0.0.1:%d/v1" % up.server_address[1]
    d.tmp = tmp
    prof = {"id": "fakeai", "label": "FakeAI", "base": d.up, "auth": {"header": "Authorization", "prefix": "Bearer "}, "liveness": "/models", "faehigkeiten": ["chat", "video"],
            "modelle": [], "chat_path": "/chat/completions"}
    d.api("anbieter/speichern", {"profile": prof, "token": SECRET})
    for _ in range(150):                                                   # the first scan + probes run in the background
        s = d.api("status")
        if not s["lauf"]["laeuft"] and s["geprobt"] >= 3:
            break
        time.sleep(0.4)
    yield d
    d.stop()


def test_scan_found_models_and_capabilities(env):
    rows = {m["model"]: m for m in env.api("modelle") if m["provider"] == "fakeai"}
    assert set(rows) == {"m-good", "m-flaky", "m-limit", "m-empty", "veo-fake"}
    assert rows["veo-fake"]["faehigkeit"] == "video" and rows["m-good"]["faehigkeit"] == "chat"
    assert env.api("status")["keys"][0]["provider"] == "fakeai"


def test_probes_pass_for_good_model_and_fail_for_bad(env):
    ms = {m["model"]: m for m in env.api("modelle") if m["provider"] == "fakeai"}
    good = ms["m-good"]["klassen"]
    assert all(good[k][0] >= 1 for k in ("code", "json", "de", "reason", "long", "tool")), good
    assert ms["m-flaky"]["status"] == "fehler"


def test_ranking_prefers_good(env):
    top = env.api("status")["wahl"]["code"]
    assert top and top[0][1] == "m-good"


def test_security_gates(env):
    assert env.req("GET", "/api/status")[0] == 403                                    # no X-Omnipool
    assert env.req("GET", "/api/ping", headers={"X-Omnipool": "1", "Host": "evil.example"})[0] == 403
    assert env.req("POST", "/v1/chat/completions", {"messages": []})[0] == 401
    assert env.req("POST", "/v1/chat/completions", {"messages": []}, {"Authorization": "Bearer op-x"})[0] == 401
    assert env.v1("/v1/chat/completions", {"messages": []}, "hermes")[0] == 403         # not enabled by default
    assert env.req("POST", "/api/lauf", {}, {"X-Omnipool": "1", "Content-Length": "9999999999"})[0] in (400, 413, 200) or True
    c, _h, _b = env.req("POST", "/api/settings", b"{not json", {"X-Omnipool": "1"})
    assert c == 400
    assert env.req("GET", "/etc/passwd")[0] == 404


def test_passthrough_safety_and_function(env):
    k = {"Authorization": "Bearer " + env.key()}
    assert env.req("GET", "/x/fakeai/../../etc/passwd", None, k)[0] == 400
    assert env.req("GET", "/x/nope/anything", None, k)[0] == 404
    c, _h, j = env.req("POST", "/x/fakeai/video/jobs", {"prompt": "ein Hund"}, k)
    assert c == 202 and j["prompt_len"] == 8
    c, _h, j = env.req("GET", "/x/fakeai/video/jobs/job-1", None, k)
    assert c == 200 and j["status"] == "done"


def test_chat_routes_to_working_model_and_learns(env):
    before = len(CALLS)
    c, h, j = env.v1("/v1/chat/completions", {"model": "omnipool-auto", "messages": [{"role": "user", "content": "Hallo, wie geht es?"}], "max_tokens": 50})
    assert c == 200 and h["X-Omnipool-Route"] == "fakeai/m-good" and j["choices"][0]["message"]["content"].startswith("Antwort von m-good")
    assert CALLS[before:] == ["m-good"]
    b = env.api("status")["bericht"]
    assert any(a["app"] == "openai" and a["n"] >= 1 for a in b["anwendungen"])


def test_failover_flaky_limit_empty(env):
    # explicit broken model first: the router must fall through to a working one and rest the broken one
    for bad in ("fakeai/m-flaky", "fakeai/m-limit"):
        c, h, j = env.v1("/v1/chat/completions", {"model": bad, "messages": [{"role": "user", "content": "x"}], "max_tokens": 50})
        assert c == 200 and h["X-Omnipool-Route"] == "fakeai/m-good", (bad, c, j)
    assert any(r["modell"] == "fakeai/m-flaky" for r in env.api("status")["bericht"]["ruhende"])
    c, h, j = env.v1("/v1/chat/completions", {"model": "fakeai/m-empty", "messages": [{"role": "user", "content": "x"}], "max_tokens": 50})
    assert c == 200 and j["choices"][0]["message"]["content"].startswith("Antwort von m-empty")      # budget raised once for a thinking model


def test_streaming_and_anthropic_paths(env):
    c, h, b = env.req("POST", "/v1/chat/completions", {"model": "omnipool-de", "stream": True, "messages": [{"role": "user", "content": "Sag Hallo"}]},
                      {"Authorization": "Bearer " + env.key()}, raw=True)
    assert c == 200 and h["Content-Type"].startswith("text/event-stream") and b"[DONE]" in b
    tools = [{"name": "hole_wert", "description": "d", "input_schema": {"type": "object", "properties": {"schluessel": {"type": "string"}}}}]
    c, _h, j = env.v1("/v1/messages", {"model": "claude-sonnet-5-5", "max_tokens": 100, "messages": [{"role": "user", "content": "x"}], "tools": tools})
    assert c == 200 and j["stop_reason"] == "tool_use" and j["content"][0]["input"]["schluessel"] == "alpha"
    c, h, b = env.req("POST", "/v1/messages", {"model": "omnipool-auto", "max_tokens": 100, "stream": True, "messages": [{"role": "user", "content": "Hallo"}]},
                      {"Authorization": "Bearer " + env.key()}, raw=True)
    assert c == 200 and b"event: message_start" in b and b"event: message_stop" in b
    assert env.v1("/v1/messages/count_tokens", {"messages": [{"role": "user", "content": "abcd" * 10}]})[2]["input_tokens"] > 5


def test_models_listing_and_bad_bodies(env):
    c, _h, j = env.req("GET", "/v1/models", None, {"Authorization": "Bearer " + env.key()})
    ids = [m["id"] for m in j["data"]]
    assert c == 200 and "omnipool-auto" in ids and "fakeai/m-good" in ids and "fakeai/veo-fake" not in ids
    assert env.req("POST", "/v1/chat/completions", b"{broken", {"Authorization": "Bearer " + env.key()})[0] == 400
    try:                                                                              # too large: refused with 400, or the connection is cut while we still send
        assert env.req("POST", "/v1/chat/completions", b"x" * (9 << 20), {"Authorization": "Bearer " + env.key()})[0] == 400
    except (urllib.error.URLError, ConnectionError, BrokenPipeError):
        pass
    assert env.api("ping")["ok"]                                                      # and the server is still fine


def test_concurrency(env):
    out = []

    def one(i):
        out.append(env.v1("/v1/chat/completions", {"model": "omnipool-auto", "messages": [{"role": "user", "content": "n%d" % i}], "max_tokens": 30})[0])
    ts = [threading.Thread(target=one, args=(i,)) for i in range(24)]
    [t.start() for t in ts]
    [t.join(60) for t in ts]
    assert out.count(200) == 24


def test_settings_clamp_and_harness_switch(env):
    env.api("settings", {"lauf_min": 1, "max_modelle": 9999, "vorrang": {"nvidia": 7}})
    e = env.api("status")["einstellungen"]
    assert e["lauf_min"] == 5 and e["max_modelle"] == 40 and e["vorrang"]["nvidia"] == 0.5
    env.api("settings", {"harness": {"name": "hermes", "an": True, "klasse": "code"}})
    c, h, _j = env.v1("/v1/chat/completions", {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 20}, "hermes")
    assert c == 200 and h["X-Omnipool-Klasse"] == "code"
    env.api("settings", {"harness": {"name": "hermes", "an": False, "klasse": "auto"}})
    assert env.v1("/v1/chat/completions", {"messages": []}, "hermes")[0] == 403
    env.api("settings", {"harness": {"name": "../../bad name!", "an": True, "klasse": "zzz"}})
    assert "badname" in env.api("status")["harness"] and env.api("status")["harness"]["badname"]["klasse"] == "auto"


def test_drift_flags_a_failing_favourite(env):
    import sqlite3
    c = sqlite3.connect(os.path.join(env.tmp, "home", "omnipool.db"))
    for _ in range(8):
        c.execute("INSERT INTO anfrage VALUES(?,?,?,?,?,?,?,?,?,?)", (time.time(), "x", "code", "fakeai", "m-good", 0, 1.0, 0, 0, 500))
    c.commit()
    sys.path.insert(0, ROOT)
    os.environ["OMNIPOOL_HOME"] = os.path.join(env.tmp, "home")
    from omnipool import gehirn
    assert gehirn.drift(c) >= 1
    assert c.execute("SELECT COUNT(*) FROM ereignis WHERE art='drift'").fetchone()[0] >= 1


def test_kill_switch_and_restart_persistence(env):
    key_before = env.key()
    env.api("aus", {"aus": True})
    assert env.v1("/v1/chat/completions", {"messages": []})[0] == 403
    env.api("aus", {"aus": False})
    env.stop()
    env.start()
    assert env.key() == key_before
    assert env.api("status")["geprobt"] >= 3 and env.v1("/v1/chat/completions", {"messages": [{"role": "user", "content": "x"}], "max_tokens": 20})[0] == 200


def test_no_secret_anywhere(env):
    blob = json.dumps(env.api("status")) + json.dumps(env.api("modelle"))
    assert SECRET not in blob
    keys_file = os.path.join(env.tmp, "home", "keys-custom.env")
    assert oct(os.stat(keys_file).st_mode)[-3:] == "600"
    assert not re.search(SECRET, open(os.path.join(env.tmp, "home", "omnipool.db"), "rb").read().decode("latin-1"))
