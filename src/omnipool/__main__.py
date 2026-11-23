"""API-OMNI-BRAIN entry point (internal package name: omnipool). No argument: make sure the background server runs, then open the app window.
--daemon: server only | --lauf [n] / --status: headless | --install [--service] / --uninstall: desktop icon, menu entry, optional background service (this one file is enough)"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request


def ping(port):
    try:
        rq = urllib.request.Request("http://127.0.0.1:%d/api/ping" % port, headers={"X-Omnipool": "1"})
        return json.load(urllib.request.urlopen(rq, timeout=2)).get("ok")
    except Exception:  # noqa: BLE001
        return False


def selbst():
    """the command that starts this very program: the bundle itself, the .pyz, or `python -m omnipool`"""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    a0 = os.path.abspath(sys.argv[0])
    return [sys.executable, a0] if os.path.isfile(a0) and not a0.endswith("__main__.py") else [sys.executable, "-m", "omnipool"]


def fenster(port):
    from . import core
    url = "http://127.0.0.1:%d/" % port
    for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser", "microsoft-edge", "vivaldi"):
        if shutil.which(c):
            return subprocess.Popen([c, "--app=" + url, "--user-data-dir=" + os.path.join(core.DATA, "browser"), "--class=API-OMNI-BRAIN", "--name=API-OMNI-BRAIN", "--no-first-run",
                                     "--no-default-browser-check", "--window-size=1320,880"], preexec_fn=lambda: os.nice(5), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for c in (["firefox", "--new-window", url], ["xdg-open", url], ["sensible-browser", url]):
        if shutil.which(c[0]):
            return subprocess.Popen(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('No browser found. Open this address yourself: ' + url)


def installieren(service=False):
    from . import core
    home = os.path.expanduser("~")
    ziel = os.path.join(core.DATA, "bin")
    os.makedirs(ziel, exist_ok=True)
    quelle = selbst()
    if len(quelle) == 1 or (len(quelle) == 2 and os.path.isfile(quelle[1])):
        src = quelle[-1]
        exe = os.path.join(ziel, "API-OMNI-BRAIN" + (".pyz" if src.endswith(".pyz") else ""))
        if os.path.abspath(src) != os.path.abspath(exe):
            shutil.copy2(src, exe + ".new")
            os.chmod(exe + ".new", 0o755)
            os.replace(exe + ".new", exe)      # atomic: replacing a running binary in place fails with "Text file busy"
        os.chmod(exe, 0o755)
    else:
        print('To install, use the .pyz file or the binary, not the source folder.')
        return 1
    for n in (512, 128, 48):
        d = os.path.join(home, ".local/share/icons/hicolor/%dx%d/apps" % (n, n))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "api-omni-brain.png"), "wb").write(core.res("assets/omnipool-%d.png" % n))
    desk = ("[Desktop Entry]\nVersion=1.0\nType=Application\nName=API-OMNI-BRAIN\nGenericName=Free API pool\nComment=Tests all your API keys, ranks models, connects your agent "
            "harnesses\nExec=%s\nIcon=api-omni-brain\nTerminal=false\nCategories=Utility;Development;\nStartupNotify=true\nStartupWMClass=API-OMNI-BRAIN\n" % exe)
    for d in (os.path.join(home, ".local/share/applications"), os.path.join(home, "Desktop")):
        if os.path.isdir(d) or d.endswith("applications"):
            os.makedirs(d, exist_ok=True)
            f = os.path.join(d, "api-omni-brain.desktop" if d.endswith("applications") else "API-OMNI-BRAIN.desktop")
            open(f, "w").write(desk)
            os.chmod(f, 0o755)
            subprocess.run(["gio", "set", f, "metadata::trusted", "true"], capture_output=True)
    os.makedirs(os.path.join(home, ".local/bin"), exist_ok=True)
    link = os.path.join(home, ".local/bin/api-omni-brain")
    if os.path.islink(link) or os.path.exists(link):
        os.remove(link)
    os.symlink(exe, link)
    if service and shutil.which("systemctl"):
        u = os.path.join(home, ".config/systemd/user")
        os.makedirs(u, exist_ok=True)
        open(os.path.join(u, "api-omni-brain.service"), "w").write("[Unit]\nDescription=API-OMNI-BRAIN (free API pool)\nStartLimitIntervalSec=300\nStartLimitBurst=5\n\n[Service]\nExecStart=%s --daemon\n"
                                                             "Nice=10\nMemoryMax=700M\nCPUQuota=60%%\nRestart=on-failure\nRestartSec=10\n\n[Install]\nWantedBy=default.target\n" % exe)
        subprocess.run(["systemctl", "--user", "daemon-reload"])
        subprocess.run(["systemctl", "--user", "enable", "api-omni-brain.service"])
        subprocess.run(["systemctl", "--user", "restart", "api-omni-brain.service"])      # also picks up an upgraded binary
    print('installed: %s, menu entry, desktop icon%s' % (exe, ', service' if service else ""))
    return 0


def deinstallieren():
    home = os.path.expanduser("~")
    subprocess.run(["systemctl", "--user", "disable", "--now", "api-omni-brain.service"], capture_output=True)
    subprocess.run(["systemctl", "--user", "disable", "--now", "omnipool.service"], capture_output=True)      # pre-1.3 name
    for f in (".config/systemd/user/api-omni-brain.service", ".local/bin/api-omni-brain", ".local/share/applications/api-omni-brain.desktop", "Desktop/API-OMNI-BRAIN.desktop", "Desktop/API-OMNI-BRAIN.desktop",
              ".config/systemd/user/omnipool.service", ".local/bin/omnipool", ".local/share/applications/omnipool.desktop",
              ".local/share/icons/hicolor/512x512/apps/api-omni-brain.png", ".local/share/icons/hicolor/128x128/apps/api-omni-brain.png", ".local/share/icons/hicolor/48x48/apps/api-omni-brain.png",
              ".local/share/icons/hicolor/512x512/apps/omnipool.png", ".local/share/icons/hicolor/128x128/apps/omnipool.png", ".local/share/icons/hicolor/48x48/apps/omnipool.png"):
        try:
            os.remove(os.path.join(home, f))
        except OSError:
            pass
    print('removed (data remains in ~/.local/share/omnipool)')


def main():
    a = sys.argv[1:]
    if a[:1] == ["--scan-worker"]:                     # sandbox entry: touches nothing but the one file it is given
        from . import scan
        return scan.worker(a[1])
    from . import core
    port = core.settings()["port"]
    if a[:1] == ["--daemon"]:
        from . import server
        return server.serve(port)
    if a[:1] == ["--lauf"]:
        print(json.dumps({k: v for k, v in core.lauf(int(a[1]) if len(a) > 1 else 8).items() if k != "ts"}, indent=1))
        return
    if a[:1] == ["--status"]:
        print(core.status())
        return
    if a[:1] == ["--version"]:
        print("API-OMNI-BRAIN 1.3.0")
        return
    if a[:1] == ["--install"]:
        return sys.exit(installieren("--service" in a))
    if a[:1] == ["--uninstall"]:
        return deinstallieren()
    if not ping(port):
        subprocess.Popen(selbst() + ["--daemon"], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.expanduser("~"))
        for _ in range(40):
            if ping(port):
                break
            time.sleep(0.25)
    fenster(port)


if __name__ == "__main__":
    main()
