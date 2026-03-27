"""Entry point for the personal assistant CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import click

# Ensure the src/ directory is importable when running `python -m assistant`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cli import commands  # noqa: E402
from observability.otel import initialize_otel  # noqa: E402


@click.group(help="Personal Assistant - Your Second Brain")
@click.version_option(version="0.1.0")
def cli() -> None:
    """Root command group."""


cli.add_command(commands.tell, "tell")
cli.add_command(commands.ask, "ask")
cli.add_command(commands.remind, "remind")
cli.add_command(commands.chat, "chat")
cli.add_command(commands.notes, "notes")
cli.add_command(commands.profile, "profile")
cli.add_command(commands.eval_cmd, "eval")


if __name__ == "__main__":
    initialize_otel()
    cli()
