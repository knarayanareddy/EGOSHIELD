/**
 * EgoShield Popup Script
 * Manages the extension popup UI
 */

document.addEventListener('DOMContentLoaded', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = new URL(tab.url);
  const domain = url.hostname;

  const manifest = chrome.runtime.getManifest();
  document.getElementById('version').textContent = `v${manifest.version}`;
  document.getElementById('currentDomain').innerHTML = `Current page: <strong>${domain}</strong>`;

  await loadState(domain);
  setupEventListeners(domain);
});

async function loadState(domain) {
  try {
    const state = await chrome.runtime.sendMessage({ action: 'getState' });
    updateDaemonStatus(state.daemonHealth);

    const trustToggle = document.getElementById('trustToggle');
    trustToggle.checked = state.trustedDomains.includes(domain);

    const overlayToggle = document.getElementById('overlayToggle');
    const result = await chrome.storage.local.get(['overlayEnabled']);
    overlayToggle.checked = result.overlayEnabled !== false;

  } catch (error) {
    console.error('Failed to load state:', error);
    updateDaemonStatus('unavailable');
  }
}

function updateDaemonStatus(status) {
  const statusDot = document.querySelector('.status-dot');
  const statusText = document.querySelector('.status-text');

  statusDot.className = 'status-dot ' + status;

  const statusMessages = {
    healthy: 'Daemon healthy',
    degraded: 'Daemon degraded',
    unavailable: 'Daemon unavailable',
    unknown: 'Checking...',
  };

  statusText.textContent = statusMessages[status] || 'Unknown';
}

function setupEventListeners(domain) {
  document.getElementById('analyzeBtn').addEventListener('click', async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      await chrome.tabs.sendMessage(tab.id, { action: 'reAnalyze' });
      showNotification('Page re-analyzed');
    } catch (error) {
      showNotification('Failed to analyze page', true);
    }
  });

  document.getElementById('dashboardBtn').addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://127.0.0.1:8766' });
  });

  document.getElementById('overlayToggle').addEventListener('change', async (e) => {
    await chrome.runtime.sendMessage({
      action: 'toggleOverlay',
      data: { enabled: e.target.checked },
    });
  });

  document.getElementById('trustToggle').addEventListener('change', async (e) => {
    try {
      await chrome.runtime.sendMessage({
        action: 'toggleDomainTrust',
        data: { domain },
      });
      showNotification(e.target.checked ? 'Domain trusted' : 'Domain untrusted');
    } catch (error) {
      showNotification('Failed to update trust status', true);
    }
  });

  document.getElementById('settingsLink').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.tabs.create({ url: 'http://127.0.0.1:8766/settings' });
  });

  document.getElementById('helpLink').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.tabs.create({ url: 'http://127.0.0.1:8766/help' });
  });
}

function showNotification(message, isError = false) {
  const existing = document.querySelector('.notification');
  if (existing) existing.remove();

  const notification = document.createElement('div');
  notification.className = 'notification' + (isError ? ' error' : '');
  notification.textContent = message;

  notification.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: ${isError ? '#f44336' : '#4CAF50'};
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 12px;
    z-index: 10000;
    animation: slideUp 0.3s ease;
  `;

  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideUp {
      from { opacity: 0; transform: translateX(-50%) translateY(10px); }
      to { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
  `;
  document.head.appendChild(style);

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}