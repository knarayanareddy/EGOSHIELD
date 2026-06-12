"""
EgoShield Database Models
Pydantic models for database entities
"""

import json
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logging import log_event
import logging

logger = logging.getLogger(__name__)


class SeverityBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ContentType(str, Enum):
    PAGE = "page"
    EMAIL = "email"
    OTHER = "other"


class RuleType(str, Enum):
    TRUSTED_DOMAIN = "trusted_domain"
    SUPPRESS_TACTIC = "suppress_tactic"
    CUSTOM_PATTERN = "custom_pattern"


@dataclass
class Analysis:
    id: str
    url_hash: str
    domain: str
    content_type: str
    composite_score: float
    severity_band: str
    tactic_count: int
    partial_result: bool
    arbiter_tier: Optional[int]
    created_at: str
    expires_at: str
    
    @classmethod
    def from_row(cls, row) -> 'Analysis':
        return cls(
            id=row['id'],
            url_hash=row['url_hash'],
            domain=row['domain'],
            content_type=row['content_type'],
            composite_score=row['composite_score'],
            severity_band=row['severity_band'],
            tactic_count=row['tactic_count'],
            partial_result=bool(row['partial_result']),
            arbiter_tier=row['arbiter_tier'],
            created_at=row['created_at'],
            expires_at=row['expires_at']
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url_hash": self.url_hash,
            "domain": self.domain,
            "content_type": self.content_type,
            "composite_score": self.composite_score,
            "severity_band": self.severity_band,
            "tactic_count": self.tactic_count,
            "partial_result": self.partial_result,
            "arbiter_tier": self.arbiter_tier,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }


@dataclass
class Tactic:
    id: str
    analysis_id: str
    detector_name: str
    tactic_name: str
    severity: float
    evidence_phrases: List[str]
    explanation: Optional[str]
    created_at: str
    
    @classmethod
    def from_row(cls, row) -> 'Tactic':
        evidence = row['evidence_phrases']
        if isinstance(evidence, str):
            evidence = json.loads(evidence)
        return cls(
            id=row['id'],
            analysis_id=row['analysis_id'],
            detector_name=row['detector_name'],
            tactic_name=row['tactic_name'],
            severity=row['severity'],
            evidence_phrases=evidence,
            explanation=row['explanation'],
            created_at=row['created_at']
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "detector_name": self.detector_name,
            "tactic_name": self.tactic_name,
            "severity": self.severity,
            "evidence_phrases": self.evidence_phrases,
            "explanation": self.explanation,
            "created_at": self.created_at
        }


@dataclass
class UserRule:
    id: str
    rule_type: str
    value: str
    notes: Optional[str]
    created_at: str
    updated_at: str
    
    @classmethod
    def from_row(cls, row) -> 'UserRule':
        return cls(
            id=row['id'],
            rule_type=row['rule_type'],
            value=row['value'],
            notes=row['notes'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_type": self.rule_type,
            "value": self.value,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class DomainStats:
    domain: str
    total_analyses: int
    avg_composite_score: float
    last_seen_at: str
    updated_at: str
    
    @classmethod
    def from_row(cls, row) -> 'DomainStats':
        return cls(
            domain=row['domain'],
            total_analyses=row['total_analyses'],
            avg_composite_score=row['avg_composite_score'],
            last_seen_at=row['last_seen_at'],
            updated_at=row['updated_at']
        )
    
    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "total_analyses": self.total_analyses,
            "avg_composite_score": self.avg_composite_score,
            "last_seen_at": self.last_seen_at,
            "updated_at": self.updated_at
        }


@dataclass
class Settings:
    key: str
    value: str
    updated_at: str
    
    @classmethod
    def from_row(cls, row) -> 'Settings':
        return cls(
            key=row['key'],
            value=row['value'],
            updated_at=row['updated_at']
        )
    
    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at
        }


