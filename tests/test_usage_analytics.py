"""Tests for the usage analytics aggregation helpers."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from services.usage_analytics import collect_usage_analytics


def _write_log(path: Path, payload: dict[str, dict]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_collect_usage_analytics_rollup(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    today_payload = {
        "1": {
            "completion_time": f"{today.isoformat()}T10:00:00",
            "type": "generate",
            "model_used": "Flux: base",
        },
        "2": {
            "completion_time": f"{today.isoformat()}T12:00:00",
            "type": "variation",
            "model_used": "Qwen Image XL",
        },
    }
    _write_log(log_dir / f"{today.isoformat()}-completed.json", today_payload)

    yesterday_payload = {
        "3": {
            "completion_time": f"{yesterday.isoformat()}T09:00:00",
            "type": "upscale",
            "model_used": "SDXL Refiner",
        }
    }
    _write_log(log_dir / f"{yesterday.isoformat()}-completed.json", yesterday_payload)

    cancelled_payload = {
        "4": {
            "cancellation_time": f"{today.isoformat()}T15:00:00",
            "type": "generate",
        }
    }
    _write_log(log_dir / f"{today.isoformat()}-cancelled.json", cancelled_payload)

    report = collect_usage_analytics(log_dir=log_dir, days=2)

    assert report.total_completed == 3
    assert report.total_cancelled == 1
    assert report.feature_totals["Generations"] == 1
    assert report.feature_totals["Variations"] == 1
    assert report.feature_totals["Upscales"] == 1
    assert report.model_totals["Flux"] == 1
    assert report.model_totals["Qwen"] == 1
    assert report.model_totals["SDXL"] == 1

    today_entry = next(entry for entry in report.feature_usage if entry.day == today)
    assert today_entry.counts["Generations"] == 1
    assert today_entry.counts["Variations"] == 1

    yesterday_entry = next(entry for entry in report.feature_usage if entry.day == yesterday)
    assert yesterday_entry.counts["Upscales"] == 1


def test_collect_usage_analytics_empty_directory(tmp_path) -> None:
    report = collect_usage_analytics(log_dir=tmp_path / "missing", days=3)
    assert report.total_completed == 0
    assert report.total_cancelled == 0
    assert report.feature_usage == ()


def test_collect_usage_analytics_requires_positive_days(tmp_path) -> None:
    with pytest.raises(ValueError):
        collect_usage_analytics(log_dir=tmp_path, days=0)


def test_collect_usage_analytics_skips_old_logs(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    old_payload = {
        "1": {
            "completion_time": "2021-01-01T00:00:00",
            "type": "generate",
            "model_used": "Flux: base",
        }
    }
    old_file = log_dir / "old-completed.json"
    _write_log(old_file, old_payload)

    long_ago = datetime.utcnow() - timedelta(days=365)
    timestamp = long_ago.timestamp()
    os.utime(old_file, (timestamp, timestamp))

    report = collect_usage_analytics(log_dir=log_dir, days=7)

    assert report.total_completed == 0
    assert report.feature_usage == ()

