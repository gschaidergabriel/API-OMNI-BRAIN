"""Safety organ for everything API-OMNI-BRAIN fetches or is asked to trust: a hardened fetch (https only, public addresses only, pinned IP, size cap, redirects re-checked)
and a verdict for a URL / API host. Honest label: rules and public facts (certificate, domain age via RDAP, known names), no proof; 'unauffaellig' is not a guarantee."""
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
import urllib.parse
import zlib

from . import core

SHORTENER = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "is.gd", "buff.ly", "rebrand.ly", "cutt.ly", "shorturl.at", "t.ly", "rb.gy"}
RISKY_TLD = {"zip", "mov", "xyz", "top", "click", "country", "gq", "tk", "ml", "ga", "cf", "work", "loan", "rest", "support", "icu", "cyou", "monster"}
BEKANNT = {"github.com", "githubusercontent.com", "huggingface.co", "openrouter.ai", "groq.com", "nvidia.com", "mistral.ai", "cerebras.ai", "sambanova.ai", "together.ai", "fireworks.ai",
           "cloudflare.com", "google.com", "googleapis.com", "anthropic.com", "openai.com", "cohere.com", "deepinfra.com", "replicate.com", "ycombinator.com", "arxiv.org",
           "bigmodel.cn", "z.ai", "perplexity.ai", "x.ai", "deepseek.com", "stability.ai", "elevenlabs.io", "assemblyai.com", "deepgram.com", "tavily.com", "brave.com", "exa.ai", "jina.ai",
           "voyageai.com", "azure.com", "microsoft.com", "amazon.com", "ollama.com", "lmsys.org", "wikipedia.org", "python.org", "mozilla.org"}
SLD2 = {"co.uk", "com.au", "co.jp", "com.br", "co.in", "org.uk", "com.cn", "co.kr", "com.tr", "co.za", "com.mx"}
MAX_BYTES = 3 << 20


def registrierbar(host):
    t = host.lower().rstrip(".").split(".")
    if len(t) >= 3 and ".".join(t[-2:]) in SLD2:
        return ".".join(t[-3:])
    return ".".join(t[-2:]) if len(t) >= 2 else host


def oeffentlich(ip):
    a = ipaddress.ip_address(ip)
    if a.version == 6 and a.ipv4_mapped is not None:
        a = a.ipv4_mapped
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast or a.is_reserved or a.is_unspecified)


def aufloesen(host, port=443):
    """-> list of public IPs of host; ValueError when the name is an IP or any address is not public (no DNS rebinding into the LAN)"""
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        raise ValueError('IP address instead of name')
    ips = []
    for _fam, _t, _p, _c, sa in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        if not oeffentlich(sa[0]):
            raise ValueError('Address not public')
        ips.append(sa[0])
    if not ips:
        raise ValueError('No address')
    return ips


class _Pinned(http.client.HTTPSConnection):
    """connects to the already checked IP, but validates the certificate against the real host name"""
    def __init__(self, host, ip, **kw):
        super().__init__(host, **kw)
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)


def hole(url, timeout=12, max_bytes=MAX_BYTES, hops=3, accept="*/*"):
    """hardened GET -> (status, bytes, headers). https only, no credentials in the URL, public IPs only, redirects followed by hand (each hop re-checked), size capped.
    Raises ValueError for anything unsafe."""
    for _ in range(hops + 1):
        u = urllib.parse.urlsplit(url)
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            raise ValueError('HTTPS only, no credentials in address')
        if (u.port or 443) not in (443, 8443):
            raise ValueError('unusual port')
        ip = aufloesen(u.hostname, u.port or 443)[0]
        cn = _Pinned(u.hostname, ip, port=u.port or 443, timeout=timeout)
        try:
            cn.request("GET", (u.path or "/") + ("?" + u.query if u.query else ""), headers={"Host": u.netloc, "User-Agent": "Omnipool-Radar/1.2 (+local)", "Accept": accept,
                                                                                             "Accept-Encoding": "identity"})
            r = cn.getresponse()
            if r.status in (301, 302, 303, 307, 308) and r.getheader("Location"):
                url = urllib.parse.urljoin(url, r.getheader("Location"))
                continue
            body = r.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ValueError('Response too large')
            enc = (r.getheader("Content-Encoding") or "").lower()
            if enc in ("gzip", "x-gzip", "deflate"):                        # some servers compress although 'identity' was asked: unpack with a hard cap (zip-bomb guard)
                dz = zlib.decompressobj(31 if "gzip" in enc else 15)
                try:
                    body = dz.decompress(body, max_bytes + 1)
                except zlib.error:
                    raise ValueError('Response cannot be unpacked')
                if len(body) > max_bytes or dz.unconsumed_tail:
                    raise ValueError('Response too large')
            return r.status, body, dict(r.getheaders())
        except (OSError, http.client.HTTPException) as e:
            raise ValueError('Connection: %s' % type(e).__name__)
        finally:
            cn.close()
    raise ValueError('Too many redirects')


