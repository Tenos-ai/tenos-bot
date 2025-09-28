"""Animation helpers for the Material configurator."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QAbstractAnimation
from PySide6.QtWidgets import (
    QLabel,
    QGraphicsOpacityEffect,
    QStackedWidget,
    QWidget,
)


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget that fades new pages in for smoother transitions."""

    def __init__(self, parent: Optional[QWidget] = None, *, duration: int = 220) -> None:
        super().__init__(parent)
        self._duration = max(120, duration)
        self._current_animation: Optional[QPropertyAnimation] = None

    def setCurrentIndex(self, index: int) -> None:  # type: ignore[override]
        if index == self.currentIndex():
            return
        widget = self.widget(index)
        if widget is None:
            return
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        super().setCurrentIndex(index)

        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(self._duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        if self._current_animation is not None:
            self._current_animation.stop()
        self._current_animation = animation
        animation.start()

    def setCurrentWidget(self, widget: QWidget) -> None:  # type: ignore[override]
        index = self.indexOf(widget)
        if index != -1:
            self.setCurrentIndex(index)


class StatusPulseAnimator(QPropertyAnimation):
    """Applies a subtle breathing animation to status chips."""

    def __init__(
        self,
        label: QLabel,
        *,
        min_opacity: float = 0.84,
        max_opacity: float = 1.0,
        duration: int = 2400,
    ) -> None:
        self._label = label
        effect = label.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(label)
            label.setGraphicsEffect(effect)
        super().__init__(effect, b"opacity", label)
        self.setDuration(max(600, duration))
        self.setStartValue(max(0.0, min_opacity))
        self.setEndValue(min(1.0, max_opacity))
        self.setEasingCurve(QEasingCurve.InOutSine)
        self.setDirection(QAbstractAnimation.Forward)
        self.finished.connect(self._handle_finished)  # pragma: no cover - Qt binding
        self.start()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Ensure the effect remains attached and animation keeps running."""
        effect = self.targetObject()
        if isinstance(effect, QGraphicsOpacityEffect) and effect.widget() is self._label:
            if self.state() != QAbstractAnimation.Running:
                self.start()
        else:  # the effect was replaced; reattach and restart
            new_effect = QGraphicsOpacityEffect(self._label)
            self._label.setGraphicsEffect(new_effect)
            self.setTargetObject(new_effect)
            self.start()

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------
    def _handle_finished(self) -> None:  # pragma: no cover - Qt binding
        direction = self.direction()
        next_direction = (
            QAbstractAnimation.Backward
            if direction == QAbstractAnimation.Forward
            else QAbstractAnimation.Forward
        )
        self.setDirection(next_direction)
        self.start()


__all__ = ["AnimatedStackedWidget", "StatusPulseAnimator"]
