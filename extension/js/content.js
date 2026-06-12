/**
 * EgoShield Content Script
 * Captures page content and renders overlay annotations
 */

const CONFIG = {
  MAX_CONTENT_SIZE: 50000,
  OVERLAY_CLASS_PREFIX: 'ego-',
  MIN_TEXT_LENGTH: 50,
};

let currentAnalysis = null;
let overlayVisible = true;
let overlayElements = [];
let annotationWrappers = []; // Track wrappers to remove later

async function init() {
  const result = await chrome.storage.local.get(['overlayEnabled']);
  overlayVisible = result.overlayEnabled !== false;

  if (document.readyState === 'complete') {
    await runAnalysis();
  } else {
    window.addEventListener('load', runAnalysis);
  }

  // Single unified message listener
  chrome.runtime.onMessage.addListener(handleMessage);
}

function handleMessage(message, sender, sendResponse) {
  switch (message.action) {
    case 'toggleOverlay':
      overlayVisible = message.enabled;
      if (!overlayVisible) clearOverlays();
      sendResponse({ success: true });
      break;
    case 'reAnalyze':
      clearOverlays();
      runAnalysis();
      sendResponse({ success: true });
      break;
    case 'getOverlayState':
      sendResponse({ enabled: overlayVisible });
      break;
    default:
      sendResponse({ error: 'Unknown action' });
  }
  return true;
}

function capturePageContent() {
  const content = {
    text: '',
    title: document.title,
    url: window.location.href,
    domain: window.location.hostname,
  };

  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: function (node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;

        const style = window.getComputedStyle(parent);
        if (style.display === 'none' || style.visibility === 'hidden') {
          return NodeFilter.FILTER_REJECT;
        }

        const tagName = parent.tagName.toLowerCase();
        if (['input', 'textarea', 'select', 'button'].includes(tagName)) {
          return NodeFilter.FILTER_REJECT;
        }

        if (parent.type === 'password' || parent.type === 'hidden') {
          return NodeFilter.FILTER_REJECT;
        }

        const autocomplete = parent.getAttribute('autocomplete');
        if (autocomplete && /password|secret|pin|card|cvc/i.test(autocomplete)) {
          return NodeFilter.FILTER_REJECT;
        }

        const text = node.textContent.trim();
        if (!text) return NodeFilter.FILTER_REJECT;

        return NodeFilter.FILTER_ACCEPT;
      },
    }
  );

  const textParts = [];
  let node;
  while ((node = walker.nextNode())) {
    textParts.push(node.textContent.trim());
  }

  content.text = textParts.join(' ').substring(0, CONFIG.MAX_CONTENT_SIZE);
  return content;
}

async function runAnalysis() {
  if (!overlayVisible) return;

  const captured = capturePageContent();

  if (captured.text.length < CONFIG.MIN_TEXT_LENGTH) {
    console.log('EgoShield: Page content too short for analysis');
    return;
  }

  try {
    const response = await chrome.runtime.sendMessage({
      action: 'analyze',
      data: {
        content: captured.text,
        url: captured.url,
        domain: captured.domain,
        contentType: 'page',
      },
    });

    if (response.error) {
      console.warn('EgoShield: Analysis failed:', response.error);
      return;
    }

    if (response.trusted) {
      console.log('EgoShield: Domain is trusted, skipping analysis');
      return;
    }

    currentAnalysis = response;
    renderOverlays(response);

  } catch (error) {
    console.error('EgoShield: Error running analysis:', error);
  }
}

function renderOverlays(analysis) {
  if (!analysis.tactics || analysis.tactics.length === 0) return;

  // Create overlay container for badge and tooltips
  let container = document.querySelector(`.${CONFIG.OVERLAY_CLASS_PREFIX}container`);
  if (!container) {
    container = document.createElement('div');
    container.className = `${CONFIG.OVERLAY_CLASS_PREFIX}container`;
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', 'EgoShield manipulation pattern annotations');
    document.body.appendChild(container);
  }

  // Create summary badge
  const badge = createSummaryBadge(analysis);
  container.appendChild(badge);

  // Annotate evidence phrases inline in the page
  for (const tactic of analysis.tactics) {
    for (const phrase of tactic.evidence_phrases) {
      wrapTextWithAnnotations(phrase, tactic);
    }
  }

  overlayElements.push(container);
}

