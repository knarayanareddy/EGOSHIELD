"""
EgoShield Content Normalizer
Converts raw text content into canonical format for detectors
"""

import re
from typing import List, Optional
from dataclasses import dataclass

from ..detectors.base import NormalizedContent


class ContentNormalizer:
    """
    Normalizes raw content for detector analysis.
    
    Handles:
    - Text cleaning
    - Tokenization
    - Sentence detection
    - Paragraph detection
    """
    
    # Common abbreviations to avoid splitting on periods
    ABBREVIATIONS = {
        'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr', 'inc', 'ltd', 'corp',
        'u.s', 'u.k', 'e.u', 'etc', 'eg', 'ie', 'vs', 'etc.', 'e.g.', 'i.e.',
        'st', 'ave', 'blvd', 'ft', 'dr', 'jan', 'feb', 'mar', 'apr', 'jun',
        'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
    }
    
    def __init__(self, max_content_length: int = 50000):
        self.max_content_length = max_content_length
    
    def normalize(self, raw_content: str) -> NormalizedContent:
        """
        Normalize raw content into canonical format.
        
        Args:
            raw_content: Raw text content from page/email
            
        Returns:
            NormalizedContent with cleaned text and parsed structures
        """
        if not raw_content:
            return NormalizedContent(
                original_text="",
                cleaned_text="",
                tokens=[],
                sentences=[],
                paragraphs=[],
                word_count=0,
                char_count=0
            )
        
        # Truncate if needed
        content = raw_content[:self.max_content_length]
        original = content
        
        # Clean the text
        cleaned = self._clean_text(content)
        
        # Tokenize
        tokens = self._tokenize(cleaned)
        
        # Detect sentences
        sentences = self._split_sentences(cleaned)
        
        # Split paragraphs
        paragraphs = self._split_paragraphs(cleaned)
        
        return NormalizedContent(
            original_text=original,
            cleaned_text=cleaned,
            tokens=tokens,
            sentences=sentences,
            paragraphs=paragraphs,
            word_count=len(tokens),
            char_count=len(cleaned)
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Decode HTML entities
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
            '&ndash;': '-',
            '&mdash;': '-',
            '&lsquo;': "'",
            '&rsquo;': "'",
            '&ldquo;': '"',
            '&rdquo;': '"',
        }
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        # Remove URLs (but keep domain references)
        text = re.sub(r'https?://\S+', ' ', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', ' ', text)
        
        # Normalize multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Trim
        text = text.strip()
        
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Returns:
            List of lowercase tokens
        """
        if not text:
            return []
        
        # Split on whitespace and punctuation (keep important punctuation)
        tokens = re.findall(r"[a-zA-Z0-9']+", text.lower())
        
        return tokens
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Handles:
        - Standard sentence endings
        - Abbreviations
        - Quote handling
        """
        if not text:
            return []
        
        # Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Split on sentence boundaries
        # Pattern handles: . ! ? followed by space and capital letter
        sentence_endings = r'(?<=[.!?])\s+(?=[A-Z"])'
        
        sentences = re.split(sentence_endings, text)
        
        # Clean each sentence
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.
        
        Uses double newlines or consistent single newlines as delimiters.
        """
        if not text:
            return []
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split on double newlines first (most reliable paragraph marker)
        paragraphs = text.split('\n\n')
        
        # If no double newlines, try single newlines but be more conservative
        if len(paragraphs) <= 1:
            paragraphs = text.split('\n')
        
        # Clean each paragraph
        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]
        
        return paragraphs
    
    def extract_significant_phrases(self, content: NormalizedContent) -> List[str]:
        """
        Extract significant phrases from content for pattern matching.
        
        Focuses on:
        - Sentence fragments
        - Phrases with manipulation keywords
        - Content between punctuation
        """
        phrases = []
        
        # Get sentences and sub-sentences
        for sentence in content.sentences:
            # Split by comma, semicolon for sub-phrases
            sub_phrases = re.split(r'[,;](?:\s+)', sentence)
            phrases.extend([p.strip() for p in sub_phrases if len(p.strip()) > 10])
        
        return phrases
    
    def get_text_summary(self, content: NormalizedContent) -> dict:
        """
        Get a summary of the normalized content.
        """
        return {
            "word_count": content.word_count,
            "char_count": content.char_count,
            "sentence_count": len(content.sentences),
            "paragraph_count": len(content.paragraphs),
            "avg_word_length": sum(len(t) for t in content.tokens) / max(len(content.tokens), 1),
            "has_content": content.word_count > 0
        }