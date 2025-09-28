"""Administrative analytics view for the Material configurator."""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Iterable

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

try:  # pragma: no cover - optional charts module
    from PySide6.QtCharts import (
        QBarCategoryAxis,
        QBarSeries,
        QBarSet,
        QChart,
        QChartView,
        QDateTimeAxis,
        QLineSeries,
        QValueAxis,
    )

    CHARTS_AVAILABLE = True
except Exception:  # pragma: no cover - gracefully degrade when QtCharts is absent
    QChart = QChartView = None
    CHARTS_AVAILABLE = False

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from services.usage_analytics import AnalyticsReport, DailyUsage


class NetworkMonitorView(BaseView):
    """Render per-feature usage analytics and model utilisation trends."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("Network & Feature Monitor")
        header.setObjectName("MaterialTitle")
        layout.addWidget(header)

        self.summary_label = QLabel("Usage analytics will appear here once collected.")
        self.summary_label.setObjectName("MaterialCard")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        if CHARTS_AVAILABLE:
            self.feature_chart = QChart()
            self.feature_chart.setTitle("Usage per Feature (Last 14 Days)")
            self.feature_chart.legend().setVisible(True)
            self.feature_chart.legend().setAlignment(Qt.AlignBottom)

            self.feature_chart_view = QChartView(self.feature_chart)
            self.feature_chart_view.setRenderHint(QPainter.Antialiasing)
            layout.addWidget(self.feature_chart_view, stretch=1)

            self.model_chart = QChart()
            self.model_chart.setTitle("Model Utilisation (Last 14 Days)")
            self.model_chart.legend().setVisible(True)
            self.model_chart.legend().setAlignment(Qt.AlignBottom)

            self.model_chart_view = QChartView(self.model_chart)
            self.model_chart_view.setRenderHint(QPainter.Antialiasing)
            layout.addWidget(self.model_chart_view, stretch=1)
        else:
            self.feature_table = _build_table_widget("Feature Usage (Last 14 Days)")
            layout.addWidget(self.feature_table)

            self.model_table = _build_table_widget("Model Utilisation (Last 14 Days)")
            layout.addWidget(self.model_table)

        self.status_label = QLabel("Select Admin to load analytics.")
        self.status_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.status_label)

    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - no-op
        del repository

    # ------------------------------------------------------------------
    # Data hooks
    # ------------------------------------------------------------------
    def show_loading(self) -> None:
        self.summary_label.setText("Collecting network analytics…")
        self.status_label.setText("Loading…")
        if CHARTS_AVAILABLE:
            self.feature_chart.removeAllSeries()
            self.model_chart.removeAllSeries()
        else:
            self.feature_table.clearContents()
            self.feature_table.setRowCount(0)
            self.feature_table.setColumnCount(0)
            self.model_table.clearContents()
            self.model_table.setRowCount(0)
            self.model_table.setColumnCount(0)

    def show_report(self, report: AnalyticsReport) -> None:
        summary_parts = [
            f"Completed jobs: {report.total_completed}",
            f"Cancelled jobs: {report.total_cancelled}",
        ]
        if report.feature_totals:
            top_feature = max(report.feature_totals.items(), key=lambda item: item[1])
            summary_parts.append(f"Most used feature: {top_feature[0]} ({top_feature[1]})")
        if report.model_totals:
            top_model = max(report.model_totals.items(), key=lambda item: item[1])
            summary_parts.append(f"Most used model family: {top_model[0]} ({top_model[1]})")

        self.summary_label.setText(" • ".join(summary_parts) or "No activity recorded in the selected window.")

        if CHARTS_AVAILABLE:
            self._populate_feature_chart(report.feature_usage)
            self._populate_model_chart(report.model_usage)
        else:
            self._populate_table(self.feature_table, report.feature_usage)
            self._populate_table(self.model_table, report.model_usage)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        self.status_label.setText(f"Last updated {timestamp}")

    def show_error(self, message: str) -> None:
        self.summary_label.setText(f"Unable to load analytics: {message}")
        self.status_label.setText("Load failed")

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _populate_feature_chart(self, series: Iterable[DailyUsage]) -> None:
        assert CHARTS_AVAILABLE
        self.feature_chart.removeAllSeries()

        data_by_feature: OrderedDict[str, list[float]] = OrderedDict()
        epochs: list[int] = []
        for entry in series:
            dt = QDateTime(entry.day.year, entry.day.month, entry.day.day, 0, 0)
            epoch = dt.toMSecsSinceEpoch()
            epochs.append(epoch)

            for values in data_by_feature.values():
                values.append(0.0)

            for feature, count in entry.counts.items():
                if feature not in data_by_feature:
                    data_by_feature[feature] = [0.0] * len(epochs)
                values = data_by_feature[feature]
                if len(values) < len(epochs):
                    values.extend([0.0] * (len(epochs) - len(values)))
                values[-1] = float(count)

        for feature, values in data_by_feature.items():
            line_series = QLineSeries()
            line_series.setName(feature)
            for index, value in enumerate(values):
                line_series.append(float(epochs[index]), value)
            self.feature_chart.addSeries(line_series)

        if not data_by_feature:
            empty_series = QLineSeries()
            empty_series.setName("No activity")
            self.feature_chart.addSeries(empty_series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM d")
        axis_x.setTickCount(max(2, len(set(epochs))))
        self.feature_chart.addAxis(axis_x, Qt.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        axis_y.setTitleText("Jobs")
        self.feature_chart.addAxis(axis_y, Qt.AlignLeft)

        for series_obj in self.feature_chart.series():
            series_obj.attachAxis(axis_x)
            series_obj.attachAxis(axis_y)

    def _populate_model_chart(self, series: Iterable[DailyUsage]) -> None:
        assert CHARTS_AVAILABLE
        self.model_chart.removeAllSeries()

        categories: list[str] = []
        data_by_model: OrderedDict[str, list[float]] = OrderedDict()
        for entry in series:
            label = entry.day.strftime("%b %d")
            categories.append(label)

            for values in data_by_model.values():
                values.append(0.0)

            for model, count in entry.counts.items():
                if model not in data_by_model:
                    data_by_model[model] = [0.0] * len(categories)
                values = data_by_model[model]
                if len(values) < len(categories):
                    values.extend([0.0] * (len(categories) - len(values)))
                values[-1] = float(count)

        bar_series = QBarSeries()
        for model, values in data_by_model.items():
            bar_set = QBarSet(model)
            for value in values:
                bar_set.append(float(value))
            bar_series.append(bar_set)

        if data_by_model:
            self.model_chart.addSeries(bar_series)
        else:
            placeholder = QBarSet("No activity")
            placeholder.append(0.0)
            bar_series.append(placeholder)
            self.model_chart.addSeries(bar_series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories or ["No data"])
        self.model_chart.addAxis(axis_x, Qt.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        axis_y.setTitleText("Jobs")
        self.model_chart.addAxis(axis_y, Qt.AlignLeft)

        for series_obj in self.model_chart.series():
            series_obj.attachAxis(axis_x)
            series_obj.attachAxis(axis_y)

    def _populate_table(self, table: QTableWidget, series: Iterable[DailyUsage]) -> None:
        ordered = list(series)
        features: OrderedDict[str, None] = OrderedDict()
        for entry in ordered:
            for feature in entry.counts:
                features.setdefault(feature, None)

        table.setColumnCount(len(features) + 1)
        headers = ["Date"] + list(features.keys())
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(ordered))

        for row, entry in enumerate(ordered):
            date_item = QTableWidgetItem(entry.day.strftime("%Y-%m-%d"))
            table.setItem(row, 0, date_item)
            for col, feature in enumerate(features.keys(), start=1):
                value = entry.counts.get(feature, 0)
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col, cell)


def _build_table_widget(title: str) -> QTableWidget:
    table = QTableWidget()
    table.setObjectName("MaterialCardList")
    table.setRowCount(0)
    table.setColumnCount(0)
    table.setStyleSheet(
        "QHeaderView::section {"
        "    background: rgba(59, 130, 246, 0.18);"
        "    color: #F8FAFC;"
        "    padding: 4px 8px;"
        "    border: none;"
        "}"
    )
    table.setCornerButtonEnabled(False)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionMode(QTableWidget.NoSelection)
    table.setShowGrid(False)
    table.setProperty("title", title)
    return table


__all__ = ["NetworkMonitorView"]

