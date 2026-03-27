"""Utilities for sanitising Personally Identifiable Information (PII)."""

from __future__ import annotations

import re
from typing import Any, Dict

PII_PATTERNS = (
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL]"),
    (re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b"), "[PHONE]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\d\b"), "[CREDIT_CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
)


def scrub_pii(text: str) -> str:
    """Replace common PII patterns with placeholder tags."""
    if not text:
        return text

    scrubbed = text
    for pattern, replacement in PII_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def scrub_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively scrub string metadata values."""
    scrubbed: Dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            scrubbed[key] = scrub_pii(value)
        elif isinstance(value, dict):
            scrubbed[key] = scrub_metadata(value)
        elif isinstance(value, list):
            scrubbed[key] = [scrub_pii(item) if isinstance(item, str) else item for item in value]
        else:
            scrubbed[key] = value
    return scrubbed
