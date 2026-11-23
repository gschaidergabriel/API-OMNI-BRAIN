#!/usr/bin/env python3
"""Headless token check + save for the key pool (~/.last-resort/keys.env). The popup (token_popup.py) is only a face on this.

  echo "<token>" | token_check.py check [--provider auto|groq|nvidia|mistral|openrouter|gemini|...]
  echo "<token>" | token_check.py save --provider P [--slot NAME]       (no --slot: first free slot, as many tokens per provider as you like)
  token_check.py slots [--provider P]          names only, never values
  token_check.py overview                      per provider: how many tokens, how many valid / in limit / refused (names, counts, hashes; never values)
  token_check.py verify [--provider P]         one read-only call per stored token, results go to the state file
  token_check.py remove --slot NAME --hash8 H  take one token out of keys.env (backup first; the hash must match)

The token is read from stdin (or a hidden prompt on a tty), never from argv, never printed, never logged; only its name and an 8-character hash appear.
`check` makes one read-only call (a model list, an account lookup, or for NVIDIA/SambaNova a 1-token chat because their model lists are public); it never buys or changes anything.
Provider list (links, notes, slot patterns): providers_free.json next to this file; layout helpers: keypool.py.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keypool  # noqa: E402

KEYS_FILE = os.environ.get("KEYS_FILE", os.path.expanduser("~/.last-resort/keys.env"))
BASE = os.environ.get("TOKEN_CHECK_BASE", "")          # tests only: send every call to this local server instead

# paid providers: built in, never synced, shown only when the vault already holds one of their slots
_PAID = {
    "deepseek": ("DeepSeek", "https://api.deepseek.com/v1/models", ["DEEPSEEK_API_KEY", "DEEPSEEK2_API_KEY"], r"^$"),
    "together": ("Together", "https://api.together.xyz/v1/models", ["TOGETHER_API_KEY"], r"^$"),
    "runpod": ("RunPod", "https://api.runpod.io/graphql", ["RUNPOD_TRAIN_API_KEY"], r"^rpa_"),
}
PINFO = {p["id"]: p for p in keypool.providers()}          # full records of the free providers
PROVIDERS = {p["id"]: (p["label"], p["check"]["url"], list(p["slots"]), p["prefix"]) for p in keypool.providers()}
PROVIDERS.update(_PAID)
ORDER = [p["id"] for p in keypool.providers()] + list(_PAID)
FREE = [p["id"] for p in keypool.providers()]


def keys_file():
    return KEYS_FILE


def _dir():
    return os.path.dirname(os.path.abspath(KEYS_FILE))


def hash8(token):
    return hashlib.sha256(token.encode()).hexdigest()[:8]


def detect(token):
    """provider by key prefix, or None when the prefix says nothing (then the caller must choose)"""
    for name in ORDER:
        if PROVIDERS[name][3] != r"^$" and re.search(PROVIDERS[name][3], token):
            return name
    return None


def _http(url, token, body=None, timeout=25, headers=None, method=None):
    if BASE:                                                   # tests only
        host, _, rest = url.split("//", 1)[1].partition("/")
        url = f"{BASE}/{host}/{rest}"
    hdr = {"Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "token-check/2"}
    if headers is not None:
        hdr = {**{k: v for k, v in hdr.items() if k != "Authorization"}, **{k: v.replace("{token}", token) for k, v in headers.items()}}
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method or ("POST" if body is not None else "GET"), headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read()[:200].decode("utf8", "replace")}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {"error": str(getattr(e, "reason", e))[:120]}
    except ValueError:
        return 200, {}


def _scrub(text, token):
    return str(text).replace(token, "<token>") if token else str(text)


_REFUSE = {401: "refused: wrong or revoked token", 403: "refused: token not allowed", 402: "token valid but no credit or subscription", 429: "rate-limited right now"}


def _fail(out, st, js, token):
    out["error"] = _scrub(_REFUSE.get(st, f"no answer (HTTP {st}) {js.get('error', '') if isinstance(js, dict) else ''}"), token)
    return out


def _ids(data, key="id"):
    return sorted({m.get(key) for m in data if isinstance(m, dict) and m.get(key)}) if isinstance(data, list) else []


def check(provider, token):
    """-> {ok, provider, label, hash8, status, models: [str], extra: {..}, error}. One read-only call (two for RunPod, OpenRouter, GitHub, NVIDIA/SambaNova)."""
    token = token.strip()
    out = {"ok": False, "provider": provider, "hash8": hash8(token), "status": 0, "models": [], "extra": {}, "error": ""}
    if not token or any(c.isspace() for c in token) or len(token) < 12:
        out["error"] = "that does not look like a token (empty, spaces or too short)"
        return out
    if provider == "auto":
        provider = detect(token)
        if provider is None:
            out["error"] = "cannot tell the provider from the prefix: choose one"
            return out
        out["provider"] = provider
    if provider not in PROVIDERS:
        out["error"] = "unknown provider"
        return out
    label, url, _slots, _ = PROVIDERS[provider]
    out["label"] = label
    try:
        _run_check(provider, url, token, out)
    finally:
        note_status(token, provider, out)
    return out


def _run_check(provider, url, token, out):
    if provider == "runpod":
        st, js = _http(url, token, {"query": "query { myself { clientBalance currentSpendPerHr } }"})
        out["status"] = st
        me = ((js.get("data") or {}).get("myself")) if isinstance(js, dict) else None
        if st != 200 or not me:
            out["error"] = _scrub("RunPod refused the token" if st in (200, 401, 403) else f"no answer ({js.get('error', '')})", token)
            return
        out["ok"] = True
        out["extra"] = {"balance_usd": me.get("clientBalance"), "spend_per_hour_usd": me.get("currentSpendPerHr")}
        st2, js2 = _http(url, token, {"query": "query { gpuTypes { id displayName memoryInGb securePrice communityPrice } }"})
        gpus = ((js2.get("data") or {}).get("gpuTypes")) or []
        gpus = [g for g in gpus if g.get("securePrice") or g.get("communityPrice")]
        gpus.sort(key=lambda g: (g.get("securePrice") or g.get("communityPrice") or 1e9))
        out["models"] = ["%s  %sGB  secure %s  community %s USD/h" % (g.get("displayName"), g.get("memoryInGb"), g.get("securePrice"), g.get("communityPrice")) for g in gpus]
        return
    spec = (PINFO.get(provider) or {}).get("check") or {"type": "openai_models", "url": url}
    kind = spec["type"]
    if kind == "chat1":
        st, js = _chat1(spec, token)
        out["status"] = st
        if st != 200:
            _fail(out, st, js, token)
            return
        lst, jl = _http(spec["list_url"], token)                     # the list itself is public for these two: only the chat proves the token
        out["ok"] = True
        out["models"] = _ids(jl.get("data", jl) if isinstance(jl, dict) else jl)
        out["extra"] = {"model_count": len(out["models"])}
        return
    hdr = {"x-goog-api-key": "{token}"} if kind == "gemini_models" else None
    st, js = _http(url, token, headers=hdr)
    out["status"] = st
    if st != 200:
        _fail(out, st, js, token)
        return
    if kind == "cloudflare":
        if not (isinstance(js, dict) and js.get("success") and (js.get("result") or {}).get("status") == "active"):
            out["error"] = "refused: token not active"
            return
        out["ok"] = True
        return
    if kind == "hf":
        out["ok"] = True
        return
    if kind == "tavily":
        key = (js.get("key") or {}) if isinstance(js, dict) else {}
        out["ok"] = True
        out["extra"] = {k: key.get(k) for k in ("usage", "limit") if key.get(k) is not None}
        return
    if kind == "github":
        lst, jl = _http(spec["list_url"], token)
        out["ok"] = True
        out["models"] = _ids(jl if isinstance(jl, list) else jl.get("data", []) if isinstance(jl, dict) else [])
        out["extra"] = {"model_count": len(out["models"])}
        return
    if kind == "gemini_models":
        ids = sorted({str(m.get("name", "")).replace("models/", "") for m in (js.get("models") or []) if isinstance(m, dict) and m.get("name")})
    elif kind == "cohere_models":
        ids = sorted({m.get("name") for m in (js.get("models") or []) if isinstance(m, dict) and m.get("name")})
    else:
        data = js.get("data", js) if isinstance(js, dict) else js
        ids = _ids(data)
    out["ok"] = True
    out["models"] = ids
    out["extra"] = {"model_count": len(ids)}
    if kind == "openrouter":
        out["extra"]["free_models"] = len([i for i in ids if i.endswith(":free")])
        st2, js2 = _http(spec["auth_url"], token)
        d = (js2.get("data") if isinstance(js2, dict) else None) or {}
        if st2 == 200 and d:
            out["extra"].update(limit_remaining=d.get("limit_remaining"), is_free_tier=d.get("is_free_tier"))
        elif st2 in (401, 403):
            out["ok"], out["error"] = False, "refused: wrong or revoked token"


def _chat1(spec, token):
    body = {"model": spec["model"], "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}
    st, js = _http(spec["url"], token, body)
    if st in (404, 410) and spec.get("list_url"):                    # the chosen model was retired: pick a current chat model from the public list
        _s, jl = _http(spec["list_url"], token)
        ids = _ids(jl.get("data", jl) if isinstance(jl, dict) else jl)
        ok_ids = [i for i in ids if not re.search(r"embed|rerank|guard|safety|vl|reward|parse|nv-", i, re.I)]
        pick = [i for i in ok_ids if re.search(r"instruct|chat|nemotron|llama|gpt-oss", i, re.I)] or ok_ids
        if pick:
            st, js = _http(spec["url"], token, {**body, "model": pick[0]})
    return st, js


# --- state + audit (counts and hashes only) --------------------------------------------------------------------------------
def state_path():
    return os.path.join(_dir(), "token-state.json")


def load_state():
    try:
        return json.load(open(state_path()))
    except (OSError, ValueError):
        return {}


def _write_json(path, obj):
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def note_status(token, provider, out, origin=None):
    """remember the last check result per token hash: ok / limit / invalid / unknown (network). Best effort, never raises."""
    try:
        st = out.get("status", 0)
        status = "ok" if out.get("ok") else "limit" if st == 429 else "invalid" if st in (401, 402, 403) or "refused" in (out.get("error") or "") else "unknown"
        s = load_state()
        h = hash8(token)
        rec = s.get(h, {})
        rec.update(provider=provider, status=status, checked=int(time.time()))
        rec.setdefault("first_seen", int(time.time()))
        if origin:
            rec.setdefault("origin", origin)
        s[h] = rec
        _write_json(state_path(), s)
    except OSError:
        pass


def audit(action, provider, slot, h8, extra=""):
    try:
        p = os.path.join(_dir(), "token-audit.log")
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write("%s %s %s %s %s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), action, provider, slot, h8, extra))
    except OSError:
        pass


# --- slots ----------------------------------------------------------------------------------------------------------------
def _vault_values():
    return keypool.read_env(KEYS_FILE)


def slot_owner(slot):
    pid = keypool.provider_of(slot)
    if pid:
        return pid
    return next((p for p, v in _PAID.items() if slot in v[2]), None)


def slots(provider=None):
    """slot names with whether keys.env already has a value there (names only): the old names, then numbered ones in use, then the next free one"""
    vals = _vault_values()
    out = []
    for p in ([provider] if provider in PROVIDERS else ORDER):
        names = list(PROVIDERS[p][2])
        if p in PINFO:
            names += [n for n in keypool.numbered(PINFO[p], vals)]
            nxt = keypool.next_slot(p, vals)
            if nxt not in names:
                names.append(nxt)
        out += [{"slot": n, "in_use": bool(vals.get(n))} for n in names]
    return out


def vault_items():
    """what the vault already holds, for display: provider, label, slot, 8-char hash, last known status. Never the value."""
    vals, st, out = _vault_values(), load_state(), []
    for p in ORDER:
        names = keypool.names_of(p, vals) if p in PINFO else [n for n in PROVIDERS[p][2] if vals.get(n)]
        for n in names:
            h = hash8(vals[n])
            out.append({"provider": p, "label": PROVIDERS[p][0], "slot": n, "hash8": h, "status": st.get(h, {}).get("status", "unknown")})
    return out


def vault_token(slot):
    """the stored value of one slot, for handing to a check call inside the process that owns the window; never printed"""
    return _vault_values().get(slot, "")


def _ok_hint(pid, lang="en"):
    """provider-specific caveat for a 'valid' key (Mistral: the models list answers, the chat needs a plan: 402). A hint only, nothing is bought."""
    p = keypool.by_id(pid)
    return (p.get("ok_hint_" + lang) or p.get("ok_hint_en") or "") if p else ""


def overview():
    """per provider: counts only. -> [{provider, label, total, ok, limit, invalid, unknown, hashes}] (paid providers only when present)"""
    items = vault_items()
    res = []
    for p in ORDER:
        mine = [i for i in items if i["provider"] == p]
        if not mine and p in _PAID:
            continue
        res.append({"provider": p, "label": PROVIDERS[p][0], "total": len(mine), "ok": sum(i["status"] == "ok" for i in mine), "limit": sum(i["status"] == "limit" for i in mine),
                    "invalid": sum(i["status"] == "invalid" for i in mine), "unknown": sum(i["status"] == "unknown" for i in mine), "hashes": [i["hash8"] for i in mine],
                    "hint_en": _ok_hint(p, "en") if any(i["status"] == "ok" for i in mine) else "",
                    "hint_de": _ok_hint(p, "de") if any(i["status"] == "ok" for i in mine) else ""})
    return res


# --- writing keys.env -------------------------------------------------------------------------------------------------------
class _Lock:
    def __enter__(self):
        os.makedirs(_dir(), mode=0o700, exist_ok=True)
        self.f = open(os.path.join(_dir(), ".keys.lock"), "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def vault_refresh():
    """Only where the claude-vault lives (A): its FREE source-backed profiles are sealed against the exact set of authorized values, so a changed
    keys.env makes unlock fail until they are re-sealed. Do exactly that for the free profiles whose values changed (backup of vault.v2.enc first);
    paid and `put` profiles are never touched. Best effort, never raises, never prints a value. Returns the re-sealed profile names or None."""
    d = os.path.expanduser("~/.claude/vault")
    if os.environ.get("TOKEN_NO_VAULT_REFRESH") or not os.path.exists(os.path.join(d, "claude_vault.py")):
        return None
    try:
        sys.path.insert(0, d)
        try:
            import claude_vault as cv
        finally:
            sys.path.remove(d)
        pol = cv.policy()
        env = cv._read_env_lenient()
        ents = env["providers"]
        changed = []
        for name, r in pol["profiles"].items():
            if r.get("class") != "free" or not r.get("sources") or (isinstance(ents.get(name), dict) and ents[name].get("mode") == "put"):
                continue
            try:
                vals = cv.source_list(name, pol)
            except cv.VaultError:
                continue
            try:
                cur = cv.unlock(name, pol)
            except cv.VaultError:
                cur = None
            if cur != vals:
                ents[name] = cv._encode(name, vals, "src", pol)
                changed.append(name)
        if changed:
            vf = str(cv.vault_file())
            bk = vf + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
            shutil.copy2(vf, bk)
            os.chmod(bk, 0o600)
            cv._save(env)
            audit("vault_refresh", ",".join(changed), "-", "-", "free profiles re-sealed")
        return changed
    except Exception as e:                                             # the vault must never break saving a token
        audit("vault_refresh_failed", "-", "-", "-", type(e).__name__)
        return None


def _backup():
    if not os.path.exists(KEYS_FILE):
        return None
    base = KEYS_FILE + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
    backup, i = base, 1
    while os.path.exists(backup):                                      # two saves within one second must not overwrite the first backup
        backup, i = f"{base}-{i}", i + 1
    shutil.copy2(KEYS_FILE, backup)
    os.chmod(backup, 0o600)
    return backup


def _atomic_write(lines):
    tmp = KEYS_FILE + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, KEYS_FILE)
    os.chmod(KEYS_FILE, 0o600)


def save(provider, token, slot=None, origin="local"):
    """write NAME=token into keys.env: backup first, atomic replace, mode 600, audit line without the value. A token that is already stored (any slot) is not stored twice.
    -> {slot, hash8, backup, replaced, duplicate}"""
    token = token.strip()
    if provider not in PROVIDERS:
        raise ValueError("unknown provider")
    if not re.match(r"^\S{12,}$", token):
        raise ValueError("not a plausible token")
    with _Lock():
        vals = _vault_values()
        mine = keypool.names_of(provider, vals) if provider in PINFO else [n for n in PROVIDERS[provider][2] if vals.get(n)]
        if slot is not None and slot_owner(slot) != provider:
            raise ValueError("slot does not belong to this provider")
        dup = next((n for n in mine if vals.get(n) == token), None)
        if dup and (slot is None or slot == dup or not vals.get(slot)):        # already stored: a free slot is never used for a second copy
            return {"slot": dup, "hash8": hash8(token), "backup": None, "replaced": False, "duplicate": True}
        if slot is None:
            slot = keypool.next_slot(provider, vals) if provider in PINFO else next((n for n in PROVIDERS[provider][2] if not vals.get(n)), PROVIDERS[provider][2][0])
        if slot_owner(slot) != provider:
            raise ValueError("slot does not belong to this provider")
        lines = open(KEYS_FILE).read().splitlines() if os.path.exists(KEYS_FILE) else []
        backup = _backup()
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith(slot + "="):
                lines[i], replaced = f"{slot}={token}", True
        if not replaced:
            lines.append(f"{slot}={token}")
        _atomic_write(lines)
        audit("save", provider, slot, hash8(token), "replaced" if replaced else "new " + origin)
    vault_refresh()
    return {"slot": slot, "hash8": hash8(token), "backup": os.path.basename(backup) if backup else None, "replaced": replaced, "duplicate": False}


def remove(slot, h8):
    """take one NAME=value line out of keys.env; only when the stored value's hash equals h8 (so a wrong slot cannot be removed by accident)"""
    with _Lock():
        vals = _vault_values()
        if not vals.get(slot) or hash8(vals[slot]) != h8:
            raise ValueError("slot is empty or the hash does not match")
        lines = [line for line in open(KEYS_FILE).read().splitlines() if not line.startswith(slot + "=")]
        backup = _backup()
        _atomic_write(lines)
        audit("remove", slot_owner(slot) or "?", slot, h8)
    vault_refresh()
    return {"slot": slot, "hash8": h8, "backup": os.path.basename(backup) if backup else None}


