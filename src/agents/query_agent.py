"""QueryAgent for answering stored knowledge questions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from date_parser import DateTimeExtractor
from llama_index_setup import LlamaIndexManager, get_manager
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters


@dataclass
class QueryResult:
    """Response payload for queries."""

    success: bool
    answer: str
    sources: List[str]


class QueryAgent:
    """Agent that queries indexed notes with optional date filters."""

    def __init__(self, manager: Optional[LlamaIndexManager] = None) -> None:
        self._manager = manager or get_manager()
        self._date_extractor = DateTimeExtractor()

    async def query(self, question: str) -> QueryResult:
        if not question or not question.strip():
            raise ValueError("question must be a non-empty string")

        question = question.strip()

        filters = self._build_date_filter(question)

        if filters:
            try:
                answer = self._manager.query(question, filters=filters)
            except ValueError:
                query_engine = self._manager.get_index().as_query_engine(
                    similarity_top_k=5
                )
                answer = str(query_engine.query(question))
        else:
            chat_engine = self._manager.get_chat_engine()
            answer = str(chat_engine.chat(question))

        sources: List[str] = []  # Placeholder for future source tracking
        return QueryResult(success=True, answer=answer, sources=sources)

    def _build_date_filter(self, text: str) -> Optional[MetadataFilters]:
        text_lower = text.lower()

        if "next week" in text_lower:
            start = datetime.now(timezone.utc)
            end = start + timedelta(days=7)
            return self._range_filter(start, end)

        if "this week" in text_lower:
            now_ts = datetime.now(timezone.utc)
            start = now_ts - timedelta(days=now_ts.weekday())
            end = start + timedelta(days=7)
            return self._range_filter(start, end)

        if "this month" in text_lower:
            now_ts = datetime.now(timezone.utc)
            start = now_ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                next_month = start.replace(year=start.year + 1, month=1)
            else:
                next_month = start.replace(month=start.month + 1)
            end = next_month - timedelta(seconds=1)
            return self._range_filter(start, end)

        if "today" in text_lower:
            now_ts = datetime.now(timezone.utc)
            start = now_ts.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(seconds=1)
            return self._range_filter(start, end)

        extraction = self._date_extractor.extract(text)
        if extraction:
            parsed_date = extraction[0]
            start = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(seconds=1)
            return self._range_filter(start, end)

        return None

    @staticmethod
    def _range_filter(start: datetime, end: datetime) -> MetadataFilters:
        return MetadataFilters(
            filters=[
                MetadataFilter(key="date_epoch", value=start.timestamp(), operator=">="),
                MetadataFilter(key="date_epoch", value=end.timestamp(), operator="<="),
            ]
        )

    def query_sync(self, question: str) -> QueryResult:
        return asyncio.run(self.query(question))
