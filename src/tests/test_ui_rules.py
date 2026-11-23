"""Guard rails for the UI files, enforced on every change (also on those made by tools/iterate.py): the promises of the safety design must survive any redesign."""
import os
import re

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "omnipool")
UI = ("ui.js", "ui_radar.js", "ui.css", "ui.html")


def rd(n):
    return open(os.path.join(PKG, n), encoding="utf-8").read()


def code(n):
    s = re.sub(r"/\*.*?\*/", "", rd(n), flags=re.S)             # comments may talk about innerHTML; only real code counts
    return re.sub(r"(?m)^\s*//.*$", "", s)


def test_no_unsafe_dom_or_external_resources():
    for n in UI:
        s = code(n)
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\s*\(|new Function", s), n
        assert not re.search(r"(src|href)=[\"']?https?://|url\(\s*[\"']?https?://|@import|<link[^>]+https?://", s), n + " laedt etwas von aussen"


def test_quarantine_popup_has_no_release_path():
    s = rd("ui_radar.js")
    assert "meldungen/gelesen" in s and "Got it" in s and "rd-mod" in s
    m = re.search(r"async function poll\(\).*?document\.body\.appendChild\(mod\)", s, re.S)
    assert m, "Popup-Code fehlt"
    popup = m.group(0)
    assert len(re.findall(r'h\("button"', popup)) == 1, "das Popup darf genau einen Knopf haben"
    assert not re.search(r"restore|override|allow it|keep it|approve it|unlock|ignore", popup, re.I)
    assert not re.search(r"api\(\s*[\"'](radar/datei|quarant)[^)]*bestaet", s, re.I)


def test_radar_tabs_registered_and_links_guarded():
    s = rd("ui_radar.js")
    assert "window.EXTRA" in s and "safeHref" in s and "noopener" in s
    for route in ("radar/news", "radar/suche", "radar/usecase", "radar/pruefe", "radar/datei", "meldungen"):
        assert '"%s"' % route in s, route
    u = rd("ui.js")
    assert "window.EXTRA" in u and u.count("EX.map") >= 2
    assert "/ui_radar.js" in rd("ui.html")


def test_dangerous_links_stay_blocked_in_ui():
    s = rd("ui_radar.js")
    assert "gefaehrlich" in s and re.search(r"blocked", s)
