# DESIGN (Chef: nvidia/nvidia/nemotron-3-ultra-550b-a55b)

# Omnipool – Designdokument (Synthese aus 10 Entitäten)

---

### 1) Leitidee
**Omnipool ist der eine Knopf, der „Gratis-KI läuft“ bedeutet – und beim zweiten Blick das gesamte Kontrollzentrum für Keys, Modelle, Routing und Radar freilegt, ohne den Nutzer je zu fragen, wer er ist.**

---

### 2) Sechs Designprinzipien

| # | Prinzip | Kernaussage |
|---|---------|-------------|
| **P1** | **Time-to-First-Success < 30 s** | Der Leerzustand zeigt *genau eine* primäre Aktion („Gratis-KIs suchen & verbinden“). Kein Wizard, kein Modal, kein Tutorial. |
| **P2** | **Progressive Disclosure = Auflösungsskalierung** | Laien sehen 4 Karten + 1 CTA. Profis klappen per globalem Toggle (`einfach ⇄ technisch`) oder `Cmd/Ctrl+K` die volle Dichte auf. Derselbe DOM, andere CSS-Sichtbarkeit. |
| **P3** | **Status als Narrativ, nicht als Log** | Header-Leiste (sticky, 40 px) zeigt *einen* lesbaren Satz: „🟢 Verbunden mit Kimi K2 via Moonshot – 12 Modelle verfügbar“. Details auf Klick. |
| **P4** | **Beleg vor Behauptung** | Jede Metrik (Latenz, Score, Health) trägt `data-evidence` → Klick öffnet `<dialog>` mit Roh-JSON, Timestamp, Skript-Hash. Keine „Black-Box-Rankings“. |
| **P5** | **Prozess vor Zustand (Live-Puls)** | Ein fixes, schmales Event-Stream-Panel (rechts/unten, WebComponent `<event-stream>`) zeigt die letzten 5 generativen Übergänge (Key validiert, Modell geroutet, Radar-Treffer). Zeit ist sichtbar. |
| **P6** | **Ehrliche Unsicherheit als Default** | Jeder Key/Modell/Eintrag hat einen „Vertrauens-Ring“ (CSS `border-left`: grün/gelb/rot/grau). Keine „Best Model“-Badges, nur „Aktuell optimal für: Code (Speed), Chat (Context), Local (Privacy)“. |

---

### 3) Die ersten fünf Sekunden

| Nutzer | Sicht (ms) | Kann sofort tun |
|--------|------------|-----------------|
| **Laie** | **0–200** Weißer Screen → Header (grüner Punkt „Dienst läuft“) → **eine** zentrierte Karte: „🟢 Gratis-KIs jetzt suchen & verbinden“ (Primär-CTA) + kleiner Sekundärlink „Ich habe schon Keys“.<br>**200–1000** Klick CTA → Side-Panel (320 px) slidet ein: „Suche läuft…“ (Progressbar, WebWorker) → Karten: Anbieter, Limit, Speed → Button „Übernehmen & Verbinden“.<br>**1000–5000** Panel schließt sich, Header aktualisiert Narrativ: „Verbunden mit …“, Tab „Verbinden“ zeigt erkanntes Tool (Claude Code, Aider…) mit „Verbinden“-Button. | **Einen Klick** → lauffähige Gratis-KI im Lieblings-Tool. |
| **Profi** | **0–50** Erkennt Header-Statusleiste (Kreis, Modell, Kosten-Limit), Profi-Toggle (`einfach/technisch`) oben rechts, `Cmd/Ctrl+K` Command Palette.<br>**50–200** Klickt Toggle → alle 8 Reiter sichtbar, Tabellen zeigen erweiterte Spalten (Latenz, Security-Score, Routing-Prio), Delta-Spalte „Δ 24h“.<br>**200–500** Nutzt `Cmd/Ctrl+K` → „Key importieren“, „Routing-Logik editieren“, „Radar-Export“. | **Null Klicks** für Kontext, **ein Shortcut** für jede Power-Aktion. |

---

### 4) Modell „geführt vs. Profi“ (ohne Bevormundung)

1. **Globaler Modus-Schalter** (Header, `role="switch"`, `aria-pressed`), speichert in `localStorage.mode = 'simple' | 'expert'`.  
   *CSS only*: `[data-mode="simple"] .pro-only { display: none; }` / `[data-mode="expert"] .pro-only { display: revert; }`.  
   Kein Re-Render, kein JS-Neustart.
