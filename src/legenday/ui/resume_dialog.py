"""Pergunta "continuar de onde parou?" com o nome do vídeo e o tempo."""
from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from legenday.core.resume import clock
from legenday.ui.style import DIALOG_STYLE, MUTED, TEXT


class ResumeDialog(QDialog):
    def __init__(self, parent, path: str, at: float, duration: float, on_start: bool):
        super().__init__(parent)
        self.setWindowTitle("Continuar assistindo?")
        self.setStyleSheet(DIALOG_STYLE + f"""
            QLabel#title {{ color:{TEXT}; font-size:18px; font-weight:bold; }}
            QLabel#file {{ color:{TEXT}; font-size:14px; }}
            QLabel#when {{ color:{MUTED}; font-size:13px; }}""")
        where = f"Você parou em <b>{clock(at)}</b>" + (f" de {clock(duration)}" if duration else "") + "."
        title = QLabel("Continuar assistindo?" if on_start else "Continuar de onde parou?", objectName="title")
        name = QLabel(f"🎬  {escape(Path(path).name)}", objectName="file")
        name.setWordWrap(True)
        name.setTextFormat(Qt.RichText)
        when = QLabel(where, objectName="when")
        when.setTextFormat(Qt.RichText)

        self.continue_btn = QPushButton(f"Continuar de {clock(at)}", objectName="primary")
        self.continue_btn.setDefault(True)
        self.continue_btn.clicked.connect(self.accept)
        self.other_btn = QPushButton("Agora não" if on_start else "Começar do início")
        self.other_btn.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.other_btn)
        buttons.addWidget(self.continue_btn)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(10)
        lay.addWidget(title)
        lay.addWidget(name)
        lay.addWidget(when)
        lay.addSpacing(6)
        lay.addLayout(buttons)
        self.setMinimumWidth(440)

    @staticmethod
    def ask(parent, path: str, at: float, duration: float, on_start: bool = False) -> bool:
        """True = continuar de onde parou."""
        return ResumeDialog(parent, path, at, duration, on_start).exec() == QDialog.Accepted
