"""Painel de legenda com palavras clicáveis (as já salvas no vocabulário ficam destacadas)."""
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from legenday.core.subtitles import split_chunk


class WordLabel(QLabel):
    clicked = Signal(int, bool)

    def __init__(self, text: str, index: int, saved: bool = False):
        super().__init__(text)
        self.index = index
        self.setObjectName("word")
        self.setIndent(0)  # sem recuo interno automático do QLabel
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("saved", saved)

    def _repolish(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def set_selected(self, on: bool):
        self.setProperty("sel", on)
        self._repolish()

    def set_saved(self, on: bool):
        if self.property("saved") != on:
            self.setProperty("saved", on)
            self._repolish()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index, bool(event.modifiers() & Qt.ShiftModifier))


class SubtitleView(QWidget):
    """Painel de legenda (fica abaixo do vídeo). Cada palavra é um QLabel clicável."""
    request_translation = Signal(str, QPoint)

    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            "SubtitleView{background:#111;}"
            "QLabel{color:white;font-size:26px;}"
            "QLabel#hint{color:#8a8a96;font-size:15px;}"
            "QLabel#trans{color:#9fb7cc;font-size:19px;padding-top:4px;}"
            "QLabel#word{padding:0 1px;border-radius:4px;}"
            "QLabel#word:hover{background:#3a3a44;}"
            'QLabel#word[saved="true"]{color:#ffd54a;}'
            'QLabel#word[sel="true"]{background:#ffd54a;color:#111;}'
            "QPushButton{color:#aaa;background:transparent;border:none;font-size:12px;}"
            "QPushButton:hover{color:white;}"
        )
        self.setMinimumHeight(120)
        self.is_saved = lambda word: False   # definido pela janela principal
        self.hint_text = ""                    # orientação mostrada quando não há legenda na tela
        self.rows = QVBoxLayout(self)
        self.btn = QPushButton("🌐 traduzir frase inteira")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setFocusPolicy(Qt.NoFocus)
        self.btn.clicked.connect(self._on_full)
        self.trans = QLabel()                  # 2ª linha: a fala em português (legenda dupla)
        self.trans.setObjectName("trans")
        self.trans.setWordWrap(True)
        self.trans.setAlignment(Qt.AlignCenter)
        self.trans.hide()
        self.words: list[WordLabel] = []
        self._anchor = None
        self._full = ""
        self.rows.addStretch()
        self.set_text("")

    @property
    def full_text(self) -> str:
        return self._full

    def _clear(self):
        def purge(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget() and item.widget() not in (self.btn, self.trans):
                    item.widget().deleteLater()
                elif item.layout():
                    purge(item.layout())
                    item.layout().deleteLater()
        self.btn.setParent(self)
        self.trans.setParent(self)
        purge(self.rows)
        self.words.clear()
        self._anchor = None

    def set_text(self, text: str):
        self._clear()
        self._full = " ".join(text.split("\n"))
        self.rows.addStretch()
        for line in text.split("\n") if text else []:
            row = QHBoxLayout()
            row.setSpacing(0)
            row.addStretch()
            for chunk in line.split():
                lead, core, trail = split_chunk(chunk)
                if lead:
                    row.addWidget(QLabel(lead))
                if core:
                    lbl = WordLabel(core, len(self.words), self.is_saved(core))
                    lbl.clicked.connect(self._on_click)
                    self.words.append(lbl)
                    row.addWidget(lbl)
                row.addWidget(QLabel(trail + " "))
            row.addStretch()
            self.rows.addLayout(row)
        if not text and self.hint_text:
            hint = QLabel(self.hint_text)
            hint.setObjectName("hint")
            hint.setWordWrap(True)
            hint.setAlignment(Qt.AlignCenter)
            self.rows.addWidget(hint)
        self.rows.addWidget(self.trans)
        self.trans.clear()
        self.trans.hide()
        self.rows.addStretch()
        self.rows.addWidget(self.btn, alignment=Qt.AlignRight)
        self.btn.setVisible(bool(text))

    def set_translation(self, text: str) -> None:
        """Mostra (ou esconde, se vazio) a fala em português abaixo da legenda."""
        self.trans.setText(text.replace("\n", " ") if text else "")
        self.trans.setVisible(bool(text) and bool(self.words))

    def refresh_saved(self):
        """Reavalia quais palavras da legenda atual estão no vocabulário (sem refazer a legenda)."""
        for w in self.words:
            w.set_saved(self.is_saved(w.text()))

    def _select(self, lo: int, hi: int):
        for i, w in enumerate(self.words):
            w.set_selected(lo <= i <= hi)

    def clear_selection(self):
        self._select(1, 0)

    def _on_click(self, idx: int, shift: bool):
        if shift and self._anchor is not None:
            lo, hi = sorted((self._anchor, idx))
        else:
            self._anchor = lo = hi = idx
        self._select(lo, hi)
        phrase = " ".join(w.text() for w in self.words[lo:hi + 1])
        label = self.words[idx]
        x = label.mapToGlobal(QPoint(label.width() // 2, 0)).x()
        self.request_translation.emit(phrase, QPoint(x, self._text_top()))

    def _text_top(self) -> int:
        """Topo da 1ª linha da legenda: o pop-up abre acima dela e não cobre nenhuma linha."""
        if not self.words:
            return self.mapToGlobal(QPoint(0, 0)).y()
        return min(w.mapToGlobal(QPoint(0, 0)).y() for w in self.words)

    def _on_full(self):
        x = self.mapToGlobal(QPoint(self.width() // 2, 0)).x()          # centralizado sobre a legenda
        self.request_translation.emit(self._full, QPoint(x, self._text_top()))
