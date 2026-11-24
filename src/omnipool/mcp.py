"""MCP stdio server (newline-delimited JSON-RPC 2.0): lets an MCP-capable harness (Claude Code and others) use the local pool as tools.
It registers itself like any other application (POST /v1/register) and works only after the user approved it in the UI."""
import json
import os
import sys
import urllib.error
import urllib.request

from . import core

PROTO = "2024-11-05"
TOOLS = [
    {"name": "pool_ask", "description": "Hand a routine sub-task (summary, boilerplate, translation, extraction, first draft) to the local pool of free models. Weaker than a frontier model; never send secrets.",
     "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}, "task_class": {"type": "string", "enum": ["auto", "code", "json", "de", "reason", "long", "tool"]}, "max_tokens": {"type": "integer"}}, "required": ["prompt"]}},
    {"name": "pool_models", "description": "List the models the pool currently offers.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "pool_offer", "description": "What the pool is good for and which model leads each task class right now.", "inputSchema": {"type": "object", "properties": {}}}]
ST = {"key": None}


def base():
    return os.environ.get("OMNIPOOL_URL") or "http://127.0.0.1:%d" % core.settings()["port"]


def call(method, path, body=None, key=None):
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = "Bearer " + key
    rq = urllib.request.Request(base() + path, None if body is None else json.dumps(body).encode(), h, method=method)
    try:
        with urllib.request.urlopen(rq, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}
    except OSError:
        return 0, {"error": "API-OMNI-BRAIN is not running; start it with: api-omni-brain"}


def ready():
    """-> (key, None) once approved, else (None, message for the agent)"""
    name = os.environ.get("OMNIPOOL_MCP_NAME", "mcp_client")
    c, r = call("POST", "/v1/register", {"name": name, "scope": ["mcp tools"]})
    if c != 200:
        return None, r.get("error") or "registration failed (%s)" % c
    if r["status"] != "approved":
        return None, "Waiting for your user: approve the application '%s' in API-OMNI-BRAIN (%s), then try again." % (r["name"], r["approve"])
    ST["key"] = r["key"]
    return r["key"], None


def tool(name, a):
    if name == "pool_offer":
        return call("GET", "/v1/offer")[1]
    key = ST["key"]
    if not key:
        key, msg = ready()
        if not key:
            return msg
    if name == "pool_models":
        return [m["id"] for m in call("GET", "/v1/models", key=key)[1].get("data", [])]
    cl = a.get("task_class", "auto")
    body = {"model": "omnipool-auto" if cl == "auto" else "omnipool-" + cl, "max_tokens": int(a.get("max_tokens") or 800), "messages": [{"role": "user", "content": str(a.get("prompt", ""))[:60000]}]}
    c, r = call("POST", "/v1/chat/completions", body, key)
    if c == 403:
        ST["key"] = None
    return (r.get("choices") or [{}])[0].get("message", {}).get("content") if c == 200 else "pool error %s: %s" % (c, json.dumps(r)[:300])


def reply(i, result=None, error=None):
    m = {"jsonrpc": "2.0", "id": i}
    m.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(m) + "\n")
    sys.stdout.flush()


def serve():
    for line in sys.stdin:
        try:
            q = json.loads(line)
        except ValueError:
            continue
        m, i = q.get("method"), q.get("id")
        if i is None:                                           # notifications need no answer
            continue
        if m == "initialize":
            reply(i, {"protocolVersion": PROTO, "capabilities": {"tools": {}}, "serverInfo": {"name": "api-omni-brain", "version": "1.4.0"}})
        elif m == "tools/list":
            reply(i, {"tools": TOOLS})
        elif m == "tools/call":
            p = q.get("params") or {}
            try:
                out = tool(p.get("name"), p.get("arguments") or {})
                reply(i, {"content": [{"type": "text", "text": out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)}]})
            except Exception as e:  # noqa: BLE001
                reply(i, {"content": [{"type": "text", "text": "error: %s" % type(e).__name__}], "isError": True})
        elif m == "ping":
            reply(i, {})
        else:
            reply(i, error={"code": -32601, "message": "unknown method"})
