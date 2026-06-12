# EgoShield Documentation

Welcome to the EgoShield documentation. This index will help you navigate the available guides.

---

## Getting Started

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview and quick start |
| [Developer Guide](developer-guide.md) | Setup and development workflow |

---

## Architecture

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System design and components |
| [API Reference](api.md) | REST API endpoint documentation |

---

## Security

| Document | Description |
|----------|-------------|
| [Security](security.md) | Security model and best practices |

---

## Extension

| Document | Description |
|----------|-------------|
| [Browser Extension](extension.md) | Extension installation and usage |

---

## Deployment

| Document | Description |
|----------|-------------|
| [Deployment Guide](deployment.md) | Production deployment instructions |

---

## Architecture Decision Records (ADRs)

| Document | Description |
|----------|-------------|
| [ADR-001: Local-First Architecture](adr-001-local-first-architecture.md) | Privacy-first design |
| [ADR-002: SQLite with WAL Mode](adr-002-sqlite-wal.md) | Database selection and configuration |
| [ADR-003: SHA-256 URL Hashing](adr-003-url-hashing.md) | Privacy-preserving URL storage |
| [ADR-004: Structured Logging](adr-004-structured-logging.md) | Logging format and rotation |
| [ADR-006: Dynamic Plugin Loading](adr-006-dynamic-plugins.md) | Extensibility system |

---

## Quick Reference

### Key Files

| File | Purpose |
|------|---------|
| `daemon/main.py` | CLI entry point |
| `daemon/detectors/base.py` | Base detector class |
| `daemon/api/routes.py` | API endpoints |
| `daemon/db/schema.sql` | Database schema |
| `extension/manifest.json` | Extension manifest |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EGOSHIELD_PORT` | 8765 | API port |
| `EGOSHIELD_HOST` | 127.0.0.1 | Bind address |
| `EGOSHIELD_DB_PATH` | auto | Database path |

### Ports

| Port | Service |
|------|---------|
| 8765 | Main API |
| 8766 | Dashboard |

---

## Support

- **Issues**: [GitHub Issues](https://github.com/knarayanareddy/egoshield/issues)
- **Discussions**: [GitHub Discussions](https://github.com/knarayanareddy/egoshield/discussions)
- **Email**: team@egoshield.local