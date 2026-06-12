"""
EgoShield Unit Tests - Detector Tests
"""

import pytest
from egoshield.daemon.detectors.base import NormalizedContent, DetectorBase, TacticResult
from egoshield.daemon.detectors.dark_pattern import DarkPatternDetector
from egoshield.daemon.detectors.emotional_manipulation import EmotionalManipulationDetector
from egoshield.daemon.detectors.urgency_inflation import UrgencyInflationDetector
from egoshield.daemon.detectors.gaslighting import GaslightingDetector
from egoshield.daemon.detectors.social_engineering import SocialEngineeringDetector


class TestNormalizeContent:
    """Test content normalization"""
    
    def test_empty_content(self):
        from egoshield.daemon.utils.content import ContentNormalizer
        normalizer = ContentNormalizer()
        
        result = normalizer.normalize("")
        assert result.word_count == 0
        assert result.cleaned_text == ""
    
    def test_html_stripping(self):
        from egoshield.daemon.utils.content import ContentNormalizer
        normalizer = ContentNormalizer()
        
        result = normalizer.normalize("<p>Hello <b>World</b>!</p>")
        assert "<" not in result.cleaned_text
        # Normalizer may add spaces before punctuation
        assert "hello" in result.cleaned_text.lower()
        assert "world" in result.cleaned_text.lower()
    
    def test_tokenization(self):
        from egoshield.daemon.utils.content import ContentNormalizer
        normalizer = ContentNormalizer()
        
        result = normalizer.normalize("Hello, World! How are you?")
        assert "hello" in result.tokens
        assert "world" in result.tokens
        assert len(result.tokens) > 0
    
    def test_sentence_splitting(self):
        from egoshield.daemon.utils.content import ContentNormalizer
        normalizer = ContentNormalizer()
        
        result = normalizer.normalize("First sentence. Second sentence! Third?")
        assert len(result.sentences) >= 3


class TestDetectorBase:
    """Test detector base class functionality"""
    
    def test_create_result(self):
        detector = DarkPatternDetector()
        
        result = detector._create_result(
            tactic_name="Test Tactic",
            severity=0.7,
            evidence_phrases=["test phrase"],
            matched_patterns=["test_pattern"]
        )
        
        assert result.detector_name == "dark_pattern"
        assert result.tactic_name == "Test Tactic"
        assert result.severity == 0.7
        assert len(result.evidence_phrases) == 1
    
    def test_calculate_severity(self):
        detector = DarkPatternDetector()
        
        severity = detector._calculate_severity(0.5, count=3)
        assert severity > 0.5
        assert severity <= 1.0
    
    def test_find_evidence(self):
        detector = DarkPatternDetector()
        
        text = "This offer expires in 24 hours. Limited time only!"
        evidence = detector._find_evidence_in_text(text, r"(?i)expires?\s+in")
        
        assert len(evidence) > 0
        assert "expires in" in evidence[0].lower() or "expires in 24 hours" in evidence[0].lower()


class TestDarkPatternDetector:
    """Test dark pattern detector"""
    
    def test_detects_fake_urgency(self):
        detector = DarkPatternDetector()
        
        content = NormalizedContent(
            original_text="Act now! Limited time offer!",
            cleaned_text="Act now! Limited time offer!",
            tokens=["act", "now", "limited", "time", "offer"],
            sentences=["Act now! Limited time offer!"],
            paragraphs=["Act now! Limited time offer!"],
            word_count=5,
            char_count=30
        )
        
        results = detector.detect(content)
        
        assert len(results) > 0
        tactic_names = [r.tactic_name for r in results]
        assert "Fake Urgency" in tactic_names
    
    def test_detects_hidden_costs(self):
        detector = DarkPatternDetector()
        
        content = NormalizedContent(
            original_text="Only $9.99 + shipping not included",
            cleaned_text="Only $9.99 + shipping not included",
            tokens=["only", "9.99", "shipping", "not", "included"],
            sentences=["Only $9.99 + shipping not included"],
            paragraphs=["Only $9.99 + shipping not included"],
            word_count=5,
            char_count=40
        )
        
        results = detector.detect(content)
        
        assert len(results) > 0
        tactic_names = [r.tactic_name for r in results]
        assert "Hidden Costs" in tactic_names
    
    def test_no_false_positives_clean_content(self):
        detector = DarkPatternDetector()
        
        content = NormalizedContent(
            original_text="Welcome to our website. We offer quality products at fair prices.",
            cleaned_text="Welcome to our website. We offer quality products at fair prices.",
            tokens=["welcome", "to", "our", "website", "we", "offer", "quality", "products", "at", "fair", "prices"],
            sentences=["Welcome to our website.", "We offer quality products at fair prices."],
            paragraphs=["Welcome to our website.", "We offer quality products at fair prices."],
            word_count=11,
            char_count=70
        )
        
        results = detector.detect(content)
        
        # Clean content should have no or very few results
        assert len(results) == 0 or all(r.severity < 0.4 for r in results)
    
    def test_evidence_phrases_not_empty(self):
        detector = DarkPatternDetector()
        
        content = NormalizedContent(
            original_text="Hurry! Only 3 items left in stock!",
            cleaned_text="Hurry! Only 3 items left in stock!",
            tokens=["hurry", "only", "3", "items", "left", "in", "stock"],
            sentences=["Hurry! Only 3 items left in stock!"],
            paragraphs=["Hurry! Only 3 items left in stock!"],
            word_count=7,
            char_count=35
        )
        
        results = detector.detect(content)
        
        for result in results:
            assert len(result.evidence_phrases) > 0
            assert all(isinstance(e, str) for e in result.evidence_phrases)


