# 09-access (Specialist: Motion & Accessibility)
Model: nvidia/nvidia/nemotron-3.5-lightning-30b-a3b

**1) Key Findings (3-5 with Rationale)**

- **Hierarchical Disclosure:** Novices may use the surface immediately without having to think about API keys or models. Professionals find leaderboards and routing options only when needed (e.g., clicking "Advanced"). Gabriel demands "gentle approach," not "initial orientation through a wall of options."
- **Keyboard-First as Standard:** All functions must be operable purely via Tab/Enter/Space. For professionals, this accelerates work; for screen reader users, it is essential. Focus patterns must be logical and visible.
- **`prefers-reduced-motion` as a Design Principle:** All micro-interactions (hover, loading spinners, transitions) must be disabled or reduced to instant-state when the system setting is active. Never use motion to convey information.
- **Contextual States (Load/Error/Empty):** Empty states must not remain blank. They offer an immediate action point (e.g., "No keys present. Add API provider"). Errors must be presented factually, briefly, and with a repair option, not depicted as a system crash.
- **Contrast & Focus Visibility:** Minimum WCAG AA Contrast (4.5:1). Focus indicators must not be removed without replacement. Color alone must never convey status (Error = Red + Icon/Text).

**2) Concrete Rules for this Interface (5-8, implementable in HTML/CSS/JS)**

1.  **Use `:focus-visible`, never `outline: none` without replacement.** Replace standard outline with a high-contrast, color-distinct ring design (e.g., `box-shadow: 0 0 0 3px #0066ff;`) that remains visible in dark theme as well.
2.  **Globally embed Reduced-Motion Media Query.** `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01s !important; transition-duration: 0.01s !important; } }`. All spinners and hover animations disappear or become instant color changes.
3.  **`aria-live="polite"` for loading, error, and empty states.** Example: `<div aria-live="polite" role="status">Loading AI models…</div>`. The text is announced to screen readers without stealing focus or opening modal windows.
4.  **Never use colors alone for status.** Error = `#dc2626` (red) *and* `icon="⚠"` + Text "API Key invalid". Success = `#059669` (green) + "Successfully connected".
5.  **Fill empty state with primary CTA.** HTML: `<p>No API Keys yet. <button class="btn-primary">Test first provider</button></p>`. The button is keyboard operable (`tabindex="0"` or natural focus) and leads directly to key setup.
6.  **Keyboard Shortcuts as Progressive Enhancement.** `Cmd/Ctrl + K` focuses global search. Combinations are explained in a non-intrusive tooltip popover that closes via `Esc` and uses animations disableable via `prefers-reduced-motion`.
7.  **Keep errors inline and recoverable.** Instead of a pop-up modal: `<small class="error">API Key invalid. <a href="#keys">Test here</a></small>`. The link jumps directly to the affected field, focus is set there.
8.  **Focus Management for Modals.** When a modal opens (e.g., key entry), focus must be set immediately to the first interactive element (`modal.focus()`) and return to the triggering element upon closing (`Esc`).

**3) What NOT to do**

- Do not auto-focus or select on page load unless the user is already interacting.
- Do not use `outline: none` globally; focus indicators must remain visible or be replaced by high-contrast design.
- Do not use animations to "announce" loading times or errors. Use text and `aria-live` instead.
- Do not use colorblind-unsafe color schemes (e.g., Green/Red alone for status).
- Do not list all API keys, models, and routing options on the dashboard. Gabe wants to "not be overwhelmed."
- Do not leave empty states blank or only with "No data" without an action option.
- Do not replace screen reader text with placeholders; `label` and `aria-describedby` are mandatory.
