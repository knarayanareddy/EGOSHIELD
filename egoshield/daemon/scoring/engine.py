"""
EgoShield Scoring Engine
Computes composite manipulation scores from detector results
"""

import math
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..detectors.base import TacticResult, DetectorBase

# CANONICAL severity thresholds
SEVERITY_THRESHOLDS = {
    "LOW": (0.0, 0.30),
    "MEDIUM": (0.30, 0.60),
    "HIGH": (0.60, 0.85),
    "CRITICAL": (0.85, 1.0),
}


@dataclass
class CompoundingFactor:
    """
    Compounding factor for multiple tactics.
    Each additional tactic adds 10% compounding, capped at 1.5x
    """
    MIN_FACTOR: float = 1.0
    MAX_FACTOR: float = 1.5
    INCREMENT: float = 0.1
    
    @classmethod
    def get(cls, tactic_count: int) -> float:
        """Get compounding factor based on number of tactics"""
        if tactic_count <= 1:
            return cls.MIN_FACTOR
        
        factor = cls.MIN_FACTOR + (cls.INCREMENT * (tactic_count - 1))
        return min(factor, cls.MAX_FACTOR)


class ScoringEngine:
    """
    Computes composite scores from detector results.
    
    Canonical scoring formula:
    composite_score = Σ (tactic.severity × detector.severity_weight) × compounding_factor(n_tactics)
    """
    
    def __init__(self, detector_registry: Dict[str, DetectorBase] = None):
        """
        Initialize scoring engine with detector registry.
        
        Args:
            detector_registry: Dict mapping detector name to detector instance
        """
        self.detector_registry = detector_registry or {}
    
    def compute_composite_score(
        self,
        tactic_results: List[TacticResult],
        partial_result: bool = False
    ) -> tuple[float, str, int]:
        """
        Compute the composite manipulation score from tactic results.
        
        Args:
            tactic_results: List of TacticResult from all detectors
            partial_result: If True, indicates some detectors timed out
            
        Returns:
            Tuple of (composite_score, severity_band, tactic_count)
        """
        if not tactic_results:
            return 0.0, "LOW", 0
        
        # Calculate weighted sum of tactic severities
        weighted_sum = 0.0
        
        for tactic in tactic_results:
            # Get detector weight
            detector_weight = self._get_detector_weight(tactic.detector_name)
            
            # Compute weighted severity
            weighted_severity = tactic.severity * detector_weight
            weighted_sum += weighted_severity
        
        # Apply compounding factor
        compounding = CompoundingFactor.get(len(tactic_results))
        composite = weighted_sum * compounding
        
        # Normalize to [0.0, 1.0]
        composite = min(composite, 1.0)
        
        # Determine severity band
        severity_band = self._get_severity_band(composite)
        
        return composite, severity_band, len(tactic_results)
    
    def _get_detector_weight(self, detector_name: str) -> float:
        """Get the severity weight for a detector"""
        if detector_name in self.detector_registry:
            return self.detector_registry[detector_name].severity_weight
        return 0.5  # Default weight if detector not found
    
    @staticmethod
    def _get_severity_band(score: float) -> str:
        """Determine severity band from composite score"""
        for band, (low, high) in SEVERITY_THRESHOLDS.items():
            if low <= score < high:
                return band
        return "CRITICAL"  # Score >= 0.85
    
    def compute_tactic_summary(
        self,
        tactic_results: List[TacticResult]
    ) -> Dict[str, dict]:
        """
        Create a summary of detected tactics by detector.
        
        Returns:
            Dict mapping detector_name to summary statistics
        """
        summary: Dict[str, dict] = {}
        
        for tactic in tactic_results:
            if tactic.detector_name not in summary:
                summary[tactic.detector_name] = {
                    "count": 0,
                    "max_severity": 0.0,
                    "avg_severity": 0.0,
                    "tactics": []
                }
            
            entry = summary[tactic.detector_name]
            entry["count"] += 1
            entry["max_severity"] = max(entry["max_severity"], tactic.severity)
            entry["tactics"].append({
                "name": tactic.tactic_name,
                "severity": tactic.severity,
                "evidence_count": len(tactic.evidence_phrases)
            })
        
        # Compute averages
        for detector_name, entry in summary.items():
            if entry["count"] > 0:
                entry["avg_severity"] = sum(
                    t["severity"] for t in entry["tactics"]
                ) / entry["count"]
        
        return summary
    
    def get_risk_level(self, composite_score: float, tactic_count: int) -> str:
        """
        Determine overall risk level.
        
        Returns:
            One of: minimal, low, moderate, elevated, high, severe
        """
        if composite_score == 0:
            return "minimal"
        elif composite_score < 0.15:
            return "low"
        elif composite_score < 0.30:
            return "moderate"
        elif composite_score < 0.50:
            return "elevated"
        elif composite_score < 0.75:
            return "high"
        elif composite_score < 0.90:
            return "severe"
        else:
            return "critical"
    
    def compute_confidence(
        self,
        tactic_count: int,
        detectors_run: int,
        detectors_total: int,
        partial_result: bool
    ) -> float:
        """
        Compute confidence score for the analysis result.
        
        Based on:
        - Number of tactics detected (more = higher confidence in pattern)
        - Ratio of detectors that ran successfully
        - Whether we have a partial result
        """
        base_confidence = min(tactic_count / 5.0, 1.0)  # Cap at 5 tactics
        
        detector_ratio = detectors_run / detectors_total if detectors_total > 0 else 0.0
        
        confidence = base_confidence * detector_ratio
        
        if partial_result:
            confidence *= 0.8  # Reduce confidence for partial results
        
        return round(confidence, 2)
    
    def format_score_explanation(
        self,
        composite_score: float,
        severity_band: str,
        tactic_count: int,
        top_tactics: List[TacticResult]
    ) -> str:
        """
        Generate a human-readable explanation of the score.
        """
        risk = self.get_risk_level(composite_score, tactic_count)
        
        if tactic_count == 0:
            return "No manipulation patterns detected."
        
        # Find the highest severity tactic
        highest = max(top_tactics, key=lambda t: t.severity) if top_tactics else None
        
        lines = [
            f"Analysis detected {tactic_count} manipulation pattern{'s' if tactic_count > 1 else ''}.",
            f"Composite score: {composite_score:.2f} ({severity_band})",
            f"Risk level: {risk.upper()}"
        ]
        
        if highest:
            lines.append(f"Primary pattern: {highest.tactic_name} (severity: {highest.severity:.2f})")
        
        if tactic_count > 3:
            lines.append(f"Multiple patterns detected indicates elevated manipulation intent.")
        
        return " ".join(lines)