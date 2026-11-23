/* API-OMNI-BRAIN manual tab: text + screenshots, loaded from /manual.json and /manual/<id>.png. Standalone (IIFE), appends one tab to window.EXTRA, uses only h() from ui.js.
   No innerHTML; every text comes from manual.json and is inserted as text. */
(function () {
  const css = document.createElement("style");
  css.textContent = `
    .mn{max-width:980px}
    .mn-toc{display:flex;flex-wrap:wrap;gap:var(--space-2,8px);margin:12px 0 20px}
    .mn-toc button{border:1px solid var(--line,#2a2a2e);background:transparent;color:var(--ink-muted,#aaa);border-radius:999px;padding:4px 12px;cursor:pointer;font:inherit;font-size:13px}
    .mn-toc button:hover,.mn-toc button:focus-visible{color:var(--ink,#eee);border-color:var(--ac,#6ea8fe)}
    .mn-sec{margin:0 0 24px;padding:20px;border:1px solid var(--line,#2a2a2e);border-radius:12px;background:var(--bg-elev,#151517);scroll-margin-top:72px}
    .mn-sec h2{margin:0 0 6px;font-size:20px}
    .mn-sum{margin:0 0 14px;color:var(--ink-muted,#aaa);line-height:1.55}
    .mn-shot{display:block;width:100%;max-width:880px;border:1px solid var(--line,#2a2a2e);border-radius:8px;margin:0 0 14px;cursor:zoom-in;background:#0b0b0c}
    .mn-shot.big{max-width:none;cursor:zoom-out}
    .mn-sec ol{margin:0 0 14px;padding-left:22px;line-height:1.6}
    .mn-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
    .mn-can,.mn-cannot{padding:12px 14px;border-radius:8px;border:1px solid var(--line,#2a2a2e)}
    .mn-can{border-color:rgba(74,222,128,.35)}
    .mn-cannot{border-color:rgba(248,113,113,.45)}
    .mn-can h3,.mn-cannot h3{margin:0 0 6px;font-size:13px;letter-spacing:.06em;text-transform:uppercase}
    .mn-can h3{color:var(--ok,#4ade80)}
    .mn-cannot h3{color:var(--er,#f87171)}
    .mn-can ul,.mn-cannot ul{margin:0;padding-left:18px;line-height:1.55}
    .mn-resp{border:2px solid var(--er,#f87171);border-radius:12px;padding:16px 20px;font-weight:700;line-height:1.55}
    @media (prefers-reduced-motion:no-preference){.mn-sec{animation:mnin .35s ease both}@keyframes mnin{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}}
  `;
  document.head.appendChild(css);

  let doc = null, failed = false;

  function list(tag, items) {
    return h(tag, {}, ...(items || []).map(x => h("li", {}, String(x))));
  }

  function section(s) {
    const img = h("img", { class: "mn-shot", src: "/manual/" + s.image, alt: "Screenshot: " + s.title, loading: "lazy", on: { click: e => e.target.classList.toggle("big") } });
    img.addEventListener("error", () => img.remove());
    return h("section", { class: "mn-sec", id: "mn-" + s.id },
      h("h2", {}, s.title), h("p", { class: "mn-sum" }, s.summary || ""), img,
      s.steps && s.steps.length ? list("ol", s.steps) : "",
      h("div", { class: "mn-cols" },
        h("div", { class: "mn-can" }, h("h3", {}, "What it can do"), list("ul", s.can)),
        h("div", { class: "mn-cannot" }, h("h3", {}, "What it cannot do - and must not"), list("ul", s.cannot))));
  }

  function manual() {
    const box = h("div", { class: "mn" });
    if (!doc) {
      box.append(h("p", {}, failed ? "The manual could not be loaded." : "Loading the manual ..."));
      if (!failed) {
        fetch("/manual.json").then(r => r.json()).then(d => { doc = d; if (document.querySelector(".mn")) document.querySelector("#main").replaceChildren(manual()); }).catch(() => { failed = true; });
      }
      return box;
    }
    box.append(h("h2", {}, "Manual"), h("p", { class: "mn-sum" }, doc.intro || ""),
      h("div", { class: "mn-toc" }, ...doc.sections.map(s => h("button", { on: { click: () => { const e = document.getElementById("mn-" + s.id); if (e) e.scrollIntoView({ behavior: "smooth", block: "start" }); } } }, s.title))));
    doc.sections.forEach(s => box.append(section(s)));
    box.append(h("section", { class: "mn-sec" }, h("h2", {}, "What this app cannot do - and does not want to"), list("ul", doc.global_cannot)),
      h("div", { class: "mn-resp" }, doc.responsibility || "You are responsible for how you use this software."));
    return box;
  }

  window.EXTRA = (window.EXTRA || []).concat([{ name: "Manual", fn: manual }]);
})();
