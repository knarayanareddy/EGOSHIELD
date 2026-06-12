"""
EgoShield Social Engineering Detector
Detects social engineering attacks: authority impersonation, reciprocity, consistency, likability, social proof, scarcity
"""

import re
from typing import List
from .base import DetectorBase, NormalizedContent, TacticResult


class SocialEngineeringDetector(DetectorBase):
    """
    Detects social engineering tactics including:
    - Authority impersonation
    - Reciprocity manipulation
    - Consistency tactics
    - Likability manipulation
    - Social proof (fake)
    - Scarcity (fake)
    - Urgency
    - Reciprocity obligations
    """
    
    name = "social_engineering"
    version = "1.0.0"
    severity_weight = 0.85
    timeout_ms = 2000
    
    PATTERNS = {
        # Authority impersonation
        "authority_impersonation": {
            "patterns": [
                r"(?i)(?:your\s+(?:account|payment|subscription)\s+(?:has\s+been|is)\s+(?:suspended|locked|restricted|flagged)|immediate\s+action\s+required)",
                r"(?i)(?:verify\s+(?:your|my)\s+(?:account|identity|information|credentials?)|confirm\s+(?:your|my)\s+(?:account|identity)\s+(?:now|immediately))",
                r"(?i)(?:we\s+(?:have\s+)?(?:noticed|detected|found)\s+(?:a\s+)?(?:problem|issue)|urgent\s+notice|action\s+required\s+immediately)",
                r"(?i)(?:confirm\s+(?:your|to\s+avoid)\s+(?:suspension|termination|closure|restriction)|avoid\s+(?:service\s+)?(?:interruption|termination|cancellation))",
                r"(?i)(?:dear\s+(?:customer|user|client|member)|suspended\s+(?:account|profile)|click\s+(?:here|below)\s+to\s+(?:verify|confirm|restore))",
            ],
            "severity_base": 0.9,
            "tactic_name": "Authority Impersonation"
        },
        
        # Reciprocity manipulation
        "reciprocity": {
            "patterns": [
                r"(?i)(?:free\s+(?:gift|bonus|reward|offer|trial|download|guide|report|ebook|course|membership)|no\s+(?:obligation|cost|charge|purchase)\s+required)",
                r"(?i)(?:you(?:'ve|\s+have)\s+(?:been\s+)?(?:selected|chosen|invited)|exclusive\s+(?:offer|invitation|deal|members?)|limited\s+(?:time\s+)?(?:invite|offer))",
                r"(?i)(?:we(?:'re|\s+are)\s+(?:giving|offering)\s+(?:you\s+)?(?:this|a|an)\s+(?:free|complimentary|special)|just\s+for\s+you)",
            ],
            "severity_base": 0.6,
            "tactic_name": "Reciprocity Manipulation"
        },
        
        # Consistency tactics
        "consistency": {
            "patterns": [
                r"(?i)(?:you(?:'ve|\s+have)\s+(?:already|previously)\s+(?:agreed|accepted|opted\s+in|subscribed|donated|contributed)|continue\s+where\s+you\s+left\s+off)",
                r"(?i)(?:since\s+you(?:'ve|\s+have)\s+(?:already|previously)|as\s+a\s+(?:continuing|member|user|customer|subscriber))",
                r"(?i)(?:keep\s+(?:receiving|getting)|don't\s+(?:want\s+to\s+)?(?:miss\s+out\s+on\s+)?(?:the\s+)?(?:updates?|content|offers?)|stay\s+(?:informed|connected|up\s+to\s+date))",
            ],
            "severity_base": 0.55,
            "tactic_name": "Consistency Tactic"
        },
        
        # Likability manipulation
        "likability": {
            "patterns": [
                r"(?i)(?:like\s+you|trust\s+you|believe\s+in\s+you|know\s+you(?:'re|\s+are)|care\s+about\s+you)",
                r"(?i)(?:our\s+(?:best|most\s+(?:valued|popular|dedicated)|favorite)|special\s+(?:for\s+)?(?:you|our\s+customers?)|(?:just|because)\s+(?:you're|you\s+are)\s+(?:a\s+)?(?:member|customer|friend))",
                r"(?i)(?:we\s+(?:know|believe|trust)\s+you(?:'ll| will)|positive\s+(?:review|rating|feedback)|you(?:'re|\s+are)\s+(?:wonderful|amazing|great))",
            ],
            "severity_base": 0.4,
            "tactic_name": "Likability Manipulation"
        },
        
        # Fake social proof
        "fake_social_proof": {
            "patterns": [
                r"(?i)(?:\d+,?\d*|\d+)\s+(?:people|customers?|users?|members?|others?|viewers?|buyers?)\s+(?:have|are|just\s+)?(?:bought|chosen|ordered|selected|signed\s+up)|(?:\d+,?\d*|\d+)\s+(?:joined|signed\s+up)\s+(?:recently|today|this\s+week)",
                r"(?i)(?:most\s+popular|bestselling|top\s+rated|highest\s+rated|#1\s+(?:selling|pick|choice|rated)|trending\s+now|hot\s+right\s+now)",
                r"(?i)(?:(?:\d+,?\d*|\d+)\s+)?five-star|5-star|excellent\s+(?:rating|reviews?)|(?:overwhelmingly|highly)\s+positive\s+(?:reviews?|feedback|response)",
                r"(?i)(?:don(?:'t|'t)\s+take\s+our\s+word\s+for\s+it|see\s+what\s+others?\s+(?:are|say)|read\s+(?:the\s+)?(?:reviews?|testimonials|feedback))",
            ],
            "severity_base": 0.65,
            "tactic_name": "Fake Social Proof"
        },
        
        # Scarcity fake
        "scarcity_fake": {
            "patterns": [
                r"(?i)(?:only\s+\d+\s+(?:left|remaining|available|in\s+stock)|selling\s+out\s+(?:fast|quickly)|going\s+(?:fast|quickly|soon)|running\s+(?:out|low)\s+(?:of\s+)?(?:stock|supply|availability))",
                r"(?i)(?:limited\s+(?:time|quantity|supply|inventory|availability)|while\s+supplies\s+last|until\s+(?:we|they|it)\s+(?:run\s+out|close|end)|few\s+remaining)",
                r"(?i)(?:demand\s+(?:is\s+)?(?:very\s+)?(?:high|strong|incredible|unprecedented)|unprecedented\s+demand|exceeded\s+expectations)",
                r"(?i)(?:final\s+(?:call|opportunity|chance|reduction|price)|last\s+(?:chance|opportunity|units?|spots?)|once\s+they(?:'re|\s+are)\s+gone)",
            ],
            "severity_base": 0.7,
            "tactic_name": "Fake Scarcity"
        },
        
        # Urgency (social engineering context)
        "urgency_se": {
            "patterns": [
                r"(?i)(?:act\s+(?:now|immediately|fast)|time\s+(?:is\s+)?(?:running\s+out|limited)|limited\s+time\s+(?:offer|deal|opportunity)|expires?\s+(?:today|soon|immediately))",
                r"(?i)(?:don(?:'t|'t)\s+(?:wait|delay|miss\s+out)|expires?\s+in\s+\d+\s+(?:hours?|minutes?|days?)|ends?\s+(?:very|really)?\s+soon)",
                r"(?i)(?:this\s+(?:offer|price|deal)\s+(?:won't|will\s+not)\s+(?:last|be\s+available|return)|special\s+pricing\s+(?:expires?|ends|closes?)\s+)",
            ],
            "severity_base": 0.65,
            "tactic_name": "Social Engineering Urgency"
        },
        
        # Obligation/guilt
        "obligation": {
            "patterns": [
                r"(?i)(?:you\s+(?:can|should|must|have\s+to|need\s+to)\s+(?:\w+\s+)?(?:because|now\s+that)\s+we\s+(?:gave|offered|provided)|since\s+we(?:'ve|\s+have)\s+(?:given|done|provided))",
                r"(?i)(?:you(?:'ve|\s+have)\s+(?:been\s+)?(?:given|offered|provided)\s+(?:a\s+)?|accept(?:ing)?\s+(?:our|this)\s+(?:gift|offer|bonus))",
                r"(?i)(?:it(?:'s|\s+is)\s+(?:only\s+)?fair\s+you|don(?:'t|'t)\s+(?:you\s+)?(?:think\s+)?(?:it's\s+)?fair|you\s+(?:should|would|shouldn(?:'t|'t))\s+(?:do\s+)?(?:the\s+)?same)",
            ],
            "severity_base": 0.6,
            "tactic_name": "Reciprocity Obligation"
        },
        
        # Impersonation indicators
        "impersonation": {
            "patterns": [
                r"(?i)(?:support\s+team|security\s+team|account\s+team|verification\s+team|compliance\s+department)",
                r"(?i)(?:your\s+account\s+(?:requires|needs)\s+immediate|urgent\s+action\s+required\s+to\s+(?:avoid|prevent)|security\s+alert)",
                r"(?i)(?:we(?:'ve|\s+have)\s+(?:noticed|detected)\s+(?:suspicious|unauthorized|unusual)\s+(?:activity|login|attempt)|verify\s+your\s+account\s+immediately)",
            ],
            "severity_base": 0.85,
            "tactic_name": "Impersonation Attempt"
        },
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """
        Detect social engineering tactics in the normalized content.
        
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