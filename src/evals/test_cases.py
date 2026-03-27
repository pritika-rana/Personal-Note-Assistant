"""Evaluation dataset for Phase 7 automated checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal

ActionType = Literal["store", "query", "remind"]


@dataclass
class EvaluationCase:
    """Single evaluation scenario for the assistant."""

    name: str
    action: ActionType
    prompt: str
    expectations: Dict[str, Any]


TEST_CASES: List[EvaluationCase] = [
    EvaluationCase(
        name="Store event with future date",
        action="store",
        prompt="Meeting with the design team next Tuesday at 10am to review prototypes",
        expectations={
            "note_type": "event",
            "requires_date": True,
            "has_future_date": True,
        },
    ),
    EvaluationCase(
        name="Store reminder with explicit date",
        action="store",
        prompt="Remember to practice the keynote on November 20th at 9am",
        expectations={
            "note_type": "reminder",
            "requires_date": True,
            "has_future_date": True,
        },
    ),
    EvaluationCase(
        name="Store task without date",
        action="store",
        prompt="Need to order new HDMI cables for the conference room",
        expectations={
            "note_type": "task",
            "requires_date": False,
            "has_future_date": False,
        },
    ),
    EvaluationCase(
        name="Query doctor appointment",
        action="query",
        prompt="When is my doctor appointment?",
        expectations={
            "answer_keywords": ["doctor", "appointment"],
            "doc_keywords": ["Doctor appointment"],
        },
    ),
    EvaluationCase(
        name="Query mom birthday",
        action="query",
        prompt="When is mom's birthday?",
        expectations={
            "answer_keywords": ["june", "15"],
            "doc_keywords": ["Mom's birthday"],
        },
    ),
    EvaluationCase(
        name="Query meetings this week",
        action="query",
        prompt="What meetings do I have this week?",
        expectations={
            "answer_keywords": ["meeting"],
            "doc_keywords": ["Meeting with Sarah"],
        },
    ),
    EvaluationCase(
        name="Query tasks overview",
        action="query",
        prompt="What tasks do I need to complete?",
        expectations={
            "answer_keywords": ["report"],
            "doc_keywords": ["Finish the quarterly report"],
        },
    ),
    EvaluationCase(
        name="Query tomorrow schedule",
        action="query",
        prompt="What do I have scheduled tomorrow?",
        expectations={
            "answer_keywords": ["meeting"],
            "doc_keywords": ["Meeting with Sarah"],
        },
    ),
    EvaluationCase(
        name="Query sister workplace",
        action="query",
        prompt="Where does my sister work?",
        expectations={
            "answer_keywords": ["google"],
            "doc_keywords": ["My sister Emma works at Google"],
        },
    ),
    EvaluationCase(
        name="Reminders for next week",
        action="remind",
        prompt="Reminders for upcoming week",
        expectations={
            "days": 7,
            "min_count": 1,
            "keywords": ["dentist"],
        },
    ),
]
