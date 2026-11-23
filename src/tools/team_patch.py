"""SEARCH/REPLACE patches for the team program: models send small exact edits instead of whole files (whole-file JS rewrites failed the syntax check ~85 % of the time).
Format:  <<<<<<< SEARCH file=ui.css \n old text \n ======= \n new text \n >>>>>>> REPLACE      (old text must occur exactly once)"""
import re

BLOCK = re.compile(r"<<<<<<< SEARCH(?: file=(\S+))?[ \t]*\n(.*?)\n=======[ \t]*\n(.*?)\n?>>>>>>> REPLACE", re.S)
ALLOWED = ("ui.css", "ui.js", "ui_radar.js", "texte.json", "gehirn.py", "ui.html")


def parse(text):
    """-> [(file, old, new)]"""
    out = []
    for m in BLOCK.finditer(text or ""):
        f = (m.group(1) or "").strip().strip("`'\"")
        out.append((f, m.group(2), m.group(3)))
    return out


def apply(files, patches, allowed=ALLOWED, max_blocks=12):
    """files: {name: text} -> (new_files, [problems]); nothing is applied when a block does not match exactly once"""
    new, bad = dict(files), []
    if not patches:
        return files, ["keine SEARCH/REPLACE-Bloecke gefunden"]
    if len(patches) > max_blocks:
        return files, ["zu viele Bloecke (%d)" % len(patches)]
    for f, old, nw in patches:
        if f not in allowed or f not in new:
            bad.append("Datei nicht erlaubt/unbekannt: %r" % f)
            continue
        if not old.strip():
            bad.append("leerer SEARCH-Text in %s" % f)
            continue
        n = new[f].count(old)
        if n != 1:
            bad.append("SEARCH in %s kommt %d-mal vor (muss genau 1x): %.60r" % (f, n, old))
            continue
        new[f] = new[f].replace(old, nw, 1)
    return (files, bad) if bad else (new, [])


def changed(files, new):
    return [k for k in new if new[k] != files.get(k)]