@dataclass
class Metric:
    id: str
    event_type: str
    value_ms: Optional[float]
    value_int: Optional[int]
    metadata: Optional[dict]
    created_at: str
    
    @classmethod
    def from_row(cls, row) -> 'Metric':
        metadata = row['metadata']
        if metadata and isinstance(metadata, str):
            metadata = json.loads(metadata)
        return cls(
            id=row['id'],
            event_type=row['event_type'],
            value_ms=row['value_ms'],
            value_int=row['value_int'],
            metadata=metadata,
            created_at=row['created_at']
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "value_ms": self.value_ms,
            "value_int": self.value_int,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


class AnalysisRepository:
    """Repository for analysis operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, data: dict) -> Analysis:
        """Create a new analysis record"""
        with self.db.get_connection() as conn:
            # Calculate expires_at based on retention_days
            retention_days = data.get('retention_days', 90)
            # Handle negative retention (for testing expired records)
            if retention_days < 0:
                expires_at = "1970-01-01 00:00:00"  # Far in the past
            else:
                # SQLite string concatenation for interval
                expires_at = conn.execute(
                    "SELECT datetime('now', '+' || ? || ' days')",
                    (retention_days,)
                ).fetchone()[0]
            
            cursor = conn.execute("""
                INSERT INTO analyses (
                    url_hash, domain, content_type, composite_score,
                    severity_band, tactic_count, partial_result, arbiter_tier, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['url_hash'],
                data['domain'],
                data['content_type'],
                data['composite_score'],
                data['severity_band'],
                data['tactic_count'],
                1 if data.get('partial_result') else 0,
                data.get('arbiter_tier'),
                expires_at
            ))
            
            # Fetch the row - use a separate query to ensure we get the data
            row = conn.execute(
                "SELECT * FROM analyses WHERE url_hash = ? ORDER BY created_at DESC LIMIT 1",
                (data['url_hash'],)
            ).fetchone()
            
            if not row:
                raise RuntimeError("Failed to create analysis record")
            
            log_event(logger, "INFO", "analysis_created", {
                "analysis_id": row['id'],
                "domain": row['domain'],
                "composite_score": row['composite_score']
            })
            
            return Analysis.from_row(row)
    
    def get_by_id(self, analysis_id: str) -> Optional[Analysis]:
        """Get analysis by ID"""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM analyses WHERE id = ?",
                (analysis_id,)
            ).fetchone()
            return Analysis.from_row(row) if row else None
    
    def get_by_domain(self, domain: str, limit: int = 50, offset: int = 0) -> List[Analysis]:
        """Get analyses by domain"""
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM analyses WHERE domain = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (domain, limit, offset)).fetchall()
            return [Analysis.from_row(r) for r in rows]
    
    def get_recent(self, limit: int = 50, offset: int = 0) -> List[Analysis]:
        """Get recent analyses"""
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM analyses ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            return [Analysis.from_row(r) for r in rows]
    
    def count(self) -> int:
        """Get total analysis count"""
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM analyses").fetchone()
            return row['count']


class TacticRepository:
    """Repository for tactic operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, analysis_id: str, data: dict) -> Tactic:
        """Create a new tactic record"""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO tactics (
                    analysis_id, detector_name, tactic_name,
                    severity, evidence_phrases, explanation
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                analysis_id,
                data['detector_name'],
                data['tactic_name'],
                data['severity'],
                json.dumps(data['evidence_phrases']),
                data.get('explanation')
            ))
            
            # Fetch the newly created tactic
            row = conn.execute(
                "SELECT * FROM tactics WHERE analysis_id = ? ORDER BY created_at DESC LIMIT 1",
                (analysis_id,)
            ).fetchone()
            
            if not row:
                raise RuntimeError("Failed to create tactic record")
            
            return Tactic.from_row(row)
    
    def get_by_analysis(self, analysis_id: str) -> List[Tactic]:
        """Get tactics for an analysis"""
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM tactics WHERE analysis_id = ?
            """, (analysis_id,)).fetchall()
            return [Tactic.from_row(r) for r in rows]