/**
 * Wrap text elements containing evidence phrases with annotation spans
 */
function wrapTextWithAnnotations(phrase, tactic) {
  const normalizedPhrase = phrase.toLowerCase().trim();
  if (normalizedPhrase.length < 3) return;

  // Create a TreeWalker to find text nodes
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: function (node) {
        // Skip nodes inside our own annotations or in script/style
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        
        const tagName = parent.tagName.toLowerCase();
        if (tagName === 'script' || tagName === 'style' || tagName === 'noscript') {
          return NodeFilter.FILTER_REJECT;
        }
        
        // Skip if already annotated
        if (parent.classList.contains(`${CONFIG.OVERLAY_CLASS_PREFIX}annotation`) ||
            parent.classList.contains(`${CONFIG.OVERLAY_CLASS_PREFIX}tooltip`)) {
          return NodeFilter.FILTER_REJECT;
        }

        const text = node.textContent.toLowerCase();
        if (text.includes(normalizedPhrase.substring(0, 30))) {
          return NodeFilter.FILTER_ACCEPT;
        }
        
        return NodeFilter.FILTER_REJECT;
      },
    }
  );

  const nodesToProcess = [];
  let node;
  while ((node = walker.nextNode())) {
    nodesToProcess.push(node);
  }

  // Process each text node and wrap matching text
  for (const textNode of nodesToProcess) {
    wrapTextNodeWithPhrase(textNode, phrase, tactic);
  }
}

/**
 * Wrap a text node's content with annotation spans for matching phrases
 */
function wrapTextNodeWithPhrase(textNode, phrase, tactic) {
  const text = textNode.textContent;
  const normalizedPhrase = phrase.toLowerCase();
  
  // Find the position of the phrase in the text
  const pos = text.toLowerCase().indexOf(normalizedPhrase);
  if (pos === -1) return;
  
  // Get the parent element
  const parent = textNode.parentElement;
  if (!parent || parent.classList.contains(`${CONFIG.OVERLAY_CLASS_PREFIX}annotation`)) return;
  
  // Create the annotation span
  const annotationSpan = createAnnotationSpan(phrase, tactic);
  
  // Split the text node and insert the annotation
  try {
    const before = document.createTextNode(text.substring(0, pos));
    const matched = document.createTextNode(text.substring(pos, pos + phrase.length));
    const after = document.createTextNode(text.substring(pos + phrase.length));
    
    annotationSpan.appendChild(matched);
    
    // Replace text node with: before + annotation + after
    parent.insertBefore(before, textNode);
    parent.insertBefore(annotationSpan, textNode);
    parent.insertBefore(after, textNode);
    parent.removeChild(textNode);
    
    // Track for cleanup
    annotationWrappers.push(annotationSpan);
  } catch (e) {
    console.error('EgoShield: Failed to wrap text:', e);
  }
}

/**
 * Create an annotation span element
 */
function createAnnotationSpan(phrase, tactic) {
  const annotation = document.createElement('span');
  annotation.className = `${CONFIG.OVERLAY_CLASS_PREFIX}annotation`;
  annotation.setAttribute('data-tactic', tactic.tactic_name);
  annotation.setAttribute('data-detector', tactic.detector_name);
  annotation.setAttribute('tabindex', '0');
  annotation.setAttribute('role', 'button');
  annotation.setAttribute('aria-label', `${tactic.tactic_name}: ${phrase}`);

  const severityColors = {
    LOW: '#4CAF50',
    MEDIUM: '#FFC107',
    HIGH: '#FF9800',
    CRITICAL: '#f44336',
  };

  const baseColor = severityColors[tactic.severity >= 0.7 ? 'CRITICAL' :
    tactic.severity >= 0.5 ? 'HIGH' :
    tactic.severity >= 0.3 ? 'MEDIUM' : 'LOW'];

  annotation.style.cssText = `
    background-color: ${baseColor}22;
    border-bottom: 2px solid ${baseColor};
    cursor: help;
    position: relative;
    text-decoration: none;
  `;

  // Create tooltip
  const tooltip = document.createElement('div');
  tooltip.className = `${CONFIG.OVERLAY_CLASS_PREFIX}tooltip`;
  tooltip.innerHTML = `
    <div class="${CONFIG.OVERLAY_CLASS_PREFIX}tooltip-header">
      <strong>${escapeHtml(tactic.tactic_name)}</strong>
      <span class="${CONFIG.OVERLAY_CLASS_PREFIX}tooltip-severity">${(tactic.severity * 100).toFixed(0)}%</span>
    </div>
    <div class="${CONFIG.OVERLAY_CLASS_PREFIX}tooltip-detector">${escapeHtml(tactic.detector_name.replace('_', ' '))}</div>
    <div class="${CONFIG.OVERLAY_CLASS_PREFIX}tooltip-evidence">"${escapeHtml(phrase.substring(0, 100))}${phrase.length > 100 ? '...' : ''}"</div>
    ${tactic.explanation ? `<div class="${CONFIG.OVERLAY_CLASS_PREFIX}tooltip-explanation">${escapeHtml(tactic.explanation)}</div>` : ''}
  `;

  annotation.appendChild(tooltip);

  // Show tooltip on hover/focus
  annotation.addEventListener('mouseenter', () => showTooltip(tooltip));
  annotation.addEventListener('mouseleave', () => hideTooltip(tooltip));
  annotation.addEventListener('focus', () => showTooltip(tooltip));
  annotation.addEventListener('blur', () => hideTooltip(tooltip));

  return annotation;
}

