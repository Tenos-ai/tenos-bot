"""First-run onboarding dialog for the Material Configurator."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class FirstRunTutorialDialog(QDialog):
    """Guided walkthrough shown to first-time users."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to Tenos.ai Configurator")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(640, 420)

        self._skipped = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        self._header = QLabel("First-Time Setup")
        self._header.setObjectName("MaterialTitle")
        layout.addWidget(self._header)

        self._step_indicator = QLabel()
        self._step_indicator.setObjectName("MaterialSubtitle")
        layout.addWidget(self._step_indicator)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        for title, body in self._build_steps():
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(12)

            step_title = QLabel(title)
            step_title.setObjectName("MaterialSubtitle")
            page_layout.addWidget(step_title)

            content = QTextBrowser()
            content.setOpenExternalLinks(True)
            content.setFrameShape(QFrame.Shape.NoFrame)
            content.setObjectName("MaterialCard")
            content.setHtml(body)
            page_layout.addWidget(content)

            self._stack.addWidget(page)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(12)

        self._skip_button = QPushButton("Skip tutorial")
        self._skip_button.clicked.connect(self._handle_skip)  # pragma: no cover - UI binding
        controls.addWidget(self._skip_button)

        controls.addStretch()

        self._back_button = QPushButton("Back")
        self._back_button.clicked.connect(self._go_back)  # pragma: no cover - UI binding
        controls.addWidget(self._back_button)

        self._next_button = QPushButton("Next")
        self._next_button.setDefault(True)
        self._next_button.clicked.connect(self._go_forward)  # pragma: no cover - UI binding
        controls.addWidget(self._next_button)

        layout.addLayout(controls)

        self._update_step_labels()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def was_skipped(self) -> bool:
        """Return ``True`` when the dialog was dismissed without finishing."""

        return self._skipped

    # ------------------------------------------------------------------
    # Qt event handlers
    # ------------------------------------------------------------------
    def reject(self) -> None:  # pragma: no cover - UI behaviour
        self._skipped = True
        super().reject()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_steps(self) -> list[tuple[str, str]]:
        return [
            (
                "Welcome aboard!",
                """
                <p>Your download includes everything required to configure the Tenos.ai bot.</p>
                <ul>
                    <li>Use the navigation on the left to jump between configuration areas.</li>
                    <li>The top action bar exposes diagnostics, update tools, and helpful shortcuts.</li>
                </ul>
                """,
            ),
            (
                "Link your Discord bot",
                """
                <p>The <strong>Discord</strong> section guides you through token, guild, and channel setup.</p>
                <ul>
                    <li>Paste your bot token and application ID to connect Tenos.ai to Discord.</li>
                    <li>Point the image and variation channels to where you want content delivered.</li>
                </ul>
                """,
            ),
            (
                "Pick your favourite models",
                """
                <p>Visit the <strong>Workflows</strong> and <strong>Appearance</strong> tabs to tune generation.</p>
                <ul>
                    <li>Select preferred Flux, SDXL, and Qwen checkpoints for quick access.</li>
                    <li>Adjust the Material theme colours or switch between light and dark modes.</li>
                </ul>
                """,
            ),
            (
                "Need help later?",
                """
                <p>You can revisit the official Qwen workflow guide or rerun diagnostics at any time.</p>
                <ul>
                    <li>The <strong>Qwen Guide</strong> button in the top bar opens the latest walkthrough.</li>
                    <li>Diagnostics capture system info to help troubleshoot connectivity issues.</li>
                </ul>
                """,
            ),
        ]

    def _update_step_labels(self) -> None:
        current = self._stack.currentIndex()
        total = self._stack.count()
        self._step_indicator.setText(f"Step {current + 1} of {total}")
        self._back_button.setEnabled(current > 0)
        self._next_button.setText("Finish" if current == total - 1 else "Next")

    def _go_forward(self) -> None:  # pragma: no cover - UI behaviour
        current = self._stack.currentIndex()
        if current >= self._stack.count() - 1:
            self.accept()
            return
        self._stack.setCurrentIndex(current + 1)
        self._update_step_labels()

    def _go_back(self) -> None:  # pragma: no cover - UI behaviour
        current = self._stack.currentIndex()
        if current <= 0:
            return
        self._stack.setCurrentIndex(current - 1)
        self._update_step_labels()

    def _handle_skip(self) -> None:  # pragma: no cover - UI behaviour
        self._skipped = True
        super().reject()


__all__ = ["FirstRunTutorialDialog"]