2. **Tabs als 2 Ebenen** (CSS Grid):  
   - Ebene 1 (immer): **Übersicht, Verbinden, Einstellungen**.  
   - Ebene 2 (`<details>` default `closed`): **Keys & Anbieter, Modelle, Ereignisse, Radar, API-Suche, Usecases**.  
   Profi-Modus setzt `open` auf alle `<details>`.
3. **Leerzustände = Aktions-Anleitung** (nicht Doku).  
   Beispiel Keys-Tab: „Noch keine Keys. [Kostenlose Keys scannen] [Manuell eintragen] [Beispiele laden]“.
4. **Command Palette (`Cmd/Ctrl+K`)** ist der Profi-Eingang. Laien sehen sie nie (kein Button, nur Shortcut).
5. **Keine Modals für Kern-Flows**. Side-Panels (`position: fixed; inset-inline-end: 0`) oder Inline-Expansion (`<details>`). Modals nur für **harte Gates** (erster fremder Key → natives `<dialog>` „Key verlässt deinen Rechner…“).

---

### 5) Ton der Texte (Microcopy-Regeln)

| Regel | Beispiel (statt Fachbegriff) |
|-------|------------------------------|
| **Plain Language** | „Anbieter“ statt „Provider“, „Server-Adresse“ statt „Endpoint“, „Wer wann was macht“ statt „Routing Policy“. |
| **Handlungsorientiert** | Buttons: „Gratis-KIs suchen“, „Claude Code verbinden“, „Key prüfen“ – nie „Absenden“, „Speichern“, „Konfigurieren“. |
| **Ehrlich & zeitgestempelt** | „Aktuell optimal für Code (Speed) – Stand 14:32“ statt „Bestes Modell“. |
| **Fehler = Wegweiser** | „Key abgelaufen. [Neuen gratis Key holen] [Eigenen Key eintragen]“ statt „Error 401“. |
| **Kein Marketing-Sprech** | Kein „Kostenlos für immer“, sondern „Gratis-Tier, Limit 50 req/min, geprüft vor 2 min“. |
| **Inline-Hilfe via `<dfn data-tipp>`** | Hover/Focus zeigt Definition, kein Modal, kein Tooltip-JS. |

---

### 6) Ehrlichkeitsregeln (Non-Negotiables)

1. **Keine Keys im Renderer-LocalStorage** – nur maskiert (`sk-***key`) via IPC aus verschlüsseltem Background-Store (OS Keychain/DPAPI).
2. **Keine stillen Key-Wechsel / Routing-Änderungen** – jeder Wechsel erzeugt Eintrag im Event-Stream + Toast „Modell gewechselt: Grund: Latency“.
3. **Keine „Best Model“-Absoluta** – nur kontextabhängige Empfehlungen mit Beleg (`data-evidence`).
4. **Kein Polling ohne Backoff** – Daemon-Status via WebSocket/EventSource; Fallback Exponential Backoff (5 s, 10 s, 30 s).
5. **Offline-First** – UI rendert sofort aus `indexedDB` (`omnipool-cache`), Sync im Hintergrund (`If-None-Match`).
6. **Keine Framework-Abhängigkeiten** – Vanilla ES Modules, CSS Custom Properties, Native Web Components (`<event-stream>`, `<key-card>`, `<model-table>`).
7. **Accessibility First** – Alle CTAs `<button>`, `:focus-visible` Ringe, ARIA-Live für Scan-Status, Tastatur-Trap in Side-Panels.
8. **`prefers-reduced-motion`** zwingend respektieren (Transitionen ≤ 150 ms oder 0).

---

### 7) Tickets (JSON, max. 12, sortiert nach Wirkung)

