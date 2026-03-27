"""
Date and time extraction from natural language
Uses dateparser library for robust parsing
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import dateparser
from dateparser.search import search_dates
import re


class DateTimeExtractor:
    """Extract dates and times from natural language text"""
    
    def __init__(self):
        self.settings = {
            'PREFER_DATES_FROM': 'future',
            'RETURN_AS_TIMEZONE_AWARE': False
        }
    
    def extract(self, text: str) -> Optional[Tuple[datetime, str]]:
        """
        Extract datetime from text
        
        Returns:
            Tuple of (datetime_obj, original_text) or None
        """
        # Try search_dates first (best for finding dates in text)
        try:
            results = search_dates(
                text,
                languages=['en'],
                settings=self.settings
            )
            if results:
                # Return first found date
                extracted_text, parsed_date = results[0]
                return (parsed_date, extracted_text)
        except Exception:
            pass  # Continue to fallback methods
        
        # Try common patterns
        patterns = [
            r'(tomorrow|today|tonight)',
            r'(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)',
            r'(next|this)\s+week',
            r'((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?)',
            r'(\d{1,2}(?:st|nd|rd|th)?)\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
            r'(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))',  # Time: 3pm, 10:30 AM
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted_text = match.group(0)
                parsed = dateparser.parse(
                    extracted_text,
                    languages=['en'],
                    settings=self.settings
                )
                if parsed:
                    return (parsed, extracted_text)
        
        text_lower = text.lower()

        # Keyword-based fallback for common phrases that can fail parsing
        if any(keyword in text_lower for keyword in ["today", "tonight", "tomorrow"]):
            now = datetime.now()
            if "tomorrow" in text_lower:
                parsed = now + timedelta(days=1)
            else:
                parsed = now

            if "tonight" in text_lower:
                parsed = parsed.replace(hour=20, minute=0, second=0, microsecond=0)

            return (parsed, text)

        # Final fallback: Try full text with dateparser
        parsed = dateparser.parse(
            text,
            languages=['en'],
            settings=self.settings
        )
        
        if parsed:
            return (parsed, text)
        
        return None
    
    def extract_all(self, text: str) -> List[Tuple[datetime, str]]:
        """Extract all date/time mentions from text"""
        # Split into sentences and try each
        sentences = text.split('.')
        results = []
        
        for sentence in sentences:
            result = self.extract(sentence.strip())
            if result:
                results.append(result)
        
        return results if results else []
    
    def has_date(self, text: str) -> bool:
        """Check if text contains a date reference"""
        return self.extract(text) is not None
    
    def format_datetime(self, dt: datetime) -> str:
        """Format datetime for display"""
        return dt.strftime("%B %d, %Y at %I:%M %p")
    
    def is_future(self, dt: datetime) -> bool:
        """Check if datetime is in the future"""
        return dt > datetime.now()
    
    def days_until(self, dt: datetime) -> int:
        """Calculate days until datetime"""
        delta = dt - datetime.now()
        return delta.days


# Convenience function
def parse_date(text: str) -> Optional[datetime]:
    """Quick date parsing"""
    extractor = DateTimeExtractor()
    result = extractor.extract(text)
    return result[0] if result else None
