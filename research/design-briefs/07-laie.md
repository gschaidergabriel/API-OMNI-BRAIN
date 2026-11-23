# 07-layperson (Critic: Layperson)
Model: nvidia/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning

1) Core Insights (3-5, with justification)
- Too many areas at once → Overwhelms laypersons; professionals seek specifics.
- Missing clear entry guidance → First-time users don't know where to start.
- Incomprehensible icons/terms → Unsure if not technically familiar.
- Quick self-configuration without instructions → Fear of breaking something.
- Inconsistent color and layout signals → Confusion about status and actions.

2) Concrete Rules for this Interface (HTML/CSS/JS without Frameworks)
- Homepage with a large, centered "Get Started" button that immediately opens the quick start view (only 2 fields: enter API Key, select Model).
- Navigation as horizontal tabs, maximum 3 visible simultaneously; others via dropdown to maintain overview.
- Icons with tooltips, plain language text, no jargon.
- Colors: Green for "ready," Red for error, subtle gray for inactive areas.
- Inline help (short explanations) on every input, appearing on focus.
- Automatic import of the last API key from browser storage, if present.
- One-click test button that immediately sends an example request and displays the result.
- Persistent "Help" bar at the bottom providing further instructions when needed, but not intrusive.

3) What NOT to do
- Dense menu bars offering all areas simultaneously.
- Using technical jargon in labels and tooltips.
- Quick, automatic configuration without confirmation that can overwrite data.
- Dark mode without notice due to missing contrast.
- Immediately displaying long log outputs instead of only upon request.
- Unclear error messages that do not explain how to proceed.
