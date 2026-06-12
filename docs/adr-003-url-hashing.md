# ADR-003: SHA-256 URL Hashing

**Status:** Accepted  
**Date:** 2024-01-15  
**Deciders:** EgoShield Team

---

## Context

EgoShield stores URLs to track analysis history per-page. We needed to decide how to store URLs:
- **Option A**: Raw URLs (privacy risk)
- **Option B**: Hashed URLs (privacy-preserving)
- **Option C**: Domain only (reduced utility)

---

## Decision

**We chose Option B: SHA-256 URL Hashing**

Raw URLs are never stored. Only their SHA-256 hashes.

```python
def compute_url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()
```

Result: 64-character hex string (256 bits)

---

## Rationale

### Privacy

- URLs may contain: tokens, session IDs, personal data, query parameters
- Example: `https://example.com/profile?user_id=123&token=abc`
- Storing raw URLs would expose this sensitive data

### Deduplication

- Same URL produces same hash
- We can track repeat visits without storing the URL

### Analytics

- Domain can be extracted from hash (stored separately in `domain` column)
- Aggregate statistics by domain are still possible

---

## Consequences

### Positive

- No sensitive data in database
- GDPR-compliant (no personal data stored)
- Audit-friendly (no URL to expose)

### Negative

- Cannot show user their original URL in history
- Cannot deep-link to analysis
- Domain extraction requires additional logic

---

## Implementation

### Storage Schema

```sql
CREATE TABLE analyses (
    url_hash TEXT NOT NULL,    -- SHA-256 hash
    domain TEXT NOT NULL,      -- eTLD+1, stored separately
    ...
);
```

### Domain Extraction

Domain is extracted during analysis and stored separately:

```python
from tldextract import extract

def extract_domain(url: str) -> str:
    _, domain, suffix = extract(url)
    return f"{domain}.{suffix}" if suffix else domain
```

### Display

History shows domain only, not full URL:

```json
{
  "url_hash": "abc123...",
  "domain": "example.com"
}
```

---

## Security Note

The hash is **not** encryption. It is one-way. If an attacker gains access to the database:
- They cannot recover original URLs
- They can only see domains and scores

---

## Related Decisions

- [ADR-001: Local-First Architecture](adr-001-local-first-architecture.md)