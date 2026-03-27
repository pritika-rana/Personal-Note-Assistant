"""Note Capture Agent implementation"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from date_parser import DateTimeExtractor
from note_classifier import NoteClassifier
from guardrails import scrub_metadata, scrub_pii
from llama_index_setup import get_manager
from observability.otel import get_tracer


@dataclass
class NoteMetadata:
    """Structured metadata stored with captured notes."""

    note_type: str
    timestamp: str
    date: Optional[str]
    date_epoch: Optional[float]
    has_future_date: bool
    entities: Dict[str, List[str]]
    keywords: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "note_type": self.note_type,
            "timestamp": self.timestamp,
            "date": self.date,
            "date_epoch": self.date_epoch,
            "has_future_date": self.has_future_date,
            "entities": self.entities,
            "keywords": self.keywords,
        }


@dataclass
class NoteCaptureResult:
    """Return payload for a captured note."""

    success: bool
    message: str
    metadata: NoteMetadata


class NoteCaptureAgent:
    """Processes user statements and stores them in the index."""

    def __init__(self) -> None:
        self._manager = get_manager()
        self._date_extractor = DateTimeExtractor()
        self._classifier = NoteClassifier()

    async def capture_note(self, user_input: str) -> NoteCaptureResult:
        """Capture and store a note, returning structured metadata."""
        if not user_input or not user_input.strip():
            raise ValueError("user_input must be a non-empty string")

        tracer = get_tracer("agents.note_capture")
        with tracer.start_as_current_span("agent.capture_note") as span:
            user_input = user_input.strip()
            sanitized_input = scrub_pii(user_input)
            span.set_attribute("note.length", len(sanitized_input))

            # Extract temporal information
            parsed_date = None
            has_future_date = False
            date_epoch = None
            extraction = self._date_extractor.extract(user_input)
            if extraction:
                parsed_date = extraction[0]
                has_future_date = self._date_extractor.is_future(parsed_date)
                date_epoch = parsed_date.timestamp()
            span.set_attribute("note.has_date", parsed_date is not None)

            # Classify note content
            classification = self._classifier.classify(sanitized_input)
            span.set_attribute("note.type", classification.note_type.value)

            timestamp = datetime.now(timezone.utc).isoformat()
            date_iso = parsed_date.isoformat() if parsed_date else None

            metadata = NoteMetadata(
                note_type=classification.note_type.value,
                timestamp=timestamp,
                date=date_iso,
                date_epoch=date_epoch,
                has_future_date=has_future_date,
                entities=classification.entities,
                keywords=classification.keywords,
            )

            try:
                # Persist note to the index with sanitized text and metadata
                self._manager.add_documents([sanitized_input], [scrub_metadata(metadata.as_dict())])
            except Exception as exc:  # pragma: no cover - propagate with tracing
                span.record_exception(exc)
                raise

            message = self._build_confirmation_message(
                user_input=sanitized_input,
                note_type=classification.note_type.value,
                date=date_iso,
            )

            return NoteCaptureResult(success=True, message=message, metadata=metadata)

    def _build_confirmation_message(
        self, *, user_input: str, note_type: str, date: Optional[str]
    ) -> str:
        parts = [f"Stored {note_type} note."]
        if date:
            parts.append(f"Date: {date}")
        else:
            parts.append("No specific date detected.")
        parts.append(f"Text: {user_input}")
        return " ".join(parts)

    def capture_note_sync(self, user_input: str) -> NoteCaptureResult:
        """Synchronous helper for environments without event loops."""
        return asyncio.run(self.capture_note(user_input))
