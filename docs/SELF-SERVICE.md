# Universal Self-Service Tools (source integration, P0)

**Status: IMPLEMENTED IN SOURCE; NO PRODUCTION ROLLOUT; READ-ONLY P0.**

API-OMNI-BRAIN is the **single provider router**. Its local model pool,
free-key registration, ranking, quotas and existing app approvals are
unchanged. The new \`omnipool.selfservice\` module is an optional local
tool/consent layer, not a second router or a new provider/key store.

## Works with any AI that supports tools

Vendor identity is deliberately irrelevant. One capability contract is
published at:

\`GET http://127.0.0.1:8799/.well-known/omnipool-tools.json\`

The same operations are exposed in:

| AI harness | Discovery/invocation |
|---|---|
| Claude, Codex, other MCP clients | \`api-omni-brain --mcp\`, tools/list |
| OpenAI-compatible function calling | \`protocols.openai_tools\` in JSON manifest |
| Anthropic-compatible tool use | \`protocols.anthropic_tools\` |
| Grok, open models and custom agents | Any compatible MCP/HTTP tool caller |
| Any other HTTP automation | Existing per-app bearer auth + \`/v1/selfservice/*\` |
| Text-only model with no tool/runtime access | Can propose instructions only; cannot execute |

**No claim of universal execution in models that have no tool integration.**
This is capability/protocol compatibility, not remote computer access.
All operations are loopback-only and use the existing **approved application**
identity. Registration alone does not activate a client.

## API contract

- \`GET /v1/selfservice/capabilities\` — supported action list; app key required
- \`POST /v1/selfservice/plans\` — JSON \`{"actions":["route_contract"]}\`;
  returns an owner-private plan ID and hash, status PENDING_LOCAL_USER_APPROVAL
- \`GET /v1/selfservice/plans/<plan_id>\` — approval state for that same app
- \`POST /v1/selfservice/execute/<plan_id>\` — runs a single local-approved
  plan once, returns only status/receipt SHA, **not host diagnostics**

The matching MCP tools are:

\`pool_selfservice_capabilities\`,
\`pool_selfservice_plan\`,
\`pool_selfservice_status\`,
\`pool_selfservice_execute\`.

Any other action name, wrong app, host mismatch, expired grant, insecure
state directory or replay is rejected. **A model-provided JSON boolean
"approved" has no meaning**. The remote API has NO grant/approve endpoint.

## Consent flow (per action)

1. The user connects an AI harness in OMNIPOOL's Connect tab; the existing
   per-app credential/approval gates are mandatory. No credential needs
   to appear in model prompts or repository content.
2. The AI proposes a bounded plan with a list of read-only diagnostics.
3. The local user reviews the app name, action list, and SHA-256 in their
   own terminal and runs:
   \`api-omni-brain --selfservice-approve <plan_id>\`
4. The local CLI demands an exact interactive confirmation. A private
   owner-only 0600 grant is written, expiring within 5 minutes.
5. The **same** approved app may execute the plan once. A private atomic
   claim file prevents replay or concurrent duplicate execution.
6. Results (diagnostic facts about the host) remain ONLY in owner-private
   0600 receipt files under \`<OMNIPOOL_HOME>/selfservice/\`. An HTTP/MCP
   caller gets a receipt hash and generic status, never the local details.

The terminal phrase alone is **not cryptographic proof** that Gabriel
(or any specific operator) was the actor; local-OS compromise, terminal
automation and malware remain out of scope. An identity-verified
click-to-approve mechanism and privilege separation are P1 work.

## Bounded diagnostics available in P0

- \`service_status\`: fixed \`systemctl --user show api-omni-brain.service\`.
- \`route_contract\`: AST inspection of this installation's server.py
  route **names only** (no source excerpt, code execution, credentials).
- \`http_status\`: unauthenticated GET of two fixed *loopback* paths;
  collects only HTTP status codes, not response bodies.

All diagnostics use fixed commands and fixed paths. There is **no**
arbitrary command execution, no generated Python/Bash execution,
no OS access through the model, no copying tokens, no service restart,
no provider call, no billing, no GRID write, no external sending, and
no repository mutation. None of these are silently "future capabilities".

## Scripts and autonomous repair (P1/P2 design, NOT implemented)

To support self-generated diagnostic/repair scripts later:
1. Generate a structured *intent*, a proposed source patch and bounded
   test plan in an untrusted workspace. **Do not execute model text**.
2. Apply static AST, path, import, subprocess, and network allowlists;
   reject dynamic imports, eval/exec, shell=True, arbitrary child programs,
   unsandboxed plugin calls and secret/file-system access.
3. Show the user an exact hash-bound diff + effects and request **fresh
   explicit permission for that exact action and target host**.
4. Run through an isolated worker with read-only mounts, network=off,
   resource limits, no inherited environment/keys, least privilege,
   immutable source snapshot, and time bounds.
5. Verify against measurable preconditions, tests, postconditions and
   independent checks; write a detailed receipt locally.
6. Require a **new, separate approval** for any live write, external
   communication, install, service change, secret use, or publication.
7. Abort on uncertain costs, paid fallback, host identity mismatch,
   unknown backend, missing isolation, mutated plan, timeout, or failed
   test. Never mark a partial outcome as completed.

These later stages need a security review before implementation.

## Credential / secret policy

- The repository includes **zero actual provider credentials by design**.
- Credentials and per-app auth derivation remain exclusively at runtime
  on the local machine, under the existing OMNIPOOL controls.
- Tests use synthetically generated fixtures; never real secrets.
- Never show credentials in API response, logs, receipts, CLI examples,
  model prompts, exception text, Git commits, published assets or PDFs.
- A local free-key pool count is not a proof of pricing or of unique
  model backends. Any paid fallback needs independent fail-closed gates.
- Never infer account payment permission from the existence of a key.
- Run \`python3 src/tools/check_secrets.py\` before commits.
- A HEAD text scan **cannot prove** binaries, old Git history, forked
  clones, external providers or historical commits never leaked secrets.
  If any real credential was exposed, rotate/revoke it through its owner;
  removing HEAD content alone does not revoke a leaked token.

## Test and deployment boundary

Source-only code added to \`src/omnipool/\`; published binaries in \`bin/\`
are **not rebuilt** by this change. Installing an old binary does NOT
enable these functions. No live service was restarted or modified.

Run \`PYTHONPATH=src python3 -m pytest src/tests/test_selfservice.py -q\`
and existing \`src/tests/test_integrate.py\`. Tests use private temporary
state and synthetic app identities, never a provider account.

**Promotion gates:** tests green; secure independent user approval
evaluated; authentic app permission measured; no host-state egress;
no paid provider fallback; explicit approval for any production rollout.
