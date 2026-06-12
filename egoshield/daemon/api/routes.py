"""
EgoShield API Routes
FastAPI router with all endpoint definitions
"""

import time
import logging
from typing import Optional
from datetime import datetime
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse

from .schemas import (
    AnalyzeRequest, AnalyzeResponse, RulesResponse,
    HealthResponse, ReadyResponse, ErrorResponse,
    HistoryResponse, HistoryEntry, TacticResult,
    SettingsUpdate, SettingsResponse, RuleCreate, RuleResponse
)

logger = logging.getLogger(__name__)

# Rate limiting state with sliding window
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # requests per window


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter that automatically expires old requests.
    Thread-safe implementation.
    """
    
    def __init__(self, window_seconds: int = 60, max_requests: int = 10):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._requests: dict = defaultdict(list)
        self._lock = Lock()
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if a client is allowed to make a request."""
        current_time = time.time()
        
        with self._lock:
            # Clean up old requests outside the window
            cutoff_time = current_time - self.window_seconds
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id]
                if req_time > cutoff_time
            ]
            
            # Check if under limit
            if len(self._requests[client_id]) >= self.max_requests:
                return False
            
            # Record this request
            self._requests[client_id].append(current_time)
            return True
    
    def get_count(self, client_id: str) -> int:
        """Get current request count for a client."""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        with self._lock:
            return len([
                req_time for req_time in self._requests.get(client_id, [])
                if req_time > cutoff_time
            ])
    
    def reset(self, client_id: str = None):
        """Reset rate limit for a client or all clients."""
        with self._lock:
            if client_id:
                self._requests.pop(client_id, None)
            else:
                self._requests.clear()


# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter(
    window_seconds=RATE_LIMIT_WINDOW,
    max_requests=RATE_LIMIT_MAX
)


def check_rate_limit(client_id: str) -> bool:
    """Check and update rate limit for a client using sliding window."""
    return rate_limiter.is_allowed(client_id)


def get_client_id(request: Request, x_egoshield_client: str = Header(None)) -> str:
    """Get client identifier from headers"""
    if x_egoshield_client:
        return x_egoshield_client
    return request.client.host if request.client else "unknown"


# Create router
router = APIRouter(prefix="/api/v2", tags=["analysis"])

# Additional routers for other endpoints
health_router = APIRouter(tags=["health"])
settings_router = APIRouter(prefix="/api/v2/settings", tags=["settings"])
rules_router = APIRouter(prefix="/api/v2/rules", tags=["rules"])
dashboard_router = APIRouter(prefix="/api/v2", tags=["dashboard"])

# Global service references (set in main.py)
analysis_service = None
rules_service = None
settings_service = None
db = None
_start_time = None


def set_services(analysis=None, rules=None, settings=None, database=None):
    """Set service references"""
    global analysis_service, rules_service, settings_service, db
    if analysis:
        analysis_service = analysis
    if rules:
        rules_service = rules
    if settings:
        settings_service = settings
    if database:
        db = database


def set_start_time(start_time):
    """Set the daemon start time for uptime calculation"""
    global _start_time
    _start_time = start_time


def get_daemon_version() -> str:
    """Get daemon version"""
    return "2.0.0"


