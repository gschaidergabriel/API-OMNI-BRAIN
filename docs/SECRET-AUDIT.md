# Credential hygiene and evidence (2026-11-25)

## Scope and findings

- Main branch source/documentation was inspected via the authenticated
  GitHub repository connection: 108 text files analyzed with common
  provider-token, bearer, private-key and literal-credential patterns.
- No confirmed real provider keys or access secrets were identified.
- Three credential-shaped *synthetic test literals* were replaced.
- The first CI scan also identified three deliberate URL-with-password
  test fixtures. Those tests now construct harmless mock URLs without
  publishing a credential-shaped static URI.
- GitHub Actions run 45661125153: source secret scanner PASS,
  143 tracked files considered, **0 matches**; modified source compiled;
  **12 targeted tests passed**, using only fake upstream services.
- A .gitignore now excludes runtime settings, API key files, credentials,
  receipts, sqlite data and secret-like extensions.
- Tools output only filenames, line numbers and rule names; matched
  credential strings are never printed.

## What this does NOT prove

The published pre-existing binaries in `bin/`, embedded executable assets,
full Git history, forks, former clones, user machine state, and providers'
databases were **not** exhaustively scanned. This is a useful HEAD text audit,
not a proof that no credential has ever leaked.

If any credential was ever published: revoke/rotate it at the provider,
check authorization logs, and audit historical artifacts. Removing a
string from a later commit **does not** erase its Git history.

## What is deliberately preserved

OMNIPOOL requires its **existing machine-local** private key vault to
reach the user-owned free model providers. That runtime vault is NOT part
of this repository, and this change does not delete it, export it,
inspect its values or introduce another store. No provider token is
placed inside examples, prompt templates, tool manifests, tests,
receipts, logs or model-facing Self-Service API responses.

## CI

`python3 src/tools/check_secrets.py` is a local fail-closed text
heuristic. A passing result should be combined with a history and
binary scan in a trusted offline environment before making any
absolute secret-free claim.
