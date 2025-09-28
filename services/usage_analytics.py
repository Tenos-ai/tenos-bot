"""Usage analytics helpers for the Material configurator network monitor."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from pathlib import Path
from typing import Dict, Mapping


@dataclass(frozen=True, slots=True)
class DailyUsage:
    """Represents aggregated usage counts for a single day."""

    day: date
    counts: Dict[str, int]


@dataclass(frozen=True, slots=True)
class AnalyticsReport:
    """Aggregated analytics payload for GUI presentation."""

    feature_usage: tuple[DailyUsage, ...]
    model_usage: tuple[DailyUsage, ...]
    total_completed: int
    total_cancelled: int
    feature_totals: Dict[str, int]
    model_totals: Dict[str, int]


def collect_usage_analytics(*, log_dir: str | Path, days: int = 14) -> AnalyticsReport:
    """Aggregate completed job logs into feature/model usage series.

    Parameters
    ----------
    log_dir:
        Directory that contains ``*-completed.json``/``*-cancelled.json`` log files.
    days:
        Number of days (including today) to surface in the rolling window.
    """

    log_path = Path(log_dir)
    if days <= 0:
        raise ValueError("days must be positive")

    today = datetime.utcnow().date()
    window_start = today - timedelta(days=days - 1)

    date_range = [window_start + timedelta(days=offset) for offset in range(days)]
    feature_day_totals: Dict[date, Dict[str, int]] = {
        day: defaultdict(int) for day in date_range
    }
    model_day_totals: Dict[date, Dict[str, int]] = {
        day: defaultdict(int) for day in date_range
    }

    feature_totals: Dict[str, int] = defaultdict(int)
    model_totals: Dict[str, int] = defaultdict(int)

    total_completed = 0
    total_cancelled = 0

    cutoff_timestamp = datetime.combine(window_start, time.min).timestamp()

    if log_path.exists():
        for file_path in log_path.glob("*-completed.json"):
            if _should_skip_log(file_path, cutoff_timestamp):
                continue
            _process_log_file(
                file_path,
                feature_day_totals,
                model_day_totals,
                feature_totals,
                model_totals,
                today,
                window_start,
            )
        for file_path in log_path.glob("*-cancelled.json"):
            if _should_skip_log(file_path, cutoff_timestamp):
                continue
            total_cancelled += _count_cancelled_jobs(file_path, today, window_start)

    for day_totals in feature_day_totals.values():
        total_completed += sum(day_totals.values())

    feature_series = _build_series(feature_day_totals)
    model_series = _build_series(model_day_totals)

    return AnalyticsReport(
        feature_usage=feature_series,
        model_usage=model_series,
        total_completed=total_completed,
        total_cancelled=total_cancelled,
        feature_totals=dict(sorted(feature_totals.items())),
        model_totals=dict(sorted(model_totals.items())),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_series(day_totals: Mapping[date, Mapping[str, int]]) -> tuple[DailyUsage, ...]:
    ordered_days = sorted(day_totals.keys())
    series: list[DailyUsage] = []
    for day in ordered_days:
        counts = {feature: count for feature, count in day_totals[day].items() if count}
        if counts:
            series.append(DailyUsage(day=day, counts=counts))
    return tuple(series)


def _should_skip_log(file_path: Path, cutoff_timestamp: float) -> bool:
    try:
        return file_path.stat().st_mtime < cutoff_timestamp
    except OSError:
        return True


def _process_log_file(
    file_path: Path,
    feature_day_totals: Dict[date, Dict[str, int]],
    model_day_totals: Dict[date, Dict[str, int]],
    feature_totals: Dict[str, int],
    model_totals: Dict[str, int],
    today: date,
    window_start: date,
) -> None:
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return

    if not isinstance(payload, dict):
        return

    for entry in payload.values():
        if not isinstance(entry, dict):
            continue

        event_time = _coerce_datetime(
            entry.get("completion_time")
            or entry.get("timestamp")
            or entry.get("created_at")
        )
        if event_time is None:
            continue

        event_date = event_time.date()
        if event_date < window_start or event_date > today:
            continue

        feature_label = _normalise_feature(entry.get("type"))
        model_label = _normalise_model(entry)

        feature_day_totals[event_date][feature_label] += 1
        model_day_totals[event_date][model_label] += 1

        feature_totals[feature_label] += 1
        model_totals[model_label] += 1


def _count_cancelled_jobs(file_path: Path, today: date, window_start: date) -> int:
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return 0

    if not isinstance(payload, dict):
        return 0

    count = 0
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        event_time = _coerce_datetime(entry.get("cancellation_time") or entry.get("timestamp"))
        if event_time is None:
            continue
        event_date = event_time.date()
        if event_date < window_start or event_date > today:
            continue
        count += 1
    return count


def _coerce_datetime(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _normalise_feature(raw: object) -> str:
    if isinstance(raw, str) and raw.strip():
        key = raw.strip().lower()
    else:
        key = "generate"

    mapping = {
        "generate": "Generations",
        "generation": "Generations",
        "img2img": "Image-to-Image",
        "edit": "Edits",
        "upscale": "Upscales",
        "variation": "Variations",
        "workflow": "Workflows",
        "queue": "Workflows",
    }
    return mapping.get(key, key.replace("_", " ").title())


def _normalise_model(entry: Mapping[str, object]) -> str:
    model_used = str(entry.get("model_used") or "").lower()
    type_hint = str(entry.get("model_type_for_enhancer") or "").lower()

    if "qwen" in model_used or "qwen" in type_hint:
        return "Qwen"
    if "sdxl" in model_used or "xl" in model_used:
        return "SDXL"
    if "flux" in model_used or "flux" in type_hint:
        return "Flux"
    if "upscale" in model_used:
        return "Upscaler"
    if "workflow" in model_used:
        return "Workflow"
    return "Other"


__all__ = [
    "AnalyticsReport",
    "DailyUsage",
    "collect_usage_analytics",
]

