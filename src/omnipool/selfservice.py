"""Model-independent, permission-gated Self-Service P0 for API-OMNI-BRAIN.

Uses existing per-app approval. Every diagnostic requires a second local,
single-use user approval. No provider keys, arbitrary shell, generated code
execution, paid traffic, GRID writes, remote secrets or remote host receipts.
Python standard library only.
"""
import ast
import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import subprocess
import sys
import urllib.error
import urllib.request

SCHEMA = "OMNIPOOL_SELF_SERVICE_PLAN/v1"
GRANT = "OMNIPOOL_SELF_SERVICE_APPROVAL/v1"
RECEIPT = "OMNIPOOL_SELF_SERVICE_RECEIPT/v1"
ACTIONS = ("service_status", "route_contract", "http_status")
VALID_APP = re.compile(r"^[a-z0-9_]{1,24}$")
VALID_ID = re.compile(r"^[0-9a-f]{24}$")
BASE_DIR = None


class Denied(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def clock():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(t):
    return t.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value):
    try:
        t = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if t.tzinfo is None:
            raise ValueError("timezone required")
        return t.astimezone(datetime.timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise Denied("invalid timestamp") from exc


def directory():
    if BASE_DIR is None:
        from . import core
        root = Path(core.DATA) / "selfservice"
    else:
        root = Path(BASE_DIR)
    try:
        st = root.lstat()
    except FileNotFoundError:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = root.lstat()
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or st.st_mode & 0o077):
        raise Denied("selfservice state must be private owner directory")
    return root


def record_path(plan_id, suffix):
    if not VALID_ID.fullmatch(str(plan_id)) or suffix not in (
            "plan", "grant", "claim", "receipt"):
        raise Denied("invalid plan identifier")
    return directory() / ("%s.%s.json" % (plan_id, suffix))


def write_new(path, obj):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(canonical(obj) + b"\n")
        file.flush()
        os.fsync(file.fileno())


def read_private(path):
    if path.is_symlink():
        raise Denied("symlink refused")
    try:
        st = path.stat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077 or st.st_size > 8192):
            raise Denied("record is not private")
        data = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise Denied("record missing or invalid") from exc
    if not isinstance(data, dict):
        raise Denied("invalid record")
    return data


def identity():
    return {"uid": os.getuid(), "machine_id": socket.gethostname()}


def validate_actions(actions):
    if (not isinstance(actions, list) or not 1 <= len(actions) <= len(ACTIONS)
            or len(set(actions)) != len(actions)
            or any(not isinstance(x, str) or x not in ACTIONS for x in actions)):
        raise Denied("only unique bounded read-only diagnostics accepted")
    return actions


def capabilities():
    return {
        "schema": "OMNIPOOL_SELF_SERVICE_CAPABILITIES/v1",
        "protocols": ["MCP-stdio", "HTTP-JSON",
                      "OpenAI-tool-schema", "Anthropic-tool-schema"],
        "model_independent": True,
        "execution": "READ_ONLY_P0",
        "actions": [{"name": a, "effect": "read-only"} for a in ACTIONS],
        "approval": "separate local interactive approval, single-use, five minutes",
        "not_supported": ["arbitrary_shell", "generated_script_execution",
                          "external_publication", "secret_export",
                          "paid_provider_fallback", "cross-host_receipt_export"],
        "receipt_details": "local-owner-only",
    }


def load_plan(plan_id, app=None):
    obj = read_private(record_path(plan_id, "plan"))
    actor = identity()
    if (obj.get("schema") != SCHEMA or obj.get("id") != plan_id
            or obj.get("uid") != actor["uid"]
            or obj.get("machine_id") != actor["machine_id"]
            or not VALID_APP.fullmatch(str(obj.get("app", "")))
            or (app is not None and obj.get("app") != app)):
        raise Denied("plan owner, host or app mismatch")
    validate_actions(obj.get("actions"))
    first, last = parse_time(obj.get("created_at")), parse_time(obj.get("expires_at"))
    if first > clock() or last < clock() or last - first > datetime.timedelta(minutes=15):
        raise Denied("plan expired or invalid")
    return obj


