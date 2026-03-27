"""Evaluation metrics and runner for Phase 7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from agents.note_capture_agent import NoteCaptureAgent
from agents.query_agent import QueryAgent
from agents.reminder_agent import ReminderAgent
from llama_index_setup import get_manager

from .test_cases import EvaluationCase, TEST_CASES
from data.sample_notes import SAMPLE_NOTES


@dataclass
class MetricResult:
    """Container for metric evaluation."""

    name: str
    passed: bool
    score: float
    details: Dict[str, Any]


@dataclass
class EvaluationSummary:
    """Summary of the evaluation run."""

    total_cases: int
    passed_cases: int
    metric_results: List[MetricResult]
    case_results: List[Dict[str, Any]]

    @property
    def pass_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.passed_cases / self.total_cases


def _check_answer_contains(answer: str, keywords: Iterable[str]) -> bool:
    lowered = answer.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def run_evaluation(cases: List[EvaluationCase] | None = None) -> EvaluationSummary:
    """Execute evaluation cases and return a summary with metrics."""

    cases = cases or TEST_CASES
    manager = get_manager()
    manager.reset()

    if SAMPLE_NOTES:
        manager.add_documents(
            texts=[note["text"] for note in SAMPLE_NOTES],
            metadatas=[note["metadata"] for note in SAMPLE_NOTES],
        )

    note_agent = NoteCaptureAgent()
    query_agent = QueryAgent(manager)
    reminder_agent = ReminderAgent(manager)

    passed_cases = 0
    case_results: List[Dict[str, Any]] = []

    for case in cases:
        result: Dict[str, Any] = {"name": case.name, "action": case.action, "passed": False}

        try:
            if case.action == "store":
                capture = note_agent.capture_note_sync(case.prompt)
                metadata = capture.metadata.as_dict()
                expected = case.expectations
                has_note_type = metadata.get("note_type") == expected.get("note_type")
                has_date = metadata.get("date") is not None
                future_flag = bool(metadata.get("has_future_date"))
                conditions = [has_note_type]
                if expected.get("requires_date"):
                    conditions.append(has_date)
                else:
                    conditions.append(not has_date)
                if expected.get("has_future_date") is not None:
                    conditions.append(future_flag == expected["has_future_date"])
                result.update({
                    "metadata": metadata,
                    "passed": all(conditions),
                })
            elif case.action == "query":
                query_result = query_agent.query_sync(case.prompt)
                expected = case.expectations
                contains = _check_answer_contains(query_result.answer, expected.get("answer_keywords", []))
                result.update({
                    "answer": query_result.answer,
                    "passed": contains,
                })
            elif case.action == "remind":
                days = int(case.expectations.get("days", 7))
                reminders = reminder_agent.get_upcoming_sync(days_ahead=days)
                keywords = case.expectations.get("keywords", [])
                text_blob = "\n".join(
                    item.text for items in reminders.reminders.values() for item in items
                ).lower()
                contains = all(keyword.lower() in text_blob for keyword in keywords)
                min_count = case.expectations.get("min_count", 0)
                result.update({
                    "count": reminders.count,
                    "passed": reminders.count >= min_count and contains,
                })
            else:
                result["error"] = f"Unknown action: {case.action}"
        except Exception as exc:  # pragma: no cover - defensive catch
            result["error"] = str(exc)

        if result.get("passed"):
            passed_cases += 1
        case_results.append(result)

    metrics = _calculate_metrics(case_results)
    return EvaluationSummary(
        total_cases=len(cases),
        passed_cases=passed_cases,
        metric_results=metrics,
        case_results=case_results,
    )


def _calculate_metrics(case_results: List[Dict[str, Any]]) -> List[MetricResult]:
    metrics: List[MetricResult] = []

    total = len(case_results)
    passed = sum(1 for case in case_results if case.get("passed"))
    score = passed / total if total else 0.0
    metrics.append(
        MetricResult(
            name="Overall Pass Rate",
            passed=score >= 0.8,
            score=score,
            details={"passed": passed, "total": total},
        )
    )

    query_cases = [case for case in case_results if case.get("action") == "query"]
    if query_cases:
        answered = sum(1 for case in query_cases if case.get("passed"))
        recall = answered / len(query_cases)
        metrics.append(
            MetricResult(
                name="Query Recall",
                passed=recall >= 0.75,
                score=recall,
                details={"passed": answered, "total": len(query_cases)},
            )
        )

    store_cases = [case for case in case_results if case.get("action") == "store"]
    if store_cases:
        stored = sum(1 for case in store_cases if case.get("passed"))
        score = stored / len(store_cases)
        metrics.append(
            MetricResult(
                name="Storage Accuracy",
                passed=score >= 0.8,
                score=score,
                details={"passed": stored, "total": len(store_cases)},
            )
        )

    reminder_cases = [case for case in case_results if case.get("action") == "remind"]
    if reminder_cases:
        reminders_ok = sum(1 for case in reminder_cases if case.get("passed"))
        score = reminders_ok / len(reminder_cases)
        metrics.append(
            MetricResult(
                name="Reminder Coverage",
                passed=score >= 0.7,
                score=score,
                details={"passed": reminders_ok, "total": len(reminder_cases)},
            )
        )

    return metrics