# ============================================================
# Analysis Endpoints
# ============================================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_content(
    request: Request,
    body: AnalyzeRequest,
    x_egoshield_client: Optional[str] = Header(None)
):
    """
    Analyze content for manipulation patterns.
    
    POST /api/v2/analyze
    """
    global analysis_service
    
    if not analysis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Rate limiting with sliding window
    client_id = get_client_id(request, x_egoshield_client)
    if not check_rate_limit(client_id):
        current_count = rate_limiter.get_count(client_id)
        logger.warning(
            "rate_limit_triggered",
            extra={'event': 'rate_limit_triggered', 'data': {
                'client_header': x_egoshield_client,
                'requests_per_min': current_count
            }}
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX} requests/minute."
        )
    
    # Check if domain is trusted
    if analysis_service.is_domain_trusted(body.domain):
        return AnalyzeResponse(
            analysis_id="trusted",
            composite_score=0.0,
            severity_band="LOW",
            partial_result=False,
            arbiter_tier=None,
            tactics=[],
            meta={
                "daemon_version": get_daemon_version(),
                "analysis_duration_ms": 0,
                "detectors_run": 0,
                "detectors_timed_out": 0
            }
        )
    
    # Content size check
    max_size = settings_service.get_int('max_content_bytes', 50000) if settings_service else 50000
    if len(body.content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"Content exceeds maximum size of {max_size} bytes"
        )
    
    try:
        # Run analysis
        result = await analysis_service.analyze(
            content=body.content,
            url=body.url_hash,  # Already hashed by extension
            domain=body.domain,
            content_type=body.content_type,
            client_timestamp=body.client_timestamp
        )
        
        return AnalyzeResponse(
            analysis_id=result.analysis_id,
            composite_score=result.composite_score,
            severity_band=result.severity_band,
            partial_result=result.partial_result,
            arbiter_tier=result.arbiter_tier,
            tactics=[TacticResult(**t) for t in result.tactics],
            meta=result.meta
        )
        
    except Exception as e:
        logger.error(
            "analysis_error",
            extra={'event': 'analysis_error', 'data': {
                'domain': body.domain,
                'error': str(e)
            }}
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Rules Endpoints
# ============================================================

@rules_router.get("/", response_model=RulesResponse)
async def get_rules():
    """
    Get all user rules.
    
    GET /api/v2/rules
    """
    global rules_service
    
    if not rules_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    rules = rules_service.get_rules_dict()
    return RulesResponse(**rules)


@rules_router.post("/", response_model=RuleResponse)
async def create_rule(rule: RuleCreate):
    """
    Create a new rule.
    
    POST /api/v2/rules
    """
    global rules_service
    
    if not rules_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        if rule.rule_type == 'trusted_domain':
            result = rules_service.add_trusted_domain(rule.value, rule.notes)
        elif rule.rule_type == 'suppress_tactic':
            result = rules_service.add_suppressed_tactic(rule.value, rule.notes)
        else:
            result = rules_service.add_custom_pattern(rule.value, rule.notes)
        
        return RuleResponse(
            id=result.id,
            rule_type=result.rule_type,
            value=result.value,
            notes=result.notes,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rules_router.delete("/{rule_id}")
async def delete_rule(rule_id: str):
    """
    Delete a rule.
    
    DELETE /api/v2/rules/{rule_id}
    """
    global rules_service, db
    
    if not rules_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    with db.get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM user_rules WHERE id = ?",
            (rule_id,)
        )
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"deleted": True}


# ============================================================
# Settings Endpoints
# ============================================================

@settings_router.get("/", response_model=SettingsResponse)
async def get_settings():
    """
    Get all settings.
    
    GET /api/v2/settings
    """
    global settings_service
    
    if not settings_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return SettingsResponse(settings=settings_service.get_all())


@settings_router.put("/")
async def update_setting(update: SettingsUpdate):
    """
    Update a setting.
    
    PUT /api/v2/settings
    """
    global settings_service
    
    if not settings_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        settings_service.set(update.key, update.value)
        return {"updated": True, "key": update.key}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@settings_router.post("/reset")
async def reset_settings():
    """
    Reset all settings to defaults.
    
    POST /api/v2/settings/reset
    """
    global settings_service
    
    if not settings_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    settings_service.reset_to_defaults()
    return {"reset": True}


# ============================================================
# Health Endpoints
# ============================================================

