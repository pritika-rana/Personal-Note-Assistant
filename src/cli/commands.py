"""CLI commands for the personal assistant."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

import click

from agents.note_capture_agent import NoteCaptureAgent
from agents.query_agent import QueryAgent
from agents.reminder_agent import ReminderAgent
from agents.router_agent import RouterAgent
from llama_index_setup import get_manager, validate_environment
from evals.metrics import run_evaluation
from observability.otel import get_tracer


PROFILE_PATH = Path("data/user_profile.json")


def _ensure_environment() -> bool:
    """Validate critical environment requirements before running commands."""
    errors = validate_environment()
    if errors:
        click.echo(click.style("⚠️  Environment issues detected:", fg="red", bold=True))
        for error in errors:
            click.echo(click.style(f" - {error}", fg="red"))
        click.echo(click.style("Please address the above issues and try again.", fg="red"))
        return False
    return True


def _load_profile() -> Dict[str, Any]:
    if PROFILE_PATH.exists():
        try:
            with PROFILE_PATH.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError:
            click.echo(click.style("⚠️  user_profile.json is corrupted. Recreating...", fg="yellow"))
    return {
        "name": "",
        "timezone": "UTC",
        "default_reminder_time": "09:00",
        "preferences": {}
    }


def _save_profile(profile: Dict[str, Any]) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PROFILE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(profile, handle, indent=2, ensure_ascii=False)


def _coerce_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    for caster in (int, float):
        try:
            return caster(raw)
        except ValueError:
            continue
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, (dict, list, int, float, bool, type(None))):
            return parsed
    except json.JSONDecodeError:
        pass
    return raw


def _set_nested(mapping: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cursor = mapping
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


@click.command(help="Store a note in the assistant's memory")
@click.argument("message", required=False)
def tell(message: Optional[str] = None) -> None:
    """Store a note in the assistant's memory."""

    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.tell") as span:
        span.set_attribute("cli.has_initial_message", message is not None)

        if not _ensure_environment():
            span.set_attribute("cli.environment_ready", False)
            return
        span.set_attribute("cli.environment_ready", True)

        if not message:
            message = click.prompt("What would you like to tell me?")

        agent = NoteCaptureAgent()
        try:
            result = asyncio.run(agent.capture_note(message))
        except Exception as exc:  # pragma: no cover - surface friendly error
            span.record_exception(exc)
            click.echo(click.style(f"✗ Failed to store note: {exc}", fg="red"))
            return

        span.set_attribute("cli.capture.success", result.success)
        span.set_attribute("cli.capture.note_type", result.metadata.note_type)

        if result.success:
            click.echo(click.style("✓ Note captured", fg="green"))
            click.echo(result.message)
        else:
            click.echo(click.style(f"✗ {result.message}", fg="red"))


@click.command(help="Ask a question about stored notes")
@click.argument("question", required=False)
def ask(question: Optional[str] = None) -> None:
    """Ask a question about stored notes."""

    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.ask") as span:
        span.set_attribute("cli.has_initial_question", question is not None)

        if not _ensure_environment():
            span.set_attribute("cli.environment_ready", False)
            return
        span.set_attribute("cli.environment_ready", True)

        if not question:
            question = click.prompt("What would you like to know?")

        agent = QueryAgent()
        try:
            result = asyncio.run(agent.query(question))
        except Exception as exc:  # pragma: no cover - user feedback path
            span.record_exception(exc)
            click.echo(click.style(f"✗ Failed to answer: {exc}", fg="red"))
            return

        span.set_attribute("cli.query.success", result.success)

        if result.success:
            click.echo(click.style("✓ Answer", fg="green"))
            click.echo(f"\n{result.answer}\n")
            if result.sources:
                click.echo("📚 Sources:")
                for source in result.sources:
                    click.echo(f"  - {source}")
        else:
            click.echo(click.style("✗ Unable to answer", fg="red"))


@click.command(help="List upcoming reminders and events")
@click.option("--days", default=7, show_default=True, help="Days to look ahead")
def remind(days: int) -> None:
    """List upcoming reminders and events."""

    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.remind") as span:
        span.set_attribute("cli.remind.days", days)

        if not _ensure_environment():
            span.set_attribute("cli.environment_ready", False)
            return
        span.set_attribute("cli.environment_ready", True)

        agent = ReminderAgent()
        try:
            result = asyncio.run(agent.get_upcoming(days_ahead=days))
        except Exception as exc:  # pragma: no cover - user feedback path
            span.record_exception(exc)
            click.echo(click.style(f"✗ Failed to fetch reminders: {exc}", fg="red"))
            return

        span.set_attribute("cli.remind.count", result.count)

        if result.count == 0:
            click.echo("✓ No upcoming reminders")
            return

        click.echo(click.style(f"\n📅 Upcoming ({result.count} items):\n", bold=True))
        for date_label, items in result.reminders.items():
            click.echo(click.style(date_label, bold=True))
            for item in items:
                click.echo(f"  • {item.text}")
            click.echo()