```json
[
  {
    "id": "T1",
    "titel": "Header-Statusleiste mit Narrativ & Profi-Toggle",
    "datei": "ui.css|ui.js",
    "beschreibung": "Sticky 40px Header: linker Kreis (Grün/Rot/Gelb), mittlerer Text-Knoten für Narrativ (z. B. '🟢 Verbunden mit Kimi K2 via Moonshot – 12 Modelle verfügbar'), rechter Toggle 'einfach/technisch' (role=switch) + Cmd/Ctrl+K Listener. CSS-Variable --mode auf <html> setzen.",
    "abnahme": "Header sichtbar, Narrativ aktualisiert sich bei IPC-Event 'status', Toggle kippt data-mode Attribut, Shortcut öffnet Command Palette (späteres Ticket)."
  },
  {
    "id": "T2",
    "titel": "Start-Tab 'Übersicht': Single-Entry-Card + Leerzustand-CTA",
    "datei": "ui.js|texte.json",
    "beschreibung": "Tab 'Übersicht' rendert nur eine zentrierte Card (CSS Grid). Wenn localStorage.hasData !== true: Primär-Button data-action='auto-scan' (Text aus texte.json), Sekundär-Link 'Ich habe schon Keys'. Bei Daten: 4 Status-Kacheln (Keys, Modelle, Verbindungen, Radar-Kurzfassung) + Primär-CTA 'Jetzt starten' (prüft Daemon, Keys, Tool).",
    "abnahme": "Leerer Start zeigt genau 1 großen Button + Link. Nach Scan zeigen Kacheln Zahlen. Button 'Jetzt starten' triggert IPC 'start-routing'."
  },
  {
    "id": "T3",
    "titel": "Side-Panel 'Auto-Scan' (Wizard-lite, 320px, Focus-Trap)",
    "datei": "ui.js|ui.css",
    "beschreibung": "Slide-in Panel (position:fixed, right:0, width:320px). Schritt 1: WebWorker Scan + Progressbar (ARIA-Live). Schritt 2: Karten-Liste (Anbieter, Limit, Speed, Vertrauens-Ring). Schritt 3: Button 'Übernehmen & Verbinden' → IPC 'apply-keys'. Panel schließbar, Zustand in localStorage.onboardingStep persistiert. Kein 'Weiter'-Zwang.",
    "abnahme": "Panel öffnet bei Klick Primär-CTA, zeigt Fortschritt, listet Ergebnisse mit Farbring, Übernehmen sendet Keys an Background, Panel schließt, Header-Narrativ aktualisiert."
  },
  {
    "id": "T4",
    "titel": "Tab-Struktur: 2 Ebenen via <details> + Profi-Modus-CSS",
    "datei": "ui.css|ui.js",
    "beschreibung": "Nav-Leiste: Ebene 1 (Übersicht, Verbinden, Einstellungen) immer sichtbar. Ebene 2 (Keys & Anbieter, Modelle, Ereignisse, Radar, API-Suche, Usecases) als <details class='pro-only'> default closed. JS: bei Mode-Wechsel alle <details>.pro-only open/closed setzen. Badge an Tab (z. B. '12') per data-count Attribut.",
    "abnahme": "Im Modus 'einfach' nur 3 Tabs + Chevron 'Mehr'. Im Modus 'technisch' alle 8 Tabs offen. Badge '12' erscheint am Modelle-Tab nach erstem Scan."
  },
  {
    "id": "T5",
    "titel": "Keys & Anbieter: Health-First Tabelle + Inline-Evidenz",
    "datei": "ui.js|ui.css|texte.json",
    "beschreibung": "Tabelle Spalten: Anbieter, Key (maskiert), Status (Badge: ✅ OK / ⚠️ Rate Limited / ❌ Dead), Letzter Check, Aktion (Neu prüfen, Löschen). Sort: Status desc, Latency asc. Jede Zelle <td data-evidence='run-123'> → Klick öffnet <dialog> mit Roh-JSON. Doppelklick Row → ContentEditable für Profi-Rohbearbeitung. Leerzustand: 3 Buttons (Scan, Manuell, Beispiele).",
    "abnahme": "Tabelle zeigt Health-Badges, Klick Metrik öffnet Evidenz-Dialog, Doppelklick editiert, Leerzustand hat 3 Aktions-Buttons."
  },
  {
    "id": "T6",
    "titel": "Modelle: Routing-Matrix mit Delta-Spalte & Drag-Prio",
    "datei": "ui.js|ui.css",
    "beschreibung": "Spalten: Modell, Anbieter, Fähigkeiten (Tags), Score (0-100), Enabled (Toggle), Δ 24h (Pfeil + Wert, CSS .delta-up/.delta-down). Drag-and-Drop (native HTML5 DnD) ändert Routing-Prio → IPC 'update-routing'. Modus 'einfach': nur Top 3 'Empfohlen' sichtbar (andere display:none).",
    "abnahme": "Drag-and-Drop funktioniert, Delta-Spalte zeigt Änderung, Modus 'einfach' blendet alle bis auf Top 3 aus."
  },
  {
    "id": "T7",
    "titel": "Verbinden: Tool-Detektor + One-Click-Patcher + Config-Copy",
    "datei": "ui.js|texte.json",
    "beschreibung": "Liste bekannter Tools (data-tool='claude-code|aider|crush|hermes'). Erkennung via IPC 'detect-tools'. Pro Tool: Status 'Nicht verbunden / Verbunden', Button 'Verbinden' → IPC 'patch-config' (Backup → Set OPENAI_API_BASE/KEY → Restore-Button). Erfolg: Toast + Header-Narrativ. Code-Block (env, JSON) mit Copy-Button.",
    "abnahme": "Erkannte Tools gelistet, Klick 'Verbinden' patcht Config, Restore-Button erscheint, Config-Block kopierbar."
  },
  {
    "id": "T8",
    "titel": "Event-Stream WebComponent <event-stream> (Live-Puls)",
    "datei": "ui.js|ui.css",
    "beschreibung": "Native WebComponent, fixed bottom-right (300px x 200px), sticky über alle Tabs. Empfängt Server-Sent-Events vom Background (EventSource). Rendert letzte 5 Einträge: Icon, Zeit, Text ('Key X validiert', 'Modell Y geroutet', 'Radar: Neuer Anbieter Z'). Klick Entry → Slide-in Drawer mit Raw-JSON. Filter-Chips (Alle/Info/Warnung/Fehler/Rotation). Virtual Scroller (IntersectionObserver) für Historie.",
    "abnahme": "Component zeigt Live-Events, Filter funktionieren, Klick öffnet Drawer mit JSON, keine DOM-Explosion (>500 Nodes)."
  },
  {
    "id": "T9",
    "titel": "Radar / API-Suche / Usecases: Labor-Drawer (Lazy Load)",
    "datei": "ui_radar.js|ui.css",
    "beschreibung": "Nicht in Tab-Leiste. Zugriff via Header-Icon 🧪 (title='Labor'). Öffnet Right-Drawer (full height). Inhalte: 3 Sub-Tabs (Radar, API-Suche, Usecases) als <details>. Lazy Load: dynamic import() von ui_radar.js beim ersten Öffnen. Karten im Grid (auto-fit minmax 280px). Primär Metriken (Free Tier, Open Weights, Local First), Name auf Hover. Clientseitiger Filter (input[type=search] auf data-tags).",
    "abnahme": "Icon öffnet Drawer, Sub-Tabs laden ui_radar.js erst bei Klick, Karten zeigen Metriken zuerst, Filter läuft clientseitig."
  },
  {
    "id": "T10",
    "titel": "Command Palette (Cmd/Ctrl+K) für Profis",
    "datei": "ui.js|texte.json",
    "beschreibung": "Globaler Keydown-Listener (Meta/Ctrl+K). Öffnet <dialog role='searchbox'> mit <input type='search'>. Fuzzy-Suche (einfaches includes) über Aktionen aus texte.json: 'Key hinzufügen', 'Modell testen', 'Log exportieren', 'Routing editieren', 'Radar öffnen', 'Einstellungen'. Enter → führt Aktion aus (Router/Handler). ESC schließt. ARIA: aria-controls, aria-activedescendant.",
    "abnahme": "Shortcut öffnet Palette, Suche filtert Liste, Enter führt Aktion aus (z. B. öffnet Keys-Tab + fokussiert 'Neu prüfen')."
  },
  {
    "id": "T11",
    "titel": "Sicherheits-Gate: Natives <dialog> beim ersten fremden Key",
    "datei": "ui.js|texte.json",
    "beschreibung": "IPC 'key-added' prüft localStorage.securityGateSeen. Wenn false: natives <dialog> (modal), Text: 'Dieser Key verlässt deinen Rechner. Wir prüfen: Gültigkeit, Rate-Limits, bekannte Leaks. Fortfahren?' Checkbox 'Nicht wieder fragen' → localStorage Flag. Buttons: 'Prüfen & Übernehmen', 'Abbrechen'. Kein Framework-Modal.",
    "abnahme": "Beim ersten Key-Add (via Scan oder Manuell) öffnet Dialog, Checkbox setzt Flag, 'Prüfen' triggert IPC 'validate-key', 'Abbrechen' verwirft."
  },
  {
    "id": "T12",
    "titel": "Offline-First Cache & Sync-Status-Icon",
    "datei": "ui.js|ui.css",
    "beschreibung": "IndexedDB 'omnipool-cache' (Stores: keys, models, radar, events). UI rendert synchron aus Cache beim Start. Background-Service sendet 'sync-complete' Event → Header-Icon (Wolke/Sync) wechselt: grün (synced), gelb (pending), rot (offline/fehler). Tooltip: 'Letzter Sync: 14:32'. Netzwerk-Requests nur bei User-Aktion oder Background-Sync.",
    "abnahme": "App startet <100ms mit Daten (Cache). Sync-Icon zeigt Status, Tooltip hat Timestamp. Kein Spinner beim Start."
  }
]
```