@health_router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    GET /health
    Returns daemon health status.
    """
    global analysis_service, db, _start_time
    
    status = "healthy"
    
    # Check SQLite
    try:
        if not db.health_check():
            status = "degraded"
    except Exception:
        status = "degraded"
    
    # Check Ollama
    if analysis_service and analysis_service.llm_arbiter.health_status.value != "healthy":
        status = "degraded"
    
    # Calculate uptime
    uptime_seconds = int(time.time() - _start_time) if _start_time else 0
    
    return HealthResponse(
        status=status,
        daemon_version=get_daemon_version(),
        uptime_seconds=uptime_seconds
    )


@health_router.get("/ready", response_model=ReadyResponse)
async def ready_check():
    """
    Readiness check endpoint.
    
    GET /ready
    Returns detailed readiness status.
    """
    global analysis_service, db
    
    checks = {
        "sqlite": "ok",
        "detectors": "ok",
        "ollama": "unavailable"
    }
    
    ready = True
    
    # Check SQLite
    try:
        if not db.health_check():
            checks["sqlite"] = "error"
            ready = False
    except Exception:
        checks["sqlite"] = "error"
        ready = False
    
    # Check detectors
    if analysis_service:
        timed_out_count = 0
        for name, count in analysis_service.detection_pool.error_counts.items():
            if count > 3:
                timed_out_count += 1
        
        if timed_out_count > 0:
            checks["detectors"] = "partial"
            ready = False
        
        # Check Ollama
        if analysis_service.llm_arbiter.health_status.value == "healthy":
            checks["ollama"] = "ok"
        elif analysis_service.llm_arbiter.health_status.value == "degraded":
            checks["ollama"] = "error"
            ready = False
        # unavailable is not a failure (graceful degradation)
    
    return ReadyResponse(
        ready=ready,
        checks=checks
    )


# ============================================================
# Dashboard Endpoints
# ============================================================

@dashboard_router.get("/history")
async def get_history(
    limit: int = 50,
    offset: int = 0,
    domain: Optional[str] = None
):
    """
    Get analysis history.
    
    GET /api/v2/history
    """
    global analysis_service
    
    if not analysis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    history = analysis_service.get_analysis_history(limit, offset, domain)
    
    entries = []
    for item in history:
        entry = item['analysis']
        entry['tactics'] = [
            TacticResult(
                detector_name=t['detector_name'],
                tactic_name=t['tactic_name'],
                severity=t['severity'],
                evidence_phrases=t['evidence_phrases'],
                explanation=t['explanation']
            )
            for t in item['tactics']
        ]
        entries.append(entry)
    
    total = analysis_service.analysis_repo.count()
    
    return {
        "analyses": entries,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@dashboard_router.get("/dashboard")
async def get_dashboard():
    """
    Get dashboard summary.
    
    GET /api/v2/dashboard
    """
    global analysis_service
    
    if not analysis_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return analysis_service.get_dashboard_summary()


@dashboard_router.get("/diagnostics")
async def get_diagnostics():
    """
    Get diagnostics for export.
    
    GET /api/v2/diagnostics
    """
    global analysis_service, settings_service, db, _start_time
    
    if not analysis_service or not settings_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Get schema version
    schema_version = db.get_schema_version()
    
    # Get metrics summary
    from ..db.models import MetricsRepository
    metrics_repo = MetricsRepository(db)
    metrics_stats = {}
    for event_type in ['analysis_latency', 'detector_latency', 'arbiter_fallback']:
        metrics_stats[event_type] = metrics_repo.get_stats(event_type, hours=24)
    
    return {
        "daemon_version": get_daemon_version(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": int(time.time() - _start_time) if _start_time else 0,
        "schema_version": schema_version,
        "settings": settings_service.export_settings(),
        "metrics_summary": metrics_stats,
        "detector_versions": [
            {"name": d.name, "version": d.version, "timeout_ms": d.timeout_ms}
            for d in analysis_service.detection_pool.detectors
        ],
        "ollama_status": analysis_service.llm_arbiter.get_status_dict()
    }


# ============================================================
# Error Handlers (on app level, not router level)
# ============================================================
# Note: Exception handlers should be registered on the FastAPI app instance
# in main.py, not on the router. The router does not support exception_handler.