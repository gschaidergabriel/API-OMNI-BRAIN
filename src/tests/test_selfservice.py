"""Universal Self-Service tests. Synthetic apps; no provider calls or host writes."""
import builtins
import json
from pathlib import Path
import sys

import pytest
from omnipool import selfservice as ss
from test_deep import env  # noqa: F401 - fake local provider fixture


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "BASE_DIR", str(tmp_path / "selfservice"))
    return tmp_path


def test_universal_tool_shapes_without_credentials():
    manifest = ss.standard_manifest("http://127.0.0.1:8799")
    names = {x["function"]["name"] for x in
             manifest["protocols"]["openai_tools"]}
    assert names == {x["name"] for x in
                     manifest["protocols"]["anthropic_tools"]}
    assert names == {x["name"] for x in ss.tool_schemas()}
    assert names == {"pool_selfservice_capabilities", "pool_selfservice_plan",
                     "pool_selfservice_status", "pool_selfservice_execute"}
    assert all("key" not in str(x).lower() for x in names)
    assert "generated_script_execution" in ss.capabilities()["not_supported"]


def test_local_plan_approval_one_use_and_secretless_remote_receipt(store, monkeypatch):
    plan = ss.propose("grok_client", ["route_contract"])
    assert plan["status"] == "PENDING_LOCAL_USER_APPROVAL"
    assert ss.status("grok_client", plan["plan_id"])["status"] == \
        "PENDING_LOCAL_USER_APPROVAL"
    assert not (store / "selfservice" / (plan["plan_id"] + ".grant.json")).exists()

    # Model has a plan but not operator permission.
    with pytest.raises(ss.Denied):
        ss.execute("grok_client", plan["plan_id"])

    class LocalTty:
        def isatty(self):
            return True

    monkeypatch.setattr(ss.sys, "stdin", LocalTty())
    plan_record = ss.load_plan(plan["plan_id"], "grok_client")
    phrase = ("APPROVE LOCAL " + plan["plan_id"] + " " +
              ss.digest(plan_record)[:12])
    monkeypatch.setattr(builtins, "input", lambda prompt: phrase)
    approval = ss.approve_local(plan["plan_id"])
    assert approval["status"] == "APPROVED_LOCAL"
    assert approval["operator_identity_proven"] is False
    assert ss.status("grok_client", plan["plan_id"])["status"] == "APPROVED_LOCAL"

    monkeypatch.setattr(ss, "diagnostic", lambda action:
                        {"synthetic_host_result": "local-only"})
    done = ss.execute("grok_client", plan["plan_id"])
    assert done["status"] == "DONE"
    assert done["details"] == "LOCAL_OWNER_ONLY"
    assert "synthetic_host_result" not in json.dumps(done)
    assert "key" not in json.dumps(done).lower()
    assert ss.receipt_local(plan["plan_id"])["results"][0]["local_result"] \
        == {"synthetic_host_result": "local-only"}
    assert ss.status("grok_client", plan["plan_id"])["status"] == "CONSUMED"
    with pytest.raises(FileExistsError):
        ss.execute("grok_client", plan["plan_id"])


def test_rejects_bad_actions_and_wrong_app_or_host(store, monkeypatch):
    for actions in (["sh"], ["service_status", "service_status"],
                    [], "service_status", ["route_contract", {}]):
        with pytest.raises((ss.Denied, TypeError)):
            ss.propose("claude", actions)
    plan = ss.propose("claude", ["route_contract"])
    with pytest.raises(ss.Denied):
        ss.status("chatgpt", plan["plan_id"])
    original = ss.identity()
    monkeypatch.setattr(ss, "identity", lambda: {
        "uid": original["uid"], "machine_id": "different-machine"})
    with pytest.raises(ss.Denied):
        ss.load_plan(plan["plan_id"], "claude")


def test_private_storage_and_bad_grants_are_fail_closed(store):
    plan = ss.propose("local_llm", ["route_contract"])
    path = store / "selfservice" / (plan["plan_id"] + ".plan.json")
    assert path.stat().st_mode & 0o077 == 0
    path.chmod(0o644)
    with pytest.raises(ss.Denied):
        ss.load_plan(plan["plan_id"], "local_llm")
    path.chmod(0o600)
    with pytest.raises(ss.Denied):
        ss.execute("local_llm", plan["plan_id"])


def test_local_tty_required_for_approval(store, monkeypatch):
    plan = ss.propose("openai", ["route_contract"])

    class NotATty:
        def isatty(self):
            return False

    monkeypatch.setattr(ss.sys, "stdin", NotATty())
    with pytest.raises(ss.Denied):
        ss.approve_local(plan["plan_id"])


def test_http_api_still_requires_existing_app_approval(env):
    c, _, manifest = env.req("GET", "/.well-known/omnipool-tools.json")
    assert c == 200 and manifest["schema"] == "OMNIPOOL_UNIVERSAL_TOOLS/v1"
    c, _, _ = env.req("GET", "/v1/selfservice/capabilities")
    assert c == 401
    key = env.key("openai")
    bearer = {"Authorization": "Bearer " + key}
    c, _, caps = env.req("GET", "/v1/selfservice/capabilities", headers=bearer)
    assert c == 200 and caps["execution"] == "READ_ONLY_P0"
    c, _, invalid = env.req("POST", "/v1/selfservice/plans",
                           {"actions": ["route_contract"], "approved": True}, bearer)
    assert c == 403
    c, _, plan = env.req("POST", "/v1/selfservice/plans",
                         {"actions": ["route_contract"]}, bearer)
    assert c == 201 and plan["status"] == "PENDING_LOCAL_USER_APPROVAL"
    id_ = plan["plan_id"]
    c, _, state = env.req("GET", "/v1/selfservice/plans/" + id_, headers=bearer)
    assert c == 200 and state["status"] == "PENDING_LOCAL_USER_APPROVAL"
    c, _, _ = env.req("POST", "/v1/selfservice/execute/" + id_, {}, bearer)
    assert c == 403  # API clients cannot self-approve