/**
 * Create summary badge showing overall score
 */
function createSummaryBadge(analysis) {
  const badge = document.createElement('div');
  badge.className = `${CONFIG.OVERLAY_CLASS_PREFIX}badge ${CONFIG.OVERLAY_CLASS_PREFIX}badge-${analysis.severity_band.toLowerCase()}`;

  const severityColors = {
    LOW: '#4CAF50',
    MEDIUM: '#FFC107',
    HIGH: '#FF9800',
    CRITICAL: '#f44336',
  };

  const color = severityColors[analysis.severity_band] || '#4CAF50';

  badge.innerHTML = `
    <div class="${CONFIG.OVERLAY_CLASS_PREFIX}badge-icon" style="background-color: ${color}">
      <svg viewBox="0 0 24 24" width="20" height="20">
        <path fill="white" d="M12 2L1 21h22L12 2zm0 3.99L19.53 19H4.47L12 5.99zM11 10v4h2v-4h-2zm0 6v2h2v-2h-2z"/>
      </svg>
    </div>
    <div class="${CONFIG.OVERLAY_CLASS_PREFIX}badge-content">
      <span class="${CONFIG.OVERLAY_CLASS_PREFIX}badge-title">EgoShield</span>
      <span class="${CONFIG.OVERLAY_CLASS_PREFIX}badge-score">${(analysis.composite_score * 100).toFixed(0)}%</span>
      <span class="${CONFIG.OVERLAY_CLASS_PREFIX}badge-band">${analysis.severity_band}</span>
      <span class="${CONFIG.OVERLAY_CLASS_PREFIX}badge-count">${analysis.tactics.length} pattern${analysis.tactics.length !== 1 ? 's' : ''}</span>
    </div>
    <button class="${CONFIG.OVERLAY_CLASS_PREFIX}dismiss" aria-label="Dismiss annotations">&times;</button>
  `;

  // Add dismiss functionality
  const dismissBtn = badge.querySelector(`.${CONFIG.OVERLAY_CLASS_PREFIX}dismiss`);
  dismissBtn.addEventListener('click', () => clearOverlays());

  badge.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 2147483647;
  `;

  return badge;
}

function showTooltip(tooltip) {
  tooltip.classList.add(`${CONFIG.OVERLAY_CLASS_PREFIX}visible`);
}

function hideTooltip(tooltip) {
  tooltip.classList.remove(`${CONFIG.OVERLAY_CLASS_PREFIX}visible`);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function clearOverlays() {
  // Remove annotation wrappers
  for (const wrapper of annotationWrappers) {
    try {
      // Get text content and replace the wrapper with a text node
      const textNode = document.createTextNode(wrapper.textContent);
      wrapper.parentNode.replaceChild(textNode, wrapper);
    } catch (e) {
      // Element may have been removed already
    }
  }
  annotationWrappers = [];
  
  // Remove container
  const containers = document.querySelectorAll(`.${CONFIG.OVERLAY_CLASS_PREFIX}container`);
  containers.forEach((container) => container.remove());
  overlayElements = [];
  currentAnalysis = null;
}

init();