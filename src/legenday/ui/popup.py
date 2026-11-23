"""Pop-up com tradução, forma base, definições e botão para salvar no vocabulário."""
from html import escape

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

POS_PT = {"noun": "substantivo", "verb": "verbo", "adjective": "adjetivo", "adverb": "advérbio",
          "pronoun": "pronome", "preposition": "preposição", "conjunction": "conjunção",
          "interjection": "interjeição", "exclamation": "exclamação", "article": "artigo",
          "determiner": "determinante", "abbreviation": "abreviação"}


def esc(text) -> str:
    return escape(str(text or ""), quote=False)


class TranslationPopup(QFrame):
    closed = Signal()
    save_requested = Signal(object)
    play_requested = Signal(str)       # link do áudio da pronúncia

    def __init__(self):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.setStyleSheet(
            "QFrame{background:#1d1d24;border:1px solid #ffd54a;border-radius:12px;}"
            "QLabel{border:none;color:#ececf1;}"
            "QPushButton{border:1px solid #ffd54a;color:#ffd54a;background:rgba(255,213,74,0.10);"
            "border-radius:10px;padding:0 12px;min-height:34px;font-size:13px;font-weight:600;}"
            "QPushButton:hover{background:#ffd54a;color:#111;}"
            "QPushButton:pressed{background:#e6bf3f;color:#111;}"
            # já salvo: verde, para a confirmação ficar óbvia
            "QPushButton:disabled{border-color:#2f5a3c;color:#8fd6a2;background:rgba(80,190,120,0.10);}"
            "QPushButton#sound{border:1px solid #2e2e39;background:#26262f;border-radius:14px;padding:0;"
            "min-height:0;font-size:14px;}"
            "QPushButton#sound:hover{background:#34343e;border-color:#ffd54a;}"
        )
        self.setFixedWidth(380)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        self.head, self.pt, self.extra = QLabel(), QLabel(), QLabel()
        self.sound_btn = QPushButton("🔊")
        self.sound_btn.setObjectName("sound")
        self.sound_btn.setFixedSize(28, 28)
        self.sound_btn.setToolTip("Ouvir a pronúncia")
        self.sound_btn.setCursor(Qt.PointingHandCursor)
        self.sound_btn.setFocusPolicy(Qt.NoFocus)
        self.sound_btn.clicked.connect(self._on_sound)
        self.sound_btn.hide()
        head_row = QHBoxLayout()
        head_row.setSpacing(4)
        head_row.addWidget(self.head, 1)
        head_row.addWidget(self.sound_btn, 0, Qt.AlignTop)
        lay.addLayout(head_row)
        for lbl in (self.head, self.pt, self.extra):
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(True)
        lay.addWidget(self.pt)
        lay.addWidget(self.extra)
        self.save_btn = QPushButton("☆  Salvar no vocabulário")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setFocusPolicy(Qt.NoFocus)
        self.save_btn.clicked.connect(self._on_save)
        lay.addWidget(self.save_btn)
        self._anchor = QPoint()
        self._result = None
        self._saved_label = None

    # --- conteúdo
    def _set_head(self, text: str, phonetic: str = ""):
        size, weight = (18, "bold") if len(text) <= 40 else (14, "normal")
        html = f"<span style='color:#ffd54a;font-size:{size}px;font-weight:{weight}'>{esc(text)}</span>"
        if phonetic:
            html += f" <span style='color:#9a9aa6;font-size:13px'>{esc(phonetic)}</span>"
        self.head.setText(html)

    def show_at(self, anchor: QPoint, term: str):
        self._anchor, self._result, self._saved_label = anchor, None, None
        self._set_head(term)
        self.sound_btn.hide()
        self.pt.setText("<span style='color:#9a9aa6'>Traduzindo…</span>")
        self.extra.setVisible(False)
        self.save_btn.setText("☆  Salvar no vocabulário")
        self.save_btn.setEnabled(False)
        self._place()
        self.show()

    def set_result(self, res, loading: bool = False):
        self._result = res
        self._set_head(res.text, res.phonetic)
        self.sound_btn.setVisible(bool(getattr(res, "audio", "")))
        pt = f"<span style='font-size:16px'>{esc(res.translation)}</span>"
        alts = [a for a in getattr(res, "alternatives", []) if a != res.translation][:3]
        if alts:                                    # outros sentidos: a palavra solta pode querer dizer outra coisa
            pt += ("<br><span style='color:#9a9aa6'>também:</span> "
                   + " <span style='color:#6f6f7a'>·</span> ".join(esc(a) for a in alts))
        self.pt.setText(pt)
        parts = []
        if res.lemma:
            base = f"<span style='color:#9a9aa6'>forma base:</span> <b>{esc(res.lemma)}</b>"
            if res.lemma_translation:
                base += f" → {esc(res.lemma_translation)}"
            parts.append(base)
        if getattr(res, "context_translation", None):   # a fala inteira traduzida: o sentido no filme
            parts.append(f"<span style='color:#9a9aa6'>na frase:</span> "
                         f"<i style='color:#e8e8ee'>{esc(res.context_translation)}</i>")
        for pos, definition, example in res.meanings[:3]:
            line = f"<span style='color:#ffd54a'>{esc(POS_PT.get(pos, pos))}</span> · {esc(definition)}"
            if example:
                line += f"<br><i style='color:#9a9aa6'>“{esc(example)}”</i>"
            parts.append(line)
        if loading:
            parts.append("<span style='color:#9a9aa6'>carregando o contexto e a definição…</span>")
        self.extra.setText("<br><br>".join(parts))
        self.extra.setVisible(bool(parts))
        if self._saved_label:                       # o estado "salvo" não some quando chegam os detalhes
            self.save_btn.setText(self._saved_label)
            self.save_btn.setEnabled(False)
        else:
            self.save_btn.setEnabled(True)
        self._place()

    def set_error(self, message: str):
        self.pt.setText(f"<span style='color:#ff8a80'>⚠ {esc(message)}</span>")
        self.extra.setVisible(False)
        self._place()

    def mark_saved(self, text: str = "✓  Salvo no vocabulário"):
        self._saved_label = text
        self.save_btn.setText(text)
        self.save_btn.setEnabled(False)

    def _on_save(self):
        if self._result is not None:
            self.save_requested.emit(self._result)

    def _on_sound(self):
        if self._result is not None and getattr(self._result, "audio", ""):
            self.play_requested.emit(self._result.audio)

    # --- posição e fechamento
    def _place(self):
        lay = self.layout()
        lay.activate()
        self.setFixedHeight(max(lay.totalHeightForWidth(self.width()), 60))
        screen = QGuiApplication.screenAt(self._anchor) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = min(max(self._anchor.x() - self.width() // 2, geo.left()), geo.right() - self.width())
        y = max(self._anchor.y() - self.height() - 8, geo.top())
        self.move(x, y)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.closed.emit()
