/* API-OMNI-BRAIN Radar UI: Neuigkeiten, Gratis-API-Suche, Usecase-Vorschläge und Sicherheits-Popup.
   Eigenständig (IIFE), registriert Tabs in window.EXTRA, bringt eigenes <style>, nutzt nur h()/api()/I() aus ui.js.
   Kein innerHTML, keine Keys im DOM, deutsche Texte, Animationen dezent & abschaltbar. */
(function(){
  const css = document.createElement("style");
  css.textContent = `
    /* Chips & Items */
    .rd-chip{display:inline-flex;align-items:center;gap:4px;padding:2px 10px;border-radius:999px;font-size:var(--fs-xs);font-weight:600;line-height:1;border:1px solid var(--line);color:var(--ink-muted);background:var(--bg-elev);white-space:nowrap;transition:all var(--trans-fast) var(--ease)}
    .rd-chip.ok{color:var(--ok);border-color:rgba(74,222,128,.45);background:var(--ok-bg)}
    .rd-chip.warn{color:var(--wa);border-color:rgba(251,191,36,.45);background:var(--wa-bg)}
    .rd-chip.bad{color:var(--er);border-color:rgba(248,113,113,.45);background:var(--er-bg)}
    .rd-chip.info{color:var(--info);border-color:rgba(96,165,250,.45);background:var(--info-bg)}
    .rd-item{padding:var(--space-4) 0;border-bottom:1px solid var(--line);opacity:0;animation:rdin var(--trans-base) var(--ease) forwards}
    .rd-item:last-child{border-bottom:none}
    .rd-item a{color:var(--ac);text-decoration:none;font-weight:600}
    .rd-item a:hover{text-decoration:underline}
    .rd-why{margin-top:var(--space-3);font-size:var(--fs-sm);color:var(--ink-dim);line-height:var(--lh-relaxed)}
    .rd-acts{display:flex;gap:var(--space-2);flex-wrap:wrap;margin-top:var(--space-4)}
    /* Modal */
    .rd-mod{position:fixed;inset:0;background:rgba(10,10,11,.9);backdrop-filter:saturate(180%) blur(8px);display:flex;align-items:center;justify-content:center;z-index:9999;opacity:0;animation:rdfade var(--trans-base) var(--ease) forwards}
    .rd-box{width:min(560px,calc(100% - 32px));background:var(--bg-elev);border:1px solid var(--er);border-radius:var(--radius-lg);padding:var(--space-6);box-shadow:var(--shadow-3);opacity:0;transform:scale(.96) translateY(12px);animation:rdpop var(--trans-slower) var(--ease) forwards}
    .rd-box h3{margin:0 0 var(--space-4);font-size:var(--fs-xl);color:var(--er-strong);line-height:var(--lh-tight)}
    .rd-box p{line-height:var(--lh-relaxed);color:var(--ink);margin:0 0 var(--space-3)}
    .rd-box p:last-of-type{margin-bottom:var(--space-4)}
    .rd-load{display:inline-block;width:16px;height:16px;border:2px solid var(--line);border-top-color:var(--ac);border-radius:50%;animation:rdspin var(--trans-slow) linear infinite;vertical-align:-3px;margin-right:var(--space-2)}
    /* Skeletons */
    .rd-skel{background:linear-gradient(90deg,var(--bg-elev) 25%,var(--bg-glass) 50%,var(--bg-elev) 75%);background-size:200% 100%;animation:rdshimmer 1.2s ease-in-out infinite;border-radius:var(--radius-sm)}
    .rd-skel-line{height:14px;margin:var(--space-2) 0}
    .rd-skel-title{height:22px;width:55%;margin-bottom:var(--space-3)}
    .rd-skel-card{padding:var(--space-5);border:1px solid var(--line);border-radius:var(--radius);background:var(--bg-glass)}
    /* Animations */
    @keyframes rdin{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
    @keyframes rdfade{from{opacity:0}to{opacity:1}}
    @keyframes rdpop{from{opacity:0;transform:scale(.96) translateY(12px)}to{opacity:1;transform:none}}
    @keyframes rdspin{to{transform:rotate(360deg)}}
    @keyframes rdshimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
    @media (prefers-reduced-motion:reduce){
      .rd-item,.rd-mod,.rd-box,.rd-load,.rd-skel{animation:none!important;opacity:1!important;transform:none!important}
      .rd-skel{background:var(--bg-elev)}
    }
    /* Better contrast for help texts */
    .mu{color:var(--ink-dim)!important}
    .di{color:var(--ink-muted)!important}
    .hint-box{padding:var(--space-4);border:1px solid var(--line);border-radius:var(--radius);background:var(--bg-elev);color:var(--ink-dim);line-height:var(--lh-relaxed)}
    .empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:var(--space-4);padding:var(--space-7);text-align:center;color:var(--ink-dim);background:var(--bg);border:1px dashed var(--line);border-radius:var(--radius)}
    .empty svg{width:56px;height:56px;opacity:.6}
    .empty p{margin:0;font-size:var(--fs-sm);max-width:300px;line-height:var(--lh-relaxed)}
    .empty .hint{font-size:var(--fs-xs);color:var(--ink-muted)}
    /* Tooltip */
    .info{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;margin-left:var(--space-2);border:1px solid var(--ink-subtle);border-radius:50%;font-size:var(--fs-xs);font-weight:600;color:var(--ink-subtle);cursor:help;position:relative;vertical-align:middle;flex-shrink:0;transition:all var(--trans-fast) var(--ease)}
    .info:hover,.info:focus{color:var(--ac);border-color:var(--ac);background:var(--ac-bg)}
    .info::after{content:attr(data-tip);position:absolute;left:calc(100% + 8px);top:50%;transform:translateY(-50%) scale(.9);z-index:100;width:max-content;max-width:320px;padding:var(--space-3) var(--space-4);background:var(--bg-elev);border:1px solid var(--ac);border-radius:var(--radius);color:var(--ink);font-size:var(--fs-sm);line-height:var(--lh-relaxed);white-space:normal;text-transform:none;letter-spacing:0;opacity:0;visibility:hidden;pointer-events:none;box-shadow:var(--shadow-3);transition:all var(--trans-base) var(--ease)}
    .info:hover::after,.info:focus::after{opacity:1;visibility:visible;transform:translateY(-50%) scale(1)}
    @media (max-width:480px){.info::after{left:auto;right:0;max-width:280px}}
    /* Card content spacing */
    .card-content > * + *{margin-top:var(--space-4)}
    .card-content > .rd-acts{margin-top:var(--space-5)}
    .rd-why + .rd-acts{margin-top:var(--space-4)}
    /* Section spacing */
    .section-gap{margin-top:var(--space-6)}
    /* Text blocks */
    .prose{line-height:var(--lh-relaxed);color:var(--ink-dim)}
    .prose p{margin:0 0 var(--space-3)}
    .prose p:last-child{margin-bottom:0}
    .prose b{color:var(--ink);font-weight:600}
  `;
  document.head.appendChild(css);

  const R = { news:null, q:"", gratis:false, busy:false, suche:null, sq:"", uc:null, ut:"", ubusy:false, pruef:{}, datei:{} };
  const rr = () => { if (window.RR_HOOK && window.RR_HOOK()) return; if (typeof render === "function") render(); };
  const ago2 = t => typeof ago === "function" ? ago(t) : "";
  const safeHref = u => /^https?:\/\//i.test(u || "") ? u : "#";
  const info = k => typeof I === "function" ? I(k) : "";

  /* Sicherheits-Urteil als Chip */
  const verdict = v => {
    if (!v || !v.urteil) return h("span", { class: "rd-chip" }, "Not checked yet");
    const map = {
      unauffaellig: { cls: "ok", txt: "✓ Nothing unusual" },
      lokal: { cls: "ok", txt: "✓ Running locally" },
      vorsicht: { cls: "warn", txt: "⚠ Caution" },
      gefaehrlich: { cls: "bad", txt: "✕ Dangerous" },
      ungeprueft: { cls: "", txt: "? Unverified" }
    };
    const m = map[v.urteil] || map.ungeprueft;
    return h("span", { class: "rd-chip " + m.cls, title: (v.gruende || []).join("\n") }, m.txt);
  };

  /* Nachrichten laden */
  async function ladeNews() {
    R.busy = true; rr();
    try { R.news = await api("radar/news", { n: 60, gratis: R.gratis, q: R.q }); }
    catch (e) { R.news = { news: [], status: null }; }
    R.busy = false; rr();
  }

  /* Einzelnen Link prüfen */
  async function pruefe(u) {
    R.pruef[u] = "…"; rr();
    const r = await api("radar/pruefe", { url: u });
    R.pruef[u] = r[u] || { urteil: "ungeprueft", gruende: [] };
    rr();
  }

  /* Datei in Sandbox laden & prüfen */
  async function datei(u) {
    R.datei[u] = { laeuft: true }; rr();
    R.datei[u] = await api("radar/datei", { url: u });
    rr(); poll();
  }
  const github = u => /^https:\/\/(github\.com|raw\.githubusercontent\.com)\//.test(u || "");

  function dateiBox(u) {
    const d = R.datei[u];
    if (!d) return "";
    if (d.laeuft) return h("div", { class: "rd-why" }, h("span", { class: "rd-load" }), "File is being checked in isolated sandbox …");
    if (d.ok) {
      return h("div", { class: "hint-box" },
        h("div", { class: "rd-chip ok" }, "✓ Sandbox: nothing suspicious found" + (d.netz_isoliert ? " (checked without network access)" : "")),
        h("pre", {}, typeof d.vorschau === 'string' ? d.vorschau.slice(0, 1500) : '')
      );
    }
    return h("div", { class: "rd-why rd-chip bad" },
      d.fehler ? "Not loaded: " + d.fehler :
      "✕ Not approved and deleted (" + d.urteil + "): " + (d.treffer || []).map(t => t.text).join("; ")
    );
  }

  /* Link-Zeile mit Aktionen */
  function link(u, titel) {
    const v = R.pruef[u];
    return h("div", {},
      h("a", { href: safeHref(u), target: "_blank", rel: "noopener noreferrer" }, titel),
      h("div", { class: "rd-acts" },
        h("button", { class: "b s", on: { click: () => pruefe(u) } }, v === "…" ? "Checking …" : "Check security"),
        v && v !== "…" ? verdict(v) : "",
        github(u) ? h("button", { class: "b s", on: { click: () => datei(u) } }, "Check file in sandbox") : ""
      ),
      v && v !== "…" && v.gruende ? h("div", { class: "rd-why" }, v.gruende.join(" · ")) : "",
      dateiBox(u)
    );
  }

  /* API-Karte für Suche & Usecases */
  function apiKarte(a) {
    return h("div", { class: "rd-item" },
      h("div", {},
        h("b", {}, a.name), " ",
        h("span", { class: "rd-chip" }, a.auth),
        h("span", { class: "rd-chip" }, a.kategorie || a.quelle),
        a.quelle === "kuratiert" ? h("span", { class: "rd-chip ok" }, "Manually reviewed") : ""
      ),
      h("div", { class: "mu" }, a.beschr),
      a.warum ? h("div", { class: "rd-why" }, a.warum) : "",
      h("div", { class: "rd-acts" },
        verdict(a.sicher),
        a.sicher && a.sicher.urteil === "gefaehrlich"
          ? h("span", { class: "rd-why rd-chip bad" }, "Link blocked: " + (a.sicher.gruende || []).join(" · "))
          : h("a", { href: safeHref(a.url), target: "_blank", rel: "noopener noreferrer" }, "Open"),
        !a.sicher || a.sicher.urteil === "ungeprueft"
          ? h("button", { class: "b s", on: { click: () => pruefe(a.url) } }, "Check security")
          : "",
        github(a.url) ? h("button", { class: "b s", on: { click: () => datei(a.url) } }, "Check file in sandbox") : ""
      ),
      a.sicher && a.sicher.gruende && a.sicher.urteil !== "unauffaellig"
        ? h("div", { class: "rd-why" }, a.sicher.gruende.join(" · "))
        : "",
      dateiBox(a.url)
    );
  }

  /* ---------- TAB: RADAR ---------- */
  function radar() {
    if (!R.news && !R.busy) ladeNews();
    const st = R.news && R.news.status;
    const n = R.news ? R.news.news : [];
    const z = st ? st.zyklus : {};
    const nx = t => t ? (t * 1000 < Date.now() ? "due" : "in " + Math.max(1, Math.round((t * 1000 - Date.now()) / 3600000)) + " h") : "due";

    return h("div", {},
      /* Status-Karte */
      h("div", { class: "card" },
        h("div", { class: "card-header" },
          h("h3", {}, "Radar: Free API news ", info("radar"))
        ),
        h("div", { class: "card-content prose" },
          h("p", {}, "API-OMNI-BRAIN monitors many sources in the background (blogs, release pages, news, forums) and remembers what looks like new free offers. Everything is fetched only over secure connections and checked in an isolated sandbox before saving."),
          st ? h("div", { class: "rd-acts" },
            h("span", { class: "rd-chip" }, st.feeds.lebendig + " Sources respond (" + st.feeds.aktiv + " active, " + st.feeds.tot + " deactivated, " + st.feeds.entdeckt + " found yourself)"),
            h("span", { class: "rd-chip" }, st.nachrichten + " Messages"),
            h("span", { class: "rd-chip" }, st.apis + " APIs in index"),
            h("span", { class: "rd-chip" }, "Sources: last updated " + ago2(z.feeds && z.feeds.zuletzt) + " ago, next " + nx(z.feeds && z.feeds.naechste)),
            h("span", { class: "rd-chip" }, "Model check (2× per week): " + (z.modellcheck && z.modellcheck.zuletzt ? ago2(z.modellcheck.zuletzt) + " ago" : "never") + ", next " + nx(z.modellcheck && z.modellcheck.naechste))
          ) : "",
          h("div", { class: "rd-acts" },
            h("button", { class: "b", on: { click: async () => { await api("radar/aktualisiere", { was: "feeds" }); R.news = null; setTimeout(ladeNews, 4000); } } }, "Update sources now"),
            h("button", { class: "b", on: { click: () => api("radar/aktualisiere", { was: "modellcheck" }) } }, "Model check now"),
            h("button", { class: "b", on: { click: () => api("radar/aktualisiere", { was: "index" }) } }, "Reload API index")
          )
        )
      ),

      /* Suchleiste + Liste */
      h("div", { class: "card section-gap" },
        h("div", { class: "card-header" }, h("h3", {}, "Search messages")),
        h("div", { class: "card-content" },
          h("div", { class: "row" },
            h("input", { type: "text", id: "rdq", placeholder: "Search messages …", value: R.q, on: { keydown: e => { if (e.key === "Enter") { R.q = e.target.value; ladeNews(); } } } }),
            h("label", { class: "mu" }, h("input", { type: "checkbox", checked: R.gratis, on: { change: e => { R.gratis = e.target.checked; ladeNews(); } } }), " Free API tips only"),
            h("button", { class: "b", on: { click: () => { R.q = document.getElementById("rdq").value; ladeNews(); } } }, "Search")
          ),
          R.busy
            ? h("div", { class: "rd-skel-card" },
                h("div", { class: "rd-skel rd-skel-title" }),
                h("div", { class: "rd-skel rd-skel-line" }),
                h("div", { class: "rd-skel rd-skel-line" }),
                h("div", { class: "rd-skel rd-skel-line" })
              )
            : n.length
              ? n.map((x, i) => h("div", { class: "rd-item", style: "animation-delay:" + Math.min(i, 12) * 30 + "ms" },
                  link(x.link, x.titel),
                  h("div", { class: "rd-why" }, x.feed + " · " + ago2(x.ts) + " ago" + (x.gratis ? " · " : ""), x.gratis ? h("span", { class: "rd-chip ok" }, "Free tip") : ""),
                  x.text ? h("div", { class: "mu" }, x.text) : ""
                ))
              : h("div", { class: "empty" },
                  h("p", {}, "No messages yet. The first fetch runs in the background shortly after startup – or start it at the top with “Update sources now”."),
                  h("span", { class: "hint" }, "Tip: The search above filters the loaded messages in real time.")
                )
        )
      )
    );
  }

  /* Tabs registrieren */
  /* API search and use cases live in the Assistant now (one input for every kind of search); it reuses these renderers */
  window.EXTRA = [{ name: "Radar", fn: radar }];
  window.RADAR_UI = { apiKarte, link, verdict };

  /* ---------- SICHERHEITS-POPUP (Quarantäne) ---------- */
  let shown = 0;
  async function poll() {
    if (shown) return;
    let m;
    try { m = await api("meldungen", {}); }
    catch (e) { return; }
    if (!Array.isArray(m) || !m.length) return;
    shown = 1;

    const close = async () => {
      await api("meldungen/gelesen", { ids: m.map(x => x.id) });
      mod.remove();
      shown = 0;
    };

    const mod = h("div", { class: "rd-mod", role: "alertdialog", "aria-modal": "true" },
      h("div", { class: "rd-box" },
        h("h3", {}, "🛡 " + m[0].titel),
        m.map(x => h("p", {}, x.text)),
        h("p", {}, "API-OMNI-BRAIN first checks everything external in an isolated sandbox. Anything that looks suspicious is not released and is permanently deleted – even if you wanted it."),
        h("div", { class: "rd-acts" }, h("button", { class: "b p", on: { click: close } }, "Got it"))
      )
    );
    document.body.appendChild(mod);
  }

  setInterval(() => { if (!document.hidden) poll(); }, 4000);
  setTimeout(poll, 1200);
})();
