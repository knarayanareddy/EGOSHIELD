"""
EgoShield Dark Pattern Detector
Detects deceptive UI patterns, hidden costs, misdirection, and trick patterns
"""

import re
from typing import List
from .base import DetectorBase, NormalizedContent, TacticResult


class DarkPatternDetector(DetectorBase):
    """
    Detects dark patterns in web content including:
    - Urgency/fake scarcity
    - Hidden costs
    - Misdirection
    - Confirm shaming
    - Trick questions
    - Hidden subscriptions
    """
    
    name = "dark_pattern"
    version = "1.0.0"
    severity_weight = 0.85
    timeout_ms = 2000
    
    # Canonical pattern definitions for dark patterns
    PATTERNS = {
        # Urgency/Scarcity patterns
        "fake_urgency": {
            "patterns": [
                r"(?i)\b(limited\s+time|offer\s+ends|act\s+now|expires?\s+(today|soon|in\s+\d+)|don't\s+miss\s+out|time'?s?\s+running\s+out|ending?\s+soon|final\s+chance)",
                r"(?i)\b(only\s+\d+\s+(left|remaining|available)|(hurry|last|final)\s+(chance|spots?)|selling\s+fast)",
                r"(?i)\b(\d+\s+people\s+(are\s+)?viewing|(\d+)\s+(have\s+)?bought\b)",
            ],
            "severity_base": 0.7,
            "tactic_name": "Fake Urgency"
        },
        
        # False scarcity
        "false_scarcity": {
            "patterns": [
                r"(?i)\b(only\s+\d+\s+items?\s+left|in\s+high\s+demand|low\s+stock|almost\s+(sold\s+out|gone)|running\s+out\s+of\s+stock)",
                r"(?i)\b(\d+\s+others?\s+(are\s+)?(viewing|shopping)|(\d+)\s+customers?\s+(recently\s+)?bought)",
            ],
            "severity_base": 0.65,
            "tactic_name": "False Scarcity"
        },
        
        # Hidden costs
        "hidden_costs": {
            "patterns": [
                r"(?i)(shipping(?:\s+not\s+included)?|\+(?:\s*\$?\d)|handling\s+fee|processing\s+fee|additional\s+charge)",
                r"(?i)(taxes?\s+(not\s+)?included|excludes?\s+(shipping|handling|tax)|subject\s+to\s+extra)",
                r"(?i)(total\s+does\s+not\s+include|final\s+price\s+may\s+vary)",
            ],
            "severity_base": 0.75,
            "tactic_name": "Hidden Costs"
        },
        
        # Confirm shaming
        "confirm_shaming": {
            "patterns": [
                r"(?i)(no\s+i\s+(don't\s+want|would\s+rather|prefer\s+to\s+go|will\s+pass|am\s+not\s+interested))",
                r"(?i)(no\s+thanks?\s+(but\s+)?(i'll\s+(miss\s+out|pay\s+full\s+price|pass|give\s+up|skip\s+this))|i\s+don't\s+need\s+this)",
            ],
            "severity_base": 0.6,
            "tactic_name": "Confirm Shaming"
        },
        
        # Misdirection
        "misdirection": {
            "patterns": [
                r"(?i)(affirmatively?\s+(decline|opt\s+out|unsubscribe)|you\s+must\s+click\s+to\s+opt\s+out)",
                r"(?i)(unsubscribe\s+(here|in\s+(the|our)\s+(email|footer))|click\s+(here|below)\s+to\s+(opt\s+out|unsubscribe))",
            ],
            "severity_base": 0.7,
            "tactic_name": "Misdirection"
        },
        
        # Trick questions
        "trick_questions": {
            "patterns": [
                r"(?i)(by\s+(clicking|continuing)\s+you\s+(agree|accept)|consent\s+to\s+receive)",
                r"(?i)(do\s+you\s+agree\s+(to|with)|please\s+confirm\s+(your|our)|accept\s+(all|terms))",
            ],
            "severity_base": 0.65,
            "tactic_name": "Trick Questions"
        },
        
        # Hidden subscriptions
        "hidden_subscription": {
            "patterns": [
                r"(?i)(cancel\s+anytime|pause\s+(your\s+)?subscription|no\s+commitment|easy\s+to\s+cancel)",
                r"(?i)(after\s+(your\s+)?(trial|introductory|initial)\s+period|subscribe\s+automatically|will\s+be\s+charged)",
                r"(?i)(unless\s+you\s+(cancel|opt\s+out|unsubscribe)|will\s+(automatically\s+)?renew)",
            ],
            "severity_base": 0.8,
            "tactic_name": "Hidden Subscription"
        },
        
        # Guilt tripping
        "guilt_trip": {
            "patterns": [
                r"(?i)(don't\s+let\s+(your|their|the)\s+(team|friends?|family|company)|miss\s+out\s+(on|with)|others\s+(have\s+)?benefited)",
                r"(?i)(you('re|\s+are)\s+(missing\s+out|missing|losing)|don't\s+deprive)",
            ],
            "severity_base": 0.55,
            "tactic_name": "Guilt Trip"
        },
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """
        Detect dark patterns in the normalized content.
        
        Returns a list of TacticResult objects with evidence phrases.
        """
        results: List[TacticResult] = []
        text = normalized.cleaned_text
        
        if not text or len(text) < 10:
            return results
        
        for pattern_type, pattern_data in self.PATTERNS.items():
            all_evidence = []
            matched_patterns = []
            
            for pattern in pattern_data["patterns"]:
                evidence = self._find_evidence_in_text(text, pattern)
                if evidence:
                    all_evidence.extend(evidence)
                    matched_patterns.append(pattern)
            
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
                    evidence_phrases=unique_evidence[:10],  # Cap at 10 evidence phrases
                    matched_patterns=[pattern_type]
                ))
        
        return results