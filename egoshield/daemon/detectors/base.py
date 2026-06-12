"""
EgoShield Detector Base Class
Abstract interface for all manipulation pattern detectors
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import logging
import concurrent.futures

logger = logging.getLogger(__name__)


@dataclass
class NormalizedContent:
    """Canonical content representation for detectors"""
    original_text: str
    cleaned_text: str
    tokens: List[str]
    sentences: List[str]
    paragraphs: List[str]
    word_count: int
    char_count: int
    
    def __repr__(self) -> str:
        return f"NormalizedContent(words={self.word_count}, chars={self.char_count})"


@dataclass
class TacticResult:
    """Result from a detector identifying a manipulation tactic"""
    detector_name: str
    tactic_name: str
    severity: float  # 0.0 to 1.0
    evidence_phrases: List[str] = field(default_factory=list)
    explanation: Optional[str] = None
    matched_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "detector_name": self.detector_name,
            "tactic_name": self.tactic_name,
            "severity": self.severity,
            "evidence_phrases": self.evidence_phrases,
            "explanation": self.explanation,
            "matched_patterns": self.matched_patterns
        }


class DetectorBase(ABC):
    """
    Abstract base class for all manipulation pattern detectors.
    
    All implementations MUST conform to this interface:
    - name: stable, unique slug
    - version: semver
    - severity_weight: in range [0.0, 1.0]
    - timeout_ms: defaults to 2000
    """
    
    name: str = "base"
    version: str = "1.0.0"
    severity_weight: float = 0.5
    timeout_ms: int = 2000
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
    
    @abstractmethod
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """
        Detect manipulation tactics in normalized content.
        
        MUST return within timeout_ms.
        MUST NOT raise exceptions — catch internally and return [].
        MUST include evidence_phrases in every TacticResult.
        """
        pass
    
    def _create_result(
        self,
        tactic_name: str,
        severity: float,
        evidence_phrases: List[str],
        matched_patterns: List[str] = None
    ) -> TacticResult:
        """Helper to create a properly structured TacticResult"""
        return TacticResult(
            detector_name=self.name,
            tactic_name=tactic_name,
            severity=severity,
            evidence_phrases=evidence_phrases,
            matched_patterns=matched_patterns or []
        )
    
    def _find_evidence_in_text(
        self,
        text: str,
        pattern: str,
        case_sensitive: bool = False
    ) -> List[str]:
        """Find evidence phrases in text matching a pattern"""
        import re
        evidence = []
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            matches = re.finditer(pattern, text, flags)
            for match in matches:
                phrase = match.group().strip()
                if len(phrase) >= 3:  # Minimum phrase length
                    evidence.append(phrase)
        except re.error as e:
            self.logger.warning(f"Regex error in pattern: {e}")
        return evidence
    
    def _calculate_severity(
        self,
        base_severity: float,
        count: int,
        context_boost: float = 0.0
    ) -> float:
        """
        Calculate adjusted severity based on:
        - Base severity for the tactic type
        - Number of occurrences (more = higher severity)
        - Context boost from surrounding patterns
        """
        # Occurrence factor: more matches increase severity
        occurrence_factor = min(1.0 + (count * 0.05), 1.5)
        
        # Combine factors
        adjusted = (base_severity * occurrence_factor) + context_boost
        
        # Cap at 1.0
        return min(adjusted, 1.0)


class DetectorTimeout(Exception):
    """Raised when a detector exceeds its time limit"""
    pass


class DetectionPool:
    """Manages parallel execution of detectors with timeouts"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.detectors: List[DetectorBase] = []
        self.error_counts: dict = {}
    
    def register(self, detector: DetectorBase):
        """Register a detector with the pool"""
        self.detectors.append(detector)
        self.error_counts[detector.name] = 0
        logger.info(f"Registered detector: {detector.name} v{detector.version}")
    
    def run_all(
        self,
        normalized: NormalizedContent,
        timeout_ms: int = 2000
    ) -> tuple[List[TacticResult], List[str]]:
        """
        Run all detectors in parallel using ThreadPoolExecutor.
        
        Uses the executor's built-in timeout handling via future.result(timeout).
        This is the correct approach - signals cannot be used in worker threads.
        
        Returns:
            Tuple of (tactic_results, timed_out_detectors)
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        
        results: List[TacticResult] = []
        timed_out: List[str] = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all detector tasks
            future_to_detector = {}
            for detector in self.detectors:
                # Use per-detector timeout if set, otherwise use global
                detector_timeout = min(detector.timeout_ms, timeout_ms) / 1000.0  # Convert to seconds
                
                future = executor.submit(self._run_detector_safe, detector, normalized)
                future_to_detector[future] = (detector, detector_timeout)
            
            # Collect results with proper timeout handling
            for future in future_to_detector:
                detector, detector_timeout = future_to_detector[future]
                
                try:
                    # Use the executor's timeout mechanism via future.result()
                    result = future.result(timeout=detector_timeout)
                    if result is not None:
                        results.extend(result)
                except TimeoutError:
                    timed_out.append(detector.name)
                    logger.warning(
                        f"Detector {detector.name} timed out after {detector.timeout_ms}ms"
                    )
                except Exception as e:
                    self.error_counts[detector.name] = self.error_counts.get(detector.name, 0) + 1
                    logger.error(
                        f"Detector {detector.name} error: {type(e).__name__}: {str(e)}"
                    )
        
        return results, timed_out
    
    def _run_detector_safe(
        self,
        detector: DetectorBase,
        normalized: NormalizedContent
    ) -> List[TacticResult]:
        """
        Safely run a detector, catching all exceptions.
        
        Note: We rely on ThreadPoolExecutor's future.result(timeout) for timeout
        handling, NOT signals. Signals only work on the main thread.
        """
        try:
            return detector.detect(normalized)
        except Exception as e:
            logger.error(f"Detector {detector.name} raised exception: {e}")
            return []