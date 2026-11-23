"""Agent self-integration: /integrate guide, manifest, offer, register -> user approval -> use. Uses the daemon and fake upstream of test_deep."""
import json

from test_deep import env  # noqa: F401  (fixture)


def test_guide_and_manifest(env):
    c, _h, b = env.req("GET", "/integrate", raw=True)
    t = b.decode()
    assert c == 200 and "/v1/register" in t and "http://127.0.0.1:%d" % env.port in t and "never send the user's own API keys" in t.replace("Never", "never")
    assert env.req("GET", "/llms.txt", raw=True)[0] == 200
    c, _h, m = env.req("GET", "/.well-known/api-omni-brain.json")
    assert c == 200 and m["openai"]["base_url"].endswith("/v1") and m["register"]["url"].endswith("/v1/register") and m["local_only"] is True


def test_offer(env):
    c, _h, o = env.req("GET", "/v1/offer")
    assert c == 200 and "good_for" in o and "ask_your_user" in o and set(o["classes"]) <= {"code", "json", "de", "reason", "long", "tool"} and "key" not in json.dumps(o)


def test_register_approve_use(env):
    assert env.req("POST", "/v1/register", b'{"name":"x"}', {"Content-Type": "text/plain"})[0] == 415          # a web page cannot do this without a preflight
    c, _h, r = env.req("POST", "/v1/register", {"name": "Test Bot!", "scope": ["summaries"]})
    assert c == 200 and r["name"] == "testbot" and r["status"] == "pending" and r["key"].startswith("op-testbot-")
    key = r["key"]
    assert env.req("GET", "/v1/register/testbot", headers={"Authorization": "Bearer " + key})[2]["status"] == "pending"
    assert env.req("GET", "/v1/register/testbot", headers={"Authorization": "Bearer op-wrong"})[0] == 401
    body = {"model": "omnipool-auto", "messages": [{"role": "user", "content": "hi"}]}
    assert env.req("POST", "/v1/chat/completions", body, {"Authorization": "Bearer " + key})[0] == 403          # pending = not authorised
    assert {"name": "testbot", "status": "pending", "scope": ["summaries"]} in env.req("GET", "/v1/offer")[2]["applications"]
    env.api("settings", {"harness": {"name": "testbot", "an": True, "klasse": "auto"}})                          # the user clicks "approve"
    assert env.req("GET", "/v1/register/testbot", headers={"Authorization": "Bearer " + key})[2]["status"] == "approved"
    assert env.req("POST", "/v1/chat/completions", body, {"Authorization": "Bearer " + key})[0] == 200


def test_deny(env):
    c, _h, r = env.req("POST", "/v1/register", {"name": "denyme"})
    assert r["status"] == "pending"
    env.api("settings", {"harness": {"name": "denyme", "an": False, "klasse": "auto", "ablehnen": True}})
    assert env.req("GET", "/v1/register/denyme", headers={"Authorization": "Bearer " + r["key"]})[2]["status"] == "denied"
    assert not any(a["name"] == "denyme" for a in env.req("GET", "/v1/offer")[2]["applications"])


def test_mcp_flow(env):
    import os, subprocess, sys
    from test_deep import ROOT
    p = subprocess.Popen([sys.executable, "-m", "omnipool", "--mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=ROOT,
                         env={**os.environ, "OMNIPOOL_URL": "http://127.0.0.1:%d" % env.port, "OMNIPOOL_MCP_NAME": "mcptest", "PYTHONPATH": ROOT})

    def rpc(i, m, params=None):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": m, "params": params or {}}) + "\n")
        p.stdin.flush()
        return json.loads(p.stdout.readline())["result"]
    try:
        assert rpc(1, "initialize")["serverInfo"]["name"] == "api-omni-brain"
        assert {t["name"] for t in rpc(2, "tools/list")["tools"]} == {"pool_ask", "pool_models", "pool_offer"}
        assert "good_for" in rpc(3, "tools/call", {"name": "pool_offer"})["content"][0]["text"]
        t = rpc(4, "tools/call", {"name": "pool_ask", "arguments": {"prompt": "hi"}})["content"][0]["text"]
        assert "approve" in t.lower()                                                                       # pending: the agent is told to ask the user
        env.api("settings", {"harness": {"name": "mcptest", "an": True, "klasse": "auto"}})
        t = rpc(5, "tools/call", {"name": "pool_ask", "arguments": {"prompt": "hi", "task_class": "code"}})["content"][0]["text"]
        assert t and "pool error" not in t
        assert "omnipool-auto" in rpc(6, "tools/call", {"name": "pool_models"})["content"][0]["text"]
    finally:
        p.kill()


def test_register_limits(env):
    for i in range(30):
        c, _h, _r = env.req("POST", "/v1/register", {"name": "spam%d" % i})
        if c == 429:
            break
    assert c == 429
    assert env.req("POST", "/v1/register", {"name": "!!!"})[0] == 400
