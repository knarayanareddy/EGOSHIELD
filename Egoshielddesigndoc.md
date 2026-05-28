🧠 EGOSHIELD
Comprehensive Engineering Design Document
Version 1.0 | Local-First Cognitive Firewall + Manipulation Detection AI

TABLE OF CONTENTS

    Project Overview & Vision
    Goals, Non-Goals & Constraints
    System Architecture
    Module Breakdown
        4.1 Content Capture Layer (Browser Extension + Email Reader + OS Notifications)
        4.2 Normalization & Extraction Engine
        4.3 Linguistic Detector Suite
        4.4 UX / Dark Pattern Detector
        4.5 Content Category Detector
        4.6 LLM Arbiter Layer (Ollama)
        4.7 Scoring & Explainer Engine
        4.8 Alert & Overlay System
        4.9 Dashboard & Weekly Report UI
        4.10 Notification & Event Bus
    Data Models & Schemas
    API Specifications
    Directory Structure
    Configuration System
    Detection Rule System
    Tactic Taxonomy Deep Dive
    LLM Arbiter Deep Dive
    Browser Extension Deep Dive (MV3)
    Email Reader Module Deep Dive
    Scoring Model Deep Dive
    Privacy & User Trust Model
    Alert Fatigue & User Rules System
    Security Model & Threat Boundaries
    Storage & Persistence
    Logging, Observability & Debugging
    Testing Strategy
    Build, Packaging & Installation
    Platform Support Matrix
    Performance Targets & Benchmarks
    Error Handling Strategy
    Dependency Registry
    Milestone & Phased Rollout Plan
    Open Questions & Future Work

1. Project Overview & Vision
1.1 What is EgoShield?

EgoShield is a local-first, user-owned AI cognitive firewall that runs entirely on the user's machine. It sits silently in the background and monitors three content surfaces — web pages, email, and OS system notifications — scanning them in real time for psychological manipulation tactics, dark UX patterns, and emotionally manipulative language.

EgoShield does not block or censor content. It annotates, explains, and exposes. Its core loop is:

    Capture content from the web, inbox, or notification stream
    Normalize and extract structured signals (text, DOM structure, metadata)
    Run a multi-detector pipeline (rules + heuristics + local LLM)
    Score and explain findings in plain language
    Surface a non-intrusive overlay or notification with what was found
    Log results locally for weekly personal analytics

All detection runs locally. No data leaves the machine. No cloud subscription. The user owns every byte of output.
1.2 The Problem Being Solved

The modern information environment is saturated with adversarial persuasion systems engineered to override deliberate decision-making:

    Manufactured urgency in email subject lines and checkout flows
    False scarcity creating artificial pressure to act immediately
    Social proof exploitation using vague or fabricated endorsements
    Dark UX patterns that make rejection harder than acceptance by design
    Fear induction in news articles, marketing copy, and push notifications
    Confirm-shaming using guilt-laden language on opt-out buttons
    Loss aversion framing structuring every choice around what the user will lose
    Gaslighting and DARVO patterns in interpersonal and institutional communications

These tactics are individually documented and well-understood. What is missing is a personal, real-time, privacy-respecting tool that identifies them at the moment of exposure, explains what's happening, and lets the user decide how to proceed.

EgoShield fills that gap.
1.3 Design Philosophy
Principle	Description
Mirror, don't muzzle	Expose manipulation; never block content or censor sources
Human-in-the-loop	AI explains; user decides. No autonomous action of any kind
Local-first	All inference, storage, and detection runs on the user's machine
Evidence-first	Every alert must show the triggering evidence (quoted text or DOM fact)
Transparent	Every detection, score, and explanation is logged and auditable
Non-alarmist	Labels describe tactics, not intent. "urgency language" not "they're lying to you"
Composable	Detectors are pluggable. Users can tune thresholds, suppress tactics, and add custom patterns
2. Goals, Non-Goals & Constraints
2.1 Goals (In Scope)

    Real-time webpage text analysis via browser extension (Chrome/Firefox MV3)
    Email inbox analysis via local IMAP reader (no cloud relay)
    OS system notification monitoring and analysis
    Multi-tactic linguistic detection: urgency, scarcity, social proof, authority, reciprocity, loss aversion, fear induction, emotional loading, gaslighting / DARVO
    UX dark pattern detection via DOM heuristics: pre-ticked checkboxes, countdown timers, confirm-shaming buttons, misdirection layouts
    Content category detection: outrage bait, clickbait, propaganda signals
    Local LLM arbiter (via Ollama) for final classification and plain-language explanations
    Confidence scoring, severity labeling, per-tactic evidence storage
    Browser overlay alert with score, tactic list, and explanation
    Desktop notification for high-severity detections
    SQLite-backed history log with full tactic evidence
    Per-domain aggregated statistics
    Weekly "manipulation exposure" personal analytics dashboard
    User-configurable rules: domain trust, tactic suppression, custom patterns, confidence thresholds

2.2 Non-Goals (Explicitly Out of Scope)

    ❌ Blocking or censoring any content, ever
    ❌ Sending any data to remote servers or cloud APIs
    ❌ Modifying web page content or injecting counter-messaging
    ❌ Acting autonomously on the user's behalf
    ❌ Automated unsubscribes, form fills, or email replies
    ❌ Browser traffic proxying or MITM interception
    ❌ Social media account access or posting
    ❌ Detecting manipulation in audio or video (v1.0 scope)
    ❌ Any form of retaliation, poisoning, or resource exhaustion against detected sources

2.3 Constraints

    All AI inference must use a locally-running model via Ollama (or compatible local backend)
    Browser extension must comply with Chrome Manifest V3 and Firefox MV3 equivalents
    Overlay must not interfere with page interaction or layout
    Detection pipeline must complete within 2 seconds P99 for text-only analysis
    LLM arbiter pass must complete within 30 seconds P99 (acceptable for explanation quality)
    SQLite is the only storage backend (no external DB server required)
    The backend daemon must be a single installable binary
    Email analysis must be IMAP-only (no OAuth cloud relay, no SMTP write access)
    The system must handle graceful degradation: if LLM is unavailable, rule-based detection still runs and surfaces results without explanations

3. System Architecture
3.1 High-Level Architecture Diagram

text

┌───────────────────────────────────────────────────────────────────────┐
│                          USER'S MACHINE                               │
│                                                                       │
│  ┌─────────────┐  ┌────────────────┐  ┌───────────────────────────┐  │
│  │   Browser   │  │  Email Client  │  │  OS Notification Stream   │  │
│  │  (Chrome /  │  │  (IMAP Local)  │  │  (macOS/Linux/Windows)    │  │
│  │  Firefox)   │  │                │  │                           │  │
│  └──────┬──────┘  └───────┬────────┘  └────────────┬──────────────┘  │
│         │                 │                         │                 │
│         ▼                 ▼                         ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │               EGOSHIELD BACKEND DAEMON (Python/FastAPI)          │ │
│  │                                                                  │ │
│  │  ┌──────────────────────┐    ┌──────────────────────────────┐   │ │
│  │  │   CAPTURE LAYER      │    │   NORMALIZATION ENGINE       │   │ │
│  │  │  browser_extension   │    │   html_cleaner.py            │   │ │
│  │  │  email_reader.py     │───►│   text_extractor.py          │   │ │
│  │  │  notification_mon.py │    │   structure_parser.py        │   │ │
│  │  └──────────────────────┘    └──────────────┬───────────────┘   │ │
│  │                                             │                   │ │
│  │                              ┌──────────────▼───────────────┐   │ │
│  │                              │   MULTI-DETECTOR ENGINE      │   │ │
│  │                              │                              │   │ │
│  │                              │  ┌──────────┐ ┌──────────┐  │   │ │
│  │                              │  │Linguistic│ │UX/Dark   │  │   │ │
│  │                              │  │Detectors │ │Pattern   │  │   │ │
│  │                              │  └────┬─────┘ └────┬─────┘  │   │ │
│  │                              │       │             │         │   │ │
│  │                              │  ┌────▼─────────────▼──────┐ │   │ │
│  │                              │  │  Content Classifiers     │ │   │ │
│  │                              │  │  (outrage/click/prop)    │ │   │ │
│  │                              │  └──────────────────────────┘ │   │ │
│  │                              └──────────────┬───────────────┘   │ │
│  │                                             │                   │ │
│  │                              ┌──────────────▼───────────────┐   │ │
│  │                              │     SCORING ENGINE           │   │ │
│  │                              │     scorer.py                │   │ │
│  │                              │     explainer.py             │   │ │
│  │                              └──────────────┬───────────────┘   │ │
│  │                                             │                   │ │
│  │                              ┌──────────────▼───────────────┐   │ │
│  │                              │     LLM ARBITER              │   │ │
│  │                              │     llm_arbiter.py           │   │ │
│  │                              │     (Ollama / local model)   │   │ │
│  │                              └──────────────┬───────────────┘   │ │
│  │                                             │                   │ │
│  │  ┌───────────────┐           ┌──────────────▼───────────────┐   │ │
│  │  │  SQLite DB    │◄──────────│     EVENT BUS + ALERT        │   │ │
│  │  │  (local only) │           │     DISPATCH LAYER           │   │ │
│  │  └───────────────┘           └──────┬──────────┬────────────┘   │ │
│  │                                     │          │                │ │
│  └─────────────────────────────────────┼──────────┼────────────────┘ │
│                                        │          │                  │
│    ┌───────────────────────────────────▼──┐  ┌───▼──────────────┐   │
│    │  BROWSER OVERLAY                     │  │  DASHBOARD UI    │   │
│    │  (Extension popup + page annotation) │  │  (Svelte/Tailwind│   │
│    │                                      │  │   port 7331)     │   │
│    └──────────────────────────────────────┘  └──────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘

3.2 Analysis Pipeline (Step by Step)

text

Step 1:  Content captured from one of three sources:
         (a) Browser extension sends page text + DOM snapshot to POST /analyze
         (b) Email reader polls IMAP inbox, processes new messages
         (c) OS notification monitor intercepts notification text

Step 2:  Normalization engine cleans and extracts:
         - Raw HTML → clean text + structural signals
         - Email → subject, body, sender metadata, headers
         - Notification → title, body, app source

Step 3:  Multi-detector engine runs in parallel:
         - Linguistic detectors: urgency, scarcity, social proof, authority,
           reciprocity, loss aversion, fear, emotional loading, gaslighting
         - UX detectors: pre-tick, countdown, confirm-shame, misdirection
         - Content classifiers: outrage bait, clickbait, propaganda

Step 4:  Each detector emits zero or more TacticCandidate objects:
         { tactic_type, confidence, severity, evidence_text, location_hint }

Step 5:  Scoring engine aggregates candidates:
         - Weighted tactic score → overall manipulation_score (0.0–1.0)
         - Severity label: CLEAN / LOW / MEDIUM / HIGH / EXTREME

Step 6:  LLM Arbiter (if score >= threshold and LLM available):
         - Receives: page context + all tactic candidates + evidence snippets
         - Validates: does the evidence actually support each tactic label?
         - Rewrites: explanation in calm, non-alarmist plain language
         - Prunes: removes false positives

Step 7:  Results persisted to SQLite (analyses + tactics + domain_stats tables)

Step 8:  Alert dispatched:
         - If HIGH/EXTREME → browser overlay + desktop notification
         - If MEDIUM → browser overlay only
         - If LOW → logged silently (visible in dashboard)
         - If CLEAN → no alert

Step 9:  Domain stats updated (rolling averages, trust rating recalculated)

Step 10: Weekly report aggregated into daily_reports table for dashboard

3.3 Component Ownership
Component	Language/Tech	Owns
Backend Daemon	Python 3.11 + FastAPI	Analysis pipeline, API, scheduling
Linguistic Detectors	Python + spaCy + regex	Tactic detection, evidence extraction
UX Detector	Python (receives DOM from extension)	Dark pattern classification
Content Classifiers	Python + regex + heuristics	Outrage/clickbait/propaganda signals
LLM Arbiter	Python + Ollama HTTP client	Final classification + explanation
Scoring Engine	Python	Weighted aggregation, severity labeling
Email Reader	Python + imaplib	IMAP polling, message parsing
Notification Monitor	Python	OS notification interception
Browser Extension	TypeScript (MV3)	Content capture, overlay rendering
Dashboard	Svelte + TailwindCSS	Analytics UI, history, settings
Storage	SQLite (via sqlite3)	All persistence
Event Bus	Python asyncio channels	Internal pub/sub
4. Module Breakdown
4.1 Content Capture Layer
Purpose

The Capture Layer is responsible for acquiring raw content from all three monitored surfaces and delivering normalized payloads to the analysis pipeline. It is the only layer that touches external content directly.
4.1.1 Browser Extension Capture

The extension runs as a Chrome/Firefox MV3 extension. Its content script fires on every page load (and on SPA navigation events) and packages content for analysis.

TypeScript

// extension/src/content/extractor.ts

export interface PagePayload {
  url: string;
  domain: string;
  title: string;
  text_content: string;      // Extracted readable text
  dom_signals: DOMSignals;   // Structured DOM facts for UX analysis
  timestamp: string;
  source_type: 'webpage';
}

export interface DOMSignals {
  buttons: ButtonSignal[];
  checkboxes: CheckboxSignal[];
  countdown_elements: CountdownSignal[];
  form_elements: FormSignal[];
  meta_tags: Record<string, string>;
  headline_text: string;
  cta_texts: string[];      // Call-to-action button texts
}

export interface ButtonSignal {
  text: string;
  type: string;             // 'submit' | 'button' | 'link'
  css_classes: string[];
  is_primary: boolean;      // Heuristic: large, colored, prominent
}

export interface CheckboxSignal {
  label: string;
  checked: boolean;         // Default state (pre-tick detection)
  name: string;
}

export interface CountdownSignal {
  text: string;             // "Offer expires in 04:32"
  has_timer: boolean;
  resets_on_reload: boolean; // Detected by re-loading iframe or JS behavior
}

export function extractPagePayload(): PagePayload {
  return {
    url: window.location.href,
    domain: window.location.hostname,
    title: document.title,
    text_content: extractReadableText(),
    dom_signals: extractDOMSignals(),
    timestamp: new Date().toISOString(),
    source_type: 'webpage',
  };
}

function extractReadableText(): string {
  // Remove script, style, nav, footer elements
  const clone = document.body.cloneNode(true) as HTMLElement;
  ['script', 'style', 'nav', 'footer', 'header', 'aside'].forEach(tag => {
    clone.querySelectorAll(tag).forEach(el => el.remove());
  });
  return (clone.innerText || clone.textContent || '').slice(0, 50000); // 50KB cap
}

function extractDOMSignals(): DOMSignals {
  const buttons: ButtonSignal[] = Array.from(
    document.querySelectorAll('button, input[type="submit"], a[role="button"]')
  ).map(el => ({
    text: (el as HTMLElement).innerText || (el as HTMLInputElement).value || '',
    type: el.tagName.toLowerCase(),
    css_classes: Array.from(el.classList),
    is_primary: isPrimaryElement(el as HTMLElement),
  }));

  const checkboxes: CheckboxSignal[] = Array.from(
    document.querySelectorAll('input[type="checkbox"]')
  ).map(el => {
    const input = el as HTMLInputElement;
    const label = document.querySelector(`label[for="${input.id}"]`);
    return {
      label: label?.innerText || input.name || '',
      checked: input.checked,
      name: input.name,
    };
  });

  return {
    buttons,
    checkboxes,
    countdown_elements: detectCountdowns(),
    form_elements: extractForms(),
    meta_tags: extractMetaTags(),
    headline_text: (document.querySelector('h1')?.innerText || ''),
    cta_texts: buttons.filter(b => b.is_primary).map(b => b.text),
  };
}

