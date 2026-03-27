"""RouterAgent to classify intent and delegate to specialized agents."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from agents.note_capture_agent import NoteCaptureAgent
from agents.query_agent import QueryAgent
from agents.reminder_agent import ReminderAgent
from llama_index_setup import get_manager


@dataclass
class RouterResult:
    """Unified result returned by RouterAgent."""

    success: bool
    message: str
    intent: str


class RouterAgent:
    """Routes user input to the appropriate agent based on intent."""

    def __init__(self) -> None:
        self._manager = get_manager()
        self._note_agent = NoteCaptureAgent()
        self._query_agent = QueryAgent(self._manager)
        self._reminder_agent = ReminderAgent(self._manager)

    async def route(self, user_input: str) -> RouterResult:
        if not user_input or not user_input.strip():
            raise ValueError("user_input must be non-empty")

        user_input = user_input.strip()
        intent = self._classify_intent(user_input)

        if intent == "tell":
            capture_result = await self._note_agent.capture_note(user_input)
            return RouterResult(
                success=capture_result.success,
                message=capture_result.message,
                intent="tell",
            )

        if intent == "ask":
            query_result = await self._query_agent.query(user_input)
            return RouterResult(
                success=query_result.success,
                message=query_result.answer,
                intent="ask",
            )

        if intent == "remind":
            reminder_result = await self._reminder_agent.get_upcoming()
            if reminder_result.count == 0:
                message = "No upcoming reminders"
            else:
                lines = []
                for date_label, items in reminder_result.reminders.items():
                    lines.append(f"{date_label}:")
                    for item in items:
                        lines.append(f"  - {item.text}")
                message = "\n".join(lines) if lines else "No upcoming reminders"
            return RouterResult(success=True, message=message, intent="remind")

        chat_engine = self._manager.get_chat_engine()
        response = chat_engine.chat(user_input)
        return RouterResult(success=True, message=str(response), intent="chat")

    def route_sync(self, user_input: str) -> RouterResult:
        return asyncio.run(self.route(user_input))

    @staticmethod
    def _classify_intent(text: str) -> str:
        text_lower = text.lower()

        tell_keywords = ["remember", "note", "my", "let me tell", "store", "save", "log", "capture"]
        ask_keywords = ["what", "when", "where", "who", "how", "?", "show", "tell me", "find"]
        remind_keywords = ["remind me", "upcoming", "next week", "coming up", "reminders", "show reminders", "list reminders", "all reminders"]

        # Check remind first (compound phrases are most specific), then ask, then tell
        if any(keyword in text_lower for keyword in remind_keywords):
            return "remind"
        if any(keyword in text_lower for keyword in ask_keywords):
            return "ask"
        if any(keyword in text_lower for keyword in tell_keywords):
            return "tell"
        if text_lower.endswith("?"):
            return "ask"
        return "tell"
