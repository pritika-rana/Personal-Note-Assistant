"""OpenTelemetry setup that writes spans to a JSONL log file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExportResult, SpanExporter


class JsonFileSpanExporter(SpanExporter):
    """Write spans to a JSONL file (one span per line)."""

    def __init__(self, filepath: Path) -> None:
        self._filepath = filepath
        self._lock = Lock()
        self._filepath.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans):  # type: ignore[override]
        serialized = [json.dumps(_span_to_dict(span)) for span in spans]

        with self._lock:
            with self._filepath.open("a", encoding="utf-8") as handle:
                for line in serialized:
                    handle.write(line)
                    handle.write("\n")

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:  # type: ignore[override]
        return None


@dataclass
class OtelConfig:
    service_name: str = "personal-assistant"
    enabled: bool = True
    log_path: Path = Path("logs/otel_spans.jsonl")


_tracer_provider: Optional[TracerProvider] = None


def initialize_otel(config: OtelConfig | None = None) -> None:
    """Initialise tracing with a console exporter (idempotent)."""
    global _tracer_provider

    if _tracer_provider is not None:
        return

    cfg = config or OtelConfig()
    if not cfg.enabled:
        return

    resource = Resource.create({"service.name": cfg.service_name})
    tracer_provider = TracerProvider(resource=resource)
    exporter = JsonFileSpanExporter(cfg.log_path)
    span_processor = BatchSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)

    trace.set_tracer_provider(tracer_provider)
    _tracer_provider = tracer_provider


def get_tracer(name: str) -> trace.Tracer:
    initialize_otel()
    return trace.get_tracer(name)


def _span_to_dict(span: Any) -> Dict[str, Any]:
    context = getattr(span, "context", None)
    parent = getattr(span, "parent", None)
    attributes = dict(getattr(span, "attributes", {}) or {})
    resource = getattr(span, "resource", None)

    events_payload = []
    for event in getattr(span, "events", []) or []:
        events_payload.append(
            {
                "name": getattr(event, "name", ""),
                "timestamp": _ns_to_iso(getattr(event, "timestamp", None)),
                "attributes": dict(getattr(event, "attributes", {}) or {}),
            }
        )

    return {
        "name": getattr(span, "name", ""),
        "kind": getattr(span, "kind", None).name if getattr(span, "kind", None) else None,
        "context": {
            "trace_id": _format_id(getattr(context, "trace_id", None), 32),
            "span_id": _format_id(getattr(context, "span_id", None), 16),
            "trace_state": str(getattr(context, "trace_state", "")),
        },
        "parent_id": _format_id(getattr(parent, "span_id", None), 16),
        "start_time": _ns_to_iso(getattr(span, "start_time", None)),
        "end_time": _ns_to_iso(getattr(span, "end_time", None)),
        "status": {
            "status_code": getattr(getattr(span, "status", None), "status_code", None).
            name
            if getattr(getattr(span, "status", None), "status_code", None)
            else None,
            "description": getattr(getattr(span, "status", None), "description", None),
        },
        "attributes": attributes,
        "events": events_payload,
        "resource": dict(resource.attributes) if resource else {},
    }


def _ns_to_iso(timestamp: Optional[int]) -> Optional[str]:
    if timestamp is None:
        return None
    # OpenTelemetry reports nanoseconds since epoch
    return datetime.fromtimestamp(timestamp / 1_000_000_000, tz=timezone.utc).isoformat()


def _format_id(value: Optional[int], hex_digits: int) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, int):
        return f"0x{value:0{hex_digits}x}"
    return str(value)