4.1.2 Email Reader

The email reader polls a locally-configured IMAP account. It never writes to the mailbox and never forwards data externally.

Python

# egoshield/capture/email_reader.py

import imaplib
import email
from email.header import decode_header
from dataclasses import dataclass
from typing import Optional
import asyncio


@dataclass
class EmailPayload:
    uid: str
    subject: str
    sender: str
    sender_domain: str
    body_text: str
    body_html: str
    received_at: str
    source_type: str = 'email'


class EmailReader:
    def __init__(self, config: dict):
        self.host = config['host']
        self.port = config.get('port', 993)
        self.username = config['username']
        self.password = config['password']
        self.mailbox = config.get('mailbox', 'INBOX')
        self.poll_interval_seconds = config.get('poll_interval_seconds', 60)
        self._seen_uids: set[str] = set()

    def _connect(self) -> imaplib.IMAP4_SSL:
        conn = imaplib.IMAP4_SSL(self.host, self.port)
        conn.login(self.username, self.password)
        conn.select(self.mailbox, readonly=True)  # READ-ONLY: never modifies mailbox
        return conn

    def fetch_new_messages(self) -> list[EmailPayload]:
        conn = self._connect()
        try:
            _, data = conn.search(None, 'UNSEEN')
            uids = data[0].split()
            results = []
            for uid in uids:
                uid_str = uid.decode()
                if uid_str in self._seen_uids:
                    continue
                payload = self._fetch_message(conn, uid)
                if payload:
                    results.append(payload)
                    self._seen_uids.add(uid_str)
            return results
        finally:
            conn.logout()

    def _fetch_message(self, conn, uid) -> Optional[EmailPayload]:
        _, data = conn.fetch(uid, '(RFC822)')
        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        subject = self._decode_header(msg.get('Subject', ''))
        sender = self._decode_header(msg.get('From', ''))
        sender_domain = self._extract_domain(sender)

        body_text, body_html = self._extract_body(msg)

        return EmailPayload(
            uid=uid.decode(),
            subject=subject,
            sender=sender,
            sender_domain=sender_domain,
            body_text=body_text[:20000],
            body_html=body_html[:50000],
            received_at=msg.get('Date', ''),
        )

    def _decode_header(self, raw: str) -> str:
        parts = decode_header(raw)
        decoded = []
        for part, encoding in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(encoding or 'utf-8', errors='replace'))
            else:
                decoded.append(part)
        return ' '.join(decoded)

    def _extract_domain(self, sender: str) -> str:
        import re
        match = re.search(r'@([\w.-]+)', sender)
        return match.group(1).lower() if match else 'unknown'

    def _extract_body(self, msg) -> tuple[str, str]:
        text, html = '', ''
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == 'text/plain':
                    text = part.get_payload(decode=True).decode('utf-8', errors='replace')
                elif ct == 'text/html':
                    html = part.get_payload(decode=True).decode('utf-8', errors='replace')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode('utf-8', errors='replace')
        return text, html

    async def run_poll_loop(self, on_message_callback):
        while True:
            try:
                messages = self.fetch_new_messages()
                for msg in messages:
                    await on_message_callback(msg)
            except Exception as e:
                # Non-fatal: log and continue
                pass
            await asyncio.sleep(self.poll_interval_seconds)

4.1.3 OS Notification Monitor

Python

# egoshield/capture/notification_monitor.py

import platform
import asyncio
from dataclasses import dataclass


@dataclass
class NotificationPayload:
    title: str
    body: str
    app_name: str
    timestamp: str
    source_type: str = 'notification'


class NotificationMonitor:
    """
    Platform-specific OS notification monitor.
    macOS: uses NSUserNotificationCenter via PyObjC or applescript
    Linux: uses dbus-monitor / python-dbus
    Windows: uses win10toast_click or WinRT notification listener
    """

    def __init__(self, config: dict):
        self.platform = platform.system()
        self.callback = None

    def start(self, on_notification_callback):
        self.callback = on_notification_callback
        if self.platform == 'Darwin':
            self._start_macos()
        elif self.platform == 'Linux':
            self._start_linux()
        elif self.platform == 'Windows':
            self._start_windows()

    def _start_linux(self):
        # Subscribe to org.freedesktop.Notifications via dbus
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        bus.add_match_string(
            "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"
        )
        bus.add_message_filter(self._on_linux_notification)
        GLib.MainLoop().run()

    def _on_linux_notification(self, bus, message):
        args = message.get_args_list()
        if len(args) >= 4:
            payload = NotificationPayload(
                app_name=str(args[0]),
                title=str(args[3]),
                body=str(args[4]) if len(args) > 4 else '',
                timestamp=__import__('datetime').datetime.utcnow().isoformat(),
            )
            asyncio.run(self.callback(payload))

    def _start_macos(self):
        # Uses applescript to monitor Notification Center
        # Implementation: pync or subprocess applescript polling
        pass

    def _start_windows(self):
        # Uses winrt.windows.ui.notifications
        pass

4.2 Normalization & Extraction Engine

Python

# egoshield/normalization/html_cleaner.py

from bs4 import BeautifulSoup
import re


class HTMLCleaner:
    REMOVE_TAGS = ['script', 'style', 'nav', 'footer', 'header', 'aside',
                   'iframe', 'noscript', 'svg', 'img']

    def clean(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in self.REMOVE_TAGS:
            for el in soup.find_all(tag):
                el.decompose()
        text = soup.get_text(separator=' ', strip=True)
        return self._collapse_whitespace(text)

    def _collapse_whitespace(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()


# egoshield/normalization/text_extractor.py

class TextExtractor:
    """
    Extracts structured zones from cleaned text:
    - headline (first H1 or title)
    - subheadlines (H2, H3)
    - body paragraphs
    - CTA / button text
    - metadata (author, date, description)
    """

    def extract(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        return {
            'headline': self._extract_headline(soup),
            'subheadlines': self._extract_subheadlines(soup),
            'body': self._extract_body(soup),
            'cta_texts': self._extract_ctas(soup),
            'meta': self._extract_meta(soup),
            'url': url,
        }

    def _extract_headline(self, soup) -> str:
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        title = soup.find('title')
        return title.get_text(strip=True) if title else ''

    def _extract_subheadlines(self, soup) -> list[str]:
        return [el.get_text(strip=True) for el in soup.find_all(['h2', 'h3'])]

    def _extract_body(self, soup) -> str:
        paragraphs = soup.find_all('p')
        return ' '.join(p.get_text(strip=True) for p in paragraphs)

    def _extract_ctas(self, soup) -> list[str]:
        buttons = soup.find_all(['button', 'a'])
        return [b.get_text(strip=True) for b in buttons if b.get_text(strip=True)]

    def _extract_meta(self, soup) -> dict:
        meta = {}
        for tag in soup.find_all('meta'):
            name = tag.get('name') or tag.get('property') or ''
            content = tag.get('content') or ''
            if name and content:
                meta[name.lower()] = content
        return meta

4.3 Linguistic Detector Suite
Base Detector Interface

All detectors inherit from a common base class that enforces the evidence-first contract.

Python

# egoshield/detectors/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class TacticCandidate:
    tactic_type: str
    confidence: float          # 0.0 – 1.0
    severity: str              # 'low' | 'medium' | 'high' | 'critical'
    evidence_text: str         # The quoted triggering text or DOM description
    explanation: str           # Human-readable description of why this is a tactic
    location_hint: str         # 'headline' | 'cta' | 'body' | 'footer' | 'subject'
    matched_patterns: list[str] = field(default_factory=list)


class BaseDetector(ABC):
    tactic_type: str = ''
    min_confidence: float = 0.3

    @abstractmethod
    def detect(self, text_zones: dict, dom_signals: Optional[dict] = None) -> list[TacticCandidate]:
        pass

    def _count_to_confidence(self, count: int, cap: int = 5) -> float:
        return min(count / cap, 1.0)

    def _severity_from_confidence(self, confidence: float) -> str:
        if confidence >= 0.85:
            return 'critical'
        elif confidence >= 0.65:
            return 'high'
        elif confidence >= 0.4:
            return 'medium'
        return 'low'

4.3.1 Urgency Detector

Python

# egoshield/detectors/linguistic/urgency.py

from .base import BaseDetector, TacticCandidate
import re


class UrgencyDetector(BaseDetector):
    tactic_type = 'urgency'

    # Weighted pattern groups: more specific = higher weight
    PATTERNS = {
        'time_pressure': {
            'weight': 1.0,
            'patterns': [
                r'\bact\s+now\b', r'\blimited\s+time\b', r'\btoday\s+only\b',
                r'\bexpires?\s+(today|tonight|in\s+\d+\s+(hours?|minutes?|days?))\b',
                r'\bends?\s+(today|tonight|soon)\b', r'\blast\s+chance\b',
                r'\bdon\'t\s+(wait|miss|delay)\b', r'\bwhile\s+(supplies?\s+last|stock\s+lasts)\b',
                r'\bhurry\b', r'\btime\s+is\s+running\s+out\b', r'\bcount(down|ing)\b',
            ]
        },
        'artificial_deadline': {
            'weight': 1.2,
            'patterns': [
                r'\boffer\s+expires?\b', r'\bdeal\s+ends?\b',
                r'\b\d+\s+hours?\s+(left|remaining|only)\b',
                r'\b\d+\s+(minutes?|mins?)\s+(left|remaining)\b',
                r'\bclaim\s+(your|this)\s+.{0,20}\s+(now|today|immediately)\b',
            ]
        },
        'fear_of_missing_out': {
            'weight': 0.8,
            'patterns': [
                r'\bdon\'t\s+(miss\s+out|be\s+left\s+behind)\b',
                r'\beveryone\s+is\s+(getting|doing|buying)\b',
                r'\bbefore\s+it\'s\s+too\s+late\b',
                r'\bfomo\b',
            ]
        },
    }

    def detect(self, text_zones: dict, dom_signals=None) -> list[TacticCandidate]:
        results = []
        full_text = ' '.join([
            text_zones.get('headline', ''),
            text_zones.get('body', ''),
            text_zones.get('cta_texts', ''),
        ])
        text_lower = full_text.lower()

        total_score = 0.0
        matched = []
        evidence_snippets = []

        for group_name, group in self.PATTERNS.items():
            for pattern in group['patterns']:
                for match in re.finditer(pattern, text_lower):
                    total_score += group['weight']
                    matched.append(pattern)
                    # Extract evidence context (30 chars either side)
                    start = max(0, match.start() - 30)
                    end = min(len(full_text), match.end() + 30)
                    evidence_snippets.append(f'...{full_text[start:end].strip()}...')

        if not matched:
            return []

        confidence = min(total_score / 6.0, 1.0)
        if confidence < self.min_confidence:
            return []

        location = self._detect_location(text_zones, matched)
        severity = self._severity_from_confidence(confidence)

        results.append(TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=severity,
            evidence_text=evidence_snippets[0] if evidence_snippets else '',
            explanation=f'This content uses time-pressure language to create a sense of urgency. '
                        f'Detected in {location}: {evidence_snippets[0] if evidence_snippets else ""}',
            location_hint=location,
            matched_patterns=matched[:5],  # Top 5 for storage
        ))
        return results

    def _detect_location(self, text_zones: dict, matched: list) -> str:
        headline = text_zones.get('headline', '').lower()
        ctas = text_zones.get('cta_texts', '').lower()
        for pattern in matched:
            if re.search(pattern, headline):
                return 'headline'
            if re.search(pattern, ctas):
                return 'cta'
        return 'body'

4.3.2 Scarcity Detector

Python

# egoshield/detectors/linguistic/scarcity.py

class ScarcityDetector(BaseDetector):
    tactic_type = 'false_scarcity'

    PATTERNS = [
        r'\bonly\s+\d+\s+(left|remaining|in\s+stock)\b',
        r'\blimited\s+(quantity|quantities|stock|availability|supply|edition)\b',
        r'\balmost\s+(sold\s+out|gone)\b',
        r'\b(selling|going)\s+fast\b',
        r'\bexclusive\s+(offer|access|deal)\b',
        r'\bonly\s+(available|accessible)\s+to\b',
        r'\blast\s+\d+\s+(items?|units?|spots?|seats?|slots?)\b',
        r'\bsold\s+out\s+soon\b',
        r'\bhigh\s+demand\b',
        r'\bjoin\s+(the\s+)?(waitlist|waiting\s+list)\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        matches = []
        for pattern in self.PATTERNS:
            for m in re.finditer(pattern, full_text):
                matches.append((pattern, m))

        if not matches:
            return []

        confidence = self._count_to_confidence(len(matches), cap=4)
        if confidence < self.min_confidence:
            return []

        evidence = self._get_evidence_snippet(full_text, matches[0][1])
        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=self._severity_from_confidence(confidence),
            evidence_text=evidence,
            explanation=f'Scarcity language used to pressure decision-making by implying limited availability.',
            location_hint='body',
            matched_patterns=[m[0] for m in matches[:3]],
        )]

    def _get_evidence_snippet(self, text, match) -> str:
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        return f'...{text[start:end].strip()}...'

4.3.3 Social Proof Exploitation Detector

Python

# egoshield/detectors/linguistic/social_proof.py

class SocialProofDetector(BaseDetector):
    tactic_type = 'social_proof_exploitation'

    PATTERNS = [
        r'\b\d[\d,]+\s+(customers?|users?|members?|people|businesses?|clients?)\b',
        r'\b(trusted|used|loved|chosen|recommended)\s+by\s+\d',
        r'\b(everyone|thousands?|millions?)\s+(is|are|has|have)\b',
        r'\b#\d+\s+(rated|ranked|reviewed)\b',
        r'\b(top|best|most\s+popular)\s+(rated|reviewed|chosen)\b',
        r'\b(5|4\.?\d?)\s*(star|★|⭐)\s*(rated|rating|reviews?)\b',
        r'\b(join|be\s+part\s+of)\s+(our|the)\s+(community|family|tribe|movement)\b',
        r'\bdon\'t\s+be\s+(the\s+)?(only|last)\s+one\b',
        r'\byour\s+(friends?|peers?|colleagues?)\s+(are|have|use)\b',
        r'\bverified\s+(reviews?|customers?|buyers?)\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        matches = [m for p in self.PATTERNS for m in re.finditer(p, full_text)]

        if not matches:
            return []

        confidence = self._count_to_confidence(len(matches), cap=4)
        if confidence < self.min_confidence:
            return []

        evidence = self._get_snippet(full_text, matches[0])
        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=self._severity_from_confidence(confidence),
            evidence_text=evidence,
            explanation='Social proof framing used to imply widespread adoption or approval, '
                        'creating conformity pressure.',
            location_hint='body',
            matched_patterns=[m.group() for m in matches[:3]],
        )]

    def _get_snippet(self, text, match) -> str:
        s, e = max(0, match.start() - 40), min(len(text), match.end() + 40)
        return f'...{text[s:e].strip()}...'

4.3.4 Authority Exploitation Detector

Python

# egoshield/detectors/linguistic/authority.py

