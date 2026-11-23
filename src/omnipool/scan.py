"""Static scanner for fetched files (malware signatures, foreign API-code tricks, prompt injection, invisible text). It only READS bytes: nothing is executed, imported or
unpacked. Honest label: signatures and heuristics, not a virus-scanner replacement; a clean verdict is 'nothing found', not 'proven harmless'.
verdict: sauber (release) | verdaechtig | schadhaft (both: never released, the file is deleted)."""
import json
import re
import sys

MAX = 3 << 20
# (id, regex, points, hard, text) - hard hits are blocked at once; points add up; documentation files count their soft rules half
REGELN = [
    ("eicar", r"EICAR-STANDARD-ANTIVIRUS-TEST-FILE", 99, True, 'Antivirus test signature (EICAR)'),
    ("revshell", r"/dev/tcp/\d|bash\s+-i\s*>&|\bnc\s+(-\w+\s+)*-e\s|\bncat\s[^\n]{0,300}-e\s|socat\s[^\n]{0,300}exec:|mkfifo\s+/tmp/\w+[^\n]{0,300}\bnc\b", 99, True, 'Reverse shell pattern'),
    ("miner", r"stratum\+tcp://|\bxmrig\b|cryptonight|coinhive", 99, True, 'Crypto miner'),
    ("b64exec", r"(eval|exec)\s*\(\s*(base64\.b64decode|atob|Buffer\.from\([^)]{0,200}base64)|echo\s+[A-Za-z0-9+/=]{40,}\s*\|\s*base64\s+(-d|--decode)\s*\|\s*(ba)?sh", 99, True, 'hidden code (Base64 gets executed)'),
    ("zerstoerer", r"rm\s+-rf\s+(/|~|\$HOME)(\s|\*|$)|\bmkfs\.\w+\s+/dev/|dd\s+if=\S+\s+of=/dev/(sd|nvme|vd)|:\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", 99, True, 'Destructive command'),
    ("erpresser", r"YOUR FILES (HAVE BEEN|ARE) ENCRYPTED|your files are encrypted", 99, True, 'Ransomware text'),
    ("exfil_senke", r"discord(app)?\.com/api/webhooks|api\.telegram\.org/bot|pastebin\.com/api|webhook\.site|requestbin|interact\.sh|\.oast\.|burpcollaborator", 4, False, 'Data exfiltration target (webhook/paste)'),
    ("geheimnis_lesen", r"\.ssh/|id_rsa|\.aws/credentials|keys\.env|wallet\.dat|Login Data|cookies\.sqlite|/etc/shadow|\.gnupg", 3, False, 'reads keys/credentials'),
    ("env_lesen", r"os\.environ|getenv\(|process\.env", 1, False, 'Reads environment variables'),
    ("remote_exec", r"(eval|exec)\s*\(\s*(requests\.get|urllib\.request\.urlopen|fetch)\([^)]{0,200}\)\s*\.(text|read)", 6, False, 'executes code loaded from the network'),
    ("pipe_sh", r"(curl|wget)\s[^\n|]{0,300}\|\s*(sudo\s+)?(ba)?sh\b", 3, False, 'loads and executes a script directly'),
    ("dl_chmod", r"(curl|wget|urlretrieve)[^\n]{0,300}(?:\n[^\n]{0,300})?chmod\s+\+x", 4, False, 'loads file and makes it executable'),
    ("psenc", r"powershell[^\n]{0,300}\s-e(nc(odedcommand)?)?\s+[A-Za-z0-9+/=]{20,}|FromBase64String|Invoke-Expression|\bIEX\s*\(", 5, False, 'PowerShell obfuscation'),
    ("persistenz", r"crontab\s+-|/etc/cron|authorized_keys|LaunchAgents|schtasks\s+/create|reg\s+add\s+HKCU\\[^\n]{0,300}\\Run", 3, False, 'establishes persistence'),
    ("os_exec", r"os\.system\s*\(\s*[\"']|os\.popen\s*\(\s*[\"']|subprocess\.(call|run|Popen)\s*\(\s*[\"']", 5, False, 'OS command execution via string'),
    ("exec_eval", r"exec\s*\(\s*[\"']|eval\s*\(\s*[\"']", 5, False, 'exec/eval with string argument'),
    ("keylogger", r"pynput|GetAsyncKeyState|SetWindowsHookEx|keylogger", 4, False, 'Keystroke logging'),
    ("blob", r"[A-Za-z0-9+/]{500,}={0,2}", 3, False, 'Huge encoded block (obfuscation)'),
    ("hexblob", r"(\\x[0-9a-fA-F]{2}){40,}", 4, False, 'Hex obfuscation'),
    ("metadaten", r"169\.254\.169\.254", 2, False, 'Cloud metadata address'),
    ("injektion", r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts)|disregard (the |all )?(system|previous)[^\n]{0,20}(prompt|instructions)|you are now (in )?(developer|dan)\b|"
                  r"reveal (your |the )?(system prompt|api key)|send (me )?your (api )?keys?\b|ignoriere (alle )?(vorherigen|bisherigen) (anweisungen|regeln)", 6, False, 'Instruction to AI systems (prompt injection)'),
]
KOMPILIERT = [(i, re.compile(rx, re.I), p, h, t) for i, rx, p, h, t in REGELN]
UNSICHTBAR = re.compile("[\u202a-\u202e\u2066-\u2069\U000e0000-\U000e007f]")           # strict (code): any bidi control or tag character
UNSICHTBAR_PROSA = re.compile("[\u202d\u202e\U000e0000-\U000e007f]")                     # prose/markup: bidi embeddings are normal in labels, only overrides and tag characters count
DOKU = (".md", ".markdown", ".txt", ".rst", ".adoc", ".xml", ".atom", ".rss", ".html", ".htm", ".json", ".csv")
BINAER = ((b"\x7fELF", 'Executable file (ELF)'), (b"MZ", 'Executable file (Windows)'), (b"\xcf\xfa\xed\xfe", 'Executable file (Mach-O)'), (b"\xca\xfe\xba\xbe", 'Executable file/Java'),
          (b"PK\x03\x04", 'Archive (zip)'), (b"\x1f\x8b", 'Archive (gzip)'), (b"7z\xbc\xaf", 'Archive (7z)'), (b"Rar!", 'Archive (rar)'), (b"BZh", 'Archive (bzip2)'), (b"\xfd7zXZ", 'Archive (xz)'),
          (b"%PDF", 'PDF (may contain scripts)'), (b"\xd0\xcf\x11\xe0", 'Office file with macros possible'))


