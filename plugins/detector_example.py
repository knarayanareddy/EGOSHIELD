"""
Sample Custom Detector Plugin for EgoShield

This is an example plugin demonstrating the ADR-006 plugin system.
Copy this file to your plugins directory and rename it with the 'detector_' prefix.

Usage:
1. Copy this file to your plugins directory as detector_example.py
2. Enable plugins in settings: plugins_enabled = 'true'
3. Optionally set plugins_path to your custom plugins directory
4. Restart the daemon to load the plugin

The filename must:
- Start with 'detector_'
- Contain a class ending with 'Detector'
- The class must inherit from DetectorBase

Security Note: Only load plugins from trusted sources!
"""

import re
from typing import List

from daemon.detectors.base import DetectorBase, NormalizedContent, TacticResult


class ExampleDetector(DetectorBase):
    """
    Example custom detector for demonstration purposes.
    Detects specific example manipulation patterns.
    """
    
    name = "example"
    version = "1.0.0"
    severity_weight = 0.5
    timeout_ms = 1000
    
    PATTERNS = {
        "custom_pattern": {
            "patterns": [
                r"(?i)example\s+manipulation\s+phrase",
                r"(?i)special\s+offer\s+just\s+for\s+you",
                r"(?i)you\s+have\s+been\s+selected",
            ],
            "severity_base": 0.6,
            "tactic_name": "Custom Manipulation"
        },
        "fake_authority": {
            "patterns": [
                r"(?i)according\s+to\s+our\s+records",
                r"(?i)we\s+have\s+determined\s+that",
                r"(?i)this\s+is\s+an\s+official\s+notice",
            ],
            "severity_base": 0.65,
            "tactic_name": "Fake Authority Claim"
        }
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """
        Detect custom manipulation patterns.
        
        Returns a list of TacticResult objects with evidence phrases.
        """
        results: List[TacticResult] = []
        text = normalized.cleaned_text
        
        if not text or len(text) < 10:
            return results
        
        for pattern_type, pattern_data in self.PATTERNS.items():
            all_evidence = []
            
            for pattern in pattern_data["patterns"]:
                try:
                    evidence = self._find_evidence_in_text(text, pattern)
                    if evidence:
                        all_evidence.extend(evidence)
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern: {e}")
                    continue
            
            if all_evidence:
                # Remove duplicates while preserving order
                seen = set()
                unique_evidence = []
                for e in all_evidence:
                    lower_e = e.lower()
                    if lower_e not in seen:
                        seen.add(lower_e)
                        unique_evidence.append(e)
                
                severity = self._calculate_severity(
                    pattern_data["severity_base"],
                    len(unique_evidence)
                )
                
                results.append(self._create_result(
                    tactic_name=pattern_data["tactic_name"],
                    severity=severity,
                    evidence_phrases=unique_evidence[:10],
                    matched_patterns=[pattern_type]
                ))
        
        return results