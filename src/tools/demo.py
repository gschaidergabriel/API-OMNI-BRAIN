"""Demo daemon with seeded data for UI checks: fake upstream + a real Omnipool daemon in a temp home. Prints JSON {port, key, home} and keeps running."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import test_deep as T  # noqa: E402


def start(tmp=None):
    up = ThreadingHTTPServer(("127.0.0.1", 0), T.Fake)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    tmp = tmp or tempfile.mkdtemp(prefix="op-demo-")
    home, state, port = os.path.join(tmp, "home"), os.path.join(tmp, "state"), T.free_port()
    os.makedirs(home, exist_ok=True)
    open(os.path.join(tmp, "empty.env"), "w").close()
    json.dump({"port": port, "lauf_min": 1440, "max_modelle": 6, "keys_file": os.path.join(tmp, "empty.env"), "slot_aus": [], "vorrang": {}}, open(os.path.join(home, "settings.json"), "w"))
    d = T.Daemon(home, port, state)
    d.up = "http://127.0.0.1:%d/v1" % up.server_address[1]
    prof = {"id": "demoai", "label": "DemoAI", "base": d.up, "auth": {"header": "Authorization", "prefix": "Bearer "}, "liveness": "/models", "faehigkeiten": ["chat", "video"], "modelle": [],
            "chat_path": "/chat/completions"}
    d.api("anbieter/speichern", {"profile": prof, "token": T.SECRET})
    for _ in range(150):
        s = d.api("status")
        if not s["lauf"]["laeuft"] and s["geprobt"] >= 3:
            break
        time.sleep(0.4)
    d.api("settings", {"harness": {"name": "hermes", "an": True, "klasse": "auto"}})
    for i in range(14):
        d.v1("/v1/chat/completions", {"model": "omnipool-auto", "messages": [{"role": "user", "content": "Frage %d zur Programmierung: schreibe eine Funktion" % i}], "max_tokens": 40}, "openai" if i % 3 else "hermes")
    d.v1("/v1/chat/completions", {"model": "demoai/m-flaky", "messages": [{"role": "user", "content": "x"}], "max_tokens": 20})
    return d, tmp


if __name__ == "__main__":
    d, tmp = start()
    print(json.dumps({"port": d.port, "key": d.key(), "home": tmp}), flush=True)
    while True:
        time.sleep(60)
