"""
EgoShield Analysis Service
Main service orchestrating content analysis
"""

import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

from ..db.connection import Database
from ..db.models import (
    AnalysisRepository, TacticRepository, DomainStatsRepository,
    MetricsRepository, SettingsRepository
)
from ..detectors.base import DetectionPool, NormalizedContent, TacticResult
from ..detectors import DETECTOR_REGISTRY, DetectorBase, get_plugin_manager
from ..scoring.engine import ScoringEngine
from ..arbiter.ollama import OllamaArbiter, ArbiterResponse
from ..utils.content import ContentNormalizer
from ..utils.logging import log_event
from ..utils.security import compute_url_hash, extract_domain

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of a content analysis"""
    analysis_id: str
    composite_score: float
    severity_band: str
    partial_result: bool
    arbiter_tier: Optional[int]
    tactics: List[Dict]
    meta: Dict


class AnalysisService:
    """
    Main service for content analysis.
    
    Orchestrates:
    - Content normalization
    - Detection pipeline (built-in + plugins)
    - Scoring
    - LLM arbiter (optional)
    - Persistence
    """
    
    def __init__(self, db: Database):
        self.db = db
        
        # Initialize repositories
        self.analysis_repo = AnalysisRepository(db)
        self.tactic_repo = TacticRepository(db)
        self.domain_stats_repo = DomainStatsRepository(db)
        self.metrics_repo = MetricsRepository(db)
        self.settings_repo = SettingsRepository(db)
        
        # Initialize content normalizer
        max_content = self.settings_repo.get_int('max_content_bytes', 50000)
        self.normalizer = ContentNormalizer(max_content)
        
        # Initialize detection pool
        max_workers = 4
        self.detection_pool = DetectionPool(max_workers)
        
        # Configure and load plugins (ADR-006)
        self._configure_plugins()
        
        # Register all detectors (built-in + plugins)
        self._register_detectors()
        
        # Initialize scoring engine
        self.scoring_engine = ScoringEngine(self._get_detector_instances())
        
        # Initialize LLM arbiter
        llm_timeout = self.settings_repo.get_int('llm_timeout_ms', 8000)
        self.llm_arbiter = OllamaArbiter(default_timeout_ms=llm_timeout)
        
        # Get settings
        self.llm_threshold = self.settings_repo.get_float('llm_threshold', 0.30)
        self.retention_days = self.settings_repo.get_int('retention_days', 90)
    
    def _configure_plugins(self):
        """Configure the plugin system based on settings"""
        plugin_manager = get_plugin_manager()
        
        plugins_enabled = self.settings_repo.get_bool('plugins_enabled', False)
        plugins_path = self.settings_repo.get('plugins_path')
        
        if plugins_enabled:
            plugin_manager.configure(enabled=True, plugins_path=plugins_path)
            logger.info(f"Plugin system enabled, path: {plugin_manager.get_plugins_path()}")
            
            # Log plugin status for observability
            plugin_status = plugin_manager.get_status_dict()
            log_event(logger, "INFO", "plugins_configured", plugin_status)
        else:
            plugin_manager.configure(enabled=False)
            logger.info("Plugin system disabled")
    
    def _register_detectors(self):
        """Register all available detectors with the pool"""
        # Register built-in detectors
        for name, detector_class in DETECTOR_REGISTRY.items():
            detector = detector_class()
            self.detection_pool.register(detector)
        
        # Register plugin detectors
        plugin_manager = get_plugin_manager()
        if plugin_manager.is_enabled():
            try:
                plugin_instances = plugin_manager.instantiate_plugins()
                for plugin in plugin_instances:
                    self.detection_pool.register(plugin)
                    logger.info(f"Registered plugin detector: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to register plugin detectors: {e}")
    
    def _get_detector_instances(self) -> Dict[str, DetectorBase]:
        """Get instances of all registered detectors"""
        instances = {}
        for detector in self.detection_pool.detectors:
            instances[detector.name] = detector
        return instances
    
    async def initialize(self):
        """Initialize async components"""
        await self.llm_arbiter.initialize()
    
    async def close(self):
        """Close async components"""
        await self.llm_arbiter.close()
    
    async def analyze(
        self,
        content: str,
        url: str,
        domain: str,
        content_type: str,
        client_timestamp: Optional[str] = None
    ) -> AnalysisResult:
        """
        Analyze content for manipulation patterns.
        
        Args:
            content: Raw text content
            url: Full URL of the page (for hashing)
            domain: eTLD+1 domain
            content_type: Type of content ('page' or 'email')
            client_timestamp: Optional client timestamp
            
        Returns:
            AnalysisResult with score, tactics, and metadata
        """
        start_time = time.time()
        detector_times = {}
        
        # Normalize content
        normalized = self.normalizer.normalize(content)
        
        # Run detection pipeline
        # Note: DetectionPool.run_all now handles timing internally
        tactic_results, timed_out = self.detection_pool.run_all(
            normalized,
            timeout_ms=self.settings_repo.get_int('detector_timeout_ms', 2000)
        )
        
        partial_result = len(timed_out) > 0
        
        # Record individual detector latencies (sampled)
        # Since we run in parallel, we record approximate times
        analysis_duration = time.time() - start_time
        avg_detector_time = (analysis_duration * 1000) / max(len(self.detection_pool.detectors), 1)
        for detector in self.detection_pool.detectors:
            detector_times[detector.name] = avg_detector_time
        
        # Compute composite score
        composite_score, severity_band, tactic_count = self.scoring_engine.compute_composite_score(
            tactic_results,
            partial_result
        )
        
        # Check for suppressed tactics
        suppressed = self._get_suppressed_tactics()
        tactic_results = [t for t in tactic_results if t.tactic_name not in suppressed]
        
        # Generate explanation with arbiter
        arbiter_tier = None
        explanations = {}
        arbiter_latency_ms = None
        
        if tactic_results and composite_score >= self.llm_threshold:
            arbiter_response = await self.llm_arbiter.generate_explanation(
                composite_score,
                severity_band,
                tactic_results,
                threshold=self.llm_threshold
            )
            arbiter_tier = arbiter_response.tier.value
            arbiter_latency_ms = arbiter_response.latency_ms
            
            # Assign explanations to tactics (use highest severity's explanation for all)
            top_explanation = arbiter_response.explanation
            for tactic in tactic_results:
                explanations[tactic.tactic_name] = top_explanation
        
        # Create URL hash (never store raw URL)
        url_hash = compute_url_hash(url)
        
        # Persist analysis
        analysis = self.analysis_repo.create({
            'url_hash': url_hash,
            'domain': domain,
            'content_type': content_type,
            'composite_score': composite_score,
            'severity_band': severity_band,
            'tactic_count': tactic_count,
            'partial_result': partial_result,
            'arbiter_tier': arbiter_tier,
            'retention_days': self.retention_days
        })
        
        # Persist tactics
        for tactic_result in tactic_results:
            self.tactic_repo.create(analysis.id, {
                'detector_name': tactic_result.detector_name,
                'tactic_name': tactic_result.tactic_name,
                'severity': tactic_result.severity,
                'evidence_phrases': tactic_result.evidence_phrases,
                'explanation': explanations.get(tactic_result.tactic_name)
            })
        
        # Update domain stats
        self.domain_stats_repo.update(domain, composite_score)
        
        # Record metrics with proper values
        duration_ms = int((time.time() - start_time) * 1000)
        self.metrics_repo.record(
            'analysis_latency',
            value_ms=float(duration_ms)
        )
        
        # Record detector latencies (sampled 1-in-10)
        import random
        if random.random() < 0.1:  # 10% sample rate
            for detector_name, latency in detector_times.items():
                self.metrics_repo.record(
                    'detector_latency',
                    value_ms=latency,
                    metadata={'detector_name': detector_name}
                )
        
        # Record arbiter latency if invoked
        if arbiter_latency_ms is not None:
            self.metrics_repo.record(
                'arbiter_latency',
                value_ms=arbiter_latency_ms
            )
            
            # Record arbiter fallback if not Tier 1
            if arbiter_tier and arbiter_tier > 1:
                self.metrics_repo.record(
                    'arbiter_fallback',
                    value_int=arbiter_tier
                )
        
        # Record detector timeouts
        for detector_name in timed_out:
            self.metrics_repo.record(
                'detector_timeout',
                value_int=1,
                metadata={'detector_name': detector_name}
            )
        
        # Build result
        tactics_data = [
            {
                'detector_name': t.detector_name,
                'tactic_name': t.tactic_name,
                'severity': t.severity,
                'evidence_phrases': t.evidence_phrases,
                'explanation': explanations.get(t.tactic_name, '')
            }
            for t in tactic_results
        ]
        
        log_event(logger, "INFO", "analysis_complete", {
            'analysis_id': analysis.id,
            'domain': domain,
            'composite_score': composite_score,
            'severity_band': severity_band,
            'duration_ms': duration_ms,
            'detectors_run': len(self.detection_pool.detectors) - len(timed_out),
            'detectors_timed_out': len(timed_out),
            'arbiter_tier': arbiter_tier
        })
        
        return AnalysisResult(
            analysis_id=analysis.id,
            composite_score=composite_score,
            severity_band=severity_band,
            partial_result=partial_result,
            arbiter_tier=arbiter_tier,
            tactics=tactics_data,
            meta={
                'daemon_version': '2.0.0',
                'analysis_duration_ms': duration_ms,
                'detectors_run': len(self.detection_pool.detectors),
                'detectors_timed_out': len(timed_out)
            }
        )
    
    def _get_suppressed_tactics(self) -> set:
        """Get list of suppressed tactic names"""
        from ..db.models import RuleType
        
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT value FROM user_rules WHERE rule_type = ?
            """, (RuleType.SUPPRESS_TACTIC.value,)).fetchall()
            return {row['value'] for row in rows}
    
    def is_domain_trusted(self, domain: str) -> bool:
        """Check if a domain is in the trusted list"""
        from ..db.models import RuleType
        
        with self.db.get_connection() as conn:
            row = conn.execute("""
                SELECT 1 FROM user_rules 
                WHERE rule_type = ? AND value = ?
            """, (RuleType.TRUSTED_DOMAIN.value, domain)).fetchone()
            return row is not None
    
    def get_analysis_history(
        self,
        limit: int = 50,
        offset: int = 0,
        domain: Optional[str] = None
    ) -> List[Dict]:
        """Get analysis history"""
        if domain:
            analyses = self.analysis_repo.get_by_domain(domain, limit, offset)
        else:
            analyses = self.analysis_repo.get_recent(limit, offset)
        
        result = []
        for analysis in analyses:
            tactics = self.tactic_repo.get_by_analysis(analysis.id)
            result.append({
                'analysis': analysis.to_dict(),
                'tactics': [t.to_dict() for t in tactics]
            })
        
        return result
    
    def get_dashboard_summary(self) -> Dict:
        """Get summary statistics for dashboard"""
        # Get counts
        total_analyses = self.analysis_repo.count()
        
        # Get domain stats
        domain_stats = self.domain_stats_repo.get_all()[:20]  # Top 20
        
        # Get recent analyses
        recent = self.analysis_repo.get_recent(10)
        
        # Get tactic distribution
        with self.db.get_connection() as conn:
            tactic_rows = conn.execute("""
                SELECT tactic_name, COUNT(*) as count
                FROM tactics
                GROUP BY tactic_name
                ORDER BY count DESC
                LIMIT 10
            """).fetchall()
        
        tactic_distribution = [
            {'tactic': row['tactic_name'], 'count': row['count']}
            for row in tactic_rows
        ]
        
        return {
            'total_analyses': total_analyses,
            'domain_stats': [ds.to_dict() for ds in domain_stats],
            'recent_analyses': [a.to_dict() for a in recent],
            'tactic_distribution': tactic_distribution,
            'llm_status': self.llm_arbiter.get_status_dict(),
            'detectors': [
                {'name': d.name, 'version': d.version, 'timeout_ms': d.timeout_ms}
                for d in self.detection_pool.detectors
            ]
        }