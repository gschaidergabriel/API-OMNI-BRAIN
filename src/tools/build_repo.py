#!/usr/bin/env python3
"""Assemble the public repository tree in ~/API-OMNI-BRAIN (a clone of github.com/gschaidergabriel/API-OMNI-BRAIN): binary + pyz + checksums, installer, README, docs, manual, source, tests, research data.
Sanitises paths, scans everything for secret patterns and ABORTS on a hit. It does not commit or push.   usage: build_repo.py"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.expanduser("~/API-OMNI-BRAIN")
SECRET = re.compile(r"(nvapi-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{24,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|xox[bp]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?i:bearer)\s+[A-Za-z0-9._~+/-]{30,})")
TEXT = (".py", ".js", ".css", ".html", ".json", ".jsonl", ".md", ".txt", ".sh", ".service", ".desktop", ".yml", ".yaml", ".toml", ".cfg")


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def tree(src, dst, skip=("__pycache__", ".pytest_cache", "build", "dist", ".git")):
    for r, ds, fs in os.walk(src):
        ds[:] = [d for d in ds if d not in skip]
        for f in fs:
            if not f.endswith((".pyc", ".log")):
                cp(os.path.join(r, f), os.path.join(dst, os.path.relpath(os.path.join(r, f), src)))


def manual_md(j):
    o = ["# Manual", "", j.get("intro", ""), ""]
    for s in j["sections"]:
        o += ["## " + s["title"], "", s.get("summary", ""), "", "![%s](manual/%s)" % (s["title"], s["image"]), ""]
        o += ["%d. %s" % (i + 1, x) for i, x in enumerate(s.get("steps", []))] + ["", "**What it can do**", ""] + ["- " + x for x in s.get("can", [])]
        o += ["", "**What it cannot do - and must not**", ""] + ["- " + x for x in s.get("cannot", [])] + [""]
    o += ["## What this app cannot do - and does not want to", ""] + ["- " + x for x in j.get("global_cannot", [])] + ["", "> " + j.get("responsibility", ""), ""]
    return "\n".join(o)


def main():
    if not os.path.isdir(REPO):
        subprocess.run(["gh", "repo", "clone", "gschaidergabriel/API-OMNI-BRAIN", REPO], check=True)
    for n in os.listdir(REPO):
        if n != ".git":
            p = os.path.join(REPO, n)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)                       # only generated content inside the clone
    out = os.path.join(ROOT, "docs_out")
    for f in ("README.md",):
        cp(os.path.join(out, f), os.path.join(REPO, f))
    for f in ("ORIGIN.md", "WHY.md", "TESTING.md", "TEAM-RUN.md", "SWARM-RUN.md"):
        if os.path.exists(os.path.join(out, f)):
            cp(os.path.join(out, f), os.path.join(REPO, "docs", f))
    j = json.load(open(os.path.join(out, "manual.json")))
    open(os.path.join(REPO, "docs", "MANUAL.md"), "w").write(manual_md(j))
    tree(os.path.join(ROOT, "omnipool", "manual"), os.path.join(REPO, "docs", "manual"))
    cp(os.path.join(ROOT, "docs_src", "install.sh"), os.path.join(REPO, "install.sh"))
    cp(os.path.join(ROOT, "docs_src", "LICENSE"), os.path.join(REPO, "LICENSE"))
    os.chmod(os.path.join(REPO, "install.sh"), 0o755)
    sums = []
    for n in ("API-OMNI-BRAIN", "API-OMNI-BRAIN.pyz"):
        cp(os.path.join(ROOT, "dist", n), os.path.join(REPO, "bin", n))
        sums.append(subprocess.run(["sha256sum", n], cwd=os.path.join(REPO, "bin"), capture_output=True, text=True).stdout)
    open(os.path.join(REPO, "bin", "SHA256SUMS"), "w").write("".join(sums))
    src = os.path.join(REPO, "src")
    tree(os.path.join(ROOT, "omnipool"), os.path.join(src, "omnipool"))
    tree(os.path.join(ROOT, "tests"), os.path.join(src, "tests"))
    tree(os.path.join(ROOT, "tools"), os.path.join(src, "tools"))
    tree(os.path.join(ROOT, "assets"), os.path.join(src, "assets"))
    for f in ("build.sh", "build_pyz.sh", "install.sh", "uninstall.sh", "launch.py"):
        cp(os.path.join(ROOT, f), os.path.join(src, f))
    cp(os.path.join(ROOT, "docs_src", "facts.md"), os.path.join(REPO, "docs", "FACTS.md"))
    rs = os.path.join(REPO, "research")
    for f in ("iter/log.jsonl", "iter/REPORT.md", "team/log.jsonl", "team/AUFSEHER.md", "team/REPORT.md", "team/IDEEN.md", "team/anglify_map.json", "team/models3.json"):
        if os.path.exists(os.path.join(ROOT, f)):
            cp(os.path.join(ROOT, f), os.path.join(rs, os.path.basename(f)))
    for f in glob.glob(os.path.join(ROOT, "team", "testing", "**", "*.json"), recursive=True):
        cp(f, os.path.join(rs, "testing", os.path.relpath(f, os.path.join(ROOT, "team", "testing"))))
    if os.path.isdir(os.path.join(out, "research")):
        tree(os.path.join(out, "research"), rs)
    for f in glob.glob(os.path.join(ROOT, "team", "DESIGN*.md")):
        if not os.path.exists(os.path.join(rs, "design-briefs", os.path.basename(f))):
            cp(f, os.path.join(rs, "design-docs", os.path.basename(f)))
    bad = []
    for r, _d, fs in os.walk(REPO):
        if ".git" in r.split(os.sep):
            continue
        for f in fs:
            p = os.path.join(r, f)
            if f.endswith(TEXT):
                s = open(p, encoding="utf-8", errors="replace").read()
                s2 = s.replace("~", "~").replace("user", "user")
                if s2 != s:
                    open(p, "w", encoding="utf-8").write(s2)
                for m in SECRET.finditer(s2):
                    if m.group(0).startswith("sk-test-not-real"):
                        continue                                                    # fake key used by the tests
                    bad.append((os.path.relpath(p, REPO), m.group(0)[:12] + "..."))
            else:
                if f.startswith(("API-OMNI-BRAIN")) is False and not f.endswith((".png", ".ico", ".pyz")):
                    pass
    if bad:
        print("SECRET-LIKE STRINGS FOUND - not publishable:", bad[:20])
        sys.exit(2)
    print("repo tree ready:", REPO, sum(len(f) for _r, _d, f in os.walk(REPO)), "files")


if __name__ == "__main__":
    main()
