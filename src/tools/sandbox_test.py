#!/usr/bin/env python3
"""Clean-room test of a release artifact (the ELF or the .pyz) inside a sandbox: empty HOME, no keys, own port. Starts the daemon, checks version, UI, manual, API gate, key-freeness, stops it.
sandboxes: plain (env -i), bwrap (read-only /usr, own pid/ipc/uts/cgroup namespaces), firejail (private home, no new privs, caps dropped), netoff (own network namespace, loopback only)
usage: sandbox_test.py ARTIFACT plain|bwrap|firejail|netoff|all"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile

INNER = r'''
import json, sys, time, urllib.request, urllib.error, subprocess, os
port, art = int(sys.argv[1]), sys.argv[2]
cmd = ([art] if not art.endswith(".pyz") else ["python3", art]) + ["--daemon"]
res = {"checks": {}}
ver = subprocess.run(([art] if not art.endswith(".pyz") else ["python3", art]) + ["--version"], capture_output=True, text=True, timeout=60)
res["version"] = ver.stdout.strip()
d = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def get(p, hdr=None, raw=False):
    rq = urllib.request.Request("http://127.0.0.1:%d%s" % (port, p), headers=hdr or {})
    try:
        r = urllib.request.urlopen(rq, timeout=10); b = r.read(); return r.status, b
    except urllib.error.HTTPError as e:
        return e.code, e.read()
up = False
for _ in range(120):
    try:
        if get("/api/ping", {"X-Omnipool": "1"})[0] == 200: up = True; break
    except OSError: time.sleep(0.5)
res["checks"]["daemon_up"] = up
if up:
    c = res["checks"]
    c["ping_version_1_5"] = json.loads(get("/api/ping", {"X-Omnipool": "1"})[1]).get("version", "").startswith("1.5")
    st, b = get("/"); c["index_200_brand"] = st == 200 and b"API-OMNI-BRAIN" in b
    for p in ("/ui.js", "/ui.css", "/ui_radar.js", "/ui_manual.js", "/texte.json"):
        c["static" + p] = get(p)[0] == 200
    st, b = get("/manual.json"); c["manual_json"] = st == 200 and len(json.loads(b).get("sections", [])) >= 8
    st, b = get("/manual/overview.png"); c["manual_png"] = st == 200 and b[:4] == b"\x89PNG"
    c["api_needs_header"] = get("/api/status")[0] == 403
    st, b = get("/api/status", {"X-Omnipool": "1"}); s = json.loads(b)
    c["status_200"] = st == 200
    c["no_keys_present"] = not s.get("keys") and "nvapi-" not in b.decode() and "gsk_" not in b.decode()
    c["v1_requires_key"] = get("/v1/models")[0] in (401, 403)
    st, b = get("/manual/../ui.js"); c["traversal_blocked"] = st in (400, 404)
d.terminate()
try: d.wait(10)
except Exception: d.kill()
res["ok"] = all(res["checks"].values())
print(json.dumps(res))
'''


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def run(art, kind):
    tmp = tempfile.mkdtemp(prefix="obrain-sb-")
    name = os.path.basename(art)
    shutil.copy2(art, os.path.join(tmp, name))
    os.chmod(os.path.join(tmp, name), 0o755)
    port = free_port()
    ddir = os.path.join(tmp, ".local", "share", "omnipool")
    os.makedirs(ddir)
    json.dump({"port": port, "lauf_min": 1440, "max_modelle": 2}, open(os.path.join(ddir, "settings.json"), "w"))
    open(os.path.join(tmp, "inner.py"), "w").write(INNER)
    env = {"HOME": tmp, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "OMNIPOOL_RADAR": "0", "OMNIPOOL_MELDEN": "0", "TMPDIR": tmp}
    inner = ["python3", "-I", os.path.join(tmp, "inner.py"), str(port), os.path.join(tmp, name)]
    envl = ["env", "-i"] + ["%s=%s" % kv for kv in env.items()]
    if kind == "plain":
        cmd = envl + inner
    elif kind == "bwrap":
        cmd = ["bwrap", "--ro-bind", "/usr", "/usr", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64", "--symlink", "usr/bin", "/bin", "--ro-bind", "/etc", "/etc", "--proc", "/proc", "--dev", "/dev",
               "--tmpfs", "/tmp", "--bind", tmp, tmp, "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--unshare-cgroup-try", "--die-with-parent", "--clearenv"] + sum((["--setenv", k, v] for k, v in env.items()), []) + inner
    elif kind == "firejail":
        home = os.path.expanduser("~")  # --private=DIR mounts DIR as the real home path
        env.update(HOME=home, TMPDIR=home)
        envl = ["env", "-i"] + ["%s=%s" % kv for kv in env.items()]
        inner = ["python3", "-I", os.path.join(home, "inner.py"), str(port), os.path.join(home, name)]
        cmd = ["firejail", "--quiet", "--noprofile", "--private=" + tmp, "--private-tmp", "--nonewprivs", "--caps.drop=all", "--nosound", "--no3d"] + envl + inner
    elif kind == "netoff":
        cmd = ["unshare", "-rn", "sh", "-c", 'ip link set lo up && exec "$@"', "sh"] + envl + inner
    else:
        raise SystemExit("unknown sandbox")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        res = json.loads(out) if out.startswith("{") else {"ok": False, "error": (r.stderr or r.stdout)[-300:]}
    except (subprocess.TimeoutExpired, ValueError) as e:
        res = {"ok": False, "error": type(e).__name__}
    shutil.rmtree(tmp, ignore_errors=True)
    return res


if __name__ == "__main__":
    art, kinds = os.path.abspath(sys.argv[1]), sys.argv[2:] or ["all"]
    kinds = ["plain", "bwrap", "firejail", "netoff"] if kinds == ["all"] else kinds
    allok = True
    for k in kinds:
        r = run(art, k)
        allok &= bool(r.get("ok"))
        print(json.dumps({"artifact": os.path.basename(art), "sandbox": k, **r}, ensure_ascii=False), flush=True)
    sys.exit(0 if allok else 1)
