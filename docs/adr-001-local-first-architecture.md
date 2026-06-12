# ADR-001: Local-First Architecture

**Status:** Accepted  
**Date:** 2024-01-15  
**Deciders:** EgoShield Team

---

## Context

EgoShield must process sensitive web content and emails to detect manipulation tactics. We needed to decide whether to:
- **Option A**: Process everything locally (local-first)
- **Option B**: Send content to a cloud service
- **Option C**: Hybrid approach (local + cloud fallback)

---

## Decision

**We chose Option A: Local-First Architecture**

All content processing happens on the user's local machine. No data is transmitted to external servers.

---

## Rationale

### Privacy

- Users should not need to trust a third party with their browsing data
- Content may include sensitive information (medical, financial, personal)
- GDPR/compliance concerns with cloud processing

### Performance

- No network latency for analysis
- Works offline
- Instant feedback for inline annotations

### Trust

- Users can audit the code
- No dependency on service availability
- No subscription required

### Security

- Reduced attack surface (no external API)
- No data exfiltration risk
- Easier to secure a single local service vs distributed system

---

## Consequences

### Positive

- Complete privacy for user data
- Works in airplane mode / low connectivity
- No subscription or API costs
- User has full control

### Negative

- Limited to local processing power
- No collaborative features (shared blocklists, etc.)
- Must bundle ML models or use local LLMs

---

## Implementation

### Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Browser        │────▶│  EgoShield      │
│  Extension      │     │  Daemon         │
│                 │     │  (Local)        │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  SQLite DB      │
                        │  (Local File)   │
                        └─────────────────┘
```

### Data Storage

- **Analyses**: Metadata only, no content
- **URLs**: SHA-256 hashes only
- **Evidence**: Extracted phrases, not full text
- **Logs**: Redacted, structured, rotated

---

## Related Decisions

- [ADR-002: SQLite with WAL Mode](adr-002-sqlite-wal.md)
- [ADR-003: SHA-256 URL Hashing](adr-003-url-hashing.md)