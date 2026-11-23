"""Minimal Chrome DevTools client (stdlib only): headless Chrome, evaluate JS, collect console errors, screenshot. Used by the UI checks of Omnipool."""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request


class WS:
    def __init__(self, url):
        host, port, path = url[5:].split("/", 1)[0].rsplit(":", 1) + [None], None, None
        hp, path = url[5:].split("/", 1)
        host, port = hp.rsplit(":", 1)
        self.s = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hp, key)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]

    def send(self, text):
        d = text.encode()
        h = b"\x81"
        n = len(d)
        h += bytes([0x80 | n]) if n < 126 else b"\xfe" + struct.pack(">H", n) if n < 65536 else b"\xff" + struct.pack(">Q", n)
        m = os.urandom(4)
        self.s.sendall(h + m + bytes(b ^ m[i % 4] for i, b in enumerate(d)))

    def _read(self, n):
        while len(self.buf) < n:
            c = self.s.recv(1 << 20)
            if not c:
                raise ConnectionError("closed")
            self.buf += c
        o, self.buf = self.buf[:n], self.buf[n:]
        return o

    def recv(self):
        data = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            n = struct.unpack(">H", self._read(2))[0] if n == 126 else struct.unpack(">Q", self._read(8))[0] if n == 127 else n
            data += self._read(n)
            if b1 & 0x80:
                return data.decode("utf-8", "replace")


class Chrome:
    def __init__(self, width=1320, height=880):
        self.dir = tempfile.mkdtemp(prefix="op-chrome-")
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        self.port = sock.getsockname()[1]
        sock.close()
        exe = next(c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c))
        self.p = subprocess.Popen([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-sandbox", "--remote-debugging-port=%d" % self.port, "--user-data-dir=" + self.dir,
                                   "--window-size=%d,%d" % (width, height), "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=lambda: os.nice(10))
        for _ in range(100):
            try:
                self.targets = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % self.port, timeout=2))
                break
            except OSError:
                time.sleep(0.2)
        page = next(t for t in self.targets if t["type"] == "page")
        self.ws, self.i, self.errors = WS(page["webSocketDebuggerUrl"]), 0, []
        for m in ("Runtime.enable", "Page.enable", "Log.enable"):
            self.call(m)
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)

    def call(self, method, **params):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("method") == "Runtime.exceptionThrown":
                self.errors.append(m["params"]["exceptionDetails"].get("exception", {}).get("description", "exception")[:300])
            elif m.get("method") == "Runtime.consoleAPICalled" and m["params"]["type"] == "error":
                self.errors.append(" ".join(str(a.get("value", a.get("description", ""))) for a in m["params"]["args"])[:300])
            elif m.get("method") == "Log.entryAdded" and m["params"]["entry"]["level"] == "error":
                self.errors.append(m["params"]["entry"]["text"][:300] + " " + m["params"]["entry"].get("url", ""))
            elif m.get("id") == self.i:
                return m.get("result", m.get("error"))

    def goto(self, url, wait=1.5):
        self.call("Page.navigate", url=url)
        time.sleep(wait)

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        return (r.get("result") or {}).get("value") if isinstance(r, dict) else None

    def shot(self, path):
        r = self.call("Page.captureScreenshot", format="png")
        open(path, "wb").write(base64.b64decode(r["data"]))
        return path

    def close(self):
        try:
            self.p.terminate()
            self.p.wait(10)
        except Exception:  # noqa: BLE001
            self.p.kill()
        shutil.rmtree(self.dir, ignore_errors=True)
