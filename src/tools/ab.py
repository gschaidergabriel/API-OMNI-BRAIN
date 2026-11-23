import os, shutil, sys, time, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iterate as I, demo  # noqa: E402
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BK = "/tmp/op-final-backup"
def run(label, src):
    for f in ("ui.css", "ui.js", "texte.json"):
        shutil.copy2(os.path.join(src, f), os.path.join(ROOT, "omnipool", f))
    d, tmp = demo.start()
    try:
        sc = []
        for rep in range(2):
            s, iss = I.judge(d.port, list(range(6)))
            sc.append(s)
        print(label, "scores", [round(x, 2) for x in sc if x], "mean", round(statistics.mean([x for x in sc if x]), 2), flush=True)
    finally:
        d.stop()
try:
    run("v000 (vorher)", os.path.join(ROOT, "iter-try2", "versions", "v000") if os.path.isdir(os.path.join(ROOT, "iter-try2", "versions", "v000")) else os.path.join(ROOT, "iter", "versions", "v000"))
    run("aktuell", BK)
finally:
    for f in os.listdir(BK):
        shutil.copy2(os.path.join(BK, f), os.path.join(ROOT, "omnipool", f))