class RulesRepository:
    """Repository for user rules operations"""
    
    def __init__(self, db):
        self.db = db
    
    def create(self, data: dict) -> UserRule:
        """Create a new rule"""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO user_rules (rule_type, value, notes)
                VALUES (?, ?, ?)
            """, (data['rule_type'], data['value'], data.get('notes')))
            
            # Fetch the newly created rule
            row = conn.execute(
                "SELECT * FROM user_rules WHERE rule_type = ? AND value = ? ORDER BY created_at DESC LIMIT 1",
                (data['rule_type'], data['value'])
            ).fetchone()
            
            if not row:
                raise RuntimeError("Failed to create user rule")
            
            return UserRule.from_row(row)
    
    def get_all(self) -> List[UserRule]:
        """Get all rules"""
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM user_rules").fetchall()
            return [UserRule.from_row(r) for r in rows]
    
    def get_by_type(self, rule_type: str) -> List[UserRule]:
        """Get rules by type"""
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM user_rules WHERE rule_type = ?
            """, (rule_type,)).fetchall()
            return [UserRule.from_row(r) for r in rows]
    
    def delete(self, rule_id: str) -> bool:
        """Delete a rule"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM user_rules WHERE id = ?",
                (rule_id,)
            )
            return cursor.rowcount > 0
    
    def get_rules_dict(self) -> dict:
        """Get all rules as a structured dict"""
        rules = self.get_all()
        return {
            "trusted_domains": [r.value for r in rules if r.rule_type == RuleType.TRUSTED_DOMAIN.value],
            "suppressed_tactics": [r.value for r in rules if r.rule_type == RuleType.SUPPRESS_TACTIC.value],
            "custom_patterns": [r.value for r in rules if r.rule_type == RuleType.CUSTOM_PATTERN.value]
        }


class SettingsRepository:
    """Repository for settings operations"""
    
    def __init__(self, db):
        self.db = db
    
    def get(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            return row['value'] if row else default
    
    def set(self, key: str, value: str):
        """Set a setting value"""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, datetime('now'))
            """, (key, value))
            
            log_event(logger, "INFO", "setting_updated", {
                "key": key,
                "value": value  # Never log sensitive values
            })
    
    def get_all(self) -> dict:
        """Get all settings as a dict"""
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {row['key']: row['value'] for row in rows}
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer setting"""
        return int(self.get(key, str(default)))
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float setting"""
        return float(self.get(key, str(default)))
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting"""
        val = self.get(key, str(default).lower())
        return val.lower() in ('true', '1', 'yes')


class MetricsRepository:
    """Repository for metrics operations"""
    
    def __init__(self, db):
        self.db = db
    
    def record(self, event_type: str, value_ms: float = None, 
               value_int: int = None, metadata: dict = None):
        """Record a metric"""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO metrics (event_type, value_ms, value_int, metadata)
                VALUES (?, ?, ?, ?)
            """, (event_type, value_ms, value_int, json.dumps(metadata) if metadata else None))
    
    def get_recent(self, event_type: str = None, limit: int = 100) -> List[Metric]:
        """Get recent metrics"""
        with self.db.get_connection() as conn:
            if event_type:
                rows = conn.execute("""
                    SELECT * FROM metrics WHERE event_type = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (event_type, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM metrics ORDER BY created_at DESC LIMIT ?
                """, (limit,)).fetchall()
            return [Metric.from_row(r) for r in rows]
    
    def get_stats(self, event_type: str, hours: int = 24) -> dict:
        """Get statistics for an event type"""
        with self.db.get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    AVG(value_ms) as avg_ms,
                    MIN(value_ms) as min_ms,
                    MAX(value_ms) as max_ms
                FROM metrics
                WHERE event_type = ?
                AND created_at > datetime('now', '-' || ? || ' hours')
            """, (event_type, hours)).fetchone()
            
            return {
                "count": row['count'],
                "avg_ms": row['avg_ms'],
                "min_ms": row['min_ms'],
                "max_ms": row['max_ms']
            }


class DomainStatsRepository:
    """Repository for domain statistics"""
    
    def __init__(self, db):
        self.db = db
    
    def update(self, domain: str, composite_score: float):
        """Update or create domain stats"""
        with self.db.get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM domain_stats WHERE domain = ?",
                (domain,)
            ).fetchone()
            
            if existing:
                new_total = existing['total_analyses'] + 1
                new_avg = ((existing['avg_composite_score'] * existing['total_analyses']) + composite_score) / new_total
                
                conn.execute("""
                    UPDATE domain_stats
                    SET total_analyses = ?, avg_composite_score = ?,
                        last_seen_at = datetime('now'), updated_at = datetime('now')
                    WHERE domain = ?
                """, (new_total, new_avg, domain))
            else:
                conn.execute("""
                    INSERT INTO domain_stats (domain, total_analyses, avg_composite_score)
                    VALUES (?, 1, ?)
                """, (domain, composite_score))
    
    def get_all(self) -> List[DomainStats]:
        """Get all domain stats"""
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM domain_stats ORDER BY total_analyses DESC").fetchall()
            return [DomainStats.from_row(r) for r in rows]
    
    def get(self, domain: str) -> Optional[DomainStats]:
        """Get stats for a specific domain"""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM domain_stats WHERE domain = ?",
                (domain,)
            ).fetchone()
            return DomainStats.from_row(row) if row else None