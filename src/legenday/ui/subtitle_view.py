"""Painel de legenda com palavras clicáveis (as já salvas no vocabulário ficam destacadas)."""
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QFontMetrics
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
            # "Traduzir a frase": pílula discreta embaixo da legenda, que acende em amarelo ao passar o mouse
            "QPushButton#full{color:#c8c8d2;background:#202028;border:1px solid #2e2e39;border-radius:13px;"
            "padding:4px 14px;font-size:13px;}"
            "QPushButton#full:hover{color:#ffd54a;border-color:#ffd54a;background:#26252a;}"
        )
        self.is_saved = lambda word: False   # definido pela janela principal
        self.hint_text = ""                    # orientação mostrada quando não há legenda na tela
        self.rows = QVBoxLayout(self)
        self.btn = QPushButton("🌐  Traduzir a frase")
        self.btn.setObjectName("full")
        self.btn.setToolTip("Traduz a fala inteira (tecla F): bom para gírias e expressões\n"
                            "que não fazem sentido palavra por palavra")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setFocusPolicy(Qt.NoFocus)
        self.btn.clicked.connect(self.translate_full)
        # escondido entre uma fala e outra, mas sem soltar o lugar: senão a legenda pula a cada fala
        keep = self.btn.sizePolicy()
        keep.setRetainSizeWhenHidden(True)
        self.btn.setSizePolicy(keep)
        self.trans = QLabel()                  # 2ª linha: a fala em português (legenda dupla)
        self.trans.setObjectName("trans")
        self.trans.setWordWrap(True)
        self.trans.setAlignment(Qt.AlignCenter)
        self.trans.hide()
        self.words: list[WordLabel] = []
        self._anchor = None
        self._full = ""
        self._demo = False                     # tour guiado: mostra o botão mesmo sem legenda na tela
        # Altura fixa (cabe 2 linhas): se o painel crescesse e encolhesse com cada fala, empurraria a barra de
        # controles e o vídeo para cima e para baixo. Só cresce se aparecer algo maior, e aí não volta a encolher.
        self._reserved = 0
        self.rows.addStretch()
        self.set_text("")
        self._grow(self._two_lines_height())

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
        self.rows.addSpacing(6)
        # botão fixo embaixo e legenda ancorada logo acima dele (só há espaço livre em cima): a última linha
        # fica sempre na mesma altura e uma fala de 2 linhas cresce para cima, como nos players de vídeo
        self.rows.addWidget(self.btn, alignment=Qt.AlignHCenter)
        self.btn.setVisible(bool(text) or self._demo)
        QTimer.singleShot(0, self, self._fit)        # mede depois que as palavras novas ganharam a fonte do estilo

    def _two_lines_height(self) -> int:
        """Altura para 2 linhas de legenda + o botão, calculada pela fonte (26 px), sem esperar a 1ª fala."""
        font = QFont(self.font())
        font.setPixelSize(26)
        line = QFontMetrics(font).height()
        self.btn.ensurePolished()
        m = self.rows.contentsMargins()
        spacing = max(self.rows.spacing(), 6)
        return m.top() + m.bottom() + 2 * line + 3 * spacing + 6 + self.btn.sizeHint().height()

    def _grow(self, need: int) -> None:
        """Altura FIXA, que só cresce (nunca encolhe): o painel não muda de tamanho a cada fala e não empurra a
        barra de controles nem o vídeo. Só uma fala maior que todas as anteriores (3 linhas) aumenta, uma vez."""
        need = max(need, 120)
        if need > self._reserved:
            self._reserved = need
            self.setFixedHeight(need)

    def _fit(self):
        self.rows.activate()
        self._grow(self.rows.minimumSize().height())

    def set_demo(self, on: bool) -> None:
        """Durante o tour, o botão "Traduzir a frase" aparece mesmo antes de abrir um filme, para ser mostrado."""
        self._demo = on
        self.btn.setVisible(on or bool(self._full))

    def set_translation(self, text: str) -> None:
        """Mostra (ou esconde, se vazio) a fala em português abaixo da legenda."""
        self.trans.setText(text.replace("\n", " ") if text else "")
        self.trans.setVisible(bool(text) and bool(self.words))
        if self.trans.isVisibleTo(self):
            QTimer.singleShot(0, self, self._fit)    # legenda dupla ligada: reserva também a linha em português

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

    def translate_full(self, *_):
        """Pop-up com a fala inteira traduzida (botão "Traduzir a frase" ou tecla F)."""
        if not self._full.strip():
            return
        x = self.mapToGlobal(QPoint(self.width() // 2, 0)).x()          # centralizado sobre a legenda
        self.request_translation.emit(self._full, QPoint(x, self._text_top()))
