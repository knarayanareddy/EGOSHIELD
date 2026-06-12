"""
EgoShield Gaslighting Detector
Detects psychological manipulation patterns that cause self-doubt and reality distortion
"""

import re
from typing import List
from .base import DetectorBase, NormalizedContent, TacticResult


class GaslightingDetector(DetectorBase):
    """
    Detects gaslighting and psychological manipulation including:
    - Reality denial
    - Self-doubt induction
    - Discrediting feelings
    - Blame shifting
    - Trivializing concerns
    - Feigned concern for manipulation
    """
    
    name = "gaslighting"
    version = "1.0.0"
    severity_weight = 0.9
    timeout_ms = 2000
    
    PATTERNS = {
        # Reality denial
        "reality_denial": {
            "patterns": [
                r"(?i)(that(?:\s+is|'s)?\s+(?:never\s+)?(?:what\s+(?:happened|i\s+said|did|meant))|you(?:'re|\s+are)\s+(?:remembering|misremembering|imagining|overreacting))",
                r"(?i)(?:that\s+never\s+(?:happened|said|occurred)|you(?:'re|\s+are)\s+(?:making\s+that\s+up|misinterpreting|misunderstanding))",
                r"(?i)(?:i\s+(?:never\s+)?(?:said|did|meant|told)\s+(?:that|this)|you(?:'re|\s+are)\s+(?:twisting|distorting))",
                r"(?i)(?:you\s+(?:can't\s+)?(?:remember\s+)?(?:it\s+)?(?:correctly)?|your\s+memory\s+(?:is\s+)?(?:wrong|incorrect))",
            ],
            "severity_base": 0.85,
            "tactic_name": "Reality Denial"
        },
        
        # Self-doubt induction
        "self_doubt": {
            "patterns": [
                r"(?i)(?:are\s+you\s+(?:sure|certain)|you(?:'re|\s+are)\s+(?:probably|maybe|just)\s+(?:overreacting|misinterpreting|misremembering)|maybe\s+you(?:'re|\s+are)\s+(?:just|tired|stressed))",
                r"(?i)(?:have\s+you\s+(?:considered|thought\s+about)\s+that\s+you\s+(?:might\s+)?(?:be\s+)?(?:wrong)?|you\s+(?:might\s+)?(?:want\s+to\s+)?(?:consider\s+)?(?:your\s+)?(?:own\s+)?(?:bias|perspective))",
                r"(?i)(?:it(?:'s|\s+is)\s+(?:all\s+)?(?:in\s+your\s+head|wrong)|you(?:'re|\s+are)\s+(?:being\s+)?(?:too\s+)?(?:sensitive|paranoid)|don't\s+be\s+(?:so)\s+(?:dramatic|sensitive))",
            ],
            "severity_base": 0.8,
            "tactic_name": "Self-Doubt Induction"
        },
        
        # Discrediting feelings
        "discredit_feelings": {
            "patterns": [
                r"(?i)(?:you\s+(?:shouldn't|should\s+not|don't\s+need\s+to)\s+(?:feel|think|believe)\s+that\s+(?:way|about)|your\s+(?:feelings?|emotions?)\s+(?:are\s+)?(?:unfounded|misplaced|wrong|inappropriate))",
                r"(?i)(?:there(?:'s|\s+is)\s+(?:nothing\s+)?(?:wrong|bad)\s+with\s+(?:you|that)|you(?:'re|\s+are)\s+(?:(?:over)?reacting|being\s+(?:too\s+)?sensitive))",
                r"(?i)(?:don't\s+(?:feel|think)\s+(?:bad|worried|sad|upset)\s+about\s+(?:that|it|this)|you\s+have\s+(?:nothing|nothing\s+to)\s+(?:worry|be\s+upset|feel\s+bad)\s+about)",
            ],
            "severity_base": 0.75,
            "tactic_name": "Discrediting Feelings"
        },
        
        # Blame shifting
        "blame_shifting": {
            "patterns": [
                r"(?i)(?:if\s+you\s+(?:hadn(?:'t|'t)|didn(?:'t|'t))\s+(?:just|only)\s+\w+|you(?:'re|\s+are)\s+(?:the\s+one\s+who|part\s+of\s+the\s+problem))",
                r"(?i)(?:what\s+about\s+your\s+(?:role|part|responsibility|contribution)|you\s+(?:didn(?:'t|'t)\s+)?(?:have\s+to\s+)?(?:do|be)\s+that\s+either)",
                r"(?i)(?:maybe\s+you\s+should\s+(?:look\s+inward|consider|examine)\s+(?:yourself|your\s+own)|the\s+real\s+(?:problem|issue)\s+is\s+you)",
                r"(?i)(?:you\s+(?:always|usually|often)\s+(?:do|make|create)\s+(?:this|that|problems?)|you\s+(?:never|rarely)\s+(?:listen|understand|compromise))",
            ],
            "severity_base": 0.8,
            "tactic_name": "Blame Shifting"
        },
        
        # Trivializing
        "trivializing": {
            "patterns": [
                r"(?i)(?:it(?:'s|\s+is)\s+(?:not\s+)?(?:that\s+)?(?:bad|serious|important|significant)|you(?:'re|\s+are)\s+(?:making\s+)?(?:a\s+)?big\s+deal\s+(?:out\s+of)?)",
                r"(?i)(?:it\s+(?:happened|doesn(?:'t|'t)\s+matter|isn(?:'t|'t)\s+worth)|that(?:'s|\s+is)\s+(?:really|actually)?\s+(?:nothing|trivial|silly))",
                r"(?i)(?:calm\s+down|relax|don(?:'t|'t)\s+be\s+(?:so|such)\s+(?:dramatic|worked\s+up|upset)|you(?:'re|\s+are)\s+(?:over)?(?:reacting|blowing)\s+(?:it\s+)?(?:up\s+)?out\s+of\s+proportion)",
            ],
            "severity_base": 0.65,
            "tactic_name": "Trivializing"
        },
        
        # Feigned concern
        "feigned_concern": {
            "patterns": [
                r"(?i)(?:i(?:'m|\s+am)\s+(?:just|only)\s+(?:worried|concerned|trying\s+to\s+help)|i\s+(?:only|just)\s+(?:want|mean|tell)\s+(?:this|you)\s+(?:for\s+your\s+own\s+)?good)",
                r"(?i)(?:i\s+care\s+about\s+you\s+(?:but|that(?:'s|\s+is)\s+why)|i\s+(?:just|only)\s+want\s+(?:the\s+)?best\s+for\s+you)",
                r"(?i)(?:you\s+(?:must|have\s+to|should)\s+(?:trust|believe)\s+me|i\s+(?:wouldn(?:'t|'t)|don(?:'t|'t))\s+lie\s+to\s+you)",
                r"(?i)(?:think\s+about\s+(?:it|this)\s+(?:from\s+my\s+perspective|from\s+my\s+point\s+of\s+view)|i\s+know\s+(?:what(?:'s|\s+is)\s+better\s+for\s+you))",
            ],
            "severity_base": 0.7,
            "tactic_name": "Feigned Concern"
        },
        
        # Isolation tactics
        "isolation": {
            "patterns": [
                r"(?i)(?:who\s+(?:else|else\s+)?(?:told|said|suggested)|did\s+someone\s+tell\s+you\s+(?:that|this)|who\s+(?:are\s+)?(?:you\s+)?(?:listening\s+to|following))",
                r"(?i)(?:your\s+(?:friends?|family|parents?|partner)\s+(?:don(?:'t|'t)|wouldn(?:'t|'t))\s+(?:understand|agree|support)|no\s+one\s+(?:else|else\s+)?(?:believes?|agrees?\s+with)\s+you)",
                r"(?i)(?:i(?:'m|\s+am)\s+the\s+only\s+(?:one|person)\s+who\s+(?:really|truly)|everyone\s+(?:else|else\s+)?(?:knows?|sees?|understands?)|only\s+i\s+(?:can|will|know))",
            ],
            "severity_base": 0.85,
            "tactic_name": "Isolation Tactics"
        },
        
        # Conditional affection
        "conditional_affection": {
            "patterns": [
                r"(?i)(?:if\s+you\s+(?:would|just)\s+(?:listen|comply|agree|obey)|you\s+would\s+(?:be\s+)?(?:happy|better|okay|good))",
                r"(?i)(?:why\s+can(?:'t|'t)\s+you\s+just\s+(?:listen|agree|do)|you\s+never\s+(?:listen|agree|satisfy))",
                r"(?i)(?:love\s+me\s+(?:and|by|then)|love\s+(?:me|them)\s+(?:means|by)|do\s+this\s+(?:for\s+me|if\s+you\s+love\s+me))",
            ],
            "severity_base": 0.8,
            "tactic_name": "Conditional Affection"
        },
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """
        Detect gaslighting patterns in the normalized content.
        
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