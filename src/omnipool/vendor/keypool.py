#!/usr/bin/env python3
"""Key pool layout shared by the token popup, the sync and the routers (llm.py, mund_say.py): which slot names belong to which free provider.

A provider owns a fixed list of old slot names (GROQ_API_KEY, GROQ2_API_KEY, GROQ3_API_KEY ...) and a numbered pattern for every further token
(GROQ4_API_KEY, GROQ5_API_KEY ...). Old names never change meaning; new tokens only ever get new numbers. Values are never printed.

  expand(names, keys)  -> values for a router: the given names first (their order kept), then every EXTRA numbered slot of the same provider
  next_slot(p, keys)   -> first free old slot, else the next number
"""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROVIDERS_FILE = os.environ.get("TOKEN_PROVIDERS", os.path.join(HERE, "providers_free.json"))
KEYS_FILE = os.environ.get("KEYS_FILE", os.path.expanduser("~/.last-resort/keys.env"))
DEAD_FILE = os.environ.get("KEYPOOL_DEAD", os.path.expanduser("~/.last-resort/dead-keys.json"))
_LINE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def load_providers(path=None):
    """-> ordered list of provider dicts, each with a compiled 'rx' for its numbered slots"""
    try:
        data = json.load(open(path or PROVIDERS_FILE))
    except (OSError, ValueError):
        return []
    out = []
    for p in data.get("providers", []):
        pat = p.get("pattern")
        p["rx"] = re.compile("^" + re.escape(pat).replace(re.escape("{n}"), r"(\d+)") + "$") if pat else None
        out.append(p)
    return out


_CACHE = {}


def providers():
    key = PROVIDERS_FILE
    if key not in _CACHE:
        _CACHE[key] = load_providers()
    return _CACHE[key]


def by_id(pid):
    return next((p for p in providers() if p["id"] == pid), None)


def read_env(path=None):
    """ordered {NAME: value} of a keys.env style file (comments and blank lines skipped)"""
    out = {}
    try:
        for line in open(path or KEYS_FILE):
            m = _LINE.match(line.strip())
            if m and not line.lstrip().startswith("#"):
                out[m.group(1)] = m.group(2).strip().strip("\"'")
    except OSError:
        pass
    return out


def provider_of(name):
    """provider id owning this slot name (old list or numbered pattern), else None"""
    for p in providers():
        if name in p["slots"] or (p["rx"] and p["rx"].match(name)):
            return p["id"]
    return None


def numbered(p, keys):
    """the numbered slots (n >= first_n) of provider p that exist in keys, ascending"""
    if not p or not p["rx"]:
        return []
    found = []
    for k in keys:
        m = p["rx"].match(k)
        if m and int(m.group(1)) >= p.get("first_n", 2):
            found.append((int(m.group(1)), k))
    return [k for _n, k in sorted(found)]


def names_of(pid, keys):
    """all slot names of a provider that hold a value in keys: old list first, then the numbered ones"""
    p = by_id(pid)
    if not p:
        return []
    return [n for n in p["slots"] if keys.get(n)] + [n for n in numbered(p, keys) if keys.get(n)]


def next_slot(pid, keys, avoid=()):
    """first unused old slot (not in avoid), else the lowest unused number from first_n"""
    p = by_id(pid)
    for n in p["slots"]:
        if not keys.get(n) and n not in avoid:
            return n
    i = p.get("first_n", 2)
    while True:
        name = p["pattern"].format(n=i)
        if not keys.get(name) and name not in avoid:
            return name
        i += 1


def dead_slots(keys):
    """slot names that rest ('dead' = refused by the provider, e.g. 401) until their value changes. dead-keys.json: {SLOT: {"hash8": first 8 hex of sha256(value), "reason": ...}}.
    A slot only counts as dead while the stored value still has that hash: a replaced token revives the slot by itself. The value itself is never kept or deleted."""
    try:
        data = json.load(open(DEAD_FILE))
    except (OSError, ValueError):
        return set()
    out = set()
    for slot, info in (data.items() if isinstance(data, dict) else []):
        v = keys.get(slot)
        if v and isinstance(info, dict) and hashlib.sha256(v.encode()).hexdigest()[:8] == info.get("hash8"):
            out.add(slot)
    return out


def expand(names, keys):
    """values for a router that asks for `names`: those first (keeping its order), then the extra numbered slots of the same provider.
    Old slots the router did NOT ask for (e.g. GROQ/GROQ2 for the mouth chain) are never added. Duplicate values appear once."""
    vals, seen = [], set()
    dead = dead_slots(keys)
    for n in names:
        v = keys.get(n)
        if v and v not in seen and n not in dead:
            seen.add(v)
            vals.append(v)
    pid = next((provider_of(n) for n in names if provider_of(n)), None)
    for n in numbered(by_id(pid), keys) if pid else []:
        v = keys.get(n)
        if v and v not in seen and n not in names and n not in dead:
            seen.add(v)
            vals.append(v)
    return vals


def expand_names(names, keys):
    """like expand() but returns the slot NAMES (for routers that keep per-key state)"""
    dead = dead_slots(keys)
    out = [n for n in names if keys.get(n) and n not in dead]
    pid = next((provider_of(n) for n in names if provider_of(n)), None)
    for n in numbered(by_id(pid), keys) if pid else []:
        if n not in out and keys.get(n) and n not in dead:
            out.append(n)
    return out