def tls_info(host, timeout=6):
    ip = aufloesen(host)[0]
    with socket.create_connection((ip, 443), timeout) as s, ssl.create_default_context().wrap_socket(s, server_hostname=host) as t:
        cert = t.getpeercert()
    return {"ablauf_tage": int((ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()) / 86400),
            "aussteller": dict(x[0] for x in cert.get("issuer", ())).get("organizationName", "?")}


def alter_tage(domain):
    """domain age in days via the public RDAP bootstrap (rdap.org), None when unknown"""
    try:
        st, body, _h = hole("https://rdap.org/domain/" + domain, timeout=7, max_bytes=300000, accept="application/rdap+json")
        if st == 200:
            for ev in json.loads(body).get("events", []):
                if ev.get("eventAction") == "registration":
                    return int((time.time() - time.mktime(time.strptime(ev["eventDate"][:10], "%Y-%m-%d"))) / 86400)
    except (ValueError, KeyError, OSError):
        pass
    return None


def eigene_domains():
    d = set(BEKANNT)
    try:
        for p in core.custom().values():
            d.add(registrierbar(urllib.parse.urlsplit(p["base"]).hostname or ""))
        for p in json.loads(core.res("vendor/providers_free.json"))["providers"]:
            for k in ("key_url", "docs_url"):
                h = urllib.parse.urlsplit(p.get(k, "")).hostname
                if h:
                    d.add(registrierbar(h))
    except Exception:  # noqa: BLE001
        pass
    return d


def pruefe(url, tief=True):
    """-> {urteil: gefaehrlich|vorsicht|unauffaellig, gruende: [...], host, bekannt}. tief=False skips the network checks (certificate, RDAP)."""
    rot, gelb, gut = [], [], []
    try:
        u = urllib.parse.urlsplit(url.strip())
        host, port = (u.hostname or "").lower(), u.port
    except ValueError:
        return {"urteil": "gefaehrlich", "gruende": ['[!] Address unreadable'], "host": "", "bekannt": False}
    if u.scheme != "https":
        rot.append('No HTTPS: a key would travel unencrypted')
    if not host:
        rot.append('No hostname')
    if u.username or u.password:
        rot.append('Credentials in address (typical for spoofing)')
    if host in SHORTENER:
        rot.append('URL shortener hides destination')
    if host and re.fullmatch(r"[\d.:]+", host):
        rot.append('bare IP address instead of name')
    if any(ord(ch) > 127 for ch in host) or "xn--" in host:
        gelb.append('Special characters/Punycode in name (possible lookalike domain)')
    reg = registrierbar(host) if host else ""
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in RISKY_TLD:
        gelb.append('TLD .%s is frequently used for abuse' % tld)
    if host.count("-") >= 3 or len(host) > 50:
        gelb.append('conspicuously long/composite name')
    if port and port not in (443, 8443):
        gelb.append('unusual port %d' % port)
    if re.search(r"(unlimited|crack|hack|cheat|generator|free-?gpt|leak)", host):
        gelb.append('Name promises impossible (unlimited/crack/generator)')
    bekannt = bool(reg) and reg in eigene_domains()
    if bekannt:
        gut.append('Known provider/service (%s)' % reg)
    if not rot and tief and host:
        try:
            aufloesen(host)
            t = tls_info(host)
            gut.append('Certificate valid, issuer %s, %d days remaining' % (t["aussteller"], t["ablauf_tage"]))
            if t["ablauf_tage"] < 7:
                gelb.append('Certificate expires in %d days' % t["ablauf_tage"])
        except (ssl.SSLError, OSError, ValueError) as e:
            rot.append('Resolution/TLS failed (%s)' % (str(e)[:60] or type(e).__name__))
        else:
            if not bekannt:
                a = alter_tage(reg)
                if a is None:
                    gut.append('Domain age unknown')
                elif a < 90:
                    gelb.append('Domain only %d days old' % a)
                else:
                    gut.append('Domain %d days old' % a)
    urteil = "gefaehrlich" if rot else ("vorsicht" if gelb else "unauffaellig")
    return {"urteil": urteil, "gruende": ["[!] " + x for x in rot] + ["[?] " + x for x in gelb] + gut, "host": host, "bekannt": bekannt,
            "hinweis": 'Rules and public facts, not proof of security'}


def pruefe_cached(c, url, tief=True, max_alter=7 * 86400):
    c.execute("CREATE TABLE IF NOT EXISTS sicher_cache(host TEXT PRIMARY KEY, ts REAL, urteil TEXT)")
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or "").lower()
    r = c.execute("SELECT ts, urteil FROM sicher_cache WHERE host=?", (host,)).fetchone()
    if r and time.time() - r[0] < max_alter and u.scheme == "https":
        return json.loads(r[1])
    v = pruefe(url, tief)
    if tief and host:
        c.execute("INSERT OR REPLACE INTO sicher_cache VALUES(?,?,?)", (host, time.time(), json.dumps(v)))
        c.commit()
    return v
