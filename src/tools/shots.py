#!/usr/bin/env python3
"""Headless screenshots for the manual (own app, own headless Chrome, no desktop capture). Tabs that show private data (keys, connect) come from a throw-away demo daemon with FAKE providers;
news/search/use-case tabs come from the real local service because they only show public information. Output: omnipool/manual/<id>.png (1280 px wide).
usage: shots.py [--real http://127.0.0.1:8799]"""
import os
import sys
import time

import team_lib as L
from team_lib import it

sys.path.insert(0, it.ROOT)
import cdp  # noqa: E402
import demo  # noqa: E402

OUT = os.path.join(it.ROOT, "omnipool", "manual")
TABS = [("assistant", 0, "demo"), ("overview", 1, "demo"), ("keys", 2, "demo"), ("models", 3, "demo"), ("connect", 4, "demo"), ("settings", 5, "demo"), ("events", 6, "demo"),
        ("radar", 7, "real")]


def grab(base, tabs, hook=None):
    c = cdp.Chrome(1280, 860)
    try:
        c.goto(base + "/", 3.0)
        vis = c.js("[...document.querySelectorAll('nav button')].filter(b=>b.offsetHeight>0).length")
        if not vis or vis < 9:
            raise SystemExit("structural check failed: only %s visible nav buttons (expected 9)" % vis)
        for name, idx, _src in tabs:
            c.js("document.querySelectorAll('nav button')[%d].click()" % idx)
            time.sleep(1.6)
            if hook:
                hook(c, name)
            c.shot(os.path.join(OUT, name + ".png"))
            print("shot", name, flush=True)
        return c.errors[:3]
    finally:
        c.close()


def hook(c, name):
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    real = sys.argv[sys.argv.index("--real") + 1] if "--real" in sys.argv else it.REAL
    d, tmp = demo.start()
    try:
        err = grab("http://127.0.0.1:%d" % d.port, [t for t in TABS if t[2] == "demo"], hook)
    finally:
        d.stop()
    err2 = grab(real, [t for t in TABS if t[2] == "real"], hook)
    print("console errors:", err, err2)


if __name__ == "__main__":
    main()