@click.command(help="Chat with the assistant using intent routing")
@click.argument("message", required=False)
def chat(message: Optional[str] = None) -> None:
    """Chat with the assistant using intent routing."""

    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.chat") as span:
        span.set_attribute("cli.has_initial_message", message is not None)

        if not _ensure_environment():
            span.set_attribute("cli.environment_ready", False)
            return
        span.set_attribute("cli.environment_ready", True)

        router = RouterAgent()

        async def run_route(user_msg: str) -> None:
            child_span = tracer.start_as_current_span("cli.chat.route")
            with child_span as cspan:
                cspan.set_attribute("cli.chat.input_length", len(user_msg))
                result = await router.route(user_msg)
                cspan.set_attribute("cli.chat.intent", result.intent)
                prefix = {
                    "tell": "📝 Stored",
                    "ask": "💬 Answer",
                    "remind": "📅 Reminders",
                    "chat": "🤖 Chat",
                }.get(result.intent, "🤖")
                click.echo(f"{prefix}:\n{result.message}\n")

        if message is not None:
            try:
                asyncio.run(run_route(message))
            except Exception as exc:  # pragma: no cover - user feedback path
                span.record_exception(exc)
                click.echo(click.style(f"✗ Error: {exc}", fg="red"))
            return

        click.echo("💬 Chat mode (type 'exit' to quit)")
        while True:
            user_input = click.prompt("You", prompt_suffix=": ")
            if user_input.strip().lower() in {"exit", "quit", "bye"}:
                click.echo("👋 Goodbye!")
                break
            try:
                asyncio.run(run_route(user_input))
            except Exception as exc:  # pragma: no cover - user feedback path
                span.record_exception(exc)
                click.echo(click.style(f"✗ Error: {exc}", fg="red"))


@click.group(help="Manage stored notes")
def notes() -> None:
    """Notes related commands."""


@notes.command("list", help="List stored notes")
@click.option("--limit", default=20, show_default=True, help="Maximum notes to display")
def notes_list(limit: int) -> None:
    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.notes.list") as span:
        span.set_attribute("cli.notes.limit", limit)

        if not _ensure_environment():
            span.set_attribute("cli.environment_ready", False)
            return
        span.set_attribute("cli.environment_ready", True)

        manager = get_manager()
        documents = manager.list_documents(limit=limit)
        span.set_attribute("cli.notes.count", len(documents))
        if not documents:
            click.echo("No notes found.")
            return

        for idx, doc in enumerate(documents, start=1):
            click.echo(click.style(f"[{idx}] {doc['text']}", bold=True))
            metadata = doc.get("metadata", {})
            if metadata:
                for key, value in metadata.items():
                    click.echo(f"    {key}: {value}")
            click.echo()


@notes.command("search", help="Search notes by keyword")
@click.argument("keyword")
@click.option("--limit", default=10, show_default=True, help="Maximum matches to display")
def notes_search(keyword: str, limit: int) -> None:
    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.notes.search") as span:
        span.set_attribute("cli.notes.limit", limit)
        span.set_attribute("cli.notes.keyword_length", len(keyword))

        if not _ensure_environment():
            span.set_attribute("cli.environment_ready", False)
            return
        span.set_attribute("cli.environment_ready", True)

        if not keyword.strip():
            click.echo(click.style("Please provide a search keyword.", fg="red"))
            return

        manager = get_manager()
        matches = manager.search_documents(keyword=keyword.strip(), limit=limit)
        span.set_attribute("cli.notes.matches", len(matches))
        if not matches:
            click.echo("No matching notes found.")
            return

        for idx, doc in enumerate(matches, start=1):
            click.echo(click.style(f"[{idx}] {doc['text']}", bold=True))
            metadata = doc.get("metadata", {})
            if metadata:
                for key, value in metadata.items():
                    click.echo(f"    {key}: {value}")
            click.echo()


@click.group(help="Manage user profile")
def profile() -> None:
    """Profile related commands."""


@profile.command("show", help="Show current profile settings")
def profile_show() -> None:
    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.profile.show"):
        profile = _load_profile()
        click.echo(json.dumps(profile, indent=2, ensure_ascii=False))


@profile.command("set", help="Set a profile field (supports dotted paths)")
@click.argument("field")
@click.argument("value")
def profile_set(field: str, value: str) -> None:
    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.profile.set") as span:
        span.set_attribute("cli.profile.field", field)
        profile = _load_profile()
        coerced = _coerce_value(value)
        _set_nested(profile, field, coerced)
        _save_profile(profile)
        click.echo(click.style(f"✓ Updated {field}", fg="green"))


@click.command(name="eval", help="Run automated evaluation suite")
def eval_cmd() -> None:
    tracer = get_tracer("cli.commands")
    with tracer.start_as_current_span("cli.eval") as span:
        if not _ensure_environment():
            span.set_attribute("cli.environment_ready", False)
            return
        span.set_attribute("cli.environment_ready", True)

        click.echo(click.style("Running evaluation suite...", bold=True))
        summary = run_evaluation()

        span.set_attribute("cli.eval.pass_rate", summary.pass_rate)
        span.set_attribute("cli.eval.total_cases", summary.total_cases)

        click.echo()
        click.echo(click.style(f"Overall pass rate: {summary.pass_rate:.0%}", bold=True))

        for metric in summary.metric_results:
            status = "✅" if metric.passed else "❌"
            click.echo(f"{status} {metric.name}: {metric.score:.0%}")

        click.echo()
        for case in summary.case_results:
            status = "✅" if case.get("passed") else "❌"
            click.echo(f"{status} {case['name']}")
            if "error" in case:
                click.echo(click.style(f"    Error: {case['error']}", fg="red"))
            elif case["action"] == "query":
                click.echo(f"    Answer: {case.get('answer', '')[:120]}")
            elif case["action"] == "store":
                metadata = case.get("metadata", {})
                click.echo(f"    Note type: {metadata.get('note_type')} | Date: {metadata.get('date')}")
            elif case["action"] == "remind":
                click.echo(f"    Count: {case.get('count', 0)}")