class AuthorityDetector(BaseDetector):
    tactic_type = 'manufactured_authority'

    PATTERNS = [
        r'\b(doctor|dr\.?|physician|expert|specialist|professor|prof\.?)\s+\w+\s+(says?|recommends?|endorses?)\b',
        r'\b(award|prize)\s+winning\b',
        r'\b(endorsed|recommended|certified|approved)\s+by\s+(experts?|professionals?|doctors?|scientists?)\b',
        r'\b(leading|top|world\'s\s+(best|#1))\s+(expert|authority|source)\b',
        r'\bpeer[\s-]reviewed\b',
        r'\bclinically\s+(proven|tested|validated|studied)\b',
        r'\b(nasa|fda|cdc|who|un)\s+(approved|endorsed|certified|backed)\b',
        r'\bscientifically\s+(proven|tested|backed|validated)\b',
        r'\bas\s+seen\s+on\s+(tv|cnn|bbc|nbc|abc|fox)\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        matches = [m for p in self.PATTERNS for m in re.finditer(p, full_text)]

        if not matches:
            return []

        confidence = self._count_to_confidence(len(matches), cap=3)
        if confidence < self.min_confidence:
            return []

        evidence = f'...{full_text[max(0, matches[0].start()-40):min(len(full_text), matches[0].end()+40)].strip()}...'
        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=self._severity_from_confidence(confidence),
            evidence_text=evidence,
            explanation='Authority claims used to bypass critical evaluation. '
                        'Credentials or endorsements invoked without verifiable sourcing.',
            location_hint='body',
            matched_patterns=[m.group() for m in matches[:3]],
        )]

4.3.5 Loss Aversion Detector

Python

# egoshield/detectors/linguistic/loss_aversion.py

class LossAversionDetector(BaseDetector):
    tactic_type = 'loss_aversion'

    PATTERNS = [
        r'\b(don\'t|do\s+not)\s+(miss|lose|waste|throw\s+away)\b',
        r'\b(risk|chance|opportunity)\s+(of\s+)?(losing|missing|wasting)\b',
        r'\byou\'ll\s+(lose|miss\s+out\s+on|regret|kick\s+yourself)\b',
        r'\b(protect|safeguard|secure)\s+(your|what\s+you\'ve)\b',
        r'\bwhat\s+you\'re\s+(giving\s+up|sacrificing|leaving\s+on\s+the\s+table)\b',
        r'\bcan\'t\s+afford\s+(not\s+to|to\s+miss)\b',
        r'\bif\s+you\s+(don\'t|fail\s+to)\s+(act|do|get)\b',
        r'\bunnecessary\s+(risk|loss|expense)\b',
        r'\bnot\s+having\s+(this|it)\s+(means?|costs?)\b',
        r'\bwhat\s+happens\s+if\s+you\s+do\s+nothing\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        matches = [m for p in self.PATTERNS for m in re.finditer(p, full_text)]

        if not matches:
            return []

        confidence = self._count_to_confidence(len(matches), cap=4)
        if confidence < self.min_confidence:
            return []

        evidence = f'...{full_text[max(0, matches[0].start()-40):matches[0].end()+40].strip()}...'
        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=self._severity_from_confidence(confidence),
            evidence_text=evidence,
            explanation='Loss framing used to make inaction feel costly. '
                        'This exploits loss aversion — the psychological tendency to '
                        'weigh losses more heavily than equivalent gains.',
            location_hint='body',
            matched_patterns=[m.group() for m in matches[:3]],
        )]

4.3.6 Fear Induction Detector

Python

# egoshield/detectors/linguistic/fear_induction.py

class FearInductionDetector(BaseDetector):
    tactic_type = 'fear_induction'

    HIGH_THREAT_PATTERNS = [
        r'\b(danger|dangerous|deadly|fatal|life[\s-]threatening)\b',
        r'\b(crisis|catastrophe|disaster|collapse|devastation)\b',
        r'\b(you\s+(could|might|may|will)\s+die|death\s+toll)\b',
        r'\b(threat|threatens?|threaten(ing)?)\s+(your|the|our)\b',
    ]

    MODERATE_THREAT_PATTERNS = [
        r'\b(alarming|shocking|terrifying|horrifying|disturbing)\b',
        r'\b(warning|alert|urgent\s+notice|emergency)\b',
        r'\b(at\s+risk|in\s+danger|vulnerable)\b',
        r'\b(protect\s+yourself|protect\s+your\s+(family|loved\s+ones))\b',
        r'\b(before\s+it\'s\s+too\s+late|while\s+you\s+(still\s+)?can)\b',
        r'\b(exposed|exposure|infection|contamination)\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        high = [m for p in self.HIGH_THREAT_PATTERNS for m in re.finditer(p, full_text)]
        moderate = [m for p in self.MODERATE_THREAT_PATTERNS for m in re.finditer(p, full_text)]

        total = len(high) * 1.5 + len(moderate) * 1.0
        if total == 0:
            return []

        confidence = min(total / 5.0, 1.0)
        if confidence < self.min_confidence:
            return []

        all_matches = high + moderate
        evidence = f'...{full_text[max(0, all_matches[0].start()-40):all_matches[0].end()+40].strip()}...'
        severity = 'critical' if len(high) >= 2 else self._severity_from_confidence(confidence)

        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=severity,
            evidence_text=evidence,
            explanation='Fear-inducing language used to lower critical evaluation '
                        'and prime an emotional rather than rational response.',
            location_hint='headline' if high else 'body',
            matched_patterns=[m.group() for m in all_matches[:3]],
        )]

4.3.7 Reciprocity Trap Detector

Python

# egoshield/detectors/linguistic/reciprocity.py

class ReciprocityDetector(BaseDetector):
    tactic_type = 'reciprocity_trap'

    PATTERNS = [
        r'\b(free\s+gift|complimentary\s+(gift|item|bonus))\b',
        r'\bwe\'re\s+giving\s+you\s+(this|a)\b',
        r'\bno\s+strings\s+attached\b',
        r'\b(claim|get)\s+your\s+free\b',
        r'\bas\s+a\s+(token\s+of\s+our\s+appreciation|thank\s+you\s+gift)\b',
        r'\bwe\'re\s+(sending|offering)\s+you\s+(this\s+)?for\s+free\b',
        r'\bour\s+gift\s+to\s+you\b',
        r'\bjust\s+pay\s+(shipping|handling|s&h)\b',   # "Free" with hidden cost
        r'\b(bonus|freebie|giveaway)\s+included\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        matches = [m for p in self.PATTERNS for m in re.finditer(p, full_text)]

        if not matches:
            return []

        confidence = self._count_to_confidence(len(matches), cap=3)
        if confidence < self.min_confidence:
            return []

        evidence = f'...{full_text[max(0,matches[0].start()-40):matches[0].end()+40].strip()}...'
        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=self._severity_from_confidence(confidence),
            evidence_text=evidence,
            explanation='Reciprocity framing used to create a sense of social obligation. '
                        'Unsolicited "gifts" prime a psychological pressure to give back.',
            location_hint='body',
            matched_patterns=[m.group() for m in matches[:3]],
        )]

4.3.8 Emotional Loading Detector

Python

# egoshield/detectors/linguistic/emotional_loading.py

class EmotionalLoadingDetector(BaseDetector):
    tactic_type = 'emotional_loading'

    # Words with strong emotional valence used to color framing
    HIGH_VALENCE_WORDS = [
        'outrage', 'disgusting', 'shameful', 'devastating', 'heartbreaking',
        'infuriating', 'despicable', 'horrifying', 'appalling', 'criminal',
        'disgusted', 'furious', 'enraged', 'betrayed', 'shocked', 'stunned',
        'unbelievable', 'unacceptable', 'intolerable', 'unconscionable',
    ]

    POSITIVE_MANIPULATION = [
        'incredible', 'amazing', 'revolutionary', 'life-changing', 'breakthrough',
        'miracle', 'magical', 'extraordinary', 'unprecedented', 'unbelievable',
        'jaw-dropping', 'mind-blowing', 'game-changer',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        words = re.findall(r'\b\w+\b', full_text)

        negative_hits = [w for w in words if w in self.HIGH_VALENCE_WORDS]
        positive_hits = [w for w in words if w in self.POSITIVE_MANIPULATION]
        total_hits = len(negative_hits) + len(positive_hits)

        if total_hits < 2:
            return []

        confidence = self._count_to_confidence(total_hits, cap=8)
        if confidence < self.min_confidence:
            return []

        dominant = 'negative' if len(negative_hits) > len(positive_hits) else 'positive'
        examples = (negative_hits + positive_hits)[:3]

        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=self._severity_from_confidence(confidence),
            evidence_text=f'Emotionally loaded words detected: {", ".join(examples)}',
            explanation=f'This content uses {dominant} emotional language at above-normal density. '
                        f'High-valence words prime emotional rather than rational responses.',
            location_hint='body',
            matched_patterns=examples,
        )]

4.3.9 Gaslighting / DARVO Detector

    ⚠️ High Risk Detector — This detector is explicitly marked as experimental. Gaslighting patterns require conversational context to reliably detect. Results from this detector are never surfaced to the user without LLM arbiter validation and a high confidence threshold (>= 0.75). The label shown to the user is always "potential reality-distortion pattern" not "gaslighting" — to avoid incorrectly labeling benign content.

Python

# egoshield/detectors/linguistic/gaslighting.py

class GaslightingDetector(BaseDetector):
    tactic_type = 'reality_distortion'  # Intentionally conservative label
    min_confidence = 0.75              # Higher threshold than other detectors
    REQUIRES_LLM_VALIDATION = True     # Cannot fire without arbiter confirmation

    # DARVO = Deny, Attack, Reverse Victim and Offender
    DARVO_PATTERNS = [
        r'\byou\'re\s+(imagining|making\s+(this|that|it)\s+up|being\s+(paranoid|too\s+sensitive))\b',
        r'\bthat\s+(never|didn\'t)\s+happen(ed)?\b',
        r'\byou\s+(always|never)\s+(do|say|think)\s+this\b',
        r'\bthe\s+(real\s+)?(victim|problem)\s+here\s+is\s+(me|us)\b',
        r'\bafter\s+everything\s+(I\'ve|we\'ve)\s+done\s+for\s+you\b',
        r'\byou\'re\s+(overreacting|being\s+(dramatic|crazy|ridiculous))\b',
        r'\bno\s+one\s+else\s+(has|would|could)\s+(a\s+problem|complain)\b',
        r'\bif\s+you\s+really\s+(loved|trusted|believed)\s+(me|us)\b',
        r'\bI\s+never\s+said\s+that\b',
        r'\byou\'re\s+twisting\s+my\s+words\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        full_text = ' '.join(text_zones.values()).lower()
        matches = [m for p in self.DARVO_PATTERNS for m in re.finditer(p, full_text)]

        if not matches:
            return []

        confidence = self._count_to_confidence(len(matches), cap=3)
        if confidence < self.min_confidence:
            return []

        evidence = f'...{full_text[max(0,matches[0].start()-50):matches[0].end()+50].strip()}...'
        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity='high',
            evidence_text=evidence,
            explanation='Language patterns consistent with reality-distortion or DARVO framing detected. '
                        'This result requires LLM validation before display.',
            location_hint='body',
            matched_patterns=[m.group() for m in matches[:3]],
        )]

4.4 UX / Dark Pattern Detector

Python

# egoshield/detectors/ux/dark_patterns.py

from ..base import BaseDetector, TacticCandidate
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class DarkPatternResult:
    pattern_name: str
    severity: str
    description: str
    evidence: str


class DarkPatternDetector(BaseDetector):
    tactic_type = 'dark_ux_pattern'

    # Confirm-shaming: reject button uses guilt language
    CONFIRM_SHAME_REJECT_PATTERNS = [
        r"no\s+thanks,?\s+i\s+(don't|do\s+not)\s+(want|need|like)",
        r"no\s+thanks,?\s+i\s+(hate|love\s+paying\s+more|prefer\s+to\s+waste)",
        r"i\s+(don't|do\s+not)\s+want\s+(to\s+)?(save|improve|succeed|be\s+happy)",
        r"i('ll|'d)\s+(rather\s+(pay\s+more|miss\s+out)|pass\s+on\s+savings)",
        r"no\s+thanks,?\s+i('m\s+fine\s+without|don't\s+care\s+about)",
    ]

    def detect(self, text_zones: dict, dom_signals: Optional[dict] = None) -> list[TacticCandidate]:
        results = []

        if dom_signals:
            results.extend(self._detect_confirm_shaming(dom_signals))
            results.extend(self._detect_pretick(dom_signals))
            results.extend(self._detect_countdown_reset(dom_signals))
            results.extend(self._detect_misdirection(dom_signals))

        # Text-based confirm shaming (in body text or email)
        full_text = ' '.join(text_zones.values()).lower()
        results.extend(self._detect_text_confirm_shame(full_text))

        return results

    def _detect_confirm_shaming(self, dom_signals: dict) -> list[TacticCandidate]:
        results = []
        for button in dom_signals.get('buttons', []):
            text_lower = button.get('text', '').lower()
            for pattern in self.CONFIRM_SHAME_REJECT_PATTERNS:
                if re.search(pattern, text_lower):
                    results.append(TacticCandidate(
                        tactic_type='confirm_shaming',
                        confidence=0.92,
                        severity='high',
                        evidence_text=f'Reject button text: "{button["text"]}"',
                        explanation='Confirm-shaming: the opt-out button uses guilt-inducing language '
                                    'to make declining feel like a personal failing.',
                        location_hint='cta',
                        matched_patterns=[pattern],
                    ))
                    break
        return results

    def _detect_pretick(self, dom_signals: dict) -> list[TacticCandidate]:
        results = []
        for cb in dom_signals.get('checkboxes', []):
            if cb.get('checked', False):
                label = cb.get('label', '').lower()
                # Is this a marketing / upsell checkbox? (not a required agreement)
                if any(kw in label for kw in [
                    'newsletter', 'email', 'offer', 'promotion', 'marketing',
                    'partner', 'third party', 'deal', 'update', 'subscribe',
                ]):
                    results.append(TacticCandidate(
                        tactic_type='pre_ticked_checkbox',
                        confidence=0.88,
                        severity='high',
                        evidence_text=f'Pre-ticked checkbox: "{cb["label"]}"',
                        explanation='A marketing or tracking opt-in checkbox is pre-selected by default, '
                                    'meaning users who do not actively notice it will inadvertently consent.',
                        location_hint='form',
                        matched_patterns=['pre_ticked_marketing_checkbox'],
                    ))
        return results

    def _detect_countdown_reset(self, dom_signals: dict) -> list[TacticCandidate]:
        results = []
        for cd in dom_signals.get('countdown_elements', []):
            if cd.get('resets_on_reload', False):
                results.append(TacticCandidate(
                    tactic_type='fake_countdown',
                    confidence=0.95,
                    severity='critical',
                    evidence_text=f'Countdown timer text: "{cd.get("text", "")}" — resets on page reload',
                    explanation='A countdown timer that resets when the page is reloaded is artificially '
                                'manufactured urgency. No real deadline exists.',
                    location_hint='body',
                    matched_patterns=['countdown_reset_on_reload'],
                ))
            elif cd.get('has_timer', False):
                results.append(TacticCandidate(
                    tactic_type='urgency_countdown',
                    confidence=0.65,
                    severity='medium',
                    evidence_text=f'Countdown timer detected: "{cd.get("text", "")}"',
                    explanation='A countdown timer creates artificial time pressure. '
                                'Verify whether this deadline is real before acting.',
                    location_hint='body',
                    matched_patterns=['countdown_timer'],
                ))
        return results

    def _detect_misdirection(self, dom_signals: dict) -> list[TacticCandidate]:
        # Heuristic: accept button is primary/large, reject is styled as text link or grayed out
        results = []
        buttons = dom_signals.get('buttons', [])
        primary_buttons = [b for b in buttons if b.get('is_primary', False)]
        secondary_buttons = [b for b in buttons if not b.get('is_primary', False)]

        accept_in_primary = any(
            any(w in b.get('text', '').lower() for w in ['accept', 'agree', 'yes', 'allow', 'okay', 'ok'])
            for b in primary_buttons
        )
        reject_in_secondary = any(
            any(w in b.get('text', '').lower() for w in ['decline', 'reject', 'no', 'refuse', 'deny'])
            for b in secondary_buttons
        )

        if accept_in_primary and reject_in_secondary:
            results.append(TacticCandidate(
                tactic_type='visual_misdirection',
                confidence=0.78,
                severity='high',
                evidence_text='Accept option styled as primary (prominent) button; '
                              'reject option styled as secondary or link.',
                explanation='Visual hierarchy misdirection: the consent UI is designed to make '
                            'accepting easier to find than declining.',
                location_hint='cta',
                matched_patterns=['accept_primary_reject_secondary'],
            ))
        return results

    def _detect_text_confirm_shame(self, text: str) -> list[TacticCandidate]:
        results = []
        for pattern in self.CONFIRM_SHAME_REJECT_PATTERNS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                s, e = max(0, match.start()-40), min(len(text), match.end()+40)
                results.append(TacticCandidate(
                    tactic_type='confirm_shaming',
                    confidence=0.80,
                    severity='medium',
                    evidence_text=f'...{text[s:e].strip()}...',
                    explanation='Confirm-shaming language detected in content: '
                                'declining or opting out is framed as a personal failure.',
                    location_hint='body',
                    matched_patterns=[pattern],
                ))
                break
        return results

