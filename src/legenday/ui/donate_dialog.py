"""Janela "Apoie o legenDay": QR Code do PIX e botões para copiar a chave ou o código copia e cola."""
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from legenday.branding import APP_NAME, PIX_CITY, PIX_KEY, PIX_NAME
from legenday.core.pix import payload
from legenday.ui.style import ACCENT, DIALOG_STYLE, MUTED, TEXT


class QrCode(QWidget):
    """Desenha o QR Code (preto no branco, com margem branca: alguns apps de banco não leem sem ela)."""

    def __init__(self, text: str, size: int = 220):
        super().__init__()
        import segno
        self.matrix = [list(row) for row in segno.make(text, error="m").matrix]
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("white"))
        p.drawRoundedRect(QRectF(self.rect()), 12, 12)
        n = len(self.matrix)
        quiet = 3                                       # margem branca, em "quadradinhos"
        cell = self.width() / (n + 2 * quiet)
        p.setBrush(QColor("#111"))
        for y, row in enumerate(self.matrix):
            for x, dark in enumerate(row):
                if dark:
                    p.drawRect(QRectF((x + quiet) * cell, (y + quiet) * cell, cell + 0.4, cell + 0.4))


class DonateDialog(QDialog):
    def __init__(self, parent=None, key: str = PIX_KEY, name: str = PIX_NAME, city: str = PIX_CITY):
        super().__init__(parent)
        self.key = key
        self.code = payload(key, name, city)
        self.setWindowTitle(f"Apoie o {APP_NAME}")
        self.setStyleSheet(DIALOG_STYLE + f"""
            QLabel#title {{ color:{TEXT}; font-size:20px; font-weight:bold; }}
            QLabel#text {{ color:#c8c8d2; font-size:13px; }}
            QLabel#key {{ color:{ACCENT}; font-size:13px; }}
            QLabel#how {{ color:{MUTED}; font-size:12px; }}""")

        title = QLabel(f"Apoie o {APP_NAME} ☕", objectName="title")
        text = QLabel(f"O {APP_NAME} é gratuito e de código aberto. Se ele está te ajudando no inglês, um PIX de "
                      "<b>qualquer valor</b> ajuda a manter o projeto e a pagar o café das próximas versões. "
                      "Muito obrigado! 💛", objectName="text")
        text.setWordWrap(True)
        text.setTextFormat(Qt.RichText)
        how = QLabel("No app do seu banco: PIX → Ler QR Code (ou Pix Copia e Cola).", objectName="how")
        how.setAlignment(Qt.AlignCenter)
        key_label = QLabel(f"Chave PIX: {key}", objectName="key")
        key_label.setAlignment(Qt.AlignCenter)
        key_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.copy_key_btn = QPushButton("Copiar chave")
        self.copy_key_btn.clicked.connect(lambda: self._copy(self.key, self.copy_key_btn, "Copiar chave"))
        self.copy_code_btn = QPushButton("Copiar código copia e cola")
        self.copy_code_btn.setObjectName("primary")
        self.copy_code_btn.clicked.connect(
            lambda: self._copy(self.code, self.copy_code_btn, "Copiar código copia e cola"))
        close = QPushButton("Fechar")
        close.clicked.connect(self.accept)

        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(QrCode(self.code))
        qr_row.addStretch()
        buttons = QHBoxLayout()
        buttons.addWidget(self.copy_key_btn)
        buttons.addWidget(self.copy_code_btn)
        buttons.addStretch()
        buttons.addWidget(close)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 18)
        lay.setSpacing(12)
        lay.addWidget(title)
        lay.addWidget(text)
        lay.addSpacing(4)
        lay.addLayout(qr_row)
        lay.addWidget(how)
        lay.addWidget(key_label)
        lay.addSpacing(6)
        lay.addLayout(buttons)
        self.setFixedWidth(500)

    @staticmethod
    def _copy(text: str, button: QPushButton, label: str):
        QApplication.clipboard().setText(text)
        button.setText("Copiado ✓")
        # ligado ao botão: se a janela fechar antes dos 2 s, o temporizador é cancelado junto
        QTimer.singleShot(2000, button, lambda: button.setText(label))