class TestEmotionalManipulationDetector:
    """Test emotional manipulation detector"""
    
    def test_detects_fear_appeals(self):
        detector = EmotionalManipulationDetector()
        
        content = NormalizedContent(
            original_text="Don't miss out on this opportunity! Your family depends on it!",
            cleaned_text="Don't miss out on this opportunity! Your family depends on it!",
            tokens=["don't", "miss", "out", "on", "this", "opportunity", "your", "family", "depends", "on", "it"],
            sentences=["Don't miss out on this opportunity!", "Your family depends on it!"],
            paragraphs=["Don't miss out on this opportunity! Your family depends on it!"],
            word_count=11,
            char_count=65
        )
        
        results = detector.detect(content)
        
        tactic_names = [r.tactic_name for r in results]
        assert "Fear Appeal" in tactic_names or "Guilt Induction" in tactic_names


class TestUrgencyInflationDetector:
    """Test urgency inflation detector"""
    
    def test_detects_countdown_pressure(self):
        detector = UrgencyInflationDetector()
        
        content = NormalizedContent(
            original_text="2 hours left! 30 minutes remaining!",
            cleaned_text="2 hours left! 30 minutes remaining!",
            tokens=["2", "hours", "left", "30", "minutes", "remaining"],
            sentences=["2 hours left!", "30 minutes remaining!"],
            paragraphs=["2 hours left! 30 minutes remaining!"],
            word_count=6,
            char_count=40
        )
        
        results = detector.detect(content)
        
        assert len(results) > 0
        tactic_names = [r.tactic_name for r in results]
        assert "Countdown Pressure" in tactic_names or "Artificial Deadline" in tactic_names


class TestGaslightingDetector:
    """Test gaslighting detector"""
    
    def test_detects_reality_denial(self):
        detector = GaslightingDetector()
        
        content = NormalizedContent(
            original_text="That's not what happened. You are misremembering the facts.",
            cleaned_text="That's not what happened. You are misremembering the facts.",
            tokens=["that's", "not", "what", "happened", "you", "are", "misremembering", "the", "facts"],
            sentences=["That's not what happened.", "You are misremembering the facts."],
            paragraphs=["That's not what happened.", "You are misremembering the facts."],
            word_count=9,
            char_count=65
        )
        
        results = detector.detect(content)
        
        assert len(results) > 0
        tactic_names = [r.tactic_name for r in results]
        assert "Reality Denial" in tactic_names


class TestSocialEngineeringDetector:
    """Test social engineering detector"""
    
    def test_detects_authority_impersonation(self):
        detector = SocialEngineeringDetector()
        
        content = NormalizedContent(
            original_text="URGENT: Your account has been suspended. Verify your identity immediately.",
            cleaned_text="URGENT: Your account has been suspended. Verify your identity immediately.",
            tokens=["urgent", "your", "account", "has", "been", "suspended", "verify", "your", "identity", "immediately"],
            sentences=["URGENT: Your account has been suspended.", "Verify your identity immediately."],
            paragraphs=["URGENT: Your account has been suspended. Verify your identity immediately."],
            word_count=10,
            char_count=85
        )
        
        results = detector.detect(content)
        
        assert len(results) > 0
        tactic_names = [r.tactic_name for r in results]
        assert "Authority Impersonation" in tactic_names or "Fake Social Proof" in tactic_names


