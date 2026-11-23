"""API-OMNI-BRAIN providers beyond the built-in list: a provider is DATA (a small JSON profile), not code. A new provider, or a token with an odd use (video, image, audio,
embedding, search ...), is onboarded by `entdecke`: it tries auth styles and well-known list/health paths, reads what the provider serves, and infers the capabilities
from model ids and OpenAPI paths; what it cannot infer, a strong model is asked (it sees only the response shape, never a token). Profiles live in
~/.local/share/omnipool/provider.d/<id>.json, their keys in keys-custom.env (mode 600). Liveness and auth are tested; content tests exist for chat only
(video/image jobs cost credits, so they are tested on request, not by default). No secret is ever printed; a redirect never carries the key to another host."""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HOME = os.path.expanduser("~")
DATA = os.environ.get("OMNIPOOL_HOME", os.path.join(HOME, ".local", "share", "omnipool"))
DIR = os.path.join(DATA, "provider.d")
KEYS = os.path.join(DATA, "keys-custom.env")
CAPS = [("video", r"video|veo|sora|kling|runway|luma|hunyuan|\bwan[-\d]|cosmos|mochi|cogvideo|pika|hailuo|seedance"),
        ("bild", r"image|flux|sdxl|stable-diffusion|dall|imagen|diffus|sana|kandinsky|midjourney|ideogram|recraft"),
        ("audio", r"whisper|tts|speech|voice|\basr\b|parakeet|canary|orpheus|transcri|riva|audio|music|eleven|suno"),
        ("embedding", r"embed|\be5-|bge-|retriev"), ("rerank", r"rerank"), ("sicherheit", r"guard|safety|moderat"),
        ("vision", r"\bvl\b|-vl-|vision|vlm|paligemma|llava|neva|\bocr\b|parse"), ("suche", r"search|serp|tavily|exa\b|brave")]
STYLES = [("Authorization", "Bearer "), ("x-api-key", ""), ("api-key", ""), ("X-API-Key", ""), ("Authorization", "Token "), ("x-goog-api-key", ""), ("Authorization", "Key ")]
PATHS = ["/models", "/v1/models", "/openapi.json", "/v1/openapi.json", "/health", "/v1/health", "/me", "/v1/me", "/user", "/account", "/v1/account", ""]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_OPEN = urllib.request.build_opener(_NoRedirect)


def infer(model_id):
    for cap, rx in CAPS:
        if re.search(rx, model_id, re.I):
            return cap
    return "chat"


def http(method, url, headers=None, body=None, timeout=30):
    """-> (status, bytes, response headers); status 0 = no answer. Redirects are not followed (the key must not travel to another host)."""
    rq = urllib.request.Request(url, body, {"User-Agent": "API-OMNI-BRAIN/1.0", **(headers or {})}, method=method)
    try:
        with _OPEN.open(rq, timeout=timeout) as r:
            return r.status, r.read(8 << 20), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(65536), dict(e.headers)
    except Exception:  # noqa: BLE001
        return 0, b"", {}


def liste():
    out = {}
    try:
        for f in sorted(os.listdir(DIR)):
            if f.endswith(".json"):
                try:
                    d = json.load(open(os.path.join(DIR, f)))
                    out[d["id"]] = d
                except (OSError, ValueError, KeyError):
                    pass
    except OSError:
        pass
    return out


def speichere(p):
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    with open(os.path.join(DIR, p["id"] + ".json"), "w") as f:
        json.dump(p, f, indent=1)


def keys():
    out = {}
    try:
        for ln in open(KEYS):
            m = re.match(r"^([A-Z0-9_]+)=(.+)$", ln.strip())
            if m:
                out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


