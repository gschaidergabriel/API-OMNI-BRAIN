# 03-web-ux (Web Researcher: UX Sources)
Model: nvidia/z-ai/glm-5.3-flash

**Note:** No web page excerpts were provided. The analysis is based on UX best practices for hybrid audiences (laypersons/professionals) with complex local tools (Key Management, Routing, Daemon Architecture).

---

### 1) Core Insights (with Reasoning)

1.  **Dual-Mode Architecture is Mandatory, Not a Feature.** Laypersons need a "Magic Button" (One-Click Start), professionals need transparency (Logs, Ranking Algo, Key Health). *Reasoning:* A single mode overwhelms laypersons (cognitive load) or bores professionals (Black Box). The mode switch must be persistent & global (e.g., Toggle in the Titlebar).
2.  **The Daemon is Invisible, But Its Status is the Life Insurance.** Users only trust local tools if the background service is *visibly* running "green". *Reasoning:* API keys rotate, rate limits hit, models go down. Without a permanent, glanceable health check (Tray/Status bar), the app feels fragile.
3.  **"Connecting" is the Most Critical Moment (Onboarding Hurdle).** Laypersons fail at CLI args, Env Vars, Config Files of target tools (Claude Code, Aider). *Reasoning:* The app must act as an *Injector*, not just documentation. An "Auto-Detect & Patch" flow for known tools decides adoption.
4.  **Radar & API Search are "Passive Value", Not Core Tabs.** Laypersons never open them; professionals use them weekly. *Reasoning:* Reserve prime screen real estate (Tabs) for daily control (Keys, Models, Connect). Move Radar to Side-Drawer or "More" Menu.
5.  **Events (Logs) = Debugging for Professionals, Reassurance for Laypersons.** *Reasoning:* Laypersons see "Running"; professionals filter for `ERROR 429 Key Rotation`. Unified event stream with severity filter covers both.

---

### 2) Concrete Rules (Implementable in Vanilla HTML/CSS/JS)

1.  **Global Mode Toggle (CSS Variable `--mode: simple | expert`).** Set on `<html>` tag. Hides entire columns (Ranking Details, Raw Key Editor, Routing Logic) via CSS (`display: none`). Persisted in `localStorage`. No JS Re-render needed.
2.  **"Start" Button as Hero Action in "Overview" Tab.** Checks: Daemon running? ≥1 valid Key? Target Tool detected? → Starts Routing & patches Config. Shows Toast: "Aider now uses `deepseek-chat` via Key #3". Disables on errors with Inline Help Link.
3.  **Daemon Status Indicator Fixed in Chrome (Header/Titlebar).** WebSocket/Server-Sent-Events from Background Service. States: `● Green` (Idle), `● Pulsing Blue` (Routing Active), `● Red` (Daemon Down/No Keys). Tooltip shows Detail: "3/12 Keys alive | Model: gemini-1.5-flash".
4.  **Tab "Connect" = Tool Detector + One-Click Patcher.** List of known tools (`<ul data-tool="aider">`). Button "Connect" executes `child_process.exec` (via IPC): Backup Config → Set `OPENAI_API_BASE=http://localhost:11434/v1` → Show Restore Button. No Terminal Knowledge Required.
5.  **Keys & Providers: "Health-First" Table.** Columns: Provider | Key (Masked `sk-***key`) | Status (Badge: ✅ OK / ⚠️ Rate Limited / ❌ Dead) | Last Check | Action (Re-check, Delete). Sorting: Status desc, then Latency asc. Professionals see Raw Input on Row Double-Click (ContentEditable).
6.  **Models Table: Routing Logic Visible & Editable.** Columns: Model | Provider | Capabilities (Code/Chat/Reasoning) | Score (0–100, Algo) | Enabled (Toggle). Drag-and-Drop to Prioritize. Laypersons see only "Recommended" (Top 3), Professionals see Full Matrix.
7.  **Events as Virtual Scroller (IntersectionObserver).** Max 500 DOM Nodes. Filter Chips Top: `[All] [Info] [Warning] [Error] [Rotation]`. Click Row → Slide-in Drawer with Raw JSON (Request/Response/Headers). Professionals copy cURL; Laypersons see "Key Switched".
8.  **Radar/API Search/Use Cases in "Lab" Drawer (Slide-in Right).** Not in Main Tab Bar. Access via Icon `🧪` in Header. Loads Content Lazy (Dynamic Import JS Module). Keeps Main App Lean & Fast.

---

### 3) What NOT To Do

*   **No Setup Wizard on First Launch.** Laypersons want to "Get Started" *immediately*. Professionals hate clicks. Replace with Empty States with Inline CTA: "No Keys Yet? Get Free Key Here".
*   **No Modal Dialogs for Core Flows (Add Keys, Connect Tool).** Modals Break Context. Use Inline Expansion (Accordion) or Side-Drawer.
*   **No Abstract Terms ("Provider", "Endpoint", "Routing Policy").** Language: "Provider" (Anbieter), "Server Address" (Server-Adresse), "Who Does What When" (Wer wann was macht).
*   **No Polling Without Backoff.** Daemon Status every 2s? Kills Battery/CPU. Use WebSocket/EventSource from Service. Fallback: Exponential Backoff (5s, 10s, 30s).
*   **Never Store Keys in Renderer Process LocalStorage.** Only in Encrypted Store of Background Service (OS Keychain/DPAPI). Renderer Receives Only Masking & Health via IPC.
*   **No Framework Dependencies (React, Vue, Tailwind).** Vanilla ES Modules + CSS Custom Properties + Web Components (for Tabs, Drawer, Table) Keep Bundle < 50kb, Start < 100ms, Maintenance 10 Years.
