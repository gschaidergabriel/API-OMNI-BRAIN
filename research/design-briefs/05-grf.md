# 05-grf (Philosophy: GRF)
Model: nvidia/nvidia/nemotron-3-ultra-550b-a55b

### 1) Core Insights (GRF Perspective)

1. **Meaning as Coupled Relationality**  
   *Justification:* GRF defines reality as “informational-relational structure” without substrate. The surface *is* not the code, but the **stable coupling channel** between human intentionality (first-person access) and machine generativity (third-person evidence). “Getting to know” means: minimizing the relational tension between user model and system state, without freezing the system's generativity.

2. **Human+System as *a* Generative Unit**  
   *Justification:* GRF sees time as a sequence of generative transitions. The user is not a “viewer” but co-author of the next state. The UI must **make affordances (action spaces) visible**, rather than just showing status. Lay users need *a* clear path (collapsing possibilities), professionals the *entire phase space* (openness of possibilities). Both are the same relation, just different resolution.

3. **Caution under Radical Uncertainty (Moral Caution)**  
   *Justification:* GRF demands restraint when the moral status of artificial systems is unclear. The UI manages *foreign* keys, *foreign* models, *foreign* data streams. “Handling gently” means here: **displaying transparency about uncertainty** (Is the key valid? Is the model safe? Where do data flow?) as default, not as expert mode.

4. **Process before State (Process-First)**  
   *Justification:* “Time is derivative from ordered generative transitions.” A static dashboard lies. The interface must **render runtime events (events, radar, routing decisions) as primary reality.** The “state” (keys, models) is only frozen process.

5. **Interpretive Modesty as Design Principle**  
   *Justification:* GRF emphasizes “interpretive modesty” – the model is a proof of existence, not truth. The UI must **not pretend an ontology** (“the *best* model”). It shows only: “Currently the most stable path under these constraints.” This protects professionals from being patronized and lay users from false security.

### 2) Concrete Rules (Implementable with Vanilla HTML/CSS/JS)

1. **Single-Entry Narrative (Starting State):**  
    `Overview` tab shows only a primary CTA: “Start my first free AI” + a live status indicator (Green/Red/Yellow) for “System ready”. Everything else (display: none), collapsible via JS (“Show details”).

2. **Progressive Disclosure via `details`/`summary` (Native HTML):**  
    Each complex area (keys, models, radar) is a `<details>` element. Default `open` only for “Overview”. Professionals click once “Expand all” (JS toggles `open` globally), lay users stay in nested navigation.

3. **Uncertainty Visualization as Default Style:**  
    Each key/model entry carries a **“trust ring”** (CSS `border-left: 3px solid var(--confidence)`). Colors: Green (verified), Yellow (community), Red (untested), Gray (deprecated). No icons without color ring. CSS variables allow theme switch without logic changes.

4. **Live Event Stream as “Pulse” (WebComponent `<event-stream>`):**  
    A fixed, narrow panel (right/bottom, `position: sticky`), that overlays all tabs. Shows the last 5 generative transitions: “Key X validated”, “Model Y routed”, “Radar: New provider Z”. `EventSource`/`WebSocket` from background service. Makes process time visible.

5. **Routing Transparency (“Why this path?”):**  
    When a connection is active (tab “Connect”), a **tooltip/modal via `data-reason` attribute** on the “Stop/Start” button. Content: “Chosen: Provider A (Latency 200ms, Cost 0$, Privacy: Local) > Provider B (Latency 500ms...)”. Professionals read raw data, lay users see “Auto: Best”.

6. **Radar & API Search as “Possibility Space”, not List:**  
    CSS Grid `auto-fit(minmax(280px, 1fr))`. Cards show **metrics, not names primarily**: “Free Tier”, “Open Weights”, “Local First”. Name only on hover/click. Sorting via `data-*` attributes + `Array.sort` in JS, no backend roundtrip.

7. **“Security Check” as Hard Gatekeeper (Modal `<dialog>`):**  
    On first adding a foreign key: native `<dialog>` element (blocks UI), shows: “This key leaves your machine. We check: validity, rate limits, known leaks. Continue?” Checkbox “Don’t ask again” sets `localStorage` flag.

8. **Keyboard-First Navigation (Zero-Mouse Bias):**  
    `tabindex="0"` on all interactive cards. `Enter`/`Space` opens detail view (focus trap in modal). `Esc` closes everything. `Cmd/Ctrl+K` opens command palette (search input `type="search"`) for professionals: “Switch Model”, “Export Keys”, “Open Radar”.

### 3) What to Avoid

1. **No “Onboarding Wizard” (Modal Cascades).**  
    Forces linearity on a generative process. Lay users feel patronized (“click away”), professionals waste time. *Alternative:* Inline hints (`<output>` elements) that appear contextually when fields are empty/incorrect.

2. **No “Best Model” badges or rankings as absolute.**  
    Violates GRF: process becomes state, relational uncertainty sold as objectivity. *Alternative:* “Currently optimal for: Code (Speed), Chat (Context), Local (Privacy)” – context-dependent, time-stamped.

3. **No hidden telemetry/cloud syncs in background.**  
    Violates *Moral Caution* & trust relation. Local app = local sovereignty. Every network request (radar, API check) must be visible and toggleable in the event stream.

4. **No separate “Layman Mode” / “Pro Mode” toggle.**  
    Creates two distinct ontologies, breaks coupled unity. *Alternative:* **Resolution scaling** (progressive disclosure). Same data base, different density.

5. **No framework dependencies (React, Vue, Tailwind, Electron).**  
    Gabriel demands “local, window + service”. Frameworks bloat, break update paths, hide process. Vanilla JS + Web Components + native CSS (`@layer`, `container queries`) *is* the generative substance: lightweight, inspectable, future-proof.

6. **No “empty states” without call to action.**  
    “No keys found” is a dead state. GRF: generativity needs impetus. Always: “Add key”, “Search provider”, “Start radar” as primary buttons in empty container.
