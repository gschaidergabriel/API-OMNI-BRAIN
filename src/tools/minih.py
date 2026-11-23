"""minih - mini harness for ONE swarm agent. Built on the ideas of github.com/gschaidergabriel/smallH (MIT): identity first, pulse as an ordered
sequence, activation = relevance (not truth), evidence checks, decay, fixed calibration cases, rollback. Honest scope: smallH itself implements only the
identity registry (clay/identitaet.py, used here unchanged); the pulse, the lesson store and the calibration below are a MINIMAL own implementation of
its design, not smallH code.

What one agent gets:
  identity     a clay_ id (FORK of the swarm's ORIGIN), checked with darf_pulsen() before every pulse
  mini DB      its own SQLite file: lesson (what went wrong / what worked, with weight), episode (what it did, outcome, evidence), calib (fixed cases)
  retrieval    top lessons by token overlap x weight go into its prompt (relevance, not truth)
  guard        a claim only counts if its quoted evidence occurs verbatim in the real file (anti-confabulation); a failed guard becomes a lesson
  learning     every rejected patch / failed guard / failed gate -> lesson with class + cause + hint; lessons decay each pulse, are reinforced
               when the next attempt that used them succeeds, and are pruned below a floor
  calibration  fixed cases the agent must pass before it may edit; failure demotes it to reviewer-only (rollback of its edit right)
"""
import json
import os
import re
import sqlite3
import sys
import time

SMALLH = os.path.expanduser("~/smallH/clay")
DECAY, FLOOR, BOOST = 0.97, 0.05, 1.3
TOK = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{2,}")

SCHEMA = """
CREATE TABLE IF NOT EXISTS lesson(id INTEGER PRIMARY KEY, ts REAL, cls TEXT, text TEXT, weight REAL, hits INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, UNIQUE(cls, text));
CREATE TABLE IF NOT EXISTS episode(id INTEGER PRIMARY KEY, ts REAL, task TEXT, action TEXT, outcome TEXT, evidence TEXT);
CREATE TABLE IF NOT EXISTS calib(case_id TEXT PRIMARY KEY, passed INTEGER, ts REAL);
"""


def _identity_mod(register):
    os.environ["MICROCLAY_REGISTER"] = register
    sys.path.insert(0, SMALLH)
    import importlib
    import identitaet
    importlib.reload(identitaet)
    return identitaet


def new_origin(register):
    idm = _identity_mod(register)
    os.makedirs(os.path.dirname(register), exist_ok=True)
    return idm.praegen("ORIGIN", pfad=register)


class Mini:
    def __init__(self, run_dir, name, role, model, origin, register):
        self.name, self.role, self.model = name, role, model
        self.idm = _identity_mod(register)
        self.register = register
        self.kid = self.idm.praegen("FORK", origin, pfad=register)
        os.makedirs(os.path.join(run_dir, "minidb"), exist_ok=True)
        self.db = sqlite3.connect(os.path.join(run_dir, "minidb", name + ".db"), timeout=30, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.can_edit = True
        self.used = []                       # ids of lessons that were in the last prompt

    # ---- pulse gate
    def alive(self):
        return bool(self.idm.darf_pulsen(self.kid, pfad=self.register))

    # ---- lessons
    def learn(self, cls, text, weight=1.0):
        text = text[:300]
        self.db.execute("INSERT INTO lesson(ts,cls,text,weight) VALUES(?,?,?,?) ON CONFLICT(cls,text) DO UPDATE SET weight=weight+0.5, ts=excluded.ts", (time.time(), cls, text, weight))
        self.db.commit()

    def recall(self, task, k=5):
        want = set(t.lower() for t in TOK.findall(task))
        rows = self.db.execute("SELECT id,cls,text,weight FROM lesson").fetchall()
        scored = []
        for i, cls, text, w in rows:
            have = set(t.lower() for t in TOK.findall(cls + " " + text))
            ov = len(want & have) / (1 + len(have) ** 0.5)
            scored.append((w * (0.3 + ov), i, cls, text))
        scored.sort(reverse=True)
        top = scored[:k]
        self.used = [i for _s, i, _c, _t in top]
        if self.used:
            self.db.executemany("UPDATE lesson SET hits=hits+1 WHERE id=?", [(i,) for i in self.used])
            self.db.commit()
        return "\n".join("- [%s] %s" % (c, t) for _s, _i, c, t in top)

    def outcome(self, task, action, ok, evidence=""):
        self.db.execute("INSERT INTO episode(ts,task,action,outcome,evidence) VALUES(?,?,?,?,?)", (time.time(), task[:200], action[:200], "ok" if ok else "fail", evidence[:300]))
        if ok and self.used:
            self.db.executemany("UPDATE lesson SET wins=wins+1, weight=weight*? WHERE id=?", [(BOOST, i) for i in self.used])
        self.decay()
        self.db.commit()

    def decay(self):
        self.db.execute("UPDATE lesson SET weight=weight*?", (DECAY,))
        self.db.execute("DELETE FROM lesson WHERE weight<?", (FLOOR,))

    # ---- evidence guard: every quote must occur verbatim in the real file text
    @staticmethod
    def guard(findings, files):
        """findings: [{file, quote, claim}] -> (verified, rejected). A quote must occur in files[file] (whitespace-normalised)."""
        norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
        ok, bad = [], []
        for f in findings or []:
            if not isinstance(f, dict):
                continue
            q, txt = norm(f.get("quote")), norm(files.get(f.get("file"), ""))
            (ok if len(q) >= 12 and q in txt else bad).append(f)
        return ok, bad

    # ---- calibration: fixed cases (callables return True when the agent's answer is right)
    def calibrate(self, cases, answer_fn):
        passed = 0
        for cid, prompt, check in cases:
            try:
                r = bool(check(answer_fn(prompt)))
            except Exception:  # noqa: BLE001
                r = False
            self.db.execute("INSERT OR REPLACE INTO calib VALUES(?,?,?)", (cid, int(r), time.time()))
            passed += r
        self.db.commit()
        self.can_edit = passed == len(cases)
        if not self.can_edit:
            self.learn("calibration", "failed fixed cases %d/%d: stay reviewer-only until the next pulse and copy exact anchors" % (passed, len(cases)), 2.0)
        return passed, len(cases)

    def stats(self):
        n, = self.db.execute("SELECT count(*) FROM lesson").fetchone()
        ok, fail = (self.db.execute("SELECT sum(outcome='ok'), sum(outcome='fail') FROM episode").fetchone() or (0, 0))
        return {"id": self.kid, "name": self.name, "role": self.role, "model": self.model.split("/")[-1], "lessons": n, "ok": ok or 0, "fail": fail or 0, "can_edit": self.can_edit}


def merge_shared(run_dir, agents):
    """end of run: export every agent's top lessons into one shared JSON (the swarm's memory for the next run)"""
    out = {}
    for a in agents:
        for cls, text, w in a.db.execute("SELECT cls,text,weight FROM lesson ORDER BY weight DESC LIMIT 20"):
            k = (cls, text)
            out[k] = out.get(k, 0) + w
    rows = sorted(({"cls": c, "text": t, "weight": round(w, 2)} for (c, t), w in out.items()), key=lambda r: -r["weight"])
    json.dump(rows[:300], open(os.path.join(run_dir, "lessons_shared.json"), "w"), ensure_ascii=False, indent=1)
    return len(rows)
