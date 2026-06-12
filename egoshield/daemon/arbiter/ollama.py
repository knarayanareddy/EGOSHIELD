"""
EgoShield LLM Arbiter (Ollama Integration)
Optional natural language explanation generation
"""

import json
import logging
import re
from enum import Enum
from typing import List, Optional, Dict
from dataclasses import dataclass

import httpx

from ..detectors.base import TacticResult

logger = logging.getLogger(__name__)


class ArbiterTier(Enum):
    """Arbiter fallback tiers"""
    TIER_1_FULL = 1  # Full validation + explanation
    TIER_2_EXPLANATION_ONLY = 2  # Accept scores, generate explanation only
    TIER_3_TEMPLATE = 3  # Template explanation


class OllamaHealthStatus(Enum):
    """Ollama health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ArbiterResponse:
    """Response from the LLM arbiter"""
    tier: ArbiterTier
    explanation: str
    validated_tactics: Optional[List[TacticResult]] = None
    latency_ms: Optional[float] = None


class OllamaArbiter:
    """
    Local LLM arbiter using Ollama.
    
    Implements three-tier fallback:
    - Tier 1: Full arbiter — validate detections + generate explanation
    - Tier 2: Explanation-only — accept scores, generate explanation only
    - Tier 3: Template explanation — fill tactic name + evidence into template
    """
    
    DEFAULT_MODEL = "llama3.2:3b"
    HEALTH_CHECK_URL = "http://localhost:11434/api/tags"
    GENERATE_URL = "http://localhost:11434/api/generate"
    
    # Canonical template for Tier 3 fallback
    TIER_3_TEMPLATE = (
        "Detected [{tactic_name}] pattern. "
        "Key signal: '{evidence_phrase}'. "
        "Severity: {severity_band}. "
        "Enable local LLM for detailed analysis."
    )
    
    def __init__(
        self,
        model: str = None,
        health_check_interval: int = 60,
        default_timeout_ms: int = 8000
    ):
        self.model = model or self.DEFAULT_MODEL
        self.health_check_interval = health_check_interval
        self.default_timeout_ms = default_timeout_ms
        
        self._health_status = OllamaHealthStatus.UNAVAILABLE
        self._last_health_check: float = 0
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Initialize the arbiter and check health"""
        self._http_client = httpx.AsyncClient(timeout=self.default_timeout_ms / 1000)
        await self.check_health()
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
    
    @property
    def health_status(self) -> OllamaHealthStatus:
        """Get current health status"""
        return self._health_status
    
    @property
    def is_healthy(self) -> bool:
        """Check if Ollama is healthy"""
        return self._health_status == OllamaHealthStatus.HEALTHY
    
    async def check_health(self) -> OllamaHealthStatus:
        """
        Check Ollama health by querying the models endpoint.
        Returns cached result if checked recently.
        """
        import time
        
        # Return cached status if checked recently
        current_time = time.time()
        if current_time - self._last_health_check < self.health_check_interval:
            return self._health_status
        
        self._last_health_check = current_time
        
        try:
            if not self._http_client:
                self._http_client = httpx.AsyncClient(timeout=5.0)
            
            response = await self._http_client.get(self.HEALTH_CHECK_URL)
            
            if response.status_code == 200:
                self._health_status = OllamaHealthStatus.HEALTHY
                logger.debug(f"Ollama health check passed (latency: {(current_time - self._last_health_check) * 1000:.0f}ms)")
            else:
                self._health_status = OllamaHealthStatus.UNAVAILABLE
                logger.warning(f"Ollama health check returned {response.status_code}")
                
        except httpx.TimeoutException:
            self._health_status = OllamaHealthStatus.UNAVAILABLE
            logger.debug("Ollama health check timed out")
            
        except Exception as e:
            self._health_status = OllamaHealthStatus.UNAVAILABLE
            logger.debug(f"Ollama health check failed: {e}")
        
        return self._health_status
    
    async def generate_explanation(
        self,
        composite_score: float,
        severity_band: str,
        tactics: List[TacticResult],
        threshold: float = 0.30
    ) -> ArbiterResponse:
        """
        Generate explanation for detected tactics.
        
        Implements three-tier fallback:
        1. If Ollama healthy and score >= threshold: Full explanation
        2. If Ollama healthy but score < threshold: Tier 2 explanation
        3. If Ollama unavailable: Tier 3 template
        
        Args:
            composite_score: The composite manipulation score
            severity_band: The severity band (LOW, MEDIUM, HIGH, CRITICAL)
            tactics: List of detected tactics
            threshold: Minimum score to trigger full LLM analysis
            
        Returns:
            ArbiterResponse with explanation and metadata
        """
        import time
        start_time = time.time()
        
        # Check if we should invoke full arbiter
        if self._health_status == OllamaHealthStatus.HEALTHY:
            if composite_score >= threshold:
                return await self._tier_1_full(composite_score, severity_band, tactics, start_time)
            else:
                return await self._tier_2_explanation_only(composite_score, severity_band, tactics, start_time)
        else:
            return self._tier_3_template(severity_band, tactics, start_time)
    
    async def _tier_1_full(
        self,
        score: float,
        severity_band: str,
        tactics: List[TacticResult],
        start_time: float
    ) -> ArbiterResponse:
        """
        Tier 1: Full arbiter validation and explanation.
        Validates detections and generates natural language explanation.
        """
        try:
            prompt = self._build_validation_prompt(tactics, score, severity_band)
            
            response = await self._http_client.post(
                self.GENERATE_URL,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 200
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "").strip()
                
                # FIX: Parse JSON from the response
                explanation = self._extract_explanation_from_response(raw_response)
                
                if explanation and len(explanation) > 10:
                    latency = (time.time() - start_time) * 1000
                    logger.info(f"Arbiter Tier 1 completed in {latency:.0f}ms")
                    return ArbiterResponse(
                        tier=ArbiterTier.TIER_1_FULL,
                        explanation=explanation,
                        latency_ms=latency
                    )
                else:
                    raise ValueError("Explanation too short or invalid")
            else:
                raise httpx.HTTPError(f"Status {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Tier 1 failed, falling back to Tier 2: {e}")
            return await self._tier_2_explanation_only(score, severity_band, tactics, start_time)
    
    async def _tier_2_explanation_only(
        self,
        score: float,
        severity_band: str,
        tactics: List[TacticResult],
        start_time: float
    ) -> ArbiterResponse:
        """
        Tier 2: Explanation-only mode.
        Accepts the detection scores but generates explanation only.
        """
        try:
            prompt = self._build_explanation_prompt(tactics, score, severity_band)
            
            response = await self._http_client.post(
                self.GENERATE_URL,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 150
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "").strip()
                
                # FIX: Parse JSON or extract clean text
                explanation = self._extract_explanation_from_response(raw_response)
                
                if explanation and len(explanation) > 5:
                    latency = (time.time() - start_time) * 1000
                    logger.info(f"Arbiter Tier 2 completed in {latency:.0f}ms")
                    return ArbiterResponse(
                        tier=ArbiterTier.TIER_2_EXPLANATION_ONLY,
                        explanation=explanation,
                        latency_ms=latency
                    )
                else:
                    raise ValueError("Explanation too short or invalid")
            else:
                raise httpx.HTTPError(f"Status {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Tier 2 failed, falling back to Tier 3: {e}")
            return self._tier_3_template(severity_band, tactics, start_time)
    
    def _tier_3_template(
        self,
        severity_band: str,
        tactics: List[TacticResult],
        start_time: float
    ) -> ArbiterResponse:
        """
        Tier 3: Template explanation.
        Uses template strings for explanation when LLM is unavailable.
        """
        import time
        
        if not tactics:
            explanation = "Low manipulation score. No specific patterns detected."
        else:
            # Use the highest severity tactic for the template
            highest = max(tactics, key=lambda t: t.severity)
            evidence = highest.evidence_phrases[0] if highest.evidence_phrases else "pattern detected"
            
            explanation = self.TIER_3_TEMPLATE.format(
                tactic_name=highest.tactic_name,
                evidence_phrase=evidence[:100],  # Cap evidence length
                severity_band=severity_band
            )
            
            if len(tactics) > 1:
                explanation += f" ({len(tactics)} total patterns detected.)"
        
        latency = (time.time() - start_time) * 1000
        logger.info(f"Arbiter Tier 3 (template) completed in {latency:.0f}ms")
        
        return ArbiterResponse(
            tier=ArbiterTier.TIER_3_TEMPLATE,
            explanation=explanation,
            latency_ms=latency
        )
    
    def _extract_explanation_from_response(self, raw_response: str) -> str:
        """
        Extract clean explanation text from LLM response.
        
        Handles:
        - JSON parsing: {"explanation": "..."}
        - Plain text explanations
        - Markdown code blocks
        """
        if not raw_response:
            return ""
        
        # Try to parse as JSON
        try:
            # First, look for JSON in the response
            json_match = re.search(r'\{[^{}]*"explanation"[^{}]*\}', raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if 'explanation' in data:
                    return data['explanation'].strip()
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Try direct JSON parsing
        try:
            data = json.loads(raw_response)
            if isinstance(data, dict) and 'explanation' in data:
                return data['explanation'].strip()
        except json.JSONDecodeError:
            pass
        
        # Clean up markdown code blocks
        if raw_response.startswith('```'):
            # Remove code block markers
            lines = raw_response.split('\n')
            clean_lines = []
            skip_first = raw_response.startswith('```json') or raw_response.startswith('```')
            for i, line in enumerate(lines):
                if skip_first and i == 0:
                    continue
                if line.strip() == '```':
                    continue
                clean_lines.append(line)
            raw_response = '\n'.join(clean_lines)
            
            # Try parsing again
            try:
                data = json.loads(raw_response)
                if isinstance(data, dict) and 'explanation' in data:
                    return data['explanation'].strip()
            except json.JSONDecodeError:
                pass
        
        # If still has JSON-like structure, try to extract explanation field
        if '"explanation"' in raw_response:
            match = re.search(r'"explanation"\s*:\s*"([^"]*)"', raw_response)
            if match:
                return match.group(1).strip()
        
        # Return cleaned plain text
        # Remove any remaining JSON artifacts
        cleaned = re.sub(r'^\{["\s]*', '', raw_response)
        cleaned = re.sub(r'["\s]*\}$', '', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned if cleaned else ""
    
    def _build_validation_prompt(
        self,
        tactics: List[TacticResult],
        score: float,
        severity_band: str
    ) -> str:
        """Build prompt for Tier 1 full validation"""
        tactics_summary = "\n".join([
            f"- {t.tactic_name} (from {t.detector_name}): severity {t.severity:.2f}, "
            f"evidence: {'; '.join(t.evidence_phrases[:2])}"
            for t in tactics
        ])
        
        return f"""You are EgoShield, a local privacy-focused analysis tool.

CONTEXT: You are analyzing text for manipulation patterns. You must only explain what you observe from the provided data - never invent or add information not in the input.

DETECTED PATTERNS:
{tactics_summary}

METADATA:
- Composite Score: {score:.2f}
- Severity Band: {severity_band}
- Total Patterns: {len(tactics)}

TASK: Provide a brief explanation of what these detected patterns mean for the user. Focus on the most severe patterns. Keep it under 3 sentences.

Output your explanation as plain text (not JSON)."""
    
    def _build_explanation_prompt(
        self,
        tactics: List[TacticResult],
        score: float,
        severity_band: str
    ) -> str:
        """Build prompt for Tier 2 explanation-only"""
        top_tactics = sorted(tactics, key=lambda t: t.severity, reverse=True)[:3]
        
        return f"""Explain these detected manipulation patterns in plain language:

Patterns detected:
{chr(10).join([f"- {t.tactic_name}: {'; '.join(t.evidence_phrases[:1])}" for t in top_tactics])}

Severity: {severity_band} (score: {score:.2f})

Brief explanation (1-2 sentences, plain text):"""
    
    def get_status_dict(self) -> Dict:
        """Get status information for diagnostics"""
        return {
            "status": self._health_status.value,
            "model": self.model,
            "last_check": self._last_health_check,
            "available": self._health_status == OllamaHealthStatus.HEALTHY
        }


# Synchronous wrapper for non-async contexts
class SyncOllamaArbiter:
    """Synchronous wrapper around OllamaArbiter"""
    
    def __init__(self, arbiter: OllamaArbiter):
        self._arbiter = arbiter
    
    def generate_explanation(
        self,
        composite_score: float,
        severity_band: str,
        tactics: List[TacticResult],
        threshold: float = 0.30
    ) -> ArbiterResponse:
        """Synchronous explanation generation"""
        import time
        start_time = time.time()
        
        if self._arbiter._health_status == OllamaHealthStatus.HEALTHY:
            # Run in event loop
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self._arbiter.generate_explanation(
                            composite_score, severity_band, tactics, threshold
                        )
                    )
                    return result
                finally:
                    loop.close()
            except Exception:
                pass
        
        # Fallback to tier 3
        return self._arbiter._tier_3_template(severity_band, tactics, start_time)