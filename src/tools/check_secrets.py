#!/usr/bin/env python3
"""Fail-closed HEAD text-file secret heuristic. Never prints matched values.

Run from any working directory: python3 src/tools/check_secrets.py.
Does not inspect binary releases or commit history; rotate exposed real keys.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TEXT = {".py", ".md", ".json", ".jsonl", ".sh", ".js", ".html", ".css",
        ".toml", ".txt", ".yaml", ".yml", ".ini", ".env"}
SKIP = {".git", "__pycache__", ".pytest_cache", "node_modules", "dist",
        "build", "bin", "assets", "manual"}
PATTERNS = [
    ("provider-token-prefix", re.compile(
        r"(?:nvapi-|gsk_|github_pat_|gh[pousr]_|"
        r"sk-(?:proj-|or-v1-)?|AIza|hf_|xox[baprs]-|AKIA)"
        r"[A-Za-z0-9_-]{14,}")),
    ("credential-in-literal", re.compile(
        r"""(?:api[_-]?key|secret|password|access[_-]?token|app_key|credential)
             \s*[:=]\s*["'][A-Za-z0-9_+=/.:~-]{20,}["']""",
        re.IGNORECASE | re.VERBOSE)),
    ("authorization-constant", re.compile(
        r"(?:Bearer|Basic)\s+[A-Za-z0-9._+=/-]{25,}")),
    ("url-with-password", re.compile(
        r"https?://[^/\s:@]+:[^/\s@]+@")),
    ("private-key-pem", re.compile(
        r"-----BEGIN\s+(?:[A-Z0-9 ]+\s+)?PRIVATE\s+KEY-----")),
]


def paths():
    git = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True, timeout=10, check=False)
    if git.returncode == 0:
        return [ROOT / os.fsdecode(p) for p in git.stdout.split(b"\0") if p]
    return [p for p in ROOT.rglob("*") if p.is_file()]


def scan(file):
    if (not file.is_file() or file.is_symlink()
            or file.suffix.lower() not in TEXT or
            any(part in SKIP for part in file.relative_to(ROOT).parts)
            or file.stat().st_size > 512_000):
        return []
    raw = file.read_bytes()
    if b"\0" in raw:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []
    alerts = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, pat in PATTERNS:
            if pat.search(line):
                alerts.append((str(file.relative_to(ROOT)), lineno, name))
    return alerts


def main():
    hits = []
    count = 0
    for file in paths():
        count += 1
        try:
            hits.extend(scan(file))
        except (OSError, ValueError):
            print("SCAN_ERROR at tracked path (check permissions)", file.name)
            return 2
    for filename, line, rule in hits:
        print("%s:%d: %s [VALUE REDACTED]" % (filename, line, rule))
    print("SECRET_TEXT_SCAN:", "FAIL" if hits else "PASS",
          "files_considered:", count, "findings:", len(hits))
    print("Limitations: no binary history or provider-side validation")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