def verify_all(provider=None):
    """one check per stored token (no output of values); updates the state file. -> overview()"""
    vals = _vault_values()
    for it in vault_items():
        if (provider and it["provider"] != provider) or it["provider"] not in FREE:      # paid/money providers are never checked in a round, only on an explicit single check
            continue
        check(it["provider"], vals[it["slot"]])
    return overview()


def _read_token():
    if sys.stdin.isatty():
        import getpass
        return getpass.getpass("token (hidden): ")
    return sys.stdin.readline().strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--provider", default="auto")
    s = sub.add_parser("save"); s.add_argument("--provider", required=True); s.add_argument("--slot")
    sl = sub.add_parser("slots"); sl.add_argument("--provider")
    sub.add_parser("overview")
    v = sub.add_parser("verify"); v.add_argument("--provider")
    r = sub.add_parser("remove"); r.add_argument("--slot", required=True); r.add_argument("--hash8", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "slots":
        print(json.dumps(slots(a.provider)))
        return 0
    if a.cmd == "overview":
        print(json.dumps(overview()))
        return 0
    if a.cmd == "verify":
        print(json.dumps(verify_all(a.provider)))
        return 0
    if a.cmd == "remove":
        try:
            print(json.dumps({"removed": True, **remove(a.slot, a.hash8)}))
            return 0
        except ValueError as e:
            print(json.dumps({"removed": False, "error": str(e)}))
            return 1
    tok = _read_token()
    if a.cmd == "check":
        r = check(a.provider, tok)
        print(json.dumps(r))
        return 0 if r["ok"] else 1
    r = check(a.provider, tok)                       # a token is only saved after it passed the check
    if not r["ok"]:
        print(json.dumps({"saved": False, "error": r["error"]}))
        return 1
    print(json.dumps({"saved": True, **save(r["provider"], tok, a.slot)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
