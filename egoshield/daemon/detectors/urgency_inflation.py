"""
EgoShield Urgency Inflation Detector
Detects artificial time pressure, false deadlines, and manufactured urgency
"""

import re
from datetime import datetime
from typing import List
from .base import DetectorBase, NormalizedContent, TacticResult


class UrgencyInflationDetector(DetectorBase):
    """
    Detects urgency inflation tactics including:
    - Countdown timers/countdowns
    - Artificial deadlines
    - Time-limited offers
    - Claimed scarcity
    - False availability claims
    """
    
    name = "urgency_inflation"
    version = "1.0.0"
    severity_weight = 0.75
    timeout_ms = 2000
    
    PATTERNS = {
        # Countdown references
        "countdown_indicators": {
            "patterns": [
                r"\d+\s*(hours?|minutes?|seconds?)\s*(left|remaining|until|before)",
                r"(?i)\b(countdown|timer|clock)\b",
                r"\d{1,2}:\d{2}(?::\d{2})?",  # Time format like 2:30 or 02:30:45
            ],
            "severity_base": 0.8,
            "tactic_name": "Countdown Pressure"
        },
        
        # Artificial deadlines
        "artificial_deadlines": {
            "patterns": [
                r"(?i)(offer\s+ends?\s+(in\s+)?(\d+\s+)?(hours?|minutes?|days?)|deal\s+(expires?|ends|lasts)\s+(in\s+)?(\d+\s+)?(hours?|minutes?|days?))",
                r"(?i)(price\s+(goes|will\s+go|increases?)\s+up\s+(in\s+)?(\d+\s+)?(hours?|minutes?|days?)|sale\s+ends\s+midnight)",
                r"(?i)(this\s+(offer|price|deal)\s+won't\s+(last|be\s+available|stay)|don't\s+wait\s+(until|for)|act\s+(now|fast))",
                r"(?i)(deadline\s+(is\s+)?(approaching|coming|fast\s+approaching)|time\s+(is\s+)?running\s+out|rush\s+(to|and))",
            ],
            "severity_base": 0.75,
            "tactic_name": "Artificial Deadline"
        },
        
        # Time-limited claims
        "time_limited_claims": {
            "patterns": [
                r"(?i)(only\s+(valid|available|open|active)\s+(for|in|today|this)|today\s+only|special\s+pricing\s+for\s+(a\s+)?limited\s+time)",
                r"(?i)(limited\s+(time\s+)?(offer|deal|opportunity|special)|for\s+a\s+limited\s+time\s+only|while\s+supplies\s+last)",
                r"(?i)(flash\s+(sale|deal|offer)|lightning\s+deal|doorbuster|snap\s+up)",
            ],
            "severity_base": 0.7,
            "tactic_name": "Time-Limited Claim"
        },
        
        # Manufactured scarcity
        "manufactured_scarcity": {
            "patterns": [
                r"(?i)\b(only\s+\d+\s+(left|available|remaining|in\s+stock)|selling\s+fast|running\s+low|running\s+out)",
                r"(?i)(\d+\s+|few\s+|a\s+few\s+)?(spots?|slots?|places?|units?|copies?)\s+(left|remaining|available|open)",
                r"(?i)(high\s+demand|popular\s+(choice|item|product)|best\s+selling|our\s+most\s+popular)",
                r"(?i)(others?\s+(are|have\s+been|will\s+be)\s+(buying|ordering|booking)|(\d+)\s+(people|customers?)\s+(have|are|looking))",
            ],
            "severity_base": 0.7,
            "tactic_name": "Manufactured Scarcity"
        },
        
        # False availability
        "false_availability": {
            "patterns": [
                r"(?i)(when\s+it's\s+gone\s+it's\s+gone|no\s+rainchecks?|once\s+it's\s+gone|won't\s+(be\s+)?back\s+(in\s+)?stock)",
                r"(?i)(this\s+(price|deal|offer|product)\s+(won't|won't\s+be|might\s+not)\s+(last|be\s+available|return|come\s+back)|we\s+can't\s+(hold|reserve|guarantee)\s+this)",
                r"(?i)(last\s+(chance|opportunity|one|unit|item|available)|final\s+(available|remaining|spots?))",
            ],
            "severity_base": 0.8,
            "tactic_name": "False Availability"
        },
        
        # Urgency through repetition
        "urgency_repetition": {
            "patterns": [
                r"(?i)(hurry|fast|quick|immediate(ly)?|instant(ly)?|now|today|don't\s+wait|limited)\b.{0,50}\1",  # Same word repeated
                r"(?i)(expires?\s+soon|runs?\s+out\s+soon|ends?\s+soon|going\s+fast|selling\s+fast)",  # "soon" pattern
            ],
            "severity_base": 0.55,
            "tactic_name": "Urgency Repetition"
        },
        
        # Implied permanent unavailability
        "permanent_unavailability": {
            "patterns": [
                r"(?i)(never\s+again|won't\s+(ever\s+)?be\s+(back|offered|available|seen)|last\s+time\s+ever)",
                r"(?i)(may\s+never\s+see\s+(this|such|a)\s+(low|great|good)|might\s+never\s+(get|find|see|have))\s+(this|such|a)\s+((price|deal|opportunity|savings?)|again)",
            ],
            "severity_base": 0.75,
            "tactic_name": "Permanent Unavailability Claim"
        },
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """
        Detect urgency inflation in the normalized content.
        
        Returns a list of TacticResult objects with evidence phrases.
        """
        results: List[TacticResult] = []
        text = normalized.cleaned_text
        
        if not text or len(text) < 10:
            return results
        
        for pattern_type, pattern_data in self.PATTERNS.items():
            all_evidence = []
            
            for pattern in pattern_data["patterns"]:
                evidence = self._find_evidence_in_text(text, pattern)
                if evidence:
                    all_evidence.extend(evidence)
            
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