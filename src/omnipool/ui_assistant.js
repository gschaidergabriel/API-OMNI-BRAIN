/* API-OMNI-BRAIN Assistant: the first page. Chat sessions (kept in this browser only), a normal polished AI chat, and every kind of search
   (free APIs, news, your own models, use cases) behind one input. Standalone (IIFE), exposes window.ASSIST, uses h()/api() from ui.js at call time.
   No innerHTML. Nothing is sent anywhere except to the local API; text that looks like a key is never sent and never stored. */
(function () {
  "use strict";
  const css = document.createElement("style");
  css.textContent = `
    .as{display:grid;grid-template-columns:272px minmax(0,1fr);height:max(540px,calc(100vh - 176px));border:1px solid var(--line);border-radius:var(--radius-xl);overflow:hidden;background:var(--bg-glass);position:relative}
    .as-side{display:flex;flex-direction:column;min-height:0;border-right:1px solid var(--line);background:rgba(255,255,255,.015)}
    .as-top{display:flex;flex-direction:column;gap:8px;padding:12px}
    .as-top button.b{width:100%}
    .as-top input{width:100%}
    .as-list{flex:1;overflow:auto;padding:0 8px 12px}
    .as-grp{padding:10px 10px 4px;font-size:var(--fs-xs);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-subtle)}
    .as-it{display:flex;align-items:center;gap:6px;padding:8px 10px;border:1px solid transparent;border-radius:var(--radius);cursor:pointer;color:var(--ink-muted)}
    .as-it:hover{background:var(--ac-bg);color:var(--ink)}
    .as-it.on{background:var(--glass-strong);border-color:var(--line-strong);color:var(--ink)}
    .as-it .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--fs-sm)}
    .as-it .x{opacity:0;border:0;background:none;color:var(--ink-subtle);cursor:pointer;font:inherit;padding:0 4px;border-radius:4px}
    .as-it:hover .x,.as-it.on .x,.as-it .x:focus-visible{opacity:1}
    .as-it .x:hover{color:var(--er-strong)}
    .as-empty{padding:16px 12px;color:var(--ink-subtle);font-size:var(--fs-sm)}
    .as-main{display:flex;flex-direction:column;min-width:0;min-height:0}
    .as-bar{display:flex;align-items:center;gap:8px;padding:10px 16px;border-bottom:1px solid var(--line);min-height:48px}
    .as-bar .ti{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink);font-weight:600}
    .as-bar .tg{display:none}
    .as-ghost{border:1px solid var(--line);background:transparent;color:var(--ink-muted);border-radius:var(--radius);padding:4px 10px;font:inherit;font-size:var(--fs-sm);cursor:pointer}
    .as-ghost:hover{color:var(--ac);border-color:var(--ac)}
    .as-thread{flex:1;min-height:0;overflow:auto;padding:20px 0}
    .as-col{max-width:820px;margin:0 auto;padding:0 20px;width:100%}
    .as-msg{display:flex;gap:12px;margin:0 0 22px}
    .as-msg.u{justify-content:flex-end}
    .as-av{flex:0 0 28px;height:28px;border-radius:50%;background:var(--ac-bg);border:1px solid rgba(200,240,58,.35);display:flex;align-items:center;justify-content:center;color:var(--ac);font-size:12px;font-weight:700}
    .as-bub{min-width:0;line-height:1.65;overflow-wrap:anywhere}
    .as-msg.u .as-bub{max-width:min(680px,88%);padding:10px 14px;background:var(--ac-bg);border:1px solid rgba(200,240,58,.28);border-radius:16px 16px 4px 16px;color:var(--ink);white-space:pre-wrap}
    .as-msg.a .as-bub{flex:1;padding-top:3px;color:var(--ink-dim)}
    .as-bub p{margin:0 0 10px;white-space:pre-wrap}
    .as-bub ul,.as-bub ol{margin:0 0 10px;padding-left:22px}
    .as-bub pre{position:relative;margin:0 0 10px;padding:12px 14px;overflow:auto;background:var(--bg-input);border:1px solid var(--line);border-radius:var(--radius);font:12.5px/1.55 var(--font-mono)}
    .as-bub code{font-family:var(--font-mono);font-size:.92em;background:var(--glass-strong);padding:1px 5px;border-radius:4px}
    .as-bub pre code{background:none;padding:0}
    .as-bub a{color:var(--ac)}
    .as-copy{position:absolute;top:6px;right:6px;border:1px solid var(--line);background:var(--bg-elev);color:var(--ink-muted);border-radius:6px;padding:2px 8px;font:inherit;font-size:var(--fs-xs);cursor:pointer}
    .as-copy:hover{color:var(--ac);border-color:var(--ac)}
    .as-meta{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-top:2px;font-size:var(--fs-xs);color:var(--ink-subtle)}
    .as-lnk{border:0;background:none;padding:0;color:var(--ink-subtle);font:inherit;cursor:pointer;text-decoration:underline dotted}
    .as-lnk:hover{color:var(--ac)}
    .as-err{color:var(--er-strong)}
    .as-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
    .as-dots span{display:inline-block;width:6px;height:6px;margin:0 2px;border-radius:50%;background:var(--ink-subtle);animation:asdot 1.1s infinite ease-in-out}
    .as-dots span:nth-child(2){animation-delay:.15s}.as-dots span:nth-child(3){animation-delay:.3s}
    @keyframes asdot{0%,80%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-3px)}}
    .as-sec{margin:0 0 12px;padding:6px 16px 10px;border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--glass)}
    .as-sec h4{margin:10px 0 2px;font-size:var(--fs-sm);letter-spacing:.05em;text-transform:uppercase;color:var(--ink-muted)}
    .as-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:6px 0;border-bottom:1px solid var(--line)}
    .as-row:last-child{border-bottom:0}
    .as .rd-item{animation:none;opacity:1;transform:none}
    .as-hello{max-width:820px;margin:0 auto;padding:6vh 20px 0;text-align:center}
    .as-hello h2{margin:0 0 6px;font-size:var(--fs-2xl);color:var(--ink)}
    .as-hello p{margin:0 auto;max-width:560px;color:var(--ink-muted)}
    .as-sug{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-top:26px;text-align:left}
    .as-sug button{display:flex;flex-direction:column;gap:4px;padding:12px 14px;border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--glass);color:var(--ink);font:inherit;cursor:pointer;text-align:left}
    .as-sug button:hover{border-color:var(--ac);background:var(--ac-bg)}
    .as-sug small{font-size:var(--fs-xs);letter-spacing:.06em;text-transform:uppercase;color:var(--ac)}
    .as-note{margin:18px auto 0;max-width:560px;padding:12px 14px;border:1px solid var(--ac);border-radius:var(--radius-lg);background:var(--ac-bg);color:var(--ink);text-align:left}
    .as-note button{margin-top:8px}
    .as-comp{border-top:1px solid var(--line);padding:10px 0 12px;background:var(--bg-elev)}
    .as-modes{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}
    .as-mode{border:1px solid var(--line);background:transparent;color:var(--ink-muted);border-radius:999px;padding:4px 12px;font:inherit;font-size:var(--fs-sm);cursor:pointer}
    .as-mode:hover{color:var(--ink);border-color:var(--ink-subtle)}
    .as-mode.on{color:var(--ac);border-color:var(--ac);background:var(--ac-bg)}
    .as-box{display:flex;align-items:flex-end;gap:8px;padding:8px 8px 8px 14px;border:1px solid var(--line-strong);border-radius:var(--radius-lg);background:var(--bg-input)}
    .as-box:focus-within{border-color:var(--line-focus);box-shadow:0 0 0 3px var(--ac-bg)}
    .as-box textarea{flex:1;min-height:24px;max-height:180px;padding:6px 0;border:0!important;background:transparent!important;box-shadow:none!important;resize:none;outline:none}
    .as-send{flex:0 0 auto;min-width:72px;padding:8px 16px;border:1px solid var(--ac);border-radius:var(--radius);background:var(--ac);color:#0b0b0c;font:inherit;font-weight:700;cursor:pointer}
    .as-send:hover{background:var(--ac-strong)}
    .as-send.stop{background:transparent;color:var(--ac)}
    .as-hint{margin-top:6px;font-size:var(--fs-xs);color:var(--ink-subtle)}
    .as-warn{color:var(--wa-strong)}
    @media (max-width:760px){
      .as{grid-template-columns:1fr}
      .as-side{display:none}
      .as.side .as-side{display:flex;position:absolute;inset:0;z-index:5;background:var(--bg-elev)}
      .as-bar .tg{display:inline-block}
      .as-col{padding:0 12px}
    }
  `;
  document.head.appendChild(css);

  /* ---------- state: sessions live in this browser only ---------- */
  const KEY = "aob.chats.v1", MAXC = 40, MAXM = 80;
  const SECRET = /(\bsk-[A-Za-z0-9_-]{16,}|\bgsk_[A-Za-z0-9]{16,}|\bnvapi-[A-Za-z0-9_-]{16,}|\bAIza[A-Za-z0-9_-]{20,}|\bhf_[A-Za-z0-9]{20,}|\bBearer\s+[A-Za-z0-9._-]{20,}|\b[A-Za-z0-9_-]{40,}\b)/;
  let st = { cur: null, list: [] };
  try { const j = JSON.parse(localStorage.getItem(KEY) || "null"); if (j && Array.isArray(j.list)) st = j; } catch (e) { /* storage blocked: sessions last until reload */ }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify({ cur: st.cur, list: st.list.slice(0, MAXC) })); } catch (e) { /* ignore */ } };
  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const cur = () => st.list.find(c => c.id === st.cur);
  const busy = {};                       /* chat id -> AbortController while a request is running */
  let mode = "ask", sq = "", stick = true, built = false, notice = "";
  let MC = { ts: 0, rows: [] };

  const MODES = [["ask", "Ask"], ["search", "Search"], ["uc", "Use case"]];
  const PLACE = {
    ask: "Ask about your keys, models and applications, or give a task. Enter sends, Shift+Enter adds a line.",
    search: "Search free APIs, news and your own models, e.g. text to speech, video generation, ocr …",
    uc: "Describe what you want to build in one or two sentences, I suggest suitable APIs."
  };
  const SUG = [
    ["Ask", "What is the best free model for code right now?", "ask"],
    ["Ask", "Which of my keys are broken?", "ask"],
    ["Search", "text to speech", "search"],
    ["Use case", "I want to generate subtitles from podcasts and translate them into German.", "uc"],
    ["Ask", "Scan my keys and probe the models now.", "ask"],
    ["Ask", "Show me the models for images.", "ask"]
  ];

  /* ---------- tiny markdown (text nodes only, no HTML) ---------- */
  const copy = t => { try { return navigator.clipboard.writeText(t); } catch (e) { return null; } };
  const safeUrl = u => /^https?:\/\//i.test(u || "") ? u : "#";
  const A = (u, t) => h("a", { href: safeUrl(u), target: "_blank", rel: "noopener noreferrer" }, t);
  function inl(s) {
    const out = [], re = /(`[^`\n]+`|\*\*[^*\n]+\*\*|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s<>")\]]+)/g;
    let i = 0, m;
    while ((m = re.exec(s))) {
      if (m.index > i) out.push(s.slice(i, m.index));
      const t = m[0];
      if (t[0] === "`") out.push(h("code", {}, t.slice(1, -1)));
      else if (t.startsWith("**")) out.push(h("b", {}, t.slice(2, -2)));
      else if (t[0] === "[") { const k = t.indexOf("]("); out.push(A(t.slice(k + 2, -1), t.slice(1, k))); }
      else out.push(A(t, t));
      i = m.index + t.length;
    }
    if (i < s.length) out.push(s.slice(i));
    return out;
  }
  function codeBlock(t) {
    const b = h("button", { class: "as-copy", type: "button", on: { click: () => { copy(t); b.textContent = "Copied"; setTimeout(() => { b.textContent = "Copy"; }, 1400); } } }, "Copy");
    return h("pre", {}, b, h("code", {}, t));
  }
  const LI = /^\s*[-*•]\s+/, OL = /^\s*\d+[.)]\s+/;
  function md(text) {
    const L = String(text || "").replace(/\r/g, "").split("\n"), out = [];
    let i = 0;
    while (i < L.length) {
      const x = L[i];
      if (/^```/.test(x)) { const buf = []; i++; while (i < L.length && !/^```\s*$/.test(L[i])) buf.push(L[i++]); i++; out.push(codeBlock(buf.join("\n"))); continue; }
      if (LI.test(x)) { const ul = h("ul"); while (i < L.length && LI.test(L[i])) ul.append(h("li", {}, inl(L[i++].replace(LI, "")))); out.push(ul); continue; }
      if (OL.test(x)) { const ol = h("ol"); while (i < L.length && OL.test(L[i])) ol.append(h("li", {}, inl(L[i++].replace(OL, "")))); out.push(ol); continue; }
      const hd = /^#{1,4}\s+(.*)$/.exec(x);
      if (hd) { out.push(h("p", {}, h("b", {}, inl(hd[1])))); i++; continue; }
      if (!x.trim()) { i++; continue; }
      const buf = [L[i++]];
      while (i < L.length && L[i].trim() && !/^```/.test(L[i]) && !LI.test(L[i]) && !OL.test(L[i]) && !/^#{1,4}\s/.test(L[i])) buf.push(L[i++]);
      out.push(h("p", {}, inl(buf.join("\n"))));
    }
    return out;
  }

  /* ---------- sessions ---------- */
  function newChat() {
    const e = st.list.find(c => !c.m.length);
    if (e) { st.cur = e.id; save(); redraw(); return e; }
    const c = { id: uid(), t: "New chat", ts: Date.now(), m: [] };
    st.list.unshift(c); st.cur = c.id; save(); redraw();
    return c;
  }
  function push(c, m) {
    m.ts = Date.now(); c.m.push(m); if (c.m.length > MAXM) c.m.splice(0, c.m.length - MAXM);
    c.ts = m.ts; st.list.sort((a, b) => b.ts - a.ts); save();
    if (c.id === st.cur) { const t = col.querySelector(".as-typing"); if (t) t.remove(); const hl = col.querySelector(".as-hello"); if (hl) hl.remove(); col.querySelectorAll(".as-regen").forEach(x => x.remove()); col.append(msgNode(m, c)); toEnd(); }
    drawSide();
  }
  function del(c) {
    if (c.m.length && !confirm("Delete this chat?")) return;
    if (busy[c.id]) busy[c.id].abort();
    st.list = st.list.filter(x => x !== c);
    if (st.cur === c.id) st.cur = st.list.length ? st.list[0].id : null;
    if (!st.cur) { newChat(); return; }
    save(); redraw();
  }
  const day = t => { const d = new Date(), s = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime(); return t >= s ? "Today" : t >= s - 864e5 ? "Yesterday" : "Earlier"; };
  const hm = t => new Date(t).toTimeString().slice(0, 5);

  /* ---------- views ---------- */
  let side, list, qin, ti, col, thread, ta, sendB, modes, hint, root;   /* created in build(): h() from ui.js does not exist yet when this file loads */

  function drawSide() {
    const rows = st.list.filter(c => !sq || c.t.toLowerCase().includes(sq) || c.m.some(m => String(m.c || m.q || "").toLowerCase().includes(sq)));
    let last = "";
    list.replaceChildren(...(rows.length ? rows.map(c => {
      const g = day(c.ts), hd = g !== last ? h("div", { class: "as-grp" }, g) : null; last = g;
      return [hd, h("div", { class: "as-it" + (c.id === st.cur ? " on" : ""), title: c.t, on: { click: () => { st.cur = c.id; save(); root.classList.remove("side"); redraw(); } } },
        h("span", { class: "t" }, c.t), h("button", { class: "x", type: "button", title: "Delete chat", "aria-label": "Delete chat", on: { click: e => { e.stopPropagation(); del(c); } } }, "✕"))];
    }).flat().filter(Boolean) : [h("div", { class: "as-empty" }, sq ? "No chat matches." : "No chats yet.")]));
  }
  function drawModes() {
    modes.replaceChildren(...MODES.map(([k, l]) => h("button", { type: "button", class: "as-mode" + (k === mode ? " on" : ""), on: { click: () => { mode = k; drawModes(); ta.focus(); } } }, l)));
    ta.placeholder = PLACE[mode];
    hint.replaceChildren(notice ? h("span", { class: "as-warn" }, notice) : "Free models can be wrong. Never paste keys here. Chats stay in this browser. Ctrl+K searches.");
  }
  function drawBar() { const c = cur(); ti.textContent = c ? c.t : "New chat"; }
  function toEnd() { if (stick) thread.scrollTop = thread.scrollHeight; }

  function hello() {
    const nokeys = typeof S !== "undefined" && S && S.keys && !S.keys.length;
    return h("div", { class: "as-hello" },
      h("h2", {}, "How can I help?"),
      h("p", {}, "Ask about your keys and models, search free APIs and news, or describe what you want to build. One input for all of it."),
      nokeys ? h("div", { class: "as-note" }, h("b", {}, "First step: add a free key."), " Without a key there is no model to answer. It takes a minute.", h("br"),
        h("button", { class: "b", type: "button", on: { click: () => window.goTab("Keys & Providers") } }, "Add a key")) : "",
      h("div", { class: "as-sug" }, SUG.map(([k, t, m]) => h("button", { type: "button", on: { click: () => { mode = m; drawModes(); send(t); } } }, h("small", {}, k), t))));
  }

  function actions(p) {
    if (!p) return "";
    return h("div", { class: "as-acts" }, h("button", { class: "b", type: "button", on: { click: async () => {
      if (p.tab) { window.goTab(p.tab); return; }
      await api(p.api, p.body); const c = cur(); if (c) push(c, { r: "a", c: "Done." }); if (window.refreshStatus) window.refreshStatus();
    } } }, p.tab ? "Open " + p.tab : "Do it: " + p.label));
  }
  function meta(m, c, isLast) {
    return h("div", { class: "as-meta" }, h("span", {}, hm(m.ts)), m.model ? h("span", {}, "answered by " + m.model.replace(/^([^\/]+)\/\1\//, "$1/")) : "",
      m.k ? "" : h("button", { class: "as-lnk", type: "button", on: { click: () => copy(m.c) } }, "Copy"),
      (isLast && !m.k) || m.err ? h("button", { class: "as-lnk" + (m.err ? "" : " as-regen"), type: "button", on: { click: () => again(c) } }, m.err ? "Try again" : "Regenerate") : "");
  }

  /* results of searches, rendered inline in the thread; the cards come from the Radar module so the safety checks work the same */
  const RU = () => window.RADAR_UI || {};
  const chip = (t, c) => h("span", { class: "rd-chip " + (c || "") }, t);
  function modelRows(rows) {
    return [h("h4", {}, "Your models (" + rows.length + ")"),
      rows.map(r => h("div", { class: "as-row" }, h("b", {}, r.provider + " / " + r.model), chip(r.faehigkeit || "chat"), chip(r.status || "", r.status === "ok" ? "ok" : ""))),
      h("div", { class: "as-row" }, h("button", { class: "as-lnk", type: "button", on: { click: () => window.goTab("Models") } }, "Open the Models tab for the full list"))];
  }
  function searchNode(m) {
    const r = m.res || {}, ru = RU();
    const apis = (r.apis || []).map(a => ru.apiKarte ? ru.apiKarte(a) : h("div", { class: "as-row" }, h("b", {}, a.name), " ", a.beschr || ""));
    const news = (r.news || []).map(x => h("div", { class: "rd-item" }, ru.link ? ru.link(x.link, x.titel) : A(x.link, x.titel), h("div", { class: "rd-why" }, x.feed || "")));
    return h("div", {},
      h("p", {}, "Results for ", h("b", {}, m.q), ":"),
      r.models && r.models.length ? h("div", { class: "as-sec" }, modelRows(r.models)) : "",
      h("div", { class: "as-sec" }, h("h4", {}, "Free APIs (" + apis.length + ")"), apis.length ? apis : h("div", { class: "as-row" }, "Nothing found. Try English keywords such as speech, image, ocr.")),
      news.length ? h("div", { class: "as-sec" }, h("h4", {}, "News (" + news.length + ")"), news) : "",
      h("p", { class: "mu" }, "“Nothing unusual” only means no warning signs were found, not proof. Free quotas change, check the provider's page."));
  }
  function ucNode(m) {
    const u = m.res || {}, ru = RU();
    return h("div", {},
      u.zusammenfassung ? h("p", {}, u.zusammenfassung) : "",
      h("div", { class: "as-acts" }, (u.faehigkeiten || []).map(f => chip(f, "ok")), (u.suchbegriffe || []).map(f => chip("🔎 " + f, "info"))),
      (u.schon_da || []).length ? h("div", { class: "as-sec" }, h("h4", {}, "You already have this"), u.schon_da.map(x => h("div", { class: "as-row" }, h("b", {}, x.provider + " / " + x.model), h("span", { class: "mu" }, x.warum || "")))) : "",
      h("div", { class: "as-sec" }, h("h4", {}, "New suggestions"), (u.empfehlungen || []).length ? u.empfehlungen.map(a => ru.apiKarte ? ru.apiKarte(a) : h("div", { class: "as-row" }, a.name)) : h("div", { class: "as-row" }, "No safe results. Rephrase the use case, the index keeps growing.")),
      (u.news || []).length ? h("div", { class: "as-sec" }, h("h4", {}, "Suitable news"), u.news.map(x => h("div", { class: "rd-item" }, ru.link ? ru.link(x.link, x.titel) : A(x.link, x.titel)))) : "",
      u.eingeordnet_von ? h("p", { class: "mu" }, "Categorized by: " + u.eingeordnet_von) : "");
  }
  /* a new free API the radar found; OMNI shows at most two a day and learns from the answer */
  function offer(c, o) { push(c, { r: "a", k: "offer", c: "New free API: " + (o.name || ""), res: o }); }
  function offerNode(m) {
    const o = m.res || {}, ru = RU();
    const answer = async a => { try { await post("angebot/antwort", { id: o.id, antwort: a }); } catch (e) { /* offline: the answer is kept here */ } m.done = a; save(); drawThread(); };
    return h("div", {},
      h("p", {}, h("b", {}, "New free API found: "), o.name || ""),
      o.beschr ? h("p", { class: "mu" }, String(o.beschr).slice(0, 300)) : "",
      h("div", { class: "as-row" }, ru.link ? ru.link(o.url, o.url) : A(o.url, o.url)),
      m.done === "ja" ? h("div", { class: "as-acts" }, h("span", { class: "mu" }, "Noted. Add its key once you have one. "),
          h("button", { class: "b", type: "button", on: { click: () => window.goTab("Keys & Providers") } }, "Open Keys & Providers"))
        : m.done ? h("p", { class: "mu" }, "OK, fewer offers like this from now on.")
        : h("div", { class: "as-acts" },
            h("button", { class: "b", type: "button", on: { click: () => answer("ja") } }, "Interested"),
            h("button", { class: "b", type: "button", on: { click: () => answer("nein") } }, "Not interested")),
      h("p", { class: "mu" }, "OMNI offers at most two new APIs a day. Free quotas change, check the provider's page."));
  }
  function msgNode(m, c) {
    if (m.r === "u") return h("div", { class: "as-msg u" }, h("div", { class: "as-bub" }, m.c));
    const last = c.m[c.m.length - 1] === m;
    const body = m.k === "search" ? searchNode(m) : m.k === "uc" ? ucNode(m) : m.k === "offer" ? offerNode(m) : h("div", { class: m.err ? "as-err" : "" }, md(m.c));
    return h("div", { class: "as-msg a" }, h("div", { class: "as-av" }, "A"), h("div", { class: "as-bub" }, body, actions(m.proposal), meta(m, c, last)));
  }
  const typing = () => h("div", { class: "as-msg a as-typing" }, h("div", { class: "as-av" }, "A"), h("div", { class: "as-bub" }, h("span", { class: "as-dots" }, h("span"), h("span"), h("span"))));

  function drawThread() {
    const c = cur();
    col.replaceChildren();
    if (!c || !c.m.length) col.append(hello());
    else c.m.forEach(m => col.append(msgNode(m, c)));
    if (c && busy[c.id]) col.append(typing());
    drawBar(); drawBtn(); toEnd();
  }
  function drawBtn() { const c = cur(), b = c && busy[c.id]; sendB.textContent = b ? "Stop" : "Send"; sendB.classList.toggle("stop", !!b); }
  function redraw() { drawSide(); drawThread(); }

  /* ---------- sending ---------- */
  const history = c => c.m.filter(m => !m.err && m.k !== "offer").map(m => ({ role: m.r === "u" ? "user" : "assistant", content: String(m.c || "").slice(0, 2000) })).filter(m => m.content);
  const title = (c, t, m0) => { if (c.m.filter(m => m.r === "u").length === 1) c.t = (m0 === "search" ? "🔎 " : m0 === "uc" ? "💡 " : "") + t.replace(/\s+/g, " ").slice(0, 46); };
  async function models(q) {
    if (Date.now() - MC.ts > 60000) { try { MC = { ts: Date.now(), rows: await api("modelle") }; } catch (e) { MC = { ts: Date.now(), rows: [] }; } }
    const w = q.toLowerCase().split(/\s+/).filter(Boolean);
    return (Array.isArray(MC.rows) ? MC.rows : []).filter(r => r.status !== "nicht_verfuegbar" && w.every(x => (r.provider + " " + r.model + " " + (r.faehigkeit || "")).toLowerCase().includes(x))).slice(0, 8);
  }
  async function post(path, body, signal) {
    const r = await fetch("/api/" + path, { method: "POST", headers: { "X-Omnipool": "1", "Content-Type": "application/json" }, body: JSON.stringify(body), signal });
    return r.json();
  }
  async function run(c, text, m0) {
    const ctl = new AbortController(); busy[c.id] = ctl;
    if (c.id === st.cur) { col.append(typing()); toEnd(); drawBtn(); }
    try {
      if (m0 === "search") {
        const [a, mm] = await Promise.all([api("radar/suche", { q: text }), models(text)]);
        if (ctl.signal.aborted) return;
        push(c, { r: "a", k: "search", q: text, c: "Search “" + text + "”: " + (a.apis || []).length + " APIs, " + (a.news || []).length + " news, " + mm.length + " of your models.", res: { apis: (a.apis || []).slice(0, 8), news: (a.news || []).slice(0, 6), models: mm } });
      } else if (m0 === "uc") {
        const u = await api("radar/usecase", { text });
        if (ctl.signal.aborted) return;
        push(c, { r: "a", k: "uc", q: text, c: "Use case: " + (u.zusammenfassung || text), res: u });
      } else {
        const r = await post("chat", { messages: history(c) }, ctl.signal);
        if (ctl.signal.aborted) return;
        if (r.reply) push(c, { r: "a", c: r.reply, model: r.model, proposal: r.proposal });
        if (r.reply && r.angebot && r.angebot.id) offer(c, r.angebot);
        else push(c, { r: "a", c: "Error: " + (r.error || "no answer"), err: true });
      }
    } catch (e) {
      if (!ctl.signal.aborted) push(c, { r: "a", c: "Error: " + (e && e.message || e), err: true });
    } finally {
      if (busy[c.id] === ctl) delete busy[c.id];
      if (c.id === st.cur) { const t = col.querySelector(".as-typing"); if (t) t.remove(); drawBtn(); }
    }
  }
  async function send(over) {
    let t = String(over != null ? over : ta.value).trim();
    if (!t) return;
    const c = cur() || newChat();
    if (busy[c.id]) return;
    let m0 = mode;
    const sl = /^\/(\w+)\b\s*([\s\S]*)$/.exec(t);
    if (sl) {
      const k = sl[1].toLowerCase();
      if (k === "new") { ta.value = ""; newChat(); return; }
      if (k === "clear") { ta.value = ""; c.m = []; c.t = "New chat"; save(); redraw(); return; }
      if (k === "help") { ta.value = ""; push(c, { r: "a", c: "Commands: /search words, /usecase text, /new, /clear. Or pick Ask, Search or Use case above the input." }); return; }
      if (["search", "api", "news"].includes(k)) { m0 = "search"; t = sl[2].trim(); }
      else if (["usecase", "uc"].includes(k)) { m0 = "uc"; t = sl[2].trim(); }
      if (!t) return;
    }
    if (SECRET.test(t)) { ta.value = ""; ta.style.height = ""; notice = "That looked like an API key, so it was not sent and not saved. Add keys in the tab “Keys & Providers”."; drawModes(); return; }
    if (m0 === "uc" && t.length < 5) { notice = "Describe the use case in a few more words."; drawModes(); return; }
    notice = ""; ta.value = ""; ta.style.height = ""; stick = true;
    push(c, { r: "u", c: t }); title(c, t, m0); drawBar(); drawModes();
    await run(c, t, m0);
  }
  function again(c) {
    if (busy[c.id]) return;
    while (c.m.length && c.m[c.m.length - 1].r === "a") c.m.pop();
    const u = c.m[c.m.length - 1]; if (!u) return;
    save(); drawThread(); run(c, u.c, "ask");
  }

  /* ---------- wiring (once) ---------- */
  function build() {
    built = true;
    side = h("aside", { class: "as-side" }); list = h("div", { class: "as-list" });
    qin = h("input", { type: "text", placeholder: "Search chats", "aria-label": "Search chats", on: { input: e => { sq = e.target.value.toLowerCase(); drawSide(); } } });
    ti = h("span", { class: "ti" });
    col = h("div", { class: "as-col" }); thread = h("div", { class: "as-thread" }, col);
    ta = h("textarea", { rows: "1", "aria-label": "Message" });
    sendB = h("button", { class: "as-send", type: "button" }, "Send");
    modes = h("div", { class: "as-modes" }); hint = h("div", { class: "as-hint" });
    root = h("div", { class: "as" });
    ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = Math.min(180, ta.scrollHeight) + "px"; if (notice) { notice = ""; drawModes(); } });
    ta.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
    sendB.addEventListener("click", () => {
      const c = cur();
      if (c && busy[c.id]) { busy[c.id].abort(); delete busy[c.id]; const t = col.querySelector(".as-typing"); if (t) t.remove(); drawBtn(); } else send();
    });
    thread.addEventListener("scroll", () => { stick = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 80; }, { passive: true });
    side.append(h("div", { class: "as-top" }, h("button", { class: "b", type: "button", on: { click: () => { newChat(); ta.focus(); } } }, "+ New chat"), qin), list);
    const bar = h("div", { class: "as-bar" }, h("button", { class: "as-ghost tg", type: "button", on: { click: () => root.classList.toggle("side") } }, "Chats"), ti,
      h("button", { class: "as-ghost", type: "button", on: { click: () => { const c = cur(); if (!c) return; const n = prompt("Rename chat", c.t); if (n && n.trim()) { c.t = n.trim().slice(0, 60); save(); drawBar(); drawSide(); } } } }, "Rename"));
    const comp = h("div", { class: "as-comp" }, h("div", { class: "as-col" }, modes, h("div", { class: "as-box" }, ta, sendB), hint));
    root.append(side, h("div", { class: "as-main" }, bar, thread, comp));
    addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); window.goTab("Assistant"); mode = "search"; drawModes(); ta.focus(); } });
    window.RR_HOOK = () => { if (!root.isConnected) return false; drawThread(); return true; };
    if (!st.list.length) newChat(); else if (!cur()) st.cur = st.list[0].id;
    drawModes(); redraw();
    post("angebot", {}).then(o => { if (o && o.id) offer(cur() || newChat(), o); }).catch(() => {});   // at most twice a day, server decides
  }
  function view() {
    if (!built) build();
    const y = thread.scrollTop, keep = !stick;
    requestAnimationFrame(() => { thread.scrollTop = keep ? y : thread.scrollHeight; });
    return root;
  }
  window.ASSIST = { view, fresh: () => { if (!built) build(); newChat(); setTimeout(() => ta.focus(), 0); } };
})();
