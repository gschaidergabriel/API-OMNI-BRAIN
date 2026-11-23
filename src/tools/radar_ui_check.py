"""UI check for the radar tabs: seeds a demo daemon's database, drives headless Chrome, prints findings + saves screenshots to /tmp/op-radar-*.png"""
import json, os, sqlite3, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cdp, demo  # noqa: E402
d, tmp = demo.start()
db = os.path.join(tmp, "home", "omnipool.db")
con = sqlite3.connect(db); con.execute("PRAGMA busy_timeout=20000")
for s in (os.path.join(tmp, "state", "omnipool.db"), ):
    pass
cands = [os.path.join(r, f) for r, _d, fs in os.walk(tmp) for f in fs if f == "omnipool.db"]
print("db", cands)
con.close()
con = sqlite3.connect(cands[0]); con.execute("PRAGMA busy_timeout=20000")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
now = time.time()
con.executescript("""CREATE TABLE IF NOT EXISTS nachricht(id TEXT PRIMARY KEY, ts REAL, feed TEXT, titel TEXT, link TEXT, text TEXT, score INT, gratis INT);
CREATE TABLE IF NOT EXISTS api_index(id TEXT PRIMARY KEY, name TEXT, url TEXT, beschr TEXT, kategorie TEXT, auth TEXT, quelle TEXT, ts REAL);
CREATE VIRTUAL TABLE IF NOT EXISTS suche USING fts5(kind UNINDEXED, ref UNINDEXED, titel, text, tokenize='unicode61 remove_diacritics 2');""")
con.execute("INSERT OR REPLACE INTO nachricht VALUES('n1',?,?,?,?,?,3,1)", (now - 3600, "Hugging Face Blog", "Neue kostenlose Inference-Stufe fuer Sprachmodelle", "https://huggingface.co/blog/free-inference", "Free inference credits for all open models, text to speech included.",))
con.execute("INSERT OR REPLACE INTO nachricht VALUES('n2',?,?,?,?,?,1,0)", (now - 90000, "Releases ollama", "ollama v0.9 released", "https://github.com/ollama/ollama/releases/tag/v0.9", "notes",))
con.execute("INSERT INTO suche(kind, ref, titel, text) VALUES('news','n1','Neue kostenlose Inference-Stufe fuer Sprachmodelle','Free inference credits text to speech Hugging Face Blog')")
con.execute("INSERT OR REPLACE INTO api_index VALUES('a1','ElevenLabs','https://elevenlabs.io/docs/api-reference','Sprachsynthese, monatliches Gratis-Kontingent','Audio TTS','','kuratiert',?)", (now,))
con.execute("INSERT INTO suche(kind, ref, titel, text) VALUES('api','a1','ElevenLabs','Sprachsynthese text to speech tts Audio')")
con.execute("CREATE TABLE IF NOT EXISTS meldung(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, art TEXT, titel TEXT, text TEXT, quelle TEXT, gelesen INT DEFAULT 0)")
con.execute("INSERT INTO meldung(ts, art, titel, text, quelle) VALUES(?,?,?,?,?)", (now, "quarantaene", "Datei nicht freigegeben und geloescht", "Die Datei 'setup.sh' aus https://github.com/x/y kann leider nicht freigegeben werden (schadhaft) und wurde deshalb geloescht. Befund: Reverse-Shell-Muster (Zeile 3)", "q"))
con.commit(); con.close()
c = cdp.Chrome()
try:
    c.goto("http://127.0.0.1:%d/" % d.port, 3)
    n = c.js("document.querySelectorAll('nav button').length"); print("nav buttons", n, c.js("[...document.querySelectorAll('nav button')].map(b=>b.textContent).join('|')"))
    time.sleep(3)
    print("popup", c.js("!!document.querySelector('.rd-mod')"), c.js("(document.querySelector('.rd-box')||{}).innerText").__str__()[:200] if c.js("!!document.querySelector('.rd-mod')") else "")
    c.shot("/tmp/op-radar-popup.png")
    c.js("(()=>{const b=[...document.querySelectorAll('.rd-box button')].pop();b&&b.click()})()"); time.sleep(0.8)
    print("popup closed", not c.js("!!document.querySelector('.rd-mod')"), "marked read", d.api("meldungen", {}) == [])
    for i, name in ((6, "radar"), (7, "suche"), (8, "usecase")):
        c.js("document.querySelectorAll('nav button')[%d].click()" % i); time.sleep(1.5)
        if name == "suche":
            c.js("document.getElementById('rds').value='text to speech';[...document.querySelectorAll('.b.p')].find(b=>b.textContent==='Suchen').click()"); time.sleep(4)
        if name == "usecase":
            c.js("(()=>{const t=document.getElementById('rdu');t.value='Ich will Sprachausgabe fuer meine Texte';t.dispatchEvent(new Event('input'));[...document.querySelectorAll('.b.p')].find(b=>b.textContent.startsWith('Passende')).click()})()"); time.sleep(6)
        txt = c.js("document.querySelector('#main').innerText") or ""
        print(name, len(txt), repr(txt[:160]))
        c.shot("/tmp/op-radar-%s.png" % name)
    print("errors", c.errors[:5])
finally:
    c.close(); d.stop()
