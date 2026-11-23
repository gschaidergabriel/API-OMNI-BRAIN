"""Scan every tab of a seeded demo daemon for render garbage ([object ...], undefined, NaN, null) and console errors; save screenshots to /tmp/op-scan-<n>.png"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp, demo  # noqa: E402
d, tmp = demo.start()
c = cdp.Chrome()
bad = 0
try:
    c.goto("http://127.0.0.1:%d/" % d.port, 3)
    time.sleep(1)
    if os.environ.get("NARROW"):
        c.call("Emulation.setDeviceMetricsOverride", width=420, height=860, deviceScaleFactor=1, mobile=False)
        time.sleep(0.5)
    names = c.js("[...document.querySelectorAll('nav button')].map(b=>b.textContent)")
    for i, n in enumerate(names):
        c.js("document.querySelectorAll('nav button')[%d].click()" % i); time.sleep(1.8)
        txt = c.js("document.querySelector('#main').innerText") or ""
        hits = [w for w in ("[object", "undefined", "NaN", "null", "[Object") if w in txt]
        ov = c.js("document.documentElement.scrollWidth - window.innerWidth")
        print("%-16s len=%5d overflow=%s garbage=%s" % (n, len(txt), ov, hits)); bad += bool(hits)
        c.shot("/tmp/op-scan-%d.png" % i)
    print("console errors:", c.errors[:6]); bad += bool(c.errors)
finally:
    c.close(); d.stop()
sys.exit(1 if bad else 0)
