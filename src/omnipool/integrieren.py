"""Agent-facing integration surface: /integrate (markdown an AI agent can follow), the machine-readable manifest, the delegation offer.
Nothing here holds a secret: keys are only handed out by POST /v1/register, and they work only after the user approves the application in the UI."""
import re

from . import core, selfservice

GOOD = ["summarise or shorten text", "boilerplate and repetitive code", "translate", "classify, extract fields, reformat as JSON", "first drafts and rewrites",
        "read long documents and report back (long context class)", "second opinion on a diff"]
NOT = ["anything that needs the strongest model's judgement", "secrets, credentials or private files (never send them)", "final decisions on security or money"]
NAME = re.compile(r"[^a-z0-9_]")


def clean_name(n):
    return NAME.sub("", str(n or "").lower())[:24]


def manifest(base, version):
    return {"name": "API-OMNI-BRAIN", "version": version, "local_only": True, "cost": "free models only",
            "openai": {"base_url": base + "/v1", "models": ["omnipool-auto"] + ["omnipool-" + k for k in core.KLASSEN]},
            "anthropic": {"base_url": base, "note": "set ANTHROPIC_BASE_URL; model omnipool-auto"},
            "register": {"method": "POST", "url": base + "/v1/register", "body": {"name": "your_harness_name", "scope": ["what you may hand over"]}, "then": "user approves once in the UI"},
            "offer": base + "/v1/offer", "guide": base + "/integrate",
            "selfservice": {"tool_contracts": base + "/.well-known/omnipool-tools.json",
                            "capabilities": base + "/v1/selfservice/capabilities",
                            "human_approval": "local per-plan approval required; no AI self-approval"},
            "mcp": {"command": "api-omni-brain", "args": ["--mcp"]}}


def offer(c, base, apps):
    wahl = {}
    for k in core.KLASSEN:
        r = core.rangfolge(c, k, None, 1)
        if r:
            wahl[k] = {"best_model": "%s/%s" % (r[0][0], r[0][1]), "score": r[0][2]}
    return {"summary": "A local pool of free models. Weaker than a frontier model, but free and unlimited by your own quota. Offered for routine sub-tasks.",
            "good_for": GOOD, "not_for": NOT, "classes": wahl, "call": base + "/v1/chat/completions with model omnipool-auto (or omnipool-<class>)",
            "ask_your_user": "API-OMNI-BRAIN is running locally. May I hand routine sub-tasks (summaries, boilerplate, translation, extraction) to it and use it as a second provider? You approve once, in its UI.",
            "applications": apps}


def guide(base, version, snippets):
    return f"""# API-OMNI-BRAIN {version}: integration guide for AI agents

You are reading this because your user asked you to look at API-OMNI-BRAIN and integrate it into your workflow. If your user did not ask for that, stop and ask them first.

## What it is
A local program (`{base}`, reachable from this machine only) that pools free LLM APIs, tests keys and models, and routes each request to the best free model for its task class
(code, json, de, reason, long, tool). OpenAI- and Anthropic-compatible. It costs nothing. Honest limit: free models are weaker than a frontier model. Use it for routine sub-tasks, not for the hard decisions.

## Integrate in 3 steps (you do this yourself; the user only approves once)
1. Register (no key needed, nothing is active yet):
   `curl -s -X POST {base}/v1/register -H 'content-type: application/json' -d '{{"name":"<your harness name>","scope":["summaries","boilerplate"]}}'`
   You get a key and `"status":"pending"`.
2. Tell your user: "Approve <name> in API-OMNI-BRAIN: {base}/#connect (one click)". Check `GET {base}/v1/register/<name>` with `Authorization: Bearer <key>` until `"status":"approved"` (a few minutes at most, then ask the user).
3. Wire it into your own configuration. Show the user the change, back up the file you edit. Pick what your harness supports:
{snippets}

Verify: `curl -s {base}/v1/models -H "Authorization: Bearer <key>"` lists models; one `POST {base}/v1/chat/completions` with `"model":"omnipool-auto"` must answer.

## What to hand over
`GET {base}/v1/offer` says what it is good for and which model currently leads each class. Good: summaries, boilerplate, translation, extraction, first drafts, long-document reading. Not good: secrets, final decisions, anything that needs the strongest model.
Ask your user once whether you may delegate such tasks; keep doing the real thinking yourself.

## Option: MCP
`api-omni-brain --mcp` is an MCP stdio server with the tools `pool_ask`, `pool_models`, `pool_offer`. It registers itself the same way and waits for the same approval.

## Model-independent tools (ChatGPT, Claude, Grok, local models, anything with tools)
The same Self-Service capability protocol works across model vendors.
- MCP-stdio: add `api-omni-brain --mcp`; discover tools via `tools/list`.
- OpenAI function calling: tool JSON schemas at `{base}/.well-known/omnipool-tools.json`.
- Anthropic tool use: the same manifest includes Anthropic-format schemas.
- Any other tool-capable AI: use the authorized HTTP JSON endpoints `{base}/v1/selfservice/*`.
- A text-only AI without tool access cannot execute anything: it may show a plan to the user.
- Registration and Connect-tab approval authorize only connection, NOT execution.
- Every diagnostic needs its own local terminal confirmation:
  `api-omni-brain --selfservice-approve <plan-id>`.
- The AI can then invoke `pool_selfservice_execute` once; returned receipt excludes host details.
- Available today: restricted read-only diagnostics only. Generated shell scripts, file
  modifications, deployments, external sending and paid-provider calls are NOT enabled.
- All app credentials remain local. Never paste, log, include or ask for tokens in an AI chat.

## Safety and rollback
- Never send the user's own API keys anywhere; this service never asks for them.
- The key you get works only on this machine and only after the user approved it. The user can switch the application off at any time (Connect tab, or the emergency stop button).
- Rollback: restore your backed-up config; nothing else was changed.
- Same text offline: `api-omni-brain --guide`. Machine-readable version of this page: `{base}/.well-known/api-omni-brain.json`
"""


def snippets(base):
    return "\n".join([
        f"   - Claude Code: env `ANTHROPIC_BASE_URL={base}`, `ANTHROPIC_API_KEY=<key>`, `ANTHROPIC_MODEL=omnipool-auto` (or the `env` block of its settings file). Alternative: add the MCP server, see below.",
        f"   - Hermes Agent, Grokbot, any OpenAI-compatible harness: provider with base URL `{base}/v1`, API key `<key>`, model `omnipool-auto`. Use your harness's own provider mechanism.",
        f"   - Crush: provider of type openai, `base_url` `{base}/v1`, `api_key` `<key>`, model `omnipool-code` for coding work.",
        f"   - Aider: `aider --openai-api-base {base}/v1 --openai-api-key <key> --model openai/omnipool-code`",
        "   - Contract for everything else: OpenAI `base_url` + key, or Anthropic `ANTHROPIC_BASE_URL` + key. Model names: omnipool-auto, omnipool-code, -json, -de, -reason, -long, -tool, or provider/model."])