def _schreibe(d):
    os.makedirs(DATA, mode=0o700, exist_ok=True)
    if os.path.exists(KEYS):
        import shutil
        shutil.copy2(KEYS, KEYS + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
    fd = os.open(KEYS + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("".join("%s=%s\n" % kv for kv in d.items()))
    os.replace(KEYS + ".tmp", KEYS)


def key_save(pid, token):
    """-> slot name; the same token twice is stored once"""
    d = keys()
    mine = [s for s in d if s.startswith(pid.upper() + "_KEY")]
    for s in mine:
        if d[s] == token:
            return s
    slot = "%s_KEY%d" % (pid.upper(), len(mine) + 1)
    d[slot] = token
    _schreibe(d)
    return slot


def key_remove(slot, h8):
    import hashlib
    d = keys()
    if slot in d and hashlib.sha256(d[slot].encode()).hexdigest()[:8] == h8:
        del d[slot]
        _schreibe(d)
        return True
    return False


def tokens(pid):
    return [(s, v) for s, v in keys().items() if s.startswith(pid.upper() + "_KEY")]


def kopf(p, token):
    a = p.get("auth") or {"header": "Authorization", "prefix": "Bearer "}
    return {a["header"]: a["prefix"] + token}


def check(p, token):
    """-> {ok, status, models: [ids]}: one read-only GET on the profile's liveness path"""
    st, body, _h = http("GET", p["base"].rstrip("/") + (p.get("liveness") or "/models"), kopf(p, token))
    out = {"ok": 200 <= st < 300, "status": st, "models": []}
    if out["ok"]:
        out["models"] = _ids(body)
    return out


def _ids(body):
    try:
        js = json.loads(body)
    except ValueError:
        return []
    rows = js.get("data", js.get("models", js.get("result", js))) if isinstance(js, dict) else js
    ids = []
    for r in rows if isinstance(rows, list) else []:
        i = r if isinstance(r, str) else (r.get("id") or r.get("name") or r.get("model") if isinstance(r, dict) else None)
        if i:
            ids.append(str(i).replace("models/", ""))
    return sorted(set(ids))


def entdecke(base, token, label=None, analyst=None):
    """onboard an unknown provider from a base URL and one token -> profile dict (not yet saved) or {"fehler": ...}
    analyst(prompt) -> text is an optional strong model that classifies capabilities when the heuristics find none"""
    u = urllib.parse.urlparse(base if "//" in base else "https://" + base)
    if u.scheme not in ("http", "https") or not u.hostname:
        return {"fehler": 'no valid address'}
    root = "%s://%s%s" % (u.scheme, u.netloc, u.path.rstrip("/"))
    name = label or (u.hostname.split(".")[-2] if u.hostname.count(".") else u.hostname)
    pid = re.sub(r"[^a-z0-9]", "", name.lower())[:20] or "anbieter"
    gefunden = None
    for hdr, pre in STYLES:
        for path in PATHS:
            st, body, _ = http("GET", root + path, {hdr: pre + token}, None, 15)
            if 200 <= st < 300 and body[:1] in (b"{", b"["):
                gefunden = (hdr, pre, path, body)
                break
        if gefunden:
            break
    if not gefunden:
        return {"fehler": 'no list/health endpoint returned a common header (checked: %d header types x %d paths)' % (len(STYLES), len(PATHS))}
    hdr, pre, path, body = gefunden
    ids = _ids(body)
    caps = {}
    for i in ids:
        caps.setdefault(infer(i), []).append(i)
    try:
        for pth in json.loads(body).get("paths", {}) if path.endswith("openapi.json") else []:
            c = "video" if "video" in pth else "bild" if "image" in pth else "audio" if re.search(r"audio|speech|tts", pth) else "embedding" if "embed" in pth \
                else "chat" if "chat/completions" in pth else None
            if c:
                caps.setdefault(c, [])
    except (ValueError, AttributeError):
        pass
    hinweis = ""
    if not caps and analyst:
        txt = analyst('An unknown API responded to GET %s with (truncated):\n%s\n\nWhat capabilities does it have? Reply ONLY with a JSON list of: chat, video, image, audio, embedding, rerank, '
                      "vision, suche, sonstiges." % (path or "/", body[:2500].decode("utf-8", "replace")))
        caps = {c: [] for c in re.findall(r"chat|video|bild|audio|embedding|rerank|vision|suche|sonstiges", txt or "")} or {}
        hinweis = 'Capabilities estimated by the analysis model (response format only, never the key)'
    return {"id": pid, "label": label or pid, "base": root, "auth": {"header": hdr, "prefix": pre}, "liveness": path or "/", "faehigkeiten": sorted(caps) or ["unbekannt"],
            "modelle": ids[:400], "chat_path": "/chat/completions" if "chat" in caps else None, "hinweis": hinweis, "angelegt": time.time()}
