# 10-chef (Chef: Gegenleser)
Model: nvidia/nvidia/nemotron-3-ultra-550b-a55b

### 1) Key Insights
1. **Tabs ≠ Navigation, Tabs = Context Switch.** 8 tabs at the top immediately cause "decision paralysis" (Hick's Law). Novices search for "Start", Pros search for "Keys". Both in the same tab bar container is UX betrayal.
2. **"Ease into it" ≠ Wizard/Overlay.** Modal tutorials annoy Pros (Blockade) and Novices (Forgetfulness). Guidance must *live* in the UI (Progressive Disclosure), not in front of it.
3. **Background service = Blackbox fear.** When the service runs but nowhere visible *what* it does (test keys, scan radar), the app feels "broken" or "spying". Trust is created through *Live Transparency*, not logs.
4. **Dual-User-Interface is a myth.** One layout for both fails. Novices need *one* big "Run" button. Pros need *Density* (tables, filters, shortcuts). Compromise = trash for both.
5. **"Radar", "API search", "Usecases" are Features, not Tabs.** These are content for *later* (discovery), not for *now* (onboarding). They belong on a "Discover" page, not in primary navigation.

### 2) Concrete Rules (Vanilla JS/CSS/HTML)
1. **Two entry points, one app.** Start view: **"Just get started"** (1 button: "Find & connect to best free model") **OR** "Expert mode" (toggle top right, saves in `localStorage`). No tab jungle at start.
2. **Progressive Disclosure via `details`/`summary` & CSS `has()`.** Tabs "Keys", "Models", "Connect" are **hidden by default** (`display: none`). They appear *only* when: a) Expert mode is ON **OR** b) Novice has first success ("Connected to X"). CSS: `#expert-mode:checked ~ .pro-panels { display: grid; }`.
3. **Status bar instead of log window.** Fixed 40px bar at bottom: `[Service: ● Green] [Last check: 12s ago] [Active model: Llama-3-70b] [● Live Radar]`. Click on "Live Radar" opens side drawer (not new tab). Novices see "It's running", Pros see metrics.
4. **"Connect" = Goal, not tab.** The tab "Connect" is called **"Targets"** and shows *only* installed tools (Claude Code, Aider, VS Code). One click → "Set as default" + Key injection. Done. No configuration forms.
5. **Radar/API search/Usecases = "Marketplace" (one tab).** One single tab "Marketplace", with 3 segments (toggle buttons). Prevents tab overflow, signals: "Here is more".
6. **Zero-Config Default.** On first start: Auto-scan → Best free model (Score: Speed/Quality/Free-Limit) → Auto-inject into detected tool. **No key management needed** as long as free keys work. Keys & providers only show when auto-scan fails or limit is reached.
7. **Keyboard-First for Pros.** `Cmd/Ctrl+K` = Command Palette (all actions: "Add key", "Switch model", "Open radar", "Logs"). Pros ignore mouse/UI completely.
8. **Errors = Action request, not red.** API key invalid? Inline in key row: `⚠️ Limit reached → [Search for new key]` (opens Marketplace/API search filtered). No toast, no modal.

### 3) What you should NOT do
*   **Do not** render all 8 tabs and hide them via CSS (DOM bloat, screenreader chaos). Render *on demand*.
*   **Do not** build an "first-time setup wizard." The first click must *create value* (model runs), not ask for data.
*   **Do not** put "Settings" as a tab. Settings = gear icon (modal/drawer), global, contextless.
*   **Do not** mix novice terms ("Simple") and pro terms ("Routing"). Use **modes** (Simple/Expert) that render the *same* UI differently dense.
*   **Do not** let the background service run "quietly." Without visible heartbeat (status bar), the novice uninstalls the app after 5 minutes of silence.