4.5 Content Category Detector

Python

# egoshield/detectors/content/outrage_bait.py

class OutrageBaitDetector(BaseDetector):
    tactic_type = 'outrage_bait'

    PATTERNS = [
        r'\b(you\s+won\'t\s+believe|can\'t\s+believe)\b',
        r'\b(everyone\s+is\s+(furious|outraged|angry|disgusted))\b',
        r'\b(this\s+(is|will)\s+(make\s+you|leave\s+you))\s+(angry|furious|sick|shocked)\b',
        r'\b(the\s+(truth|real\s+story|secret)\s+(about|behind|they)\s+don\'t\s+want\s+you)\b',
        r'\b(mainstream\s+media\s+(won\'t|refuses\s+to)\s+(report|tell\s+you))\b',
        r'\b(what\s+(they|the\s+government|big\s+\w+)\s+(doesn\'t|don\'t)\s+want\s+you\s+to\s+know)\b',
        r'\b(we\s+need\s+to\s+(talk|have\s+a\s+conversation)\s+about)\b',
        r'\bthis\s+should\s+(outrage|anger|horrify|disgust)\s+every\b',
    ]

    def detect(self, text_zones, dom_signals=None) -> list[TacticCandidate]:
        headline = text_zones.get('headline', '').lower()
        body = text_zones.get('body', '').lower()

        headline_matches = [m for p in self.PATTERNS for m in re.finditer(p, headline)]
        body_matches = [m for p in self.PATTERNS for m in re.finditer(p, body)]

        # Outrage bait is more likely in headlines
        score = len(headline_matches) * 1.5 + len(body_matches) * 0.8
        if score == 0:
            return []

        confidence = min(score / 4.0, 1.0)
        if confidence < self.min_confidence:
            return []

        all_matches = headline_matches + body_matches
        text = headline if headline_matches else body
        evidence = f'...{text[max(0,all_matches[0].start()-30):all_matches[0].end()+30].strip()}...'

        return [TacticCandidate(
            tactic_type=self.tactic_type,
            confidence=confidence,
            severity=self._severity_from_confidence(confidence),
            evidence_text=evidence,
            explanation='Outrage-bait framing detected. Content is structured to provoke anger '
                        'or disgust, which reduces analytical thinking and increases engagement/sharing.',
            location_hint='headline' if headline_matches else 'body',
            matched_patterns=[m.group() for m in all_matches[:3]],
        )]

4.6 LLM Arbiter Layer
Purpose

The LLM Arbiter is the final pass in the pipeline. It receives all tactic candidates produced by the rule-based detectors and performs three functions:

    Validates each candidate: does the provided evidence snippet genuinely support the tactic label?
    Prunes false positives: marks candidates as invalidated with a reason
    Rewrites explanations in calm, plain, non-alarmist language, citing only the provided evidence — it does not infer intent or generate unsupported accusations

Python

# egoshield/detectors/llm_arbiter.py

import json
import httpx
from dataclasses import dataclass
from typing import Optional
from .base import TacticCandidate


@dataclass
class ArbitratedResult:
    original: TacticCandidate
    validated: bool
    adjusted_confidence: float
    rewritten_explanation: str
    arbiter_reasoning: str    # Why it was kept or pruned (internal, not shown to user)
    invalidation_reason: Optional[str] = None


