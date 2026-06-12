"""
EgoShield API Schemas
Pydantic models for request/response validation
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re


class AnalyzeRequest(BaseModel):
    """Request for content analysis"""
    url_hash: str = Field(..., description="SHA-256 hash of the full URL")
    domain: str = Field(..., description="eTLD+1 domain")
    content_type: str = Field(..., description="'page' or 'email'")
    content: str = Field(..., description="Pre-sanitized visible text")
    truncated: bool = Field(False, description="True if content was truncated")
    client_timestamp: Optional[str] = Field(None, description="ISO-8601 client timestamp")
    
    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v):
        if v not in ('page', 'email', 'other'):
            raise ValueError("content_type must be 'page', 'email', or 'other'")
        return v
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        # Basic domain validation
        if not v or len(v) < 3:
            raise ValueError("Invalid domain")
        return v.lower()


class TacticResult(BaseModel):
    """Individual tactic detection result"""
    detector_name: str
    tactic_name: str
    severity: float = Field(..., ge=0.0, le=1.0)
    evidence_phrases: List[str]
    explanation: Optional[str] = None


class AnalysisMeta(BaseModel):
    """Metadata about the analysis"""
    daemon_version: str
    analysis_duration_ms: int
    detectors_run: int
    detectors_timed_out: int


class AnalyzeResponse(BaseModel):
    """Response from content analysis"""
    analysis_id: str
    composite_score: float = Field(..., ge=0.0, le=1.0)
    severity_band: str
    partial_result: bool
    arbiter_tier: Optional[int] = None
    tactics: List[TacticResult]
    meta: AnalysisMeta


class RulesResponse(BaseModel):
    """Response containing user rules"""
    trusted_domains: List[str]
    suppressed_tactics: List[str]
    custom_patterns: List[str]


class HealthResponse(BaseModel):
    """Response from health check endpoint"""
    status: str  # 'healthy' or 'degraded'
    daemon_version: str
    uptime_seconds: int


class ReadyChecks(BaseModel):
    """Readiness check results"""
    sqlite: str  # 'ok' or 'error'
    detectors: str  # 'ok', 'partial', or 'error'
    ollama: str  # 'ok', 'unavailable', or 'error'


class ReadyResponse(BaseModel):
    """Response from readiness check endpoint"""
    ready: bool
    checks: ReadyChecks


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    code: str
    detail: Optional[str] = None


class HistoryEntry(BaseModel):
    """Analysis history entry"""
    analysis_id: str
    url_hash: str
    domain: str
    content_type: str
    composite_score: float
    severity_band: str
    tactic_count: int
    partial_result: bool
    arbiter_tier: Optional[int] = None
    created_at: str
    tactics: List[TacticResult]


class HistoryResponse(BaseModel):
    """Response containing analysis history"""
    analyses: List[HistoryEntry]
    total: int
    limit: int
    offset: int


class DashboardSummary(BaseModel):
    """Dashboard summary statistics"""
    total_analyses: int
    domain_stats: List[dict]
    recent_analyses: List[dict]
    tactic_distribution: List[dict]
    llm_status: dict
    detectors: List[dict]


class DiagnosticsExport(BaseModel):
    """Diagnostics export structure"""
    daemon_version: str
    timestamp: str
    uptime_seconds: int
    schema_version: str
    settings: dict
    metrics_summary: dict
    detector_versions: List[dict]
    ollama_status: dict


class SettingsUpdate(BaseModel):
    """Request to update a setting"""
    key: str
    value: str


class SettingsResponse(BaseModel):
    """Response containing all settings"""
    settings: dict


class RuleCreate(BaseModel):
    """Request to create a rule"""
    rule_type: str
    value: str
    notes: Optional[str] = None
    
    @field_validator('rule_type')
    @classmethod
    def validate_rule_type(cls, v):
        if v not in ('trusted_domain', 'suppress_tactic', 'custom_pattern'):
            raise ValueError("rule_type must be one of: trusted_domain, suppress_tactic, custom_pattern")
        return v


class RuleResponse(BaseModel):
    """Response for a rule operation"""
    id: str
    rule_type: str
    value: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str