def propose(app, actions):
    if not isinstance(app, str) or not VALID_APP.fullmatch(app):
        raise Denied("invalid application identity")
    actions = validate_actions(actions)
    moment = clock()
    plan_id = secrets.token_hex(12)
    plan = dict({
        "schema": SCHEMA, "id": plan_id, "app": app,
        "actions": actions, "created_at": stamp(moment),
        "expires_at": stamp(moment + datetime.timedelta(minutes=15))
    }, **identity())
    write_new(record_path(plan_id, "plan"), plan)
    return {
        "status": "PENDING_LOCAL_USER_APPROVAL", "plan_id": plan_id,
        "plan_sha256": digest(plan), "app": app, "actions": actions,
        "expires_at": plan["expires_at"],
        "next": "Local user runs: api-omni-brain --selfservice-approve " + plan_id,
        "credential_in_response": False, "model_can_approve": False
    }


def status(app, plan_id):
    plan = load_plan(plan_id, app)
    if record_path(plan_id, "claim").exists():
        state = "CONSUMED"
    elif record_path(plan_id, "grant").exists():
        state = "APPROVED_LOCAL"
    else:
        state = "PENDING_LOCAL_USER_APPROVAL"
    return {"plan_id": plan_id, "app": plan["app"], "status": state,
            "plan_sha256": digest(plan)}


def approve_local(plan_id):
    """A terminal prompt, not a cryptographic proof of a human actor."""
    if not sys.stdin.isatty():
        raise Denied("local interactive terminal required; API cannot approve")
    plan = load_plan(plan_id)
    print("APP:", plan["app"])
    print("ACTIONS:", ", ".join(plan["actions"]))
    print("No arbitrary shell, secrets, provider calls, writes or generated scripts.")
    print("PLAN_SHA256:", digest(plan))
    phrase = "APPROVE LOCAL " + plan_id + " " + digest(plan)[:12]
    if input('Type exactly "%s" to approve once: ' % phrase) != phrase:
        raise Denied("approval refused")
    moment = clock()
    grant = dict({
        "schema": GRANT, "plan_id": plan_id,
        "plan_sha256": digest(plan), "app": plan["app"],
        "approved_at": stamp(moment),
        "expires_at": stamp(min(moment + datetime.timedelta(minutes=5),
                                 parse_time(plan["expires_at"]))),
        "operator_identity_proven": False
    }, **identity())
    write_new(record_path(plan_id, "grant"), grant)
    return {"status": "APPROVED_LOCAL", "plan_id": plan_id,
            "operator_identity_proven": False}


def diagnostic(action):
    if action == "route_contract":
        tree = ast.parse((Path(__file__).parent / "server.py").read_text(encoding="utf-8"))
        routes = ("/v1/models", "/v1/messages", "/v1/chat/completions", "/v1/offer")
        return {"route_literals": sorted({n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value in routes})}
    if action == "service_status":
        try:
            r = subprocess.run(["systemctl", "--user", "show",
                "api-omni-brain.service", "-p", "ActiveState", "--value"],
                capture_output=True, text=True, timeout=3)
            value = (r.stdout or "").strip()
            return {"state": value if r.returncode == 0 and value in (
                "active", "inactive", "failed", "activating", "deactivating")
                else "UNKNOWN"}
        except (OSError, subprocess.TimeoutExpired):
            return {"state": "UNKNOWN"}
    if action == "http_status":
        from . import core
        port = core.settings().get("port", 8799)
        if not isinstance(port, int) or not 1024 <= port <= 65535:
            raise Denied("invalid OMNIPOOL port")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        statuses = {}
        for route in ("/v1/models", "/v1/offer"):
            try:
                req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, route),
                                             method="GET")
                with opener.open(req, timeout=2) as response:
                    statuses[route] = response.status
            except urllib.error.HTTPError as exc:
                statuses[route] = exc.code
            except (urllib.error.URLError, OSError, TimeoutError):
                statuses[route] = "UNAVAILABLE"
        return {"local_http_status": statuses}
    raise Denied("unknown diagnostic")


