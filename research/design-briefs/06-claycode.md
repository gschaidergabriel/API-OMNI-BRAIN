# 06-claycode (Philosopher: ClayCode)
Model: nvidia/mistralai/mistral-large-4-1t-a52b

### 1) Core Insights (with Evidence)

1. **Orientation over Dashboard** – Laypeople need *one* next step, pros need *all* levers. Evidence: ClayCode shapes in "small evidenced steps"; a start screen showing everything shapes nothing, it fossilizes.
2. **Evidence as UI Element** – Every leaderboard number (latency, cost, success) must link via click to its measurement run (timestamp, raw data, method). Evidence: "Evidence is authority," not the number itself.
3. **Contradiction Remains Visible** – If Key A is #1 today, #3 tomorrow, the UI shows the delta, does not hide it. Evidence: "Patterns are not truth, contradiction remains visible."
4. **Malleable Tone = Progressive Disclosure** – Tabs are not fixed walls, but layers. "Connect" is a button for laypeople ("Make it run"), for pros a panel (routing logic, fallback chain). Evidence: "Structure is malleable tone."
5. **Human–System as Epistemic Unit** – The background service delivers *suggestions* (Radar: "New Key found"), the human decides *finally* ("Adopt"). No automatisms without confirmation. Evidence: "Human and system form a coupled epistemic unit."

---

### 2) Concrete Rules (implementable in vanilla HTML/CSS/JS)

1. **Single-Entry-Start**: `index.html` renders *only* three cards: "Get Started" (Auto-Setup), "My Keys", "Radar". Everything else loadable via `details` element or hash route (`#models`, `#routing`).
2. **Evidence-Tooltip Mandatory**: Every metric cell (`<td data-evidence="run-123">`) has a `title` attribute *and* a `click` listener opening a `<dialog>` with raw JSON, timestamp, script hash.
3. **Delta Column Standard**: Tables (Models, Keys) *always* have column "Δ 24h" (arrow + value). CSS: `.delta-up{color:#c00}.delta-down{color:#0a0}` – no hiding.
4. **Mode Switch (Lay/Pro)**: A `toggle` in header (`<button role="switch" aria-pressed="false">`) flips `body[data-mode="pro"]`. CSS shows/hides columns, panels, advanced settings *without* JS re-render.
5. **Radar as Feed, not List**: `#radar` is an `<ol>` with `datetime` attributes. New entry = `prepend` + `animation: slide-in 0.3s`. Filter (`input[type=search]`) runs client-side via `dataset.tags`.
6. **Connect = Wizard + Raw Editor**: Step 1: `<form>` with `select` (Program) + "Auto" Button. Step 2 (Pro): `textarea` for generated JSON config, `onchange` validates via `JSON.parse`, saves to `localStorage` + sends to Background Service via `navigator.sendBeacon`.
7. **Events = Append-Only Log**: `#events` is `<ul>` with `data-level="info|warn|error"`. CSS filters via `:has([data-level="error"]:target)`. No "Delete", only "Hide" (Checkbox "Errors only").
8. **Offline-First Cache**: All Keys, Models, Radar entries in `indexedDB` (`omnipool-cache`). UI renders *immediately* from cache, fetches delta in background (`fetch` + `If-None-Match`). "Done means verified" → Sync status icon (green/yellow/red) in header.

---

### 3) What NOT to do

- **No "Dashboard" Default** loading 9 tabs simultaneously – cognitive load ≠ malleable tone.
- **No Metric without Source Link** – "Trust me" is not authority, evidence is.
- **No Auto-Switch without Confirmation** – Routing change silently = disempowerment of the epistemic unit.
- **No Modals breaking History** – Use `<dialog>` + Hash Routes so "Back" works.
- **No Framework Dependency** – ClayCode shapes *tone*, no foreign scaffolds; vanilla secures "done = verified".
- **No "Hiding" of Failures** – Keys that lock stay visibly red; hiding = lie.
- **No Onboarding Tour that isn't skippable** – Pros are not laypeople, paternalism breaks the coupling.
