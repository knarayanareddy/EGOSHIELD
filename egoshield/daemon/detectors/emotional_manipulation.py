"""
EgoShield Emotional Manipulation Detector
Detects emotional appeals, fear mongering, and psychological manipulation tactics
"""

import re
from typing import List
from .base import DetectorBase, NormalizedContent, TacticResult


class EmotionalManipulationDetector(DetectorBase):
    """
    Detects emotional manipulation in content including:
    - Fear-based appeals
    - Guilt induction
    - Love bombing
    - Pity appeals
    - Superficial compliments
    - False hope
    """
    
    name = "emotional_manipulation"
    version = "1.0.0"
    severity_weight = 0.8
    timeout_ms = 2000
    
    PATTERNS = {
        # Fear mongering
        "fear_appeals": {
            "patterns": [
                r"(?i)(?:don't\s+(?:let\s+)?(?:yourself?|your\s+(?:family|loved\s+ones?|children?|business))?\s+(?:miss\s+out\s+on|be\s+left\s+without|be\s+without|end\s+up\s+without))",
                r"(?i)(?:dangerous?|threats?|risk(?:s?|ing)?|warning|urgent|emergenc(?:y|ies)|critical|act\s+now\s+to\s+avoid)",
                r"(?i)(?:if\s+you\s+(?:don't|won't|fail\s+to))\s+(?:miss\s+out|end\s+up|suffer|lose|regret)",
                r"(?i)(?:lose\s+(?:out\s+on|everything|your\s+)|permanent\s+(?:damage|loss|consequences)|irreparable)",
            ],
            "severity_base": 0.75,
            "tactic_name": "Fear Appeal"
        },
        
        # Guilt induction
        "guilt_induction": {
            "patterns": [
                r"(?i)(?:why\s+(?:would\s+)?(?:you|they)\s+(?:deny|deprive|hold\s+back\s+from|not\s+give)\s+(?:your|their|your\s+family))",
                r"(?i)(?:don't\s+(?:you|they)\s+deserve|others\s+(?:have|got)|your\s+family\s+(?:deserves?|depends\s+on))",
                r"(?i)(?:after\s+everything\s+(?:you|they)\s+(?:did|have\s+done|sacrificed)|think\s+of\s+(?:your|their))",
            ],
            "severity_base": 0.7,
            "tactic_name": "Guilt Induction"
        },
        
        # Love bombing
        "love_bombing": {
            "patterns": [
                r"(?i)(?:you(?:'re|\s+are)\s+(?:special|unique|important|exceptional|our\s+(?:best|most\s+important)|one\s+of\s+(?:a\s+kind|the\s+select)|chosen))",
                r"(?i)(?:we\s+(?:believe|trust)\s+in\s+you|we\s+(?:know|feel|see)\s+you(?:'re|\s+are)|extraordinary)",
                r"(?i)(?:nothing\s+is\s+(?:too\s+)?(?:much|big|good)|unlimited\s+(?:potential|opportunities?)|transform)",
            ],
            "severity_base": 0.55,
            "tactic_name": "Love Bombing"
        },
        
        # Pity appeals
        "pity_appeals": {
            "patterns": [
                r"(?i)(?:help\s+(?:us|me|those?\s+in\s+need|the\s+less\s+fortunate)|donate\s+to\s+(?:save|support|help)|make\s+a\s+difference)",
                r"(?i)(?:just\s+\d+\s+(?:dollars?|cents?|cents)\s+a\s+day|no\s+child\s+(?:should|deserves?)\s+go)",
                r"(?i)(?:every\s+(?:donation|contribution|amount)|even\s+a\s+(?:small|little)|change\s+a\s+life)",
            ],
            "severity_base": 0.45,
            "tactic_name": "Pity Appeal"
        },
        
        # Superficial compliments
        "superficial_compliments": {
            "patterns": [
                r"(?i)(?:smart\s+(?:people?|investors?)\s+(?:like\s+you|choose|know)|brilliant\s+(?:choice|decision|move)|you(?:'re|\s+are)\s+(?:wise|intelligent|smart))",
                r"(?i)(?:successful\s+(?:people?|entrepreneurs?|business\s+owners?)\s+know|proven\s+(?:method|strategy|system)\s+(?:that\s+)?(?:works?)?)",
            ],
            "severity_base": 0.4,
            "tactic_name": "Superficial Compliment"
        },
        
        # False hope
        "false_hope": {
            "patterns": [
                r"(?i)\b(?:earn\s+\$?\d+(?:,\d+)+(?:(?:\s+(?:per|every)\s+(?:day|month|year))?|))(?:make\s+\$?\d+(?:,\d+)+(?:(?:\s+(?:daily|monthly|yearly|year))?))?",
                r"(?i)(?:guaranteed\s+(?:results?|income|success|money)|unlimited\s+(?:earnings|income|money)|no\s+(?:risk|failure|limit))",
                r"(?i)(?:lose\s+\d+\s+(?:pounds?|kgs?|lbs?|inches?)\s+(?:in\s+)?(?:just|as\s+little\s+as)\s+\d+\s+(?:days?|weeks?)|works\s+100%|results\s+(?:guaranteed|seen|visible))",
            ],
            "severity_base": 0.8,
            "tactic_name": "False Hope"
        },
        
        # Emotional blackmail
        "emotional_blackmail": {
            "patterns": [
                r"(?i)(?:if\s+(?:you|they)\s+(?:really|truly)\s+(?:love|care\s+about|believe\s+in))\s+(?:me|them|your)",
                r"(?i)(?:show\s+(?:your|their)\s+(?:love|commitment|dedication)|prove\s+(?:your|their)\s+(?:love|worth))",
                r"(?i)(?:can(?:'t|'t)\s+(?:you|they)\s+even|after\s+(?:all\s+)?(?:this|what\s+we(?:'ve|'ve))|(?:you|they)\s+(?:should|would|wouldn(?:'t|'t))\s+do\s+this)",
            ],
            "severity_base": 0.75,
            "tactic_name": "Emotional Blackmail"
        },
        
        # Artificial intimacy
        "artificial_intimacy": {
            "patterns": [
                r"(?i)(?:we(?:'ve)?|I(?:'ve)?)?\s+(?:been\s+)?(?:waiting\s+(?:for\s+)?you|looking\s+(?:for\s+)?you|want\s+you\s+here)",
                r"(?i)(?:you(?:'re|\s+are)\s+(?:part\s+of\s+(?:our|a)|family|belong(?:ing)?\s+here|welcome)|join\s+(?:our|their)\s+(?:family|community|team))",
            ],
            "severity_base": 0.5,
            "tactic_name": "Artificial Intimacy"
        },
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """
        Detect emotional manipulation in the normalized content.
        
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
                    self.logger.warning(f"Invalid regex pattern: {pattern[:50]}... - {e}")
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