def pruefe(data, name=""):
    """-> {urteil, punkte, treffer:[{id, text, zeile}], art}"""
    if len(data) > MAX:
        return {"urteil": "verdaechtig", "punkte": 5, "art": "gross", "treffer": [{"id": "groesse", "text": 'File larger than %d MB' % (MAX >> 20), "zeile": 0}]}
    for magic, text in BINAER:
        if data.startswith(magic):
            return {"urteil": "schadhaft", "punkte": 99, "art": "binaer", "treffer": [{"id": "binaer", "text": text + ': only text allowed in pool', "zeile": 0}]}
    if b"\x00" in data[:8192]:
        return {"urteil": "schadhaft", "punkte": 99, "art": "binaer", "treffer": [{"id": "binaer", "text": 'Binary data: only text allowed in pool', "zeile": 0}]}
    txt = data.decode("utf-8", "replace")
    doku = name.lower().endswith(DOKU)
    treffer, punkte, hart = [], 0.0, False
    um = (UNSICHTBAR_PROSA if doku else UNSICHTBAR).search(txt)
    if um:
        treffer.append({"id": "unsichtbar", "text": 'Invisible control characters (Trojan Source/hidden text)', "zeile": txt[:um.start()].count("\n") + 1})
        hart = True
    if data.startswith(b"#!"):
        punkte += 1
        treffer.append({"id": "shebang", "text": 'Script with shebang (intended to be executable)', "zeile": 1})
    for i, rx, p, h, t in KOMPILIERT:
        for m in rx.finditer(txt):
            w = p if (h or i == "injektion" or not doku) else p / 2
            treffer.append({"id": i, "text": t, "zeile": txt.count("\n", 0, m.start()) + 1})
            punkte += w
            hart = hart or h
            break
    ids = {x["id"] for x in treffer}
    if "exfil_senke" in ids and ("geheimnis_lesen" in ids or "env_lesen" in ids):
        punkte += 5                                   # reads secrets AND knows a drop point: the typical key thief
    urteil = "schadhaft" if hart or punkte >= 8 else ("verdaechtig" if punkte >= 4 else "sauber")
    return {"urteil": urteil, "punkte": round(punkte, 1), "art": "doku" if doku else "text", "treffer": treffer[:12]}


def worker(pfad):
    """sandbox entry (own process, no network, no writes): reads the file, prints the verdict as JSON"""
    try:
        with open(pfad, "rb") as f:
            data = f.read(MAX + 1)
        r = pruefe(data, pfad)
    except Exception as e:  # noqa: BLE001
        r = {"urteil": "verdaechtig", "punkte": 5, "art": "fehler", "treffer": [{"id": "fehler", "text": 'Scanner error: %s' % type(e).__name__, "zeile": 0}]}
    sys.stdout.write(json.dumps(r))
