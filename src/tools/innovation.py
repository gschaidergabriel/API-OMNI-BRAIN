#!/usr/bin/env python3
"""Out-of-the-box round for the supervisor: several different free-pool models (all providers behind Omnipool) propose unconventional but buildable ideas for Omnipool's interface and intelligence,
one judge ranks them. Writes team/IDEEN.md and prints at most ~700 characters. It changes no code; the supervisor decides what becomes a ticket (team/tickets.json) or bug (team/bugs.json).
usage: innovation.py [--thema "..."]"""
import json
import os
import random
import sys
import time
import urllib.request

import team_lib as L
from team_lib import TEAM, it

thema = sys.argv[sys.argv.index("--thema") + 1] if "--thema" in sys.argv else "Oberflaeche und Intelligenz von Omnipool"
rq = urllib.request.Request(it.REAL + "/v1/models", headers={"Authorization": "Bearer " + it.real_key()})
ids = [m["id"] for m in json.load(urllib.request.urlopen(rq, timeout=20))["data"] if not any(s in m["id"] for s in L.SKIP)]
by = {}
for i in ids:
    by.setdefault(i.split("/")[1] if i.startswith("nvidia/") else i.split("/")[0], []).append(i)
team = [random.choice(v) for v in random.sample(list(by.values()), min(4, len(by)))]
P = ("Denke ausserhalb der Schablone. Omnipool testet Gratis-KI-Keys, ordnet Modelle ein, waehlt zur Laufzeit das beste (Bandit-Statistik, Richter-Modell), verbindet KI-Programme, hat ein Web-Fenster mit Reitern (Uebersicht, Keys, Modelle, Verbinden, Radar ...). "
     "Ziel: Laien sofort an die Hand nehmen, Profis nie bevormunden. Denkrahmen (GRF/ClayCode): Zustand R_t, Belege E_t, Uebergang R_t+1=F(R_t,E_t) als reine Funktion; harte Invarianten statt weicher Kommentare; Beleg statt Behauptung; Widerspruch sichtbar. "
     "Thema: %s. Liefere genau EINEN ```json Block: 5 Ideen [{\"titel\":\"\",\"idee\":\"2 Saetze\",\"nutzen\":\"fuer wen/was\",\"datei\":\"ui.css|ui.js|texte.json|gehirn.py|core.py\",\"aufwand\":\"klein|mittel|gross\",\"risiko\":\"\"}]. Machbar mit Python-Stdlib und reinem JS/CSS, keine externen Ressourcen." % thema)
ideas = []
for m in team:
    t, mm = L.ask([m], P, 3000, 200)
    j = L.jsonblock(t) if t else None
    for x in (j if isinstance(j, list) else []):
        if isinstance(x, dict) and x.get("titel") and x.get("idee"):
            ideas.append({**{k: str(v)[:300] for k, v in x.items()}, "von": mm})
if not ideas:
    print("keine Ideen (Pool am Limit?)")
    sys.exit(0)
t, jm = L.ask([L.pick(L.pool(), "ultra")], "Rangfolge: waehle die 3 wirkungsvollsten UND sicher machbaren Ideen (kleiner/mittlerer Aufwand bevorzugt, Laien-Fuehrung und Profi-Tempo, keine Spielerei). Daten:\n%s\nAntworte NUR ```json [Indizes]." % json.dumps([[i, x["titel"], x["idee"], x["aufwand"]] for i, x in enumerate(ideas)], ensure_ascii=False)[:9000], 400)
top = [ideas[i] for i in (L.jsonblock(t) or []) if isinstance(i, int) and 0 <= i < len(ideas)][:3] or ideas[:3]
with open(os.path.join(TEAM, "IDEEN.md"), "a") as f:
    f.write("\n## %s (%s) Thema: %s\nModelle: %s | Richter: %s\n" % (time.strftime("%H:%M"), len(ideas), thema, ", ".join(team), jm))
    for x in top:
        f.write("- **%s** [%s, %s, von %s]: %s | Nutzen: %s | Risiko: %s\n" % (x["titel"], x.get("datei"), x.get("aufwand"), x["von"], x["idee"], x.get("nutzen"), x.get("risiko")))
print("Ideen %d, Top3:" % len(ideas))
for x in top:
    print("- %s [%s/%s]: %s" % (x["titel"], x.get("datei"), x.get("aufwand"), x["idee"][:140]))
