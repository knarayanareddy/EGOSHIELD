/**
 * EgoShield Background Service Worker
 * Handles communication between content script and daemon
 */

// Configuration
const CONFIG = {
  DAEMON_URL: 'http://127.0.0.1:8765',
  API_VERSION: 'v2',
  TIMEOUT_MS: 5000,
  MAX_RETRIES: 2,
  DAEMON_CHECK_INTERVAL: 60000,
};

// State management
const state = {
  daemonHealth: 'unknown',
  lastDaemonCheck: 0,
  trustedDomains: [],
  suppressedTactics: [],
  retryCount: {},
};

// Initialize on install
chrome.runtime.onInstalled.addListener(async () => {
  console.log('EgoShield extension installed');
  await initializeState();
  await checkDaemonHealth();
});

// Start daemon health check on startup
chrome.runtime.onStartup.addListener(async () => {
  console.log('EgoShield extension started');
  await initializeState();
  await checkDaemonHealth();
});

// Periodic daemon health check
chrome.alarms.create('daemonHealthCheck', { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'daemonHealthCheck') {
    checkDaemonHealth();
  }
});

/**
 * Initialize extension state from storage
 */
async function initializeState() {
  const result = await chrome.storage.local.get([
    'trustedDomains',
    'suppressedTactics',
    'daemonHealth',
  ]);

  state.trustedDomains = result.trustedDomains || [];
  state.suppressedTactics = result.suppressedTactics || [];
  state.daemonHealth = result.daemonHealth || 'unknown';

  // Refresh rules from daemon
  await refreshRules();
}

/**
 * Refresh rules from daemon
 */
async function refreshRules() {
  try {
    const response = await sendToDaemon('/api/v2/rules', 'GET');
    if (response && response.trusted_domains) {
      state.trustedDomains = response.trusted_domains;
      state.suppressedTactics = response.suppressed_tactics;
      await chrome.storage.local.set({
        trustedDomains: state.trustedDomains,
        suppressedTactics: state.suppressedTactics,
      });
    }
  } catch (error) {
    console.warn('Failed to refresh rules:', error);
  }
}

/**
 * Check daemon health status
 */
async function checkDaemonHealth() {
  try {
    const response = await sendToDaemon('/health', 'GET', null, 3000);
    if (response) {
      state.daemonHealth = response.status;
      state.lastDaemonCheck = Date.now();
      await chrome.storage.local.set({ daemonHealth: response.status });
    }
  } catch (error) {
    state.daemonHealth = 'unavailable';
    await chrome.storage.local.set({ daemonHealth: 'unavailable' });
  }
}

/**
 * Send request to daemon with timeout and retries
 */
async function sendToDaemon(endpoint, method = 'GET', body = null, timeout = CONFIG.TIMEOUT_MS) {
  const url = `${CONFIG.DAEMON_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-EgoShield-Client': `extension/${chrome.runtime.getManifest().version}`,
      },
      signal: controller.signal,
    };

    if (body && method !== 'GET') {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

/**
 * Hash URL using SHA-256
 */
async function hashUrl(url) {
  const encoder = new TextEncoder();
  const data = encoder.encode(url);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Get current extension state
 */
async function getState() {
  return {
    daemonHealth: state.daemonHealth,
    trustedDomains: state.trustedDomains,
    suppressedTactics: state.suppressedTactics,
    version: chrome.runtime.getManifest().version,
  };
}

/**
 * Toggle trust status for a domain
 */
async function toggleDomainTrust(domain) {
  const index = state.trustedDomains.indexOf(domain);

  if (index >= 0) {
    state.trustedDomains.splice(index, 1);
  } else {
    state.trustedDomains.push(domain);
    try {
      await sendToDaemon('/api/v2/rules', 'POST', {
        rule_type: 'trusted_domain',
        value: domain,
      });
    } catch (error) {
      console.error('Failed to add rule to daemon:', error);
    }
  }

  await chrome.storage.local.set({ trustedDomains: state.trustedDomains });
  return { trustedDomains: state.trustedDomains };
}

/**
 * Toggle overlay visibility
 */
async function toggleOverlay(enabled) {
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    try {
      await chrome.tabs.sendMessage(tab.id, { action: 'toggleOverlay', enabled });
    } catch (e) {
      // Tab might not have content script
    }
  }
  await chrome.storage.local.set({ overlayEnabled: enabled });
}

// ============================================================
// UNIFIED MESSAGE LISTENER
// ============================================================

/**
 * Handle ALL messages from content scripts and popup
 * Single listener to avoid conflicts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Wrap in async handler to support async responses
  (async () => {
    const { action, data } = message;

    try {
      switch (action) {
        case 'analyze':
          sendResponse(await handleAnalyze(data, sender));
          break;

        case 'getState':
          sendResponse(await getState());
          break;

        case 'toggleDomainTrust':
          sendResponse(await toggleDomainTrust(data.domain));
          break;

        case 'checkHealth':
          sendResponse(await checkDaemonHealth());
          break;

        case 'toggleOverlay':
          sendResponse(await toggleOverlay(data.enabled));
          break;

        case 'getRules':
          sendResponse(await refreshRules());
          break;

        case 'getOverlayState':
          // This is the handler for getOverlayState - single location
          const result = await chrome.storage.local.get(['overlayEnabled']);
          sendResponse({ enabled: result.overlayEnabled !== false });
          break;

        case 'reAnalyze':
          // Re-analyze the current tab
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (tab) {
            await chrome.tabs.sendMessage(tab.id, { action: 'reAnalyze' });
          }
          sendResponse({ success: true });
          break;

        default:
          // Unknown action - return error but don't crash
          console.warn(`Unknown message action: ${action}`);
          sendResponse({ error: `Unknown action: ${action}` });
      }
    } catch (error) {
      console.error('Message handler error:', error);
      sendResponse({ error: error.message });
    }
  })();
  
  // Return true to indicate we'll respond asynchronously
  return true;
});

/**
 * Handle analyze request from content script
 */
async function handleAnalyze(data, sender) {
  const { content, url, domain, contentType } = data;

  // Check if domain is trusted
  if (state.trustedDomains.includes(domain)) {
    return {
      analysis_id: 'trusted',
      composite_score: 0,
      severity_band: 'LOW',
      partial_result: false,
      arbiter_tier: null,
      tactics: [],
      trusted: true,
    };
  }

  // Check daemon health
  if (state.daemonHealth === 'unavailable') {
    throw new Error('EgoShield daemon is unavailable');
  }

  // Hash URL (never send raw URL)
  const urlHash = await hashUrl(url);

  // Send analysis request
  try {
    const result = await sendToDaemon('/api/v2/analyze', 'POST', {
      url_hash: urlHash,
      domain: domain,
      content_type: contentType || 'page',
      content: content,
      truncated: content.length >= 50000,
      client_timestamp: new Date().toISOString(),
    });

    return result;
  } catch (error) {
    console.error('Analysis failed:', error);
    throw error;
  }
}