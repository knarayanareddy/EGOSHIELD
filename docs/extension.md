# EgoShield Browser Extension Documentation

**Version:** 3.0.0

---

## Overview

The EgoShield browser extension provides real-time protection by:
- Analyzing web page content as you browse
- Highlighting detected manipulation tactics inline
- Showing warnings for high-severity pages
- Providing quick access to analysis history

---

## Installation

### Chrome / Chromium

1. Open `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/` folder from the EgoShield directory
5. The EgoShield shield icon will appear in your toolbar

### Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on..."
3. Select `extension/manifest.json`
4. The EgoShield icon will appear in your toolbar

### Safari

1. Open Safari > Preferences > Developer
2. Check "Allow unsigned extensions" (if needed)
3. Click "Load Extension..." in the Extensions pane
4. Select the `extension/` folder

---

## Components

### 1. Content Script (`js/content.js`)

Runs on every page load.

**Responsibilities:**
- Extract visible text content
- Send content to daemon for analysis
- Receive analysis results
- Inject inline highlights around detected phrases
- Show tooltip on hover

**Injection Points:**
```javascript
// Wraps detected phrases in annotation spans
<span class="ego-annotation" data-tactic="Fake Urgency" data-severity="0.84">
  detected phrase
  <span class="ego-tooltip">...</span>
</span>
```

### 2. Background Service (`js/background.js`)

Manages communication between content scripts and the daemon.

**Responsibilities:**
- Single message listener for all API calls
- Cache recent analysis results
- Handle extension icon badge updates
- Manage settings sync

**Message Types:**
```javascript
{
  action: 'analyzeContent',
  payload: { content, url, domain }
}

{
  action: 'getHistory',
  payload: { limit: 50 }
}

{
  action: 'getOverlayState',
  payload: { url }
}
```

### 3. Popup UI (`popup.html`, `js/popup.js`)

User interface shown when clicking the extension icon.

**Features:**
- Current page analysis summary
- Severity band indicator
- Detected tactic list
- Quick settings access
- Link to full dashboard

---

## User Interface

### Popup View

```
┌─────────────────────────────────┐
│  🛡️ EgoShield                   │
├─────────────────────────────────┤
│  Example.com                    │
│  ████████████░░░░ HIGH          │
│                                 │
│  3 tactics detected:            │
│  • Fake Urgency (0.84)          │
│  • Hidden Costs (0.71)          │
│  • Confirm Shaming (0.65)       │
├─────────────────────────────────┤
│  [View Full Report]             │
│  [Settings]                     │
└─────────────────────────────────┘
```

### Inline Highlights

Highlighted manipulation phrases appear as:
- **Yellow background** for medium severity
- **Orange background** for high severity
- **Red background** for critical severity

Hovering shows a tooltip with:
- Tactic name
- Severity score
- Brief explanation

### Notification Toast

When entering a high-severity page:

```
┌─────────────────────────────────────────┐
│ ⚠️ EgoShield: High Manipulation Risk    │
│                                         │
│ This page scored 0.73 (HIGH)            │
│ 5 manipulation tactics detected.        │
│                                         │
│         [View Details]                  │
└─────────────────────────────────────────┘
```

---

## Configuration

### Settings (via Popup)

| Setting | Default | Description |
|---------|---------|-------------|
| Overlay Enabled | true | Show inline highlights |
| Analysis on Load | true | Auto-analyze pages |
| Show Notifications | true | Toast notifications |

### Dashboard Settings

More advanced settings available in the web dashboard at `http://127.0.0.1:8766`:
- LLM threshold
- Detector timeouts
- Retention policy
- Plugin configuration

---

## Communication Flow

```
User visits page
       │
       ▼
Content Script extracts text
       │
       ▼
Background receives 'analyzeContent'
       │
       ▼
Background calls daemon API
       │
       ▼
Daemon analyzes content
       │
       ▼
Results returned to Background
       │
       ▼
Background sends to Content Script
       │
       ▼
Content Script injects highlights
```

---

## Permissions

The extension requests minimal permissions:

```json
{
  "permissions": [
    "activeTab",    // Analyze current tab only
    "storage"       // Store settings locally
  ],
  "host_permissions": []
}
```

**No permissions for:**
- Accessing all websites
- Reading cookies
- Managing tabs (beyond activeTab)
- Network requests

---

## Troubleshooting

### Extension not working

1. **Check daemon is running:**
   ```bash
   curl http://127.0.0.1:8765/health
   ```

2. **Reload extension:**
   - Go to `chrome://extensions/`
   - Click refresh on EgoShield

3. **Check for errors:**
   - Open DevTools (F12)
   - Check console for errors

### No highlights appearing

1. **Verify overlay is enabled:**
   - Click EgoShield icon
   - Check "Overlay Enabled" setting

2. **Check if page has manipulation:**
   - Not all pages have dark patterns
   - Lower severity pages won't show highlights

3. **Check daemon response:**
   - Open DevTools on the page
   - Look for console messages from EgoShield

### Popup shows "Daemon not connected"

1. **Start the daemon:**
   ```bash
   python -m egoshield.daemon.main
   ```

2. **Check port:**
   ```bash
   curl http://127.0.0.1:8765/health
   ```

3. **Restart browser:**

---

## Developer Tools

### Debug Content Script

1. Open DevTools on any page
2. Console shows EgoShield messages
3. Network tab shows API calls

### Debug Background Script

1. Go to `chrome://extensions/`
2. Find EgoShield
3. Click "service worker" link
4. DevTools opens for background context

### Extension Source Maps

For development, add source maps:
1. `chrome://extensions/`
2. EgoShield > Details
3. Enable "Developer mode" if not already
4. Extension reloads with source maps

---

## Updating

### Manual Update

1. Pull latest code: `git pull`
2. Reload extension in browser

### Version Check

The extension checks daemon version on startup. Version mismatch shows warning in popup.