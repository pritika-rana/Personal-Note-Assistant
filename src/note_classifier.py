"""
Classify notes and extract entities
Simple keyword-based approach for MVP
"""

from enum import Enum
from typing import List, Dict
from dataclasses import dataclass
import re


class NoteType(Enum):
    """Types of notes"""
    EVENT = "event"
    TASK = "task"
    REMINDER = "reminder"
    FACT = "fact"
    GENERAL = "general"


@dataclass
class ClassificationResult:
    """Result of note classification"""
    note_type: NoteType
    confidence: float  # 0.0 to 1.0
    entities: Dict[str, List[str]]  # people, locations, etc.
    keywords: List[str]


class NoteClassifier:
    """Classify notes and extract entities"""
    
    def __init__(self):
        # Keywords for each note type
        self.type_keywords = {
            NoteType.EVENT: [
                'meeting', 'appointment', 'conference', 'dinner',
                'lunch', 'call', 'interview', 'presentation',
                'scheduled', 'agenda'
            ],
            NoteType.TASK: [
                'need to', 'should', 'must', 'have to', 'todo',
                'buy', 'finish', 'complete', 'submit', 'send',
                'prepare', 'review'
            ],
            NoteType.REMINDER: [
                'remind', 'remember', "don't forget", 'note to self'
            ],
            NoteType.FACT: [
                'birthday', 'anniversary', 'lives at', 'works at',
                'phone', 'email', 'address', 'favorite'
            ]
        }
    
    def classify(self, text: str) -> ClassificationResult:
        """
        Classify note type based on content
        
        Returns:
            ClassificationResult with type and confidence
        """
        text_lower = text.lower()
        
        # Priority check for reminders (highest priority)
        if any(kw in text_lower for kw in ['remind', 'remember', "don't forget"]):
            note_type = NoteType.REMINDER
            confidence = 0.9
        else:
            # Count keyword matches for each type
            scores = {}
            for note_type_key, keywords in self.type_keywords.items():
                if note_type_key == NoteType.REMINDER:
                    continue  # Already checked above
                score = sum(self._keyword_match_count(text_lower, kw) for kw in keywords)
                if score > 0:
                    scores[note_type_key] = score
            
            # Determine type with task-friendly tie-breaking
            if not scores:
                note_type = NoteType.GENERAL
                confidence = 0.5
            else:
                task_score = scores.get(NoteType.TASK, 0)
                if task_score > 0:
                    competing_score = max(
                        (score for type_key, score in scores.items() if type_key != NoteType.TASK),
                        default=0,
                    )
                    if task_score >= competing_score:
                        note_type = NoteType.TASK
                        max_score = task_score
                    else:
                        note_type = max(scores, key=scores.get)
                        max_score = scores[note_type]
                else:
                    note_type = max(scores, key=scores.get)
                    max_score = scores[note_type]

                total_keywords = len(self.type_keywords.get(note_type, [])) or 1
                confidence = min(max_score / 3.0, 1.0)  # Cap at 1.0
        
        # Extract entities
        entities = self._extract_entities(text)
        keywords = self._extract_keywords(text_lower)

        return ClassificationResult(
            note_type=note_type,
            confidence=confidence,
            entities=entities,
            keywords=keywords
        )
    
    @staticmethod
    def _keyword_match_count(text: str, keyword: str) -> int:
        """Count whole-word keyword matches in text"""
        # Use word boundaries to avoid substring matches (e.g., 'at' in 'presentation')
        pattern = r'\b' + re.escape(keyword) + r'\b'
        return len(re.findall(pattern, text))
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities (simple approach)"""
        entities = {
            'people': [],
            'locations': [],
            'organizations': []
        }
        
        # Extract capitalized words (potential names)
        # Pattern: Capitalized word not at start of sentence
        words = text.split()
        for i, word in enumerate(words):
            if i > 0 and word and len(word) > 1 and word[0].isupper():
                # Simple heuristic: likely a name
                if not word.endswith('.'):  # Not abbreviation
                    entities['people'].append(word)
        
        # Extract locations (words after "at", "in", "to")
        location_patterns = [
            r'(?:at|in|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            entities['locations'].extend(matches)
        
        return entities
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords (nouns and verbs)"""
        # Simple: words > 4 characters, not common words
        common_words = {
            'this', 'that', 'with', 'have', 'from', 'they',
            'been', 'were', 'said', 'about', 'would', 'their'
        }
        
        words = re.findall(r'\b\w{5,}\b', text.lower())
        keywords = [w for w in words if w not in common_words]
        
        return list(set(keywords))[:5]  # Top 5 unique


# Convenience function
def classify_note(text: str) -> NoteType:
    """Quick classification"""
    classifier = NoteClassifier()
    result = classifier.classify(text)
    return result.note_type
