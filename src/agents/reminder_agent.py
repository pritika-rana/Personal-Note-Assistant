"""ReminderAgent for surfacing upcoming events and tasks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from llama_index_setup import LlamaIndexManager, get_manager
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters


@dataclass
class ReminderItem:
    """Individual reminder entry."""

    text: str
    note_type: str
    date: Optional[str]
    date_epoch: Optional[float]


@dataclass
class ReminderResult:
    """Structured result returned by ReminderAgent."""

    reminders: Dict[str, List[ReminderItem]]
    count: int


class ReminderAgent:
    """Agent responsible for fetching upcoming reminders and events."""

    def __init__(self, manager: Optional[LlamaIndexManager] = None) -> None:
        self._manager = manager or get_manager()

    async def get_upcoming(self, *, days_ahead: int = 7) -> ReminderResult:
        if days_ahead <= 0:
            raise ValueError("days_ahead must be positive")

        now = datetime.now(timezone.utc)
        # Start from beginning of today to include items already past
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        horizon = now + timedelta(days=days_ahead)

        filters = MetadataFilters(
            filters=[
                MetadataFilter(key="date_epoch", value=start_of_today.timestamp(), operator=">="),
                MetadataFilter(key="date_epoch", value=horizon.timestamp(), operator="<="),
            ]
        )

        try:
            response = self._manager.query(
                "List upcoming events and tasks", filters=filters
            )
        except ValueError:
            query_engine = self._manager.get_index().as_query_engine(similarity_top_k=10)
            response = str(query_engine.query("List upcoming events and tasks"))

        reminders = self._parse_response(response)
        total = sum(len(items) for items in reminders.values())
        return ReminderResult(reminders=reminders, count=total)

    async def get_today(self) -> ReminderResult:
        return await self.get_upcoming(days_ahead=1)

    def _parse_response(self, response: str) -> Dict[str, List[ReminderItem]]:
        lines = [line.strip("- ") for line in response.splitlines() if line.strip()]
        normalized = response.strip().lower()
        if not lines or normalized in {"", "empty response", "no results"}:
            return {"No upcoming": []}

        grouped: Dict[str, List[ReminderItem]] = {}

        for line in lines:
            date_label = "Unknown"
            text = line

            if ":" in line:
                possible_date, remainder = line.split(":", 1)
                if any(token in possible_date.lower() for token in ["202", "20", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]):
                    date_label = possible_date.strip()
                    text = remainder.strip()

            grouped.setdefault(date_label, []).append(
                ReminderItem(text=text, note_type="unknown", date=None, date_epoch=None)
            )

        if not grouped:
            grouped["Unknown"] = []

        return grouped

    def get_upcoming_sync(self, *, days_ahead: int = 7) -> ReminderResult:
        return asyncio.run(self.get_upcoming(days_ahead=days_ahead))