def execute(app, plan_id):
    plan = load_plan(plan_id, app)
    grant = read_private(record_path(plan_id, "grant"))
    actor = identity()
    if (grant.get("schema") != GRANT or grant.get("plan_id") != plan_id
            or grant.get("app") != app or grant.get("uid") != actor["uid"]
            or grant.get("machine_id") != actor["machine_id"]
            or not hmac.compare_digest(str(grant.get("plan_sha256", "")), digest(plan))
            or clock() > parse_time(grant.get("expires_at"))):
        raise Denied("approval invalid, expired or mismatched")
    # Atomic one-shot claim; a crash consumes it, never retries by default.
    write_new(record_path(plan_id, "claim"),
              {"plan_sha256": digest(plan), "claimed_at": stamp(clock())})
    outcomes = []
    for action in plan["actions"]:
        try:
            outcomes.append({"action": action, "status": "DONE",
                             "local_result": diagnostic(action)})
        except Exception as exc:  # noqa: BLE001
            outcomes.append({"action": action, "status": "BLOCKED",
                             "reason": type(exc).__name__})
            break
    completed = (len(outcomes) == len(plan["actions"])
                 and all(x["status"] == "DONE" for x in outcomes))
    receipt = dict({
        "schema": RECEIPT, "plan_id": plan_id, "app": app,
        "plan_sha256": digest(plan), "executed_at": stamp(clock()),
        "results": outcomes, "status": "DONE" if completed else "PARTIAL_OR_BLOCKED",
        "effects": {"external_writes": 0, "grid_writes": 0, "model_calls": 0},
        "operator_identity_proven": False
    }, **actor)
    write_new(record_path(plan_id, "receipt"), receipt)
    # Host state is NOT sent to a remote model. Detailed receipt stays local.
    return {"status": receipt["status"], "plan_id": plan_id,
            "receipt_sha256": digest(receipt), "details": "LOCAL_OWNER_ONLY",
            "external_writes": 0, "grid_writes": 0, "model_calls": 0}


def receipt_local(plan_id):
    return read_private(record_path(plan_id, "receipt"))


def tool_schemas():
    return [
        {"name": "pool_selfservice_capabilities",
         "description": "Discover bounded local tools; no secrets or host details.",
         "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
        {"name": "pool_selfservice_plan",
         "description": "Propose read-only diagnostics; separate explicit local user approval required.",
         "inputSchema": {"type": "object", "properties": {
             "actions": {"type": "array", "items": {
                 "type": "string", "enum": list(ACTIONS)},
                 "minItems": 1, "maxItems": len(ACTIONS)}
         }, "required": ["actions"], "additionalProperties": False}},
        {"name": "pool_selfservice_status",
         "description": "Check approval status of one plan.",
         "inputSchema": {"type": "object", "properties": {
             "plan_id": {"type": "string", "pattern": VALID_ID.pattern}
         }, "required": ["plan_id"], "additionalProperties": False}},
        {"name": "pool_selfservice_execute",
         "description": "Run previously locally approved diagnostics once; remote receipt contains no host state.",
         "inputSchema": {"type": "object", "properties": {
             "plan_id": {"type": "string", "pattern": VALID_ID.pattern}
         }, "required": ["plan_id"], "additionalProperties": False}}
    ]


def standard_manifest(base):
    specs = tool_schemas()
    return {
        "schema": "OMNIPOOL_UNIVERSAL_TOOLS/v1",
        "protocols": {
            "mcp": {"transport": "stdio", "command": "api-omni-brain --mcp"},
            "http": {"url": base + "/v1/selfservice",
                     "auth": "existing approved application bearer key"},
            "openai_tools": [{"type": "function", "function": {
                "name": t["name"], "description": t["description"],
                "parameters": t["inputSchema"]}} for t in specs],
            "anthropic_tools": [{"name": t["name"],
                "description": t["description"], "input_schema": t["inputSchema"]}
                for t in specs]
        },
        "consent": "local CLI per plan; no model self-authorization",
        "limitations": capabilities()["not_supported"],
    }