class LLMArbiter:
    def __init__(self, config: dict):
        self.ollama_url = config.get('ollama_url', 'http://localhost:11434')
        self.model = config.get('model', 'mistral')
        self.timeout = config.get('timeout_seconds', 30)
        self.enabled = config.get('enabled', True)

    SYSTEM_PROMPT = """You are a precise, calm content analysis validator for EgoShield.
Your job is to review detected psychological manipulation tactics and:
1. Validate whether the provided evidence snippet genuinely supports the tactic label
2. Rewrite the explanation in plain, non-alarmist, factual language
3. If the evidence does NOT support the label, mark it as a false positive

Rules:
- NEVER infer intent. You describe what is present in the text, not why.
- Use calm, descriptive language. Never say "they are lying" or "this is evil."
- Cite only the provided evidence. Do not add information not in the snippet.
- If the match is ambiguous or benign in context, invalidate it.
- Respond in valid JSON only."""

    VALIDATION_PROMPT = """Review this detected manipulation tactic:

Tactic Type: {tactic_type}
Confidence: {confidence}
Location: {location_hint}
Evidence Snippet: "{evidence_text}"
Original Explanation: {explanation}
Page URL: {url}
Page Title: {title}

Respond in this exact JSON format:
{{
  "validated": true/false,
  "adjusted_confidence": 0.0-1.0,
  "rewritten_explanation": "Plain language explanation citing only the evidence",
  "arbiter_reasoning": "Why you validated or invalidated this",
  "invalidation_reason": "null or the reason it's a false positive"
}}"""

    async def arbitrate(
        self,
        candidates: list[TacticCandidate],
        page_context: dict
    ) -> list[ArbitratedResult]:
        if not self.enabled:
            # Fallback: return all candidates as-is with original explanations
            return [
                ArbitratedResult(
                    original=c,
                    validated=True,
                    adjusted_confidence=c.confidence,
                    rewritten_explanation=c.explanation,
                    arbiter_reasoning='LLM arbiter disabled',
                )
                for c in candidates
            ]

        results = []
        for candidate in candidates:
            result = await self._validate_candidate(candidate, page_context)
            results.append(result)
        return results

    async def _validate_candidate(
        self,
        candidate: TacticCandidate,
        context: dict
    ) -> ArbitratedResult:
        prompt = self.VALIDATION_PROMPT.format(
            tactic_type=candidate.tactic_type,
            confidence=candidate.confidence,
            location_hint=candidate.location_hint,
            evidence_text=candidate.evidence_text[:500],  # Cap to prevent prompt stuffing
            explanation=candidate.explanation,
            url=context.get('url', ''),
            title=context.get('title', ''),
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f'{self.ollama_url}/api/generate',
                    json={
                        'model': self.model,
                        'prompt': prompt,
                        'system': self.SYSTEM_PROMPT,
                        'stream': False,
                        'format': 'json',
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                parsed = json.loads(data.get('response', '{}'))

                return ArbitratedResult(
                    original=candidate,
                    validated=parsed.get('validated', True),
                    adjusted_confidence=float(parsed.get('adjusted_confidence', candidate.confidence)),
                    rewritten_explanation=parsed.get('rewritten_explanation', candidate.explanation),
                    arbiter_reasoning=parsed.get('arbiter_reasoning', ''),
                    invalidation_reason=parsed.get('invalidation_reason'),
                )
        except Exception as e:
            # Arbiter failure is non-fatal: return original candidate
            return ArbitratedResult(
                original=candidate,
                validated=True,
                adjusted_confidence=candidate.confidence,
                rewritten_explanation=candidate.explanation,
                arbiter_reasoning=f'LLM unavailable: {str(e)}',
            )

4.7 Scoring & Explainer Engine

Python

# egoshield/scoring/scorer.py

from dataclasses import dataclass
from typing import Optional


# Tactic weights (some tactics are inherently more impactful)
TACTIC_WEIGHTS = {
    'urgency':                    1.0,
    'false_scarcity':             1.0,
    'social_proof_exploitation':  0.8,
    'manufactured_authority':     0.9,
    'reciprocity_trap':           0.7,
    'loss_aversion':              0.9,
    'fear_induction':             1.2,
    'emotional_loading':          0.7,
    'reality_distortion':         1.5,  # Highest weight — most serious
    'confirm_shaming':            1.0,
    'pre_ticked_checkbox':        1.1,
    'fake_countdown':             1.3,
    'urgency_countdown':          0.8,
    'visual_misdirection':        1.0,
    'dark_ux_pattern':            0.9,
    'outrage_bait':               0.8,
    'clickbait':                  0.5,
    'propaganda':                 1.1,
}

SEVERITY_LABELS = {
    (0.0, 0.15): 'CLEAN',
    (0.15, 0.35): 'LOW',
    (0.35, 0.60): 'MEDIUM',
    (0.60, 0.80): 'HIGH',
    (0.80, 1.01): 'EXTREME',
}


@dataclass
class ScoringResult:
    overall_score: float          # 0.0 – 1.0
    severity: str                 # CLEAN / LOW / MEDIUM / HIGH / EXTREME
    tactic_count: int
    dominant_tactic: Optional[str]
    tactic_breakdown: dict        # { tactic_type: { confidence, severity, evidence } }
    processing_ms: int


class Scorer:
    def score(self, validated_tactics: list) -> ScoringResult:
        if not validated_tactics:
            return ScoringResult(
                overall_score=0.0,
                severity='CLEAN',
                tactic_count=0,
                dominant_tactic=None,
                tactic_breakdown={},
                processing_ms=0,
            )

        # Weighted average with diminishing returns on stacking tactics
        weighted_scores = []
        breakdown = {}

        for result in validated_tactics:
            if not result.validated:
                continue
            tactic = result.original.tactic_type
            weight = TACTIC_WEIGHTS.get(tactic, 0.8)
            weighted_score = result.adjusted_confidence * weight
            weighted_scores.append(weighted_score)
            breakdown[tactic] = {
                'confidence': result.adjusted_confidence,
                'severity': result.original.severity,
                'evidence': result.original.evidence_text,
                'explanation': result.rewritten_explanation,
                'location': result.original.location_hint,
            }

        if not weighted_scores:
            return ScoringResult(0.0, 'CLEAN', 0, None, {}, 0)

        # Combine with diminishing returns: each additional tactic adds less
        base = max(weighted_scores)
        bonus = sum(s * 0.3 for s in sorted(weighted_scores[1:], reverse=True)[:3])
        overall = min(base + bonus, 1.0)

        severity = next(
            label for (low, high), label in SEVERITY_LABELS.items()
            if low <= overall < high
        )
        dominant = max(breakdown.keys(), key=lambda t: breakdown[t]['confidence'])

        return ScoringResult(
            overall_score=round(overall, 4),
            severity=severity,
            tactic_count=len(breakdown),
            dominant_tactic=dominant,
            tactic_breakdown=breakdown,
            processing_ms=0,
        )


# egoshield/scoring/explainer.py

class Explainer:
    """
    Generates the final user-facing summary from a ScoringResult.
    Conservative, evidence-citing, non-accusatory tone.
    """

    SEVERITY_INTROS = {
        'CLEAN': 'No manipulation patterns detected in this content.',
        'LOW': 'Minor persuasive language patterns detected.',
        'MEDIUM': 'Several persuasive or pressuring patterns detected.',
        'HIGH': 'Multiple strong manipulation tactics detected.',
        'EXTREME': 'High concentration of manipulation tactics detected across this content.',
    }

    def generate_summary(self, score_result: ScoringResult) -> str:
        intro = self.SEVERITY_INTROS.get(score_result.severity, '')
        if score_result.tactic_count == 0:
            return intro

        tactic_lines = []
        for tactic_type, detail in score_result.tactic_breakdown.items():
            line = f'• {self._format_tactic_name(tactic_type)} ({detail["severity"]}): {detail["explanation"]}'
            tactic_lines.append(line)

        return f'{intro}\n\n' + '\n'.join(tactic_lines)

    def _format_tactic_name(self, tactic_type: str) -> str:
        return tactic_type.replace('_', ' ').title()

4.8 Alert & Overlay System
Browser Extension Overlay

TypeScript

// extension/src/content/overlay.ts

export interface AlertPayload {
  url: string;
  domain: string;
  overall_score: number;
  severity: 'CLEAN' | 'LOW' | 'MEDIUM' | 'HIGH' | 'EXTREME';
  tactic_count: number;
  dominant_tactic: string | null;
  tactics: TacticDetail[];
  summary: string;
  analysis_id: string;
}

export interface TacticDetail {
  tactic_type: string;
  confidence: number;
  severity: string;
  explanation: string;
  evidence_text: string;
  location_hint: string;
}

const SEVERITY_COLORS = {
  CLEAN: 'transparent',
  LOW: '#3b82f6',      // Blue
  MEDIUM: '#f59e0b',   // Amber
  HIGH: '#ef4444',     // Red
  EXTREME: '#7c3aed',  // Purple
};

export function renderOverlay(alert: AlertPayload): void {
  if (alert.severity === 'CLEAN') return;
  removeExistingOverlay();

  const overlay = document.createElement('div');
  overlay.id = 'egoshield-overlay';
  overlay.style.cssText = `
    position: fixed;
    top: 16px;
    right: 16px;
    width: 340px;
    max-height: 480px;
    background: #1e1e2e;
    border: 2px solid ${SEVERITY_COLORS[alert.severity]};
    border-radius: 12px;
    padding: 16px;
    z-index: 2147483647;
    font-family: system-ui, sans-serif;
    font-size: 13px;
    color: #cdd6f4;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    overflow-y: auto;
    transition: all 0.2s ease;
  `;

  overlay.innerHTML = buildOverlayHTML(alert);
  document.body.appendChild(overlay);

  // Auto-dismiss after 12 seconds unless hovered
  let dismissTimer = setTimeout(() => overlay.remove(), 12000);
  overlay.addEventListener('mouseenter', () => clearTimeout(dismissTimer));
  overlay.addEventListener('mouseleave', () => {
    dismissTimer = setTimeout(() => overlay.remove(), 4000);
  });

  document.getElementById('egoshield-close')?.addEventListener('click', () => overlay.remove());
  document.getElementById('egoshield-trust')?.addEventListener('click', () => {
    trustDomain(alert.domain);
    overlay.remove();
  });
}

function buildOverlayHTML(alert: AlertPayload): string {
  const scorePercent = Math.round(alert.overall_score * 100);
  const tacticItems = alert.tactics.map(t => `
    <div style="margin-top: 8px; padding: 8px; background: #313244; border-radius: 6px;">
      <div style="font-weight: 600; color: ${SEVERITY_COLORS[alert.severity] || '#cdd6f4'};">
        ${formatTacticName(t.tactic_type)}
        <span style="font-weight:400; color: #6c7086; font-size:11px;">
          ${Math.round(t.confidence * 100)}% confidence
        </span>
      </div>
      <div style="margin-top: 4px; color: #bac2de; font-size: 12px;">${t.explanation}</div>
      <div style="margin-top: 4px; color: #6c7086; font-size: 11px; font-style: italic;">
        ${t.evidence_text}
      </div>
    </div>
  `).join('');

  return `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <div style="font-weight:700; font-size:14px;">
        🧠 EgoShield
        <span style="color:${SEVERITY_COLORS[alert.severity]}; margin-left:8px;">
          ${alert.severity}
        </span>
      </div>
      <button id="egoshield-close" style="background:none; border:none; color:#6c7086; cursor:pointer; font-size:16px;">✕</button>
    </div>

    <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
      <div style="width:52px; height:52px; border-radius:50%; border: 3px solid ${SEVERITY_COLORS[alert.severity]};
           display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:700;">
        ${scorePercent}
      </div>
      <div>
        <div style="color:#6c7086; font-size:11px;">${alert.domain}</div>
        <div style="margin-top:2px;">${alert.tactic_count} tactic${alert.tactic_count !== 1 ? 's' : ''} detected</div>
      </div>
    </div>

    ${tacticItems}

    <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
      <button onclick="window.open('http://localhost:7331/history?id=${alert.analysis_id}')"
        style="flex:1; padding:6px; background:#313244; border:none; border-radius:6px;
               color:#cdd6f4; cursor:pointer; font-size:12px;">
        Full Report
      </button>
      <button id="egoshield-trust"
        style="flex:1; padding:6px; background:#313244; border:none; border-radius:6px;
               color:#cdd6f4; cursor:pointer; font-size:12px;">
        Trust Domain
      </button>
    </div>
  `;
}

function formatTacticName(type: string): string {
  return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function removeExistingOverlay(): void {
  document.getElementById('egoshield-overlay')?.remove();
}

function trustDomain(domain: string): void {
  chrome.runtime.sendMessage({ type: 'TRUST_DOMAIN', domain });
}

Desktop Notification (beeep equivalent in Python)

Python

# egoshield/alerts/desktop_notifier.py

import platform
import subprocess


class DesktopNotifier:
    """Cross-platform desktop notifications without external Go dependency."""

    def __init__(self):
        self.platform = platform.system()

    def notify(self, title: str, message: str, severity: str = 'MEDIUM'):
        if self.platform == 'Darwin':
            self._notify_macos(title, message)
        elif self.platform == 'Linux':
            self._notify_linux(title, message, severity)
        elif self.platform == 'Windows':
            self._notify_windows(title, message)

    def _notify_macos(self, title: str, message: str):
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(['osascript', '-e', script], capture_output=True)

    def _notify_linux(self, title: str, message: str, severity: str):
        urgency = {'LOW': 'low', 'MEDIUM': 'normal', 'HIGH': 'critical', 'EXTREME': 'critical'}.get(severity, 'normal')
        subprocess.run(
            ['notify-send', '-u', urgency, '-t', '8000', title, message],
            capture_output=True
        )

    def _notify_windows(self, title: str, message: str):
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title, message, duration=8, threaded=True)
        except ImportError:
            pass  # Graceful degradation

4.9 Dashboard & Weekly Report UI
Tech Stack
Layer	Technology	Why
Frontend	Svelte 4 + TypeScript	Lightweight, reactive, fast compile
Styling	TailwindCSS	Utility-first, consistent spacing
Charts	Chart.js (via svelte-chartjs)	Simple, well-supported
Table	svelte-virtual-list	Virtualized for large history logs
State	Svelte stores	Built-in, no extra dependency
Build	Vite	Fast HMR
Port	7331	Local only
Dashboard Pages

Page 1: Live Overview

text

┌──────────────────────────────────────────────────────────────┐
│  🧠 EGOSHIELD     ● Active    127 analyzed today             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Today's Exposure Score    Tactic Breakdown                  │
│  ┌─────────────────────┐   ┌──────────────────────────────┐  │
│  │      64 / 100       │   │ Urgency          ████ 34     │  │
│  │   Manipulation Load │   │ False Scarcity   ██   18     │  │
│  └─────────────────────┘   │ Fear Induction   ███  22     │  │
│                             │ Dark UX Pattern  ██   14     │  │
│                             │ Outrage Bait     █    8      │  │
│                             └──────────────────────────────┘  │
│                                                              │
│  Recent Detections                                           │
│  ┌──────┬──────────────────────┬──────────┬────────────────┐ │
│  │ Time │ Domain               │ Severity │ Tactics        │ │
│  ├──────┼──────────────────────┼──────────┼────────────────┤ │
│  │ now  │ shop.example.com     │ HIGH     │ 4 tactics      │ │
│  │ 2m   │ news.example.com     │ MEDIUM   │ 2 tactics      │ │
│  │ 5m   │ promo.example.com    │ EXTREME  │ 6 tactics      │ │
│  └──────┴──────────────────────┴──────────┴────────────────┘ │
└──────────────────────────────────────────────────────────────┘

Page 2: Analysis Detail

text

┌──────────────────────────────────────────────────────────────┐
│  ← Back   Analysis: shop.example.com          HIGH  Score:72 │
├──────────────────────────────────────────────────────────────┤
│  📄 promo.example.com/checkout                               │
│  Analyzed: 2 minutes ago  •  Source: webpage                 │
│                                                              │
│  ⚠️ Fake Countdown Timer [CRITICAL / 95%]                    │
│  A countdown timer on this page resets when the page is      │
│  reloaded, indicating it is not a real deadline.             │
│  Evidence: "Offer ends in 04:32" [resets on reload]          │
│                                                              │
│  ⚠️ Pre-Ticked Checkbox [HIGH / 88%]                         │
│  A marketing email opt-in checkbox is selected by default.   │
│  Evidence: Pre-ticked checkbox: "Send me exclusive deals"    │
│                                                              │
│  ⚠️ Urgency Language [MEDIUM / 62%]                          │
│  Time-pressure language detected in the page body.           │
│  Evidence: "...act now before this deal disappears..."       │
│                                                              │
│  [Always Trust This Domain]   [View Domain History]          │
└──────────────────────────────────────────────────────────────┘

Page 3: Domain Leaderboard

text

┌──────────────────────────────────────────────────────────────┐
│  DOMAIN STATS        [Last 7 days ▼]    [Export CSV]         │
├──────────────────────────────────────────────────────────────┤
│  Worst Offenders                                             │
│  promo.example.com      Avg Score: 0.84  Visits: 12  EXTREME │
│  shop.another.com       Avg Score: 0.71  Visits: 8   HIGH    │
│  news.clickbait.io      Avg Score: 0.65  Visits: 23  HIGH    │
│                                                              │
│  Trusted / Clean Sites                                       │
│  docs.python.org        Avg Score: 0.02  Visits: 34  CLEAN   │
│  en.wikipedia.org       Avg Score: 0.00  Visits: 19  CLEAN   │
│  github.com             Avg Score: 0.04  Visits: 56  CLEAN   │
└──────────────────────────────────────────────────────────────┘

Page 4: Weekly Report

text

┌──────────────────────────────────────────────────────────────┐
│  📊 WEEKLY MANIPULATION REPORT                               │
│  May 19 – May 25, 2025                                       │
├──────────────────────────────────────────────────────────────┤
│  Pages Analyzed:        342                                  │
│  Emails Analyzed:       89                                   │
│  Alerts Fired:          47  (14% of pages)                   │
│  Manipulation Minutes:  ~38 min                              │
│                                                              │
│  Most Frequent Tactic:  Urgency Language (114 occurrences)   │
│  Worst Domain:          promo.example.com  (0.84 avg)        │
│                                                              │
│  [📥 Download Full Report PDF]   [Share Summary]            │
└──────────────────────────────────────────────────────────────┘

Page 5: Settings & Rules

text

┌──────────────────────────────────────────────────────────────┐
│  SETTINGS                                                    │
├──────────────────────────────────────────────────────────────┤
│  LLM Arbiter Model:    [mistral ▼]                           │
│  Ollama URL:           [http://localhost:11434      ]        │
│  Alert Threshold:      [MEDIUM ▼]  (only alert above this)  │
│  Min Confidence:       [0.50 ─────────────── ]              │
│                                                              │
│  TRUSTED DOMAINS (never analyzed)                           │
│  docs.python.org                              [Remove]       │
│  [+ Add Domain]                                              │
│                                                              │
│  SUPPRESSED TACTICS                                          │
│  ☑ Urgency Language (suppress on news sites)                 │
│  ☐ Emotional Loading                                         │
│  [Manage...]                                                 │
│                                                              │
│  [💾 Save Settings]                                          │
└──────────────────────────────────────────────────────────────┘

4.10 Notification & Event Bus

Python

# egoshield/events/bus.py

import asyncio
from dataclasses import dataclass
from typing import Any, Callable
from datetime import datetime
import uuid


@dataclass
class Event:
    id: str
    event_type: str
    timestamp: str
    payload: Any
    source_type: str   # 'webpage' | 'email' | 'notification'


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, event_type: str, payload: Any, source_type: str = 'webpage'):
        event = Event(
            id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            payload=payload,
            source_type=source_type,
        )
        for callback in self._subscribers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception:
                pass  # Never let subscriber errors crash the pipeline


# Event type constants
class EventTypes:
    ANALYSIS_COMPLETE   = 'analysis.complete'
    ALERT_FIRED         = 'alert.fired'
    DOMAIN_TRUSTED      = 'domain.trusted'
    EMAIL_ANALYZED      = 'email.analyzed'
    NOTIFICATION_ANALYZED = 'notification.analyzed'
    LLM_UNAVAILABLE     = 'llm.unavailable'
    SETTINGS_UPDATED    = 'settings.updated'

5. Data Models & Schemas
5.1 SQLite Schema

SQL

-- migrations/001_initial.sql

CREATE TABLE IF NOT EXISTS analyses (
    id                TEXT PRIMARY KEY,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_type       TEXT NOT NULL,        -- 'webpage' | 'email' | 'notification'
    url               TEXT,
    domain            TEXT,
    title             TEXT,
    preview_snippet   TEXT,                 -- First 200 chars of content
    overall_score     REAL NOT NULL,        -- 0.0 – 1.0
    severity          TEXT NOT NULL,        -- CLEAN | LOW | MEDIUM | HIGH | EXTREME
    tactic_count      INTEGER NOT NULL DEFAULT 0,
    dominant_tactic   TEXT,
    summary_text      TEXT,                 -- Generated by explainer
    llm_arbitrated    BOOLEAN NOT NULL DEFAULT FALSE,
    llm_model         TEXT,
    processing_ms     INTEGER,
    source_metadata   TEXT                  -- JSON: email sender, notification app, etc.
);

CREATE TABLE IF NOT EXISTS tactics (
    id                TEXT PRIMARY KEY,
    analysis_id       TEXT NOT NULL,
    tactic_type       TEXT NOT NULL,
    confidence        REAL NOT NULL,
    severity          TEXT NOT NULL,
    evidence_text     TEXT NOT NULL,        -- Quoted snippet or DOM description
    explanation       TEXT NOT NULL,        -- Plain-language user-facing text
    location_hint     TEXT,                 -- headline | cta | body | footer | subject | form
    matched_patterns  TEXT,                 -- JSON array of triggered patterns
    arbiter_validated BOOLEAN,
    arbiter_reasoning TEXT,                 -- Internal, not shown to user
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS domain_stats (
    id                TEXT PRIMARY KEY,
    domain            TEXT UNIQUE NOT NULL,
    first_seen        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    analysis_count    INTEGER NOT NULL DEFAULT 0,
    avg_score         REAL NOT NULL DEFAULT 0.0,
    max_score         REAL NOT NULL DEFAULT 0.0,
    tactic_counts     TEXT NOT NULL DEFAULT '{}',  -- JSON: { tactic_type: count }
    trust_rating      TEXT NOT NULL DEFAULT 'neutral',
                                                   -- trusted | neutral | suspicious | hostile
    is_trusted        BOOLEAN NOT NULL DEFAULT FALSE,
    trusted_by_user   BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS daily_reports (
    id                TEXT PRIMARY KEY,
    report_date       DATE NOT NULL UNIQUE,
    analyses_count    INTEGER NOT NULL DEFAULT 0,
    emails_count      INTEGER NOT NULL DEFAULT 0,
    alerts_count      INTEGER NOT NULL DEFAULT 0,
    avg_score         REAL NOT NULL DEFAULT 0.0,
    top_tactic        TEXT,
    worst_domain      TEXT,
    manipulation_minutes INTEGER NOT NULL DEFAULT 0,
    tactic_summary    TEXT NOT NULL DEFAULT '{}',  -- JSON breakdown
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_rules (
    id                TEXT PRIMARY KEY,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rule_type         TEXT NOT NULL,        -- 'trusted_domain' | 'suppressed_tactic' | 'custom_pattern'
    target            TEXT NOT NULL,        -- Domain, tactic type, or pattern string
    action            TEXT NOT NULL,        -- 'trust' | 'suppress' | 'block_alert' | 'elevate'
    conditions        TEXT,                 -- JSON: additional conditions (e.g., "only on news sites")
    enabled           BOOLEAN NOT NULL DEFAULT TRUE,
    notes             TEXT
);

-- Performance indexes
CREATE INDEX idx_analyses_domain     ON analyses(domain);
CREATE INDEX idx_analyses_created_at ON analyses(created_at);
CREATE INDEX idx_analyses_severity   ON analyses(severity);
CREATE INDEX idx_analyses_source     ON analyses(source_type);
CREATE INDEX idx_tactics_analysis_id ON tactics(analysis_id);
CREATE INDEX idx_tactics_tactic_type ON tactics(tactic_type);
CREATE INDEX idx_domain_stats_domain ON domain_stats(domain);
CREATE INDEX idx_daily_reports_date  ON daily_reports(report_date);

6. API Specifications
6.1 Internal REST API (Extension + Dashboard ↔ Backend)

All endpoints served at http://localhost:7330/api/v1/
Analysis Endpoints

text

POST   /api/v1/analyze
       Body: {
         source_type: 'webpage' | 'email' | 'notification',
         url?: string,
         title?: string,
         text_content: string,
         dom_signals?: DOMSignals,
         source_metadata?: object
       }
       Returns: AnalysisResult (full result with tactics, score, summary)

GET    /api/v1/analyses
       Query: ?limit=50&offset=0&domain=&severity=&source_type=&from=&to=
       Returns: { total: int, items: AnalysisSummary[] }

GET    /api/v1/analyses/:id
       Returns: AnalysisResult (full, with all tactics)

DELETE /api/v1/analyses
       Body: { older_than_days: int }
       Returns: { deleted_count: int }

Tactics Endpoints

text

GET    /api/v1/tactics
       Query: ?analysis_id=&tactic_type=&severity=
       Returns: Tactic[]

GET    /api/v1/tactics/summary
       Query: ?days=7
       Returns: { tactic_type: count }[] (ranked)

Domain Endpoints

text

GET    /api/v1/domains
       Query: ?sort=avg_score&order=desc&trust_rating=&limit=50
       Returns: DomainStat[]

GET    /api/v1/domains/:domain
       Returns: DomainStat (with recent analyses)

POST   /api/v1/domains/:domain/trust
       Body: { trusted: bool }
       Returns: DomainStat

GET    /api/v1/domains/leaderboard
       Returns: { worst: DomainStat[], cleanest: DomainStat[] }

Reports Endpoints

text

GET    /api/v1/reports/daily
       Query: ?from=&to=
       Returns: DailyReport[]

GET    /api/v1/reports/weekly
       Query: ?week_of=YYYY-MM-DD
       Returns: WeeklyReportSummary

GET    /api/v1/reports/stats
       Returns: {
         total_analyzed_today: int,
         total_alerts_today: int,
         avg_score_today: float,
         top_tactic_week: string,
         worst_domain_week: string
       }

User Rules Endpoints

text

GET    /api/v1/rules
       Returns: UserRule[]

POST   /api/v1/rules
       Body: { rule_type, target, action, conditions?, notes? }
       Returns: UserRule

PUT    /api/v1/rules/:id
       Body: Partial<UserRule>
       Returns: UserRule

DELETE /api/v1/rules/:id
       Returns: { success: bool }

Settings Endpoints

text

GET    /api/v1/settings
       Returns: Settings

PUT    /api/v1/settings
       Body: Partial<Settings>
       Returns: Settings

GET    /api/v1/health
       Returns: {
         daemon_running: bool,
         llm_available: bool,
         db_healthy: bool,
         version: string,
         uptime_seconds: int
       }

Real-Time Stream

text

GET    /api/v1/stream/events
       Content-Type: text/event-stream
       Events: analysis.complete | alert.fired | llm.unavailable | settings.updated

7. Directory Structure

text

egoshield/
│
├── cmd/
│   └── main.py                         # Entrypoint: starts daemon + FastAPI + pollers
│
├── egoshield/
│   │
│   ├── api/
│   │   ├── server.py                   # FastAPI app factory, route registration
│   │   ├── middleware.py               # CORS (localhost only), logging
│   │   ├── sse.py                      # Server-Sent Events handler
│   │   └── handlers/
│   │       ├── analyze.py              # POST /analyze
│   │       ├── analyses.py             # GET /analyses, GET /analyses/:id
│   │       ├── tactics.py              # GET /tactics
│   │       ├── domains.py              # Domain stats + trust
│   │       ├── reports.py              # Daily/weekly reports
│   │       ├── rules.py                # User rules CRUD
│   │       ├── settings.py             # Settings
│   │       └── health.py              # Health check
│   │
│   ├── capture/
│   │   ├── email_reader.py             # IMAP polling (readonly)
│   │   └── notification_monitor.py     # OS notification monitor (platform-specific)
│   │
│   ├── normalization/
│   │   ├── html_cleaner.py             # Strip noise tags, collapse whitespace
│   │   ├── text_extractor.py           # Zone extraction (headline, body, CTA, meta)
│   │   └── structure_parser.py         # DOM signal normalization from extension
│   │
│   ├── detectors/
│   │   ├── base.py                     # TacticCandidate dataclass, BaseDetector ABC
│   │   ├── registry.py                 # Detector registry + pipeline runner
│   │   │
│   │   ├── linguistic/
│   │   │   ├── urgency.py              # UrgencyDetector
│   │   │   ├── scarcity.py             # ScarcityDetector
│   │   │   ├── social_proof.py         # SocialProofDetector
│   │   │   ├── authority.py            # AuthorityDetector
│   │   │   ├── reciprocity.py          # ReciprocityDetector
│   │   │   ├── loss_aversion.py        # LossAversionDetector
│   │   │   ├── fear_induction.py       # FearInductionDetector
│   │   │   ├── emotional_loading.py    # EmotionalLoadingDetector
│   │   │   └── gaslighting.py          # GaslightingDetector (experimental, LLM-gated)
│   │   │
│   │   ├── ux/
│   │   │   ├── dark_patterns.py        # Master UX detector (dispatches to sub-detectors)
│   │   │   ├── confirm_shame.py        # Confirm-shaming detector
│   │   │   ├── pretick.py              # Pre-ticked checkbox detector
│   │   │   ├── countdown.py            # Fake/real countdown detector
│   │   │   └── misdirection.py         # Visual hierarchy misdirection
│   │   │
│   │   └── content/
│   │       ├── outrage_bait.py         # OutrageBaitDetector
│   │       ├── clickbait.py            # ClickbaitDetector
│   │       └── propaganda.py           # PropagandaSignalDetector
│   │
│   ├── llm/
│   │   ├── llm_arbiter.py              # LLMArbiter: validate + rewrite explanations
│   │   ├── ollama_client.py            # Ollama HTTP client wrapper
│   │   └── prompts.py                  # All prompt templates
│   │
│   ├── scoring/
│   │   ├── scorer.py                   # Weighted aggregation, ScoringResult
│   │   └── explainer.py                # Human-readable summary generation
│   │
│   ├── alerts/
│   │   ├── dispatcher.py               # Routes alerts to overlay / desktop / log
│   │   └── desktop_notifier.py         # Cross-platform desktop notifications
│   │
│   ├── events/
│   │   ├── bus.py                      # EventBus (asyncio pub/sub)
│   │   └── types.py                    # EventTypes constants
│   │
│   ├── storage/
│   │   ├── db.py                       # SQLite connection, migration runner
│   │   ├── analyses_repo.py            # Analyses CRUD
│   │   ├── tactics_repo.py             # Tactics CRUD
│   │   ├── domain_stats_repo.py        # Domain stats aggregation
│   │   ├── reports_repo.py             # Daily/weekly report aggregation
│   │   ├── rules_repo.py               # User rules CRUD
│   │   └── settings_repo.py            # Settings key/value store
│   │
│   ├── config/
│   │   ├── config.py                   # Config dataclass + TOML loader
│   │   ├── defaults.py                 # Default configuration values
│   │   └── validator.py                # Config validation
│   │
│   └── scheduler/
│       ├── report_scheduler.py         # Daily report aggregation job
│       ├── domain_stats_scheduler.py   # Domain stats rollup
│       └── cleanup_scheduler.py        # Log retention enforcement
│
├── extension/                          # Browser extension (TypeScript MV3)
│   ├── src/
│   │   ├── background/
│   │   │   ├── service_worker.ts       # MV3 service worker (event handling)
│   │   │   ├── api_client.ts           # Calls localhost:7330 backend
│   │   │   └── trust_store.ts          # Local trusted domain cache
│   │   │
│   │   ├── content/
│   │   │   ├── extractor.ts            # Page content + DOM signal extraction
│   │   │   ├── overlay.ts              # Alert overlay rendering
│   │   │   ├── highlighter.ts          # Evidence text highlighting (optional)
│   │   │   └── spa_observer.ts         # SPA navigation detection (MutationObserver)
│   │   │
│   │   └── popup/
│   │       ├── Popup.tsx               # Extension popup UI
│   │       ├── popup.html
│   │       └── popup.css
│   │
│   ├── manifest.json                   # MV3 manifest
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── dashboard/                          # Svelte dashboard UI
│   ├── src/
│   │   ├── App.svelte
│   │   ├── pages/
│   │   │   ├── Overview.svelte         # Live overview + recent detections
│   │   │   ├── History.svelte          # Full analysis history log
│   │   │   ├── AnalysisDetail.svelte   # Single analysis drill-down
│   │   │   ├── Domains.svelte          # Domain leaderboard
│   │   │   ├── WeeklyReport.svelte     # Weekly analytics
│   │   │   └── Settings.svelte         # Settings + user rules
│   │   │
│   │   ├── components/
│   │   │   ├── ScoreBadge.svelte       # Score ring + severity label
│   │   │   ├── TacticCard.svelte       # Single tactic display
│   │   │   ├── AlertFeed.svelte        # Live SSE feed of alerts
│   │   │   ├── DomainLeaderboard.svelte
│   │   │   ├── TacticBreakdownChart.svelte
│   │   │   └── WeeklyTimeline.svelte
│   │   │
│   │   ├── stores/
│   │   │   ├── analyses.ts             # Analysis history store
│   │   │   ├── domains.ts              # Domain stats store
│   │   │   ├── settings.ts             # Settings store
│   │   │   └── live_feed.ts            # SSE live event store
│   │   │
│   │   └── api/
│   │       └── client.ts               # Typed API client
│   │
│   ├── package.json
│   ├── svelte.config.js
│   └── vite.config.ts
│
├── data/                               # SQLite DB (gitignored, created at runtime)
├── logs/                               # Log files (gitignored, opt-in)
│
├── tests/
│   ├── unit/
│   │   ├── test_urgency_detector.py
│   │   ├── test_scarcity_detector.py
│   │   ├── test_dark_patterns.py
│   │   ├── test_scorer.py
│   │   └── test_explainer.py
│   ├── integration/
│   │   ├── test_analyze_endpoint.py
│   │   ├── test_llm_arbiter_mock.py
│   │   └── test_email_reader.py
│   └── fixtures/
│       ├── sample_pages/               # HTML snapshots for testing
│       ├── sample_emails/              # .eml fixtures
│       └── sample_dom_signals/         # JSON DOM signal fixtures
│
├── config.toml                         # Default config (user-editable)
├── Makefile
├── pyproject.toml
├── requirements.txt
└── README.md

8. Configuration System
8.1 Config File (TOML)

Stored at ~/.egoshield/config.toml

toml

[daemon]
host = "127.0.0.1"
port = 7330                           # Backend API port
dashboard_port = 7331                 # Dashboard UI port
log_level = "info"                    # debug | info | warn | error

[analysis]
min_confidence_threshold = 0.40       # Minimum confidence to store a tactic
alert_severity_threshold = "MEDIUM"   # Minimum severity to fire an overlay/notification
enable_llm_arbiter = true             # Enable LLM validation pass
llm_arbiter_min_score = 0.30          # Only send to LLM if score >= this
max_content_length_chars = 50000      # Cap page text to prevent oversized payloads
analysis_timeout_seconds = 5          # Fail gracefully if rules take too long

[llm]
backend = "ollama"                    # "ollama" | "none"
ollama_url = "http://localhost:11434"
model = "mistral"                     # or "llama3", "phi3", etc.
timeout_seconds = 30
max_concurrent_jobs = 2

[detectors]
# Enable/disable individual detector categories
enable_linguistic = true
enable_ux = true
enable_content = true
enable_gaslighting = false            # Experimental — off by default

# Per-detector min_confidence overrides
[detectors.overrides]
reality_distortion = 0.75            # Higher bar for gaslighting detector
fake_countdown = 0.90                # Require high confidence on countdown claims

[email]
enabled = false                       # Off by default until user configures
host = ""
port = 993
username = ""
password = ""                         # Stored in system keychain if available
mailbox = "INBOX"
poll_interval_seconds = 60

[notifications]
enabled = true
monitor_os_notifications = false      # OS notification monitoring (off by default)

[alerts]
enable_browser_overlay = true
enable_desktop_notifications = true
desktop_notify_severity = "HIGH"      # Only desktop notify at HIGH+
overlay_auto_dismiss_seconds = 12

[storage]
db_path = "~/.egoshield/egoshield.db"
log_traffic = true
retention_days = 90
max_db_size_mb = 200

[dashboard]
open_on_start = false
theme = "dark"

[user_rules]
# Populated by dashboard UI; not typically hand-edited
trusted_domains = []
suppressed_tactics = []

8.2 Config Loader

Python

# egoshield/config/config.py

import tomllib
import os
from pathlib import Path
from dataclasses import dataclass, field


DEFAULT_CONFIG_PATH = Path.home() / '.egoshield' / 'config.toml'


@dataclass
class LLMConfig:
    backend: str = 'ollama'
    ollama_url: str = 'http://localhost:11434'
    model: str = 'mistral'
    timeout_seconds: int = 30
    max_concurrent_jobs: int = 2


@dataclass
class AnalysisConfig:
    min_confidence_threshold: float = 0.40
    alert_severity_threshold: str = 'MEDIUM'
    enable_llm_arbiter: bool = True
    llm_arbiter_min_score: float = 0.30
    max_content_length_chars: int = 50000
    analysis_timeout_seconds: int = 5


@dataclass
class StorageConfig:
    db_path: str = str(Path.home() / '.egoshield' / 'egoshield.db')
    log_traffic: bool = True
    retention_days: int = 90
    max_db_size_mb: int = 200


@dataclass
class EgoShieldConfig:
    daemon_host: str = '127.0.0.1'
    daemon_port: int = 7330
    dashboard_port: int = 7331
    log_level: str = 'info'
    llm: LLMConfig = field(default_factory=LLMConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> EgoShieldConfig:
    if not path.exists():
        config = EgoShieldConfig()
        save_default(path, config)
        return config

    with open(path, 'rb') as f:
        raw = tomllib.load(f)

    cfg = EgoShieldConfig()

    if 'daemon' in raw:
        cfg.daemon_host = raw['daemon'].get('host', cfg.daemon_host)
        cfg.daemon_port = raw['daemon'].get('port', cfg.daemon_port)
        cfg.dashboard_port = raw['daemon'].get('dashboard_port', cfg.dashboard_port)

    if 'llm' in raw:
        cfg.llm = LLMConfig(**{k: v for k, v in raw['llm'].items()
                               if k in LLMConfig.__dataclass_fields__})

    if 'analysis' in raw:
        cfg.analysis = AnalysisConfig(**{k: v for k, v in raw['analysis'].items()
                                         if k in AnalysisConfig.__dataclass_fields__})

    return cfg


def save_default(path: Path, config: EgoShieldConfig):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write TOML skeleton with comments
    with open(path, 'w') as f:
        f.write('# EgoShield Configuration\n# See documentation for all options\n\n')
        f.write(f'[daemon]\nhost = "{config.daemon_host}"\nport = {config.daemon_port}\n')

9. Detection Rule System
9.1 Detector Registry & Pipeline Runner

Python

# egoshield/detectors/registry.py

import asyncio
from typing import Optional
from .base import BaseDetector, TacticCandidate
from .linguistic.urgency import UrgencyDetector
from .linguistic.scarcity import ScarcityDetector
from .linguistic.social_proof import SocialProofDetector
from .linguistic.authority import AuthorityDetector
from .linguistic.reciprocity import ReciprocityDetector
from .linguistic.loss_aversion import LossAversionDetector
from .linguistic.fear_induction import FearInductionDetector
from .linguistic.emotional_loading import EmotionalLoadingDetector
from .linguistic.gaslighting import GaslightingDetector
from .ux.dark_patterns import DarkPatternDetector
from .content.outrage_bait import OutrageBaitDetector
from .content.clickbait import ClickbaitDetector
from .content.propaganda import PropagandaSignalDetector


ALL_DETECTORS = [
    UrgencyDetector,
    ScarcityDetector,
    SocialProofDetector,
    AuthorityDetector,
    ReciprocityDetector,
    LossAversionDetector,
    FearInductionDetector,
    EmotionalLoadingDetector,
    DarkPatternDetector,
    OutrageBaitDetector,
    ClickbaitDetector,
    PropagandaSignalDetector,
]

EXPERIMENTAL_DETECTORS = [
    GaslightingDetector,
]


class DetectorRegistry:
    def __init__(self, config: dict, suppressed_tactics: list[str] = None):
        self.suppressed = set(suppressed_tactics or [])
        self.detectors: list[BaseDetector] = []

        for cls in ALL_DETECTORS:
            detector = cls()
            if detector.tactic_type not in self.suppressed:
                self.detectors.append(detector)

        if config.get('enable_gaslighting', False):
            self.detectors.append(GaslightingDetector())

    def run_all(
        self,
        text_zones: dict,
        dom_signals: Optional[dict] = None
    ) -> list[TacticCandidate]:
        all_candidates = []
        for detector in self.detectors:
            try:
                candidates = detector.detect(text_zones, dom_signals)
                all_candidates.extend(candidates)
            except Exception as e:
                # Detector failure is non-fatal
                pass
        return all_candidates

9.2 Rule Priority

Rules and user settings are applied in this order (highest priority first):

text

1. User trusted domain  → Skip all analysis entirely
2. User suppressed tactic → Remove that tactic from results
3. User custom pattern (block) → Force EXTREME severity
4. Confidence threshold filter → Prune below min_confidence
5. LLM arbiter validation → Prune false positives
6. Alert threshold filter → Decide whether to surface overlay

10. Tactic Taxonomy Deep Dive
Tactic	Detector Class	What It Targets	LLM Required	Default Severity
Urgency	UrgencyDetector	Time-pressure language in text	No	MEDIUM
False Scarcity	ScarcityDetector	Availability/stock pressure	No	MEDIUM
Social Proof Exploitation	SocialProofDetector	Conformity pressure via numbers/crowds	No	LOW-MEDIUM
Manufactured Authority	AuthorityDetector	Unverifiable credential claims	No	MEDIUM
Reciprocity Trap	ReciprocityDetector	Unsolicited gifts, obligation framing	No	LOW-MEDIUM
Loss Aversion	LossAversionDetector	Framing choices around what's lost	No	MEDIUM
Fear Induction	FearInductionDetector	Threat language, danger framing	No	HIGH
Emotional Loading	EmotionalLoadingDetector	High-valence word density	No	LOW-MEDIUM
Reality Distortion (DARVO)	GaslightingDetector	Reality-denial, blame-reversal patterns	Yes (mandatory)	HIGH
Confirm-Shaming	DarkPatternDetector	Guilt-laden reject button text	No	HIGH
Pre-Ticked Checkbox	DarkPatternDetector	Default-selected marketing opt-ins	No	HIGH
Fake Countdown	DarkPatternDetector	Countdowns that reset on reload	No	CRITICAL
Urgency Countdown	DarkPatternDetector	Countdown timers (real or fake)	No	MEDIUM
Visual Misdirection	DarkPatternDetector	Accept-prominent, reject-hidden layout	No	HIGH
Outrage Bait	OutrageBaitDetector	Anger-priming content structure	No	MEDIUM
Clickbait	ClickbaitDetector	Curiosity-gap headline structure	No	LOW
Propaganda Signals	PropagandaSignalDetector	Us/them framing, loaded terminology	No	MEDIUM-HIGH
11. LLM Arbiter Deep Dive
11.1 When the LLM Arbiter Fires

The arbiter is invoked only when:

    enable_llm_arbiter = true in config
    The overall score is >= llm_arbiter_min_score (default 0.30)
    Ollama is reachable (health check passes)

If any condition fails, the pipeline falls through with rule-based results and no explanations are rewritten.
11.2 Prompt Architecture

text

System: [SYSTEM_PROMPT] — establishes calm, evidence-citing, non-accusatory persona
User:   [VALIDATION_PROMPT per tactic] — provides tactic + evidence + context
Model:  [JSON response] — validated: bool, confidence, rewritten_explanation, reasoning

11.3 Special Handling: Gaslighting / Reality Distortion

The GaslightingDetector sets REQUIRES_LLM_VALIDATION = True. This means:

    Its candidates are never stored or surfaced if the LLM arbiter is unavailable
    The arbiter is given additional context about the conversational framing
    The user-facing label is always "potential reality-distortion language" — never "gaslighting" (to prevent unfair accusatory labeling of ambiguous content)

11.4 Model Recommendations
Use Case	Recommended Model	RAM Required
Fast, low resource	Phi-3 Mini (3.8B)	~4GB
Balanced	Mistral 7B Q4	~6GB
High quality validation	Llama 3 8B Q4	~8GB
Maximum accuracy	Llama 3 70B Q4	~40GB
12. Browser Extension Deep Dive (MV3)
12.1 MV3 Architecture Constraints

Chrome Manifest V3 imposes key constraints that the extension design must respect:

    Background scripts are service workers — they have no persistent state; use chrome.storage.local for cross-event state
    Content scripts have DOM access — all page extraction happens in content scripts, not the service worker
    No remote code execution — all logic must be bundled at install time
    activeTab permission — extension can only read the current tab's DOM when the user interacts with the popup

12.2 Message Flow

text

Content Script (extractor.ts)
  → chrome.runtime.sendMessage({ type: 'PAGE_PAYLOAD', payload: PagePayload })

Service Worker (service_worker.ts)
  → Receives message
  → Checks: is domain trusted? if yes, drop
  → POSTs to http://localhost:7330/api/v1/analyze
  → Receives AnalysisResult
  → Sends to content script: chrome.tabs.sendMessage(tabId, { type: 'SHOW_OVERLAY', alert })

Content Script (overlay.ts)
  → Renders overlay in page DOM

12.3 Service Worker Implementation

TypeScript

// extension/src/background/service_worker.ts

import { isLocalBackendAvailable, postAnalyze } from './api_client';
import { isTrustedDomain, trustDomain } from './trust_store';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'PAGE_PAYLOAD') {
    handlePagePayload(message.payload, sender.tab?.id);
  }
  if (message.type === 'TRUST_DOMAIN') {
    trustDomain(message.domain);
  }
  return true; // Keep channel open for async
});

async function handlePagePayload(payload: any, tabId?: number): Promise<void> {
  if (!tabId) return;

  // Skip trusted domains entirely
  if (await isTrustedDomain(payload.domain)) return;

  // Check backend is available
  const available = await isLocalBackendAvailable();
  if (!available) return; // Silent fail — never break browsing

  try {
    const result = await postAnalyze(payload);

    // Only send overlay if severity warrants it
    if (['MEDIUM', 'HIGH', 'EXTREME'].includes(result.severity)) {
      chrome.tabs.sendMessage(tabId, {
        type: 'SHOW_OVERLAY',
        alert: result,
      });
    }
  } catch (err) {
    // Non-fatal: backend errors never affect browsing
    console.warn('[EgoShield] Analysis failed:', err);
  }
}

// SPA navigation: re-analyze on URL change
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url) {
    // URL changed in same tab (SPA) — content script will re-fire
    chrome.tabs.sendMessage(tabId, { type: 'URL_CHANGED', url: changeInfo.url })
      .catch(() => {}); // Content script may not be ready yet
  }
});