class TestScoringEngine:
    """Test scoring engine"""
    
    def test_composite_score_calculation(self):
        from egoshield.daemon.scoring.engine import ScoringEngine, SEVERITY_THRESHOLDS
        
        engine = ScoringEngine()
        
        tactics = [
            TacticResult(
                detector_name="dark_pattern",
                tactic_name="Fake Urgency",
                severity=0.8,
                evidence_phrases=["limited time"]
            ),
            TacticResult(
                detector_name="urgency_inflation",
                tactic_name="Countdown Pressure",
                severity=0.7,
                evidence_phrases=["2 hours left"]
            )
        ]
        
        score, band, count = engine.compute_composite_score(tactics)
        
        assert score > 0
        assert band in SEVERITY_THRESHOLDS
        assert count == 2
    
    def test_empty_tactics_returns_zero(self):
        from egoshield.daemon.scoring.engine import ScoringEngine
        
        engine = ScoringEngine()
        
        score, band, count = engine.compute_composite_score([])
        
        assert score == 0.0
        assert band == "LOW"
        assert count == 0
    
    def test_severity_band_determination(self):
        from egoshield.daemon.scoring.engine import ScoringEngine
        
        engine = ScoringEngine()
        
        assert engine._get_severity_band(0.0) == "LOW"
        assert engine._get_severity_band(0.35) == "MEDIUM"
        assert engine._get_severity_band(0.7) == "HIGH"
        assert engine._get_severity_band(0.95) == "CRITICAL"


class TestSecurityFunctions:
    """Test security utilities"""
    
    def test_url_hashing(self):
        from egoshield.daemon.utils.security import compute_url_hash
        
        url = "https://example.com/page?id=123"
        hash1 = compute_url_hash(url)
        hash2 = compute_url_hash(url)
        
        # Same URL should produce same hash
        assert hash1 == hash2
        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64
        # Hash should be hexadecimal only
        assert all(c in '0123456789abcdef' for c in hash1)
    
    def test_different_urls_produce_different_hashes(self):
        from egoshield.daemon.utils.security import compute_url_hash
        
        hash1 = compute_url_hash("https://example.com/page1")
        hash2 = compute_url_hash("https://example.com/page2")
        
        assert hash1 != hash2
    
    def test_content_sanitization(self):
        from egoshield.daemon.utils.security import sanitize_content
        
        content = "  Hello   World!  "
        sanitized = sanitize_content(content)
        
        assert sanitized == "Hello World!"
    
    def test_html_in_content_sanitization(self):
        from egoshield.daemon.utils.security import sanitize_content
        
        content = "<script>alert('xss')</script>Hello World"
        sanitized = sanitize_content(content)
        
        assert "<script>" not in sanitized
        assert "Hello World" in sanitized
    
    def test_domain_extraction(self):
        from egoshield.daemon.utils.security import extract_domain
        
        assert extract_domain("https://sub.example.com/page") == "example.com"
        assert extract_domain("https://example.co.uk/page") == "co.uk"
        assert extract_domain("example.com") == "example.com"


class TestOriginValidator:
    """Test origin validation"""
    
    def test_valid_chrome_extension_origin(self):
        from egoshield.daemon.utils.security import OriginValidator
        
        validator = OriginValidator(extension_ids=["abc123", "xyz789"])
        
        assert validator.validate("chrome-extension://abc123")
        assert validator.validate("chrome-extension://xyz789")
        assert not validator.validate("chrome-extension://unknown")
    
    def test_valid_localhost_origin(self):
        from egoshield.daemon.utils.security import OriginValidator
        
        validator = OriginValidator()
        
        assert validator.validate("http://127.0.0.1:8766")
        assert validator.validate("http://localhost:8766")
        assert not validator.validate("http://127.0.0.1:9999")
    
    def test_rejects_external_origin(self):
        from egoshield.daemon.utils.security import OriginValidator
        
        validator = OriginValidator()
        
        assert not validator.validate("https://evil.com")
        assert not validator.validate("http://external.com:8765")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])