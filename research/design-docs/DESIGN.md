# DESIGN (Chef: nvidia/nvidia/nemotron-3-ultra-550b-a55b)

# Omnipool Design Document

## 1. Core Idea (One Sentence)
Omnipool is a local AI API testing and routing tool that immediately helps users connect free AI programs to working keys without overwhelming them or under-serving professionals.

## 2. Six Design Principles

1. **Immediate Actionability**: The first screen shows only one primary action with clear next steps for both beginners and experts.
2. **Progressive Disclosure**: Complex features are hidden until needed, revealed through expandable sections or mode toggles.
3. **Status as Narrative**: System state is communicated through a single human-readable status line, not technical logs.
4. **Empty States as Workflows**: When data is missing, show actionable buttons instead of empty tables or error messages.
5. **Cognitive Load Management**: Limit visible elements to 4 main areas initially, using visual grouping to create perceived chunks.
6. **Transparency with Simplicity**: Show routing decisions and system processes clearly, but present them in accessible language.

## 3. The First Five Seconds

### For Beginners:
- See a large green status indicator: "🟢 Ready - 3 free AI keys found"
- See one prominent button: "Connect Claude Code Now" 
- See one secondary button: "I have my own keys"
- Everything else is hidden or collapsed

### For Professionals:
- Same status indicator with additional details on hover/click
- Access to full tab bar via "Show All Features" 
- Keyboard shortcut Cmd/Ctrl+K for command palette
- Advanced settings immediately accessible

## 4. Guided vs. Professional Mode

The interface adapts based on user expertise without forcing either path:

**Guided Mode (Default):**
- Large, friendly buttons with plain language
- Step-by-step wizards for complex tasks
- Pre-filled defaults and smart suggestions
- Visual feedback at every step

**Professional Mode:**
- Direct access to raw configuration
- Detailed metrics and technical information
- Advanced routing controls and priority settings
- Keyboard shortcuts and batch operations

Users can switch modes at any time, with their preference saved in localStorage.

## 5. Tone of Text

All UI text uses plain, conversational English:
- Action buttons use verbs: "Connect", "Scan", "Test", "Save"
- Status messages are complete sentences: "Connected to Kimi K2 via Moonshot"
- Error messages explain solutions: "No keys found. [Scan for free keys] or [Add manually]"
- Technical terms are explained inline: "Provider (AI service)" with tooltips
- No jargon, no marketing language, no passive voice

## 6. Honesty Rules

1. Never claim a model is "the best" - show why it was selected for current context
2. Always show when keys are rate-limited or failing
3. Display actual costs and limitations, not promises
4. Show uncertainty: "Likely working" vs "Confirmed working"
5. Never hide failures or errors - make them visible and actionable
6. Be clear about what's local vs. what requires internet
7. Show when processes are running, not just results

---

```json
[
  {
    "id": "T1",
    "titel": "Create Single Primary CTA in Overview Tab",
    "datei": "ui.html",
    "beschreibung": "Replace current Overview tab content with one large button 'Connect Free AI Now' centered with secondary 'I have my own keys' button below. Hide all other tabs initially.",
    "abnahme": "Opening app shows only status line and one big button. Other tabs are hidden with CSS display:none."
  },
  {
    "id": "T2",
    "titel": "Implement Sticky Header Status Bar",
    "datei": "ui.css",
    "beschreibung": "Add 40px fixed header at top showing connection status circle, active model name, and cost limit. Include dropdown with quick model switch options.",
    "abnahme": "Status bar visible on all tabs showing green/red indicator, model name, and cost. Dropdown accessible via click."
  },
  {
    "id": "T3",
    "titel": "Add Smart Defaults Auto-Scan",
    "datei": "ui.js",
    "beschreibung": "On app load, automatically check for working keys or public endpoints. If found, show 'Ready' status. If not, show 'Scan for free keys' button.",
    "abnahme": "App either shows 'Ready' with working key or prompts to scan. No manual setup required for first use."
  },
  {
    "id": "T4",
    "titel": "Create Empty State Action Buttons",
    "datei": "texte.json",
    "beschreibung": "For Keys tab when empty: show 'No keys found. [Scan for free keys] [Add manually] [Load examples]' buttons. Same pattern for other empty states.",
    "abnahme": "Empty tabs show actionable buttons, not just 'No data' messages."
  },
  {
    "id": "T5",
    "titel": "Implement Mode Toggle (Simple/Expert)",
    "datei": "ui.js",
    "beschreibung": "Add toggle button in header to switch between simple (4 main tabs) and expert (all 8 tabs) mode. Save preference in localStorage.",
    "abnahme": "Toggle switches between reduced and full tab sets. Preference persists across reloads."
  },
  {
    "id": "T6",
    "titel": "Add Human-Readable Status Line",
    "datei": "ui.html",
    "beschreibung": "Add prominent status message in header: '🟢 Connected to Kimi K2 via Moonshot - 12 models available' replacing technical logs.",
    "abnahme": "Single status line replaces detailed logs. Shows connection, model, and availability in plain language."
  }
]
```
