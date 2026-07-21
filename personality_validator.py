"""
personality_validator.py - Personality Validator for Clew AI Assistant
"""
import re

class PersonalityValidator:
    """
    Lightweight, sub-millisecond validator to strip sycophancy, preambles, and exclamations.
    """
    # Patterns for preambles (using ^ anchor for start of string)
    PREAMBLE_PATTERNS = [
        r"^(sure|absolutely|certainly|here is|here are|i can help with that|of course|no problem|gladly)[,\s!.]*",
        r"^as an ai\b[,\s!.]*",
        r"^i am programmed to\b[,\s!.]*"
    ]
    
    # Patterns for sycophancy (applied globally)
    SYCOPHANCY_PATTERNS = [
        r"\bi'd be happy to\s*(help)?\b",
        r"\bgreat choice\b",
        r"\bexcellent request\b",
        r"\bi am sorry if this was\b",
        r"\bhappy to help\b",
        r"\blet me know if you need anything else\b",
        r"\byou made a\s*(great choice)?\b"
    ]
    
    @classmethod
    def clean(cls, text: str) -> str:
        if not text:
            return ""
            
        # Clean preambles recursively
        cleaned = text.strip()
        while True:
            old_cleaned = cleaned
            for pattern in cls.PREAMBLE_PATTERNS:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
            if cleaned == old_cleaned:
                break
            
        # Clean sycophancy
        for pattern in cls.SYCOPHANCY_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
            
        # Strip exclamations: replace "!" with "."
        cleaned = cleaned.replace("!", ".")
        
        # Remove consecutive dots and surrounding whitespace, collapse to a single dot
        cleaned = re.sub(r'\s*\.+\s*', '.', cleaned)
        # Collapse any multiple dots that might be left
        cleaned = re.sub(r'\.+', '.', cleaned)
        
        # Strip extra whitespace at ends
        cleaned = cleaned.strip()
        
        return cleaned
