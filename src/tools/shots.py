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
TABS = [("overview", 0, "demo"), ("keys", 1, "demo"), ("models", 2, "demo"), ("connect", 3, "demo"), ("settings", 4, "demo"), ("events", 5, "demo"),
        ("radar", 6, "real"), ("search", 7, "real"), ("usecases", 8, "real")]


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
    if name == "search":
        c.js("(()=>{const i=document.querySelector('#main input[type=search],#main input[type=text],#main input');if(i){i.focus();i.value='speech to text';i.dispatchEvent(new Event('input',{bubbles:true}));const b=[...document.querySelectorAll('#main button')].find(x=>/search/i.test(x.textContent));b&&b.click()}})()")
        time.sleep(3.5)
    if name == "usecases":
        c.js("(()=>{const t=document.querySelector('#main textarea');if(t){t.value='Transcribe meeting recordings to text, free, for a small team';t.dispatchEvent(new Event('input',{bubbles:true}));const b=[...document.querySelectorAll('#main button')].find(x=>/find|search|match/i.test(x.textContent));b&&b.click()}})()")
        time.sleep(9)


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
