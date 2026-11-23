# 08-profi (Critic: Pro)
Model: nvidia/poolside/laguna-xs-2.1

## 1) Core Insights

- **Progressive Disclosure**: Pros want to get to work immediately, beginners need orientation. First visibility of the most important actions (Keys, Models, Connection) without menu search.
- **Keyboard-First**: Power users expect Ctrl+K for search, tab navigation, copy-paste directly from the UI. Mouse clicks are annoying.
- **Data-Density without Overload**: Tables with all relevant metadata (Provider, Limits, Status) in compact form, but not in one huge blob.
- **Zero-Tour-Approach**: No welcome emails, but context help via ? symbol or Cmd+Shift+H for shortcut cheat sheet.
- **Direct Manipulation**: Drag & Drop for Key Import, Inline-Edit for Model Ratings, no modal windows for everyday tasks.

## 2) Concrete Rules for This Interface

```html
<!-- Keyboard Search omnipresent -->
<input type="search" id="global-search" placeholder="Search: Key, Model, Provider..." 
       style="position:fixed;top:12px;right:12px;z-index:1000;width:280px;">

<!-- Key-Grid with Inline Status -->
<div class="key-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;">
  <div class="key-card" style="border:1px solid #ddd;border-radius:8px;padding:12px;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <strong>Anthropic</strong>
      <span class="status" style="background:#4CAF50;color:white;padding:2px 8px;border-radius:12px;font-size:12px;">Active</span>
    </div>
    <small>Limit: 100k/month | Remaining: 84.2k</small>
    <button onclick="copyKey('sk-ant-...')" style="background:#f0f0f0;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;">Copy</button>
  </div>
</div>

<!-- Model Ranking via Drag & Drop -->
<ul id="model-ranking" style="list-style:none;padding:0;margin:0;">
  <li draggable="true" style="padding:8px;background:#f9f9f9;margin-bottom:4px;">Claude 3 Opus <span style="float:right">[↑↓]</span></li>
</ul>

<!-- Events as Timeline -->
<div class="event-log" style="max-height:200px;overflow-y:auto;font-family:monospace;font-size:12px;">
  <div>14:23 Key checked: anthropic_key_01 ✅</div>
  <div>14:22 New API discovered: huggingface-llama-3 ✨</div>
</div>
```

```css
/* Dense, but readable Styles */
.key-card small { color:#666; }
[draggable] { cursor:move; }
[draggable]:hover { background:#e9e9e9; }
```

```js
// Global Shortcut Handler
document.addEventListener('keydown', e => {
  if (e.key === '/' && e.ctrlKey) {
    e.preventDefault();
    document.getElementById('global-search').focus();
  }
  if (e.key === 'Escape') {
    document.activeElement.blur();
  }
});

// Key-Copy without Confirmation
function copyKey(key) {
  navigator.clipboard.writeText(key);
  // Optional: Mini Toast bottom right
}
```

## 3) What You Should NOT Do

- **No Onboarding Tours**: Beginners understand the dashboard immediately, pros don't want to be forced.
- **No Modals for Standard Workflows**: Add Key = Inline Form, not Popup.
- **No Animations on Loading**: Load time = direct transition, not spinner nonsense.
- **No Tooltips Instead of Labels**: If something is important, it should be readable without hover.
- **No "Welcome" Screens**: Every visitor should see their goals immediately.
- **No Dark-Mode Toggle**: Default is dark, light only available as override option.