12.4 Extension Manifest

JSON

// extension/manifest.json

{
  "manifest_version": 3,
  "name": "EgoShield",
  "version": "1.0.0",
  "description": "Local-first cognitive firewall. Detects manipulation tactics in real time.",
  "permissions": [
    "activeTab",
    "storage",
    "tabs"
  ],
  "host_permissions": [
    "http://localhost:7330/*"
  ],
  "background": {
    "service_worker": "dist/background/service_worker.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": ["http://*/*", "https://*/*"],
      "js": ["dist/content/extractor.js", "dist/content/overlay.js"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "32": "icons/icon32.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}

13. Email Reader Module Deep Dive
13.1 Analysis Approach for Email

Email content is analyzed differently from web pages:
Zone	How Extracted	Detectors Applied
Subject line	msg['Subject'] decoded	Urgency, Scarcity, Fear, Emotional Loading, Loss Aversion
Sender domain	Parsed from From: header	Domain stats lookup
Body (plain text)	text/plain part	All linguistic detectors
Body (HTML → text)	BeautifulSoup stripped	All linguistic detectors
CTA text	Extracted from HTML links/buttons	Urgency, Confirm-shame
13.2 Email-Specific Patterns

Subject lines get elevated weight for urgency/scarcity patterns because this is the primary manipulation surface for email:

Python

# egoshield/detectors/linguistic/urgency.py

EMAIL_SUBJECT_MULTIPLIER = 1.5  # Subject-line matches count 50% more

def detect_in_email(self, subject: str, body: str) -> list[TacticCandidate]:
    subject_zones = {'headline': subject, 'body': '', 'cta_texts': ''}
    body_zones = {'headline': '', 'body': body, 'cta_texts': ''}

    subject_candidates = self.detect(subject_zones)
    body_candidates = self.detect(body_zones)

    # Elevate severity for subject-line matches
    for c in subject_candidates:
        c.confidence = min(c.confidence * self.EMAIL_SUBJECT_MULTIPLIER, 1.0)
        c.location_hint = 'subject'
        c.severity = self._severity_from_confidence(c.confidence)

    return subject_candidates + body_candidates

14. Scoring Model Deep Dive
14.1 Weighted Combination Formula

text

Let W(t) = TACTIC_WEIGHTS[tactic_type]
Let C(t) = adjusted_confidence from LLM arbiter (or raw confidence if LLM unavailable)
Let weighted_score(t) = C(t) × W(t)

base_score    = max(weighted_score(t) for all t)
stacking_bonus = sum(weighted_score(t) × 0.3 for t in top_3_additional_tactics)
overall_score = min(base_score + stacking_bonus, 1.0)

Design rationale: The diminishing-returns stacking model means a page with one extremely strong tactic (e.g., a fake countdown at 0.95 confidence) scores HIGH even without other tactics. Additional tactics add context but cannot exceed 1.0, and each contributes less than the last. This prevents score inflation from many weak detections drowning out signal.
14.2 Severity Bands
Score Range	Severity	Alert Behavior
0.00 – 0.15	CLEAN	No alert, logged
0.15 – 0.35	LOW	Logged, visible in dashboard
0.35 – 0.60	MEDIUM	Browser overlay
0.60 – 0.80	HIGH	Overlay + desktop notification
0.80 – 1.00	EXTREME	Overlay + desktop notification (urgent styling)
15. Privacy & User Trust Model
15.1 Data Flow — What EgoShield Never Does
Action	Status
Send page content to any remote server	❌ Never
Use cloud-hosted LLM APIs	❌ Never
Share domain stats or tactic data externally	❌ Never
Store full page HTML	❌ Never (preview snippet only, 200 chars)
Access or store email credentials in plaintext	❌ Use OS keychain when available
Access email in write mode	❌ Read-only IMAP only
Collect behavioral analytics on user actions	❌ Never
15.2 What is Stored Locally
Data	Where	Retention
Analysis results (score, severity, tactics)	SQLite	Configurable (default 90 days)
200-char content preview snippet	SQLite	Same as above
Evidence snippets (30-50 char quoted text)	SQLite	Same as above
Domain stats (aggregated averages)	SQLite	Indefinite (user-deletable)
User rules (trusted domains, suppressions)	SQLite	Indefinite
LLM arbiter prompts/responses (internal)	SQLite	Same as analyses
15.3 User Control

Users can at any time:

    View exactly what was captured for any alert (evidence snippet, not full page)
    Delete all data for a specific domain
    Delete all data older than N days
    Trust a domain permanently (preventing any future analysis)
    Export all their data as JSON/CSV
    Pause EgoShield entirely via the dashboard

16. Alert Fatigue & User Rules System
16.1 The Alert Fatigue Problem

If every page with a single urgency phrase fires a notification, users will disable the extension within a day. The system has multiple layers to prevent this:

text

Layer 1: Confidence threshold (global min_confidence)
         → Low-confidence matches don't even become TacticCandidates

Layer 2: Severity threshold (alert_severity_threshold)
         → Below threshold: logged silently, not overlayed

Layer 3: LLM arbiter pruning
         → False positives removed before scoring

Layer 4: User trusted domains
         → Domains the user has said "always trust" are skipped entirely

Layer 5: User suppressed tactics
         → "I don't want urgency alerts on news sites" supported

Layer 6: Rate limiting per domain
         → Max 1 overlay per domain per N minutes (configurable)

16.2 User Rules Data Model

Python

# User rules are stored in the user_rules table and enforced in DetectorRegistry

RULE_TYPES = {
    'trusted_domain':   'Skip all analysis for this domain',
    'suppressed_tactic': 'Never alert on this tactic type',
    'custom_pattern':   'Force-flag content matching this regex',
    'confidence_override': 'Change minimum confidence for a specific tactic',
    'severity_override': 'Change alert threshold for a specific domain',
}

RULE_ACTIONS = {
    'trust':         'Mark domain as trusted; skip analysis',
    'suppress':      'Remove tactic from results',
    'elevate':       'Force HIGH severity regardless of score',
    'min_conf_x':    'Set custom minimum confidence (value = float)',
}

17. Security Model & Threat Boundaries
17.1 Trust Zones

text

┌─────────────────────────────────────────┐
│  FULLY TRUSTED (localhost)              │
│  - Backend daemon (port 7330)           │
│  - Dashboard UI (port 7331)             │
│  - SQLite database (local file)         │
│  - Ollama LLM backend (port 11434)      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  SEMI-TRUSTED (browser extension)       │
│  - Content scripts read page DOM        │
│  - Send extracted text to localhost     │
│  - Render overlay into page DOM         │
│  - No network access except localhost   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  UNTRUSTED (web content)                │
│  - All page content treated as          │
│    potentially adversarial input        │
│  - Input sanitized before processing   │
│  - Regex patterns have match limits     │
└─────────────────────────────────────────┘

17.2 Dashboard Access Control

Python

# egoshield/api/middleware.py

from fastapi import Request, HTTPException
import ipaddress


def local_only_middleware(request: Request, call_next):
    client_ip = request.client.host
    try:
        addr = ipaddress.ip_address(client_ip)
        if not (addr.is_loopback or addr.is_link_local):
            raise HTTPException(status_code=403, detail='Dashboard is localhost only.')
    except ValueError:
        raise HTTPException(status_code=403, detail='Invalid client address.')
    return call_next(request)

17.3 Input Sanitization

All content received from the browser extension is treated as untrusted input:

Python

# egoshield/normalization/sanitizer.py

import re


MAX_TEXT_LENGTH = 50000
MAX_EVIDENCE_LENGTH = 500
MAX_URL_LENGTH = 2000

DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # No HTML execution
    r'javascript:',                 # No JS URIs
]


def sanitize_text_input(text: str) -> str:
    if not isinstance(text, str):
        return ''
    text = text[:MAX_TEXT_LENGTH]
    for pattern in DANGEROUS_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    return text


def sanitize_url(url: str) -> str:
    if not isinstance(url, str):
        return ''
    url = url[:MAX_URL_LENGTH]
    if not url.startswith(('http://', 'https://')):
        return ''
    return url

17.4 Threat Model Summary
Threat	Mitigation
Malicious page injecting commands via page text	Input sanitization; regex patterns have caps; LLM prompts use system/user separation
Dashboard exposed to network	LocalOnly middleware on all API routes
LLM prompt injection via page content	Evidence text capped at 500 chars; system prompt enforces evidence-only reasoning
Email credentials stolen	Stored in OS keychain; never in plaintext config
SQLite DB containing sensitive snippets	Local file only; configurable retention; full export/delete control
Extension capturing excessive page content	Hard cap at 50,000 chars; no full HTML storage
Regex catastrophic backtracking (ReDoS)	Patterns reviewed for ambiguity; re.timeout wrapper in Python 3.11+
18. Storage & Persistence
18.1 Database Connection

Python

# egoshield/storage/db.py

import sqlite3
import threading
from pathlib import Path


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._run_migrations()

    def _connect(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA journal_mode=WAL')      # Write-Ahead Logging for concurrency
            conn.execute('PRAGMA synchronous=NORMAL')    # Balance durability and speed
            conn.execute('PRAGMA foreign_keys=ON')
            self._local.conn = conn
        return self._local.conn

    def execute(self, sql: str, params: tuple = ()):
        conn = self._connect()
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._connect().execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._connect().execute(sql, params).fetchone()

    def _run_migrations(self):
        conn = self._connect()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        self._apply_migration(1, MIGRATION_001)

    def _apply_migration(self, version: int, sql: str):
        conn = self._connect()
        existing = conn.execute(
            'SELECT 1 FROM schema_migrations WHERE version = ?', (version,)
        ).fetchone()
        if not existing:
            conn.executescript(sql)
            conn.execute('INSERT INTO schema_migrations (version) VALUES (?)', (version,))
            conn.commit()

18.2 Domain Stats Repository

Python

# egoshield/storage/domain_stats_repo.py

import json
from .db import Database


class DomainStatsRepo:
    def __init__(self, db: Database):
        self.db = db

    def upsert_from_analysis(self, domain: str, score: float, tactics: dict):
        existing = self.db.fetchone(
            'SELECT * FROM domain_stats WHERE domain = ?', (domain,)
        )

        if not existing:
            tactic_counts = {t: 1 for t in tactics.keys()}
            self.db.execute('''
                INSERT INTO domain_stats
                (id, domain, analysis_count, avg_score, max_score, tactic_counts, trust_rating)
                VALUES (?, ?, 1, ?, ?, ?, 'neutral')
            ''', (self._new_id(), domain, score, score, json.dumps(tactic_counts)))
        else:
            n = existing['analysis_count']
            new_avg = ((existing['avg_score'] * n) + score) / (n + 1)
            new_max = max(existing['max_score'], score)

            existing_counts = json.loads(existing['tactic_counts'] or '{}')
            for tactic in tactics.keys():
                existing_counts[tactic] = existing_counts.get(tactic, 0) + 1

            trust_rating = self._compute_trust_rating(new_avg, n + 1)

            self.db.execute('''
                UPDATE domain_stats SET
                    analysis_count = ?,
                    avg_score = ?,
                    max_score = ?,
                    tactic_counts = ?,
                    trust_rating = ?,
                    last_seen = CURRENT_TIMESTAMP
                WHERE domain = ?
            ''', (n + 1, new_avg, new_max, json.dumps(existing_counts), trust_rating, domain))

    def _compute_trust_rating(self, avg_score: float, count: int) -> str:
        if count < 3:
            return 'neutral'
        if avg_score < 0.15:
            return 'trusted'
        elif avg_score < 0.40:
            return 'neutral'
        elif avg_score < 0.70:
            return 'suspicious'
        return 'hostile'

    def _new_id(self) -> str:
        import uuid
        return str(uuid.uuid4())

19. Logging, Observability & Debugging
19.1 Structured Logging

Python

# egoshield/logging/logger.py

import logging
import json
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'ts': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'msg': record.getMessage(),
        }
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        return json.dumps(log_entry)


def setup_logging(level: str = 'info', log_file: str = None):
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers = [logging.StreamHandler()]

    if log_file:
        from logging.handlers import RotatingFileHandler
        handlers.append(RotatingFileHandler(
            log_file, maxBytes=50 * 1024 * 1024, backupCount=3
        ))

    for handler in handlers:
        handler.setFormatter(StructuredFormatter())

    logging.basicConfig(level=numeric_level, handlers=handlers)

19.2 Key Log Events

text

INFO   [daemon.start]       Daemon started. Port: 7330. LLM: mistral @ localhost:11434
INFO   [analysis.complete]  domain=shop.example.com score=0.72 severity=HIGH tactics=4 ms=1840
WARN   [llm.unavailable]    Ollama not reachable at localhost:11434. Running without arbiter.
INFO   [llm.arbitrated]     analysis_id=abc123 pruned=1 validated=3
DEBUG  [detector.urgency]   Matched 3 patterns in headline. confidence=0.71
INFO   [alert.fired]        domain=promo.example.com severity=EXTREME overlay=true desktop=true
INFO   [domain.trusted]     domain=docs.python.org trusted=true by_user=true
INFO   [email.analyzed]     sender=promo@shop.com subject_score=0.82 body_score=0.54
WARN   [detector.error]     detector=GaslightingDetector error="timeout" skipped=true
INFO   [cleanup.run]        Deleted 234 analyses older than 90 days.

20. Testing Strategy
20.1 Test Pyramid

text

                    ┌──────────────┐
                    │   E2E (5%)   │
                    │  Playwright  │
                    │ (Extension   │
                    │  + Overlay)  │
                    └──────┬───────┘
              ┌────────────┴────────────┐
              │  Integration (25%)      │
              │  API + DB + LLM Mock    │
              └────────────┬────────────┘
         ┌─────────────────┴─────────────────┐
         │         Unit Tests (70%)          │
         │  Detectors, Scorer, Explainer,    │
         │  Normalization, Storage           │
         └───────────────────────────────────┘

20.2 Unit Tests — Detectors

Python

# tests/unit/test_urgency_detector.py

import pytest
from egoshield.detectors.linguistic.urgency import UrgencyDetector


@pytest.fixture
def detector():
    return UrgencyDetector()


def test_detects_act_now(detector):
    zones = {'headline': 'Act now — offer ends tonight!', 'body': '', 'cta_texts': ''}
    results = detector.detect(zones)
    assert len(results) == 1
    assert results[0].tactic_type == 'urgency'
    assert results[0].confidence > 0.5
    assert results[0].location_hint == 'headline'


def test_detects_limited_time(detector):
    zones = {'headline': '', 'body': 'This is a limited time offer. Hurry before it expires.', 'cta_texts': ''}
    results = detector.detect(zones)
    assert len(results) == 1
    assert results[0].confidence >= 0.40


def test_no_false_positive_on_neutral_text(detector):
    zones = {'headline': 'How to improve your Python skills', 'body': 'Here are ten tips for learning Python effectively.', 'cta_texts': ''}
    results = detector.detect(zones)
    assert len(results) == 0


def test_evidence_text_is_populated(detector):
    zones = {'headline': '', 'body': 'Act now and save 50% today only!', 'cta_texts': ''}
    results = detector.detect(zones)
    assert len(results) == 1
    assert len(results[0].evidence_text) > 0
    assert '...' in results[0].evidence_text  # Confirms snippet format


def test_high_density_elevates_severity(detector):
    zones = {
        'headline': 'Act now! Last chance! Today only! Hurry!',
        'body': 'Limited time. Expires tonight. Don\'t miss out. Time is running out.',
        'cta_texts': 'Buy now before it\'s too late'
    }
    results = detector.detect(zones)
    assert len(results) == 1
    assert results[0].severity in ('high', 'critical')

20.3 Unit Tests — Dark Pattern Detector

Python

# tests/unit/test_dark_patterns.py

from egoshield.detectors.ux.dark_patterns import DarkPatternDetector


def test_detects_pretick():
    dom = {
        'checkboxes': [
            {'label': 'Send me exclusive deals and newsletters', 'checked': True, 'name': 'marketing'}
        ],
        'buttons': [],
        'countdown_elements': [],
    }
    results = DarkPatternDetector().detect({}, dom)
    pre_ticks = [r for r in results if r.tactic_type == 'pre_ticked_checkbox']
    assert len(pre_ticks) == 1
    assert pre_ticks[0].confidence >= 0.80


def test_ignores_required_agreement_pretick():
    dom = {
        'checkboxes': [
            {'label': 'I agree to the Terms of Service', 'checked': True, 'name': 'tos'}
        ],
        'buttons': [],
        'countdown_elements': [],
    }
    results = DarkPatternDetector().detect({}, dom)
    pre_ticks = [r for r in results if r.tactic_type == 'pre_ticked_checkbox']
    assert len(pre_ticks) == 0  # ToS agreement is not a marketing opt-in


def test_detects_fake_countdown():
    dom = {
        'checkboxes': [],
        'buttons': [],
        'countdown_elements': [
            {'text': 'Offer ends in 04:32', 'has_timer': True, 'resets_on_reload': True}
        ],
    }
    results = DarkPatternDetector().detect({}, dom)
    fakes = [r for r in results if r.tactic_type == 'fake_countdown']
    assert len(fakes) == 1
    assert fakes[0].severity == 'critical'


def test_detects_confirm_shaming():
    dom = {
        'checkboxes': [],
        'buttons': [
            {'text': 'Accept all cookies', 'is_primary': True, 'type': 'button'},
            {'text': "No thanks, I don't want to save money", 'is_primary': False, 'type': 'button'},
        ],
        'countdown_elements': [],
    }
    results = DarkPatternDetector().detect({}, dom)
    shame = [r for r in results if r.tactic_type == 'confirm_shaming']
    assert len(shame) == 1


def test_detects_visual_misdirection():
    dom = {
        'buttons': [
            {'text': 'Accept all', 'is_primary': True, 'type': 'button'},
            {'text': 'Decline', 'is_primary': False, 'type': 'button'},
        ],
        'checkboxes': [],
        'countdown_elements': [],
    }
    results = DarkPatternDetector().detect({}, dom)
    misdirect = [r for r in results if r.tactic_type == 'visual_misdirection']
    assert len(misdirect) == 1

20.4 Unit Tests — Scorer

Python

# tests/unit/test_scorer.py

from egoshield.scoring.scorer import Scorer
from egoshield.detectors.base import TacticCandidate
from egoshield.llm.llm_arbiter import ArbitratedResult


def make_result(tactic_type, confidence):
    candidate = TacticCandidate(
        tactic_type=tactic_type,
        confidence=confidence,
        severity='medium',
        evidence_text='test evidence',
        explanation='test explanation',
        location_hint='body',
    )
    return ArbitratedResult(
        original=candidate,
        validated=True,
        adjusted_confidence=confidence,
        rewritten_explanation='test explanation',
        arbiter_reasoning='',
    )


def test_empty_input_returns_clean():
    result = Scorer().score([])
    assert result.severity == 'CLEAN'
    assert result.overall_score == 0.0


def test_single_high_confidence_tactic():
    results = [make_result('fear_induction', 0.90)]
    score = Scorer().score(results)
    assert score.severity == 'EXTREME'
    assert score.overall_score > 0.85


def test_stacking_increases_score():
    single = Scorer().score([make_result('urgency', 0.60)])
    stacked = Scorer().score([
        make_result('urgency', 0.60),
        make_result('false_scarcity', 0.60),
        make_result('fear_induction', 0.60),
    ])
    assert stacked.overall_score > single.overall_score


def test_invalidated_tactics_excluded():
    candidate = TacticCandidate('urgency', 0.90, 'high', 'evidence', 'explanation', 'body')
    invalidated = ArbitratedResult(
        original=candidate,
        validated=False,     # LLM said false positive
        adjusted_confidence=0.90,
        rewritten_explanation='',
        arbiter_reasoning='benign in context',
        invalidation_reason='Context indicates genuine time-sensitive offer',
    )
    result = Scorer().score([invalidated])
    assert result.severity == 'CLEAN'


def test_score_capped_at_1():
    results = [make_result(t, 0.99) for t in [
        'urgency', 'false_scarcity', 'fear_induction',
        'emotional_loading', 'manufactured_authority', 'loss_aversion'
    ]]
    score = Scorer().score(results)
    assert score.overall_score <= 1.0

20.5 Integration Tests — Analyze Endpoint

Python

# tests/integration/test_analyze_endpoint.py

import pytest
from httpx import AsyncClient
from egoshield.api.server import create_app


@pytest.fixture
async def client():
    app = create_app(test_mode=True)  # Uses in-memory SQLite, mock LLM
    async with AsyncClient(app=app, base_url='http://test') as c:
        yield c


@pytest.mark.asyncio
async def test_analyze_webpage_returns_result(client):
    response = await client.post('/api/v1/analyze', json={
        'source_type': 'webpage',
        'url': 'https://test.example.com/promo',
        'title': 'Special Offer',
        'text_content': 'Act now! Limited time offer. Only 3 left in stock! Don\'t miss out!',
        'dom_signals': {
            'buttons': [],
            'checkboxes': [],
            'countdown_elements': [],
        }
    })
    assert response.status_code == 200
    data = response.json()
    assert 'overall_score' in data
    assert data['overall_score'] > 0.3
    assert data['severity'] in ['MEDIUM', 'HIGH', 'EXTREME']
    assert len(data['tactics']) > 0


@pytest.mark.asyncio
async def test_analyze_clean_content(client):
    response = await client.post('/api/v1/analyze', json={
        'source_type': 'webpage',
        'url': 'https://docs.python.org/tutorial',
        'title': 'Python Tutorial',
        'text_content': 'This tutorial introduces the reader to the basic concepts and features of Python.',
        'dom_signals': {'buttons': [], 'checkboxes': [], 'countdown_elements': []}
    })
    assert response.status_code == 200
    data = response.json()
    assert data['severity'] == 'CLEAN'
    assert data['overall_score'] < 0.15


@pytest.mark.asyncio
async def test_evidence_text_always_present(client):
    response = await client.post('/api/v1/analyze', json={
        'source_type': 'webpage',
        'url': 'https://shop.example.com',
        'title': 'Sale',
        'text_content': 'Hurry! Sale ends at midnight! Last chance to save!',
        'dom_signals': {'buttons': [], 'checkboxes': [], 'countdown_elements': []}
    })
    data = response.json()
    for tactic in data.get('tactics', []):
        assert tactic['evidence_text'], 'Every tactic must have evidence text'
        assert len(tactic['evidence_text']) > 0

21. Build, Packaging & Installation
21.1 Makefile

Makefile

.PHONY: all install dev test lint clean build-extension build-dashboard

# Python backend
install:
	pip install -e ".[dev]"

dev:
	uvicorn egoshield.api.server:app --host 127.0.0.1 --port 7330 --reload &
	cd dashboard && npm run dev

# Tests
test:
	pytest tests/ -v --cov=egoshield --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v -m integration

# Lint
lint:
	ruff check egoshield/
	mypy egoshield/ --strict

# Dashboard (Svelte)
build-dashboard:
	cd dashboard && npm install && npm run build
	cp -r dashboard/dist/ egoshield/api/static/dashboard/

# Browser Extension
build-extension:
	cd extension && npm install && npm run build

# All
all: build-dashboard build-extension

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf dist/ dashboard/dist/ extension/dist/ .coverage

# Package
package: all
	python -m build
	# Produces dist/egoshield-1.0.0-py3-none-any.whl

# Install Ollama model (recommended)
setup-llm:
	ollama pull mistral
	@echo "Mistral model ready for EgoShield LLM arbiter."

21.2 pyproject.toml

toml

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "egoshield"
version = "1.0.0"
description = "Local-first cognitive firewall: real-time manipulation detection"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}

dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.7",
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "spacy>=3.7",
    "tomllib; python_version < '3.11'",
    "python-multipart>=0.0.9",
    "sse-starlette>=2.1",
    "apscheduler>=3.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "mypy>=1.10",
    "httpx>=0.27",
]

[project.scripts]
egoshield = "cmd.main:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = ["integration: integration tests requiring running backend"]

21.3 Installation Script

Bash

#!/bin/bash
# install.sh

set -e

EGOSHIELD_HOME="$HOME/.egoshield"
mkdir -p "$EGOSHIELD_HOME/logs" "$EGOSHIELD_HOME/data"

echo "🧠 Installing EgoShield..."

# Check Python version
python3 --version | grep -E "3\.1[1-9]" || {
    echo "❌ Python 3.11+ required"
    exit 1
}

# Install Python package
pip install egoshield

# Download spaCy model (used for NLP)
python3 -m spacy download en_core_web_sm

# Check Ollama
if command -v ollama &> /dev/null; then
    echo "✅ Ollama found. Pulling recommended model (mistral)..."
    ollama pull mistral
else
    echo "⚠️  Ollama not found. LLM arbiter will be disabled."
    echo "   Install from https://ollama.ai to enable AI-powered explanations."
fi

# Write default config
if [ ! -f "$EGOSHIELD_HOME/config.toml" ]; then
    egoshield --write-default-config
    echo "✅ Default config written to $EGOSHIELD_HOME/config.toml"
fi

echo ""
echo "✅ EgoShield installed."
echo ""
echo "Next steps:"
echo "  1. Run: egoshield start"
echo "  2. Dashboard: http://localhost:7331"
echo "  3. Install the browser extension from extension/dist/"
echo "  4. (Optional) Configure IMAP in $EGOSHIELD_HOME/config.toml"

22. Platform Support Matrix
Feature	macOS (Intel)	macOS (Apple Silicon)	Linux (amd64)	Linux (arm64)	Windows (amd64)
Backend daemon (Python)	✅	✅	✅	✅	✅
FastAPI + SQLite	✅	✅	✅	✅	✅
Browser extension (Chrome MV3)	✅	✅	✅	✅	✅
Browser extension (Firefox MV3)	✅	✅	✅	✅	✅
Dashboard UI	✅	✅	✅	✅	✅
Ollama LLM arbiter	✅	✅	✅	✅	✅
Desktop
