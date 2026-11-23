"""Revisão das palavras salvas, em cartões: tente lembrar, veja a resposta e diga se acertou.

A agenda (caixas de Leitner, em study.py) traz de volta antes o que você erra e espaça o que você acerta.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from legenday.core.vocab import highlight
from legenday.ui.popup import esc
from legenday.ui.style import ACCENT, DIALOG_STYLE

STYLE = DIALOG_STYLE + f"""
QFrame#card {{ background:#1c1c22; border:1px solid #2e2e38; border-radius:12px; }}
QLabel#progress {{ color:#9a9aa6; font-size:13px; }}
QPushButton#good {{ background:{ACCENT}; color:#111; font-weight:bold; }}
QPushButton#good:hover {{ background:#ffe17d; }}
QPushButton#bad {{ background:#3a2a2e; color:#ffb4a8; }}
QPushButton#bad:hover {{ background:#4a3036; }}
"""


class ReviewDialog(QDialog):
    """`scene` (opcional): objeto com can_play(word) e play(word), para ouvir a fala do filme."""

    def __init__(self, vocab, parent=None, scene=None):
        super().__init__(parent)
        self.vocab, self.scene = vocab, scene
        self.setWindowTitle("Revisar palavras")
        self.resize(640, 520)
        self.setStyleSheet(STYLE)
        self.words = vocab.due()
        self.i, self.right, self.revealed = 0, 0, False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        self.progress = QLabel()
        self.progress.setObjectName("progress")
        lay.addWidget(self.progress)

        card = QFrame()
        card.setObjectName("card")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(24, 22, 24, 22)
        inner.setSpacing(10)
        self.term, self.sentence, self.answer = QLabel(), QLabel(), QLabel()
        for lbl in (self.term, self.sentence, self.answer):
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignCenter)
        inner.addStretch()
        inner.addWidget(self.term)
        inner.addWidget(self.sentence)
        self.scene_btn = self._btn("▶  Ouvir a fala no filme", self._play_scene)
        inner.addWidget(self.scene_btn, alignment=Qt.AlignCenter)
        inner.addSpacing(8)
        inner.addWidget(self.answer)
        inner.addStretch()
        lay.addWidget(card, 1)

        row = QHBoxLayout()
        self.show_btn = self._btn("Mostrar resposta  (Espaço)", self.reveal, "primary")
        self.bad_btn = self._btn("Errei  (1)", lambda: self.grade(False), "bad")
        self.good_btn = self._btn("Acertei  (2)", lambda: self.grade(True), "good")
        self.close_btn = self._btn("Fechar", self.accept)
        row.addWidget(self.close_btn)
        row.addStretch()
        for b in (self.show_btn, self.bad_btn, self.good_btn):
            row.addWidget(b)
        lay.addLayout(row)

        for key, fn in ((Qt.Key_Space, self._space), (Qt.Key_1, lambda: self._answer(False)),
                        (Qt.Key_2, lambda: self._answer(True))):
            QShortcut(QKeySequence(key), self, activated=fn)
        self._show_card()

    @staticmethod
    def _btn(text, slot, name=None) -> QPushButton:
        b = QPushButton(text)
        b.setFocusPolicy(Qt.NoFocus)            # o Espaço é da revisão, não do botão em foco
        b.setCursor(Qt.PointingHandCursor)
        if name:
            b.setObjectName(name)
        b.clicked.connect(slot)
        return b

    @property
    def current(self):
        return self.words[self.i] if self.i < len(self.words) else None

    def _show_card(self):
        w = self.current
        self.revealed = False
        self.answer.clear()
        if w is None:
            self._finish()
            return
        self.progress.setText(f"Cartão {self.i + 1} de {len(self.words)}")
        phon = f"<br><span style='color:#9a9aa6;font-size:15px'>{esc(w.phonetic)}</span>" if w.phonetic else ""
        self.term.setText(f"<span style='color:{ACCENT};font-size:34px;font-weight:bold'>{esc(w.term)}</span>{phon}")
        film = f"<br><span style='color:#6f6f7a;font-size:12px'>{esc(w.video)}</span>" if w.video else ""
        self.sentence.setText(f"<span style='color:#d4d4dc;font-size:17px'><i>{highlight(w.sentence, w.term)}</i>"
                              f"</span>{film}" if w.sentence else "")
        self.scene_btn.setVisible(bool(self.scene and self.scene.can_play(w)))
        self.show_btn.setVisible(True)
        self.bad_btn.setVisible(False)
        self.good_btn.setVisible(False)

    def reveal(self):
        w = self.current
        if w is None or self.revealed:
            return
        self.revealed = True
        parts = [f"<span style='font-size:24px;color:#ffffff'>{esc(w.translation)}</span>"]
        if w.lemma and w.lemma.lower() != w.term.lower():
            parts.append(f"<span style='color:#9a9aa6'>forma base:</span> <b>{esc(w.lemma)}</b>")
        if w.definition:
            parts.append(f"<span style='color:#9a9aa6;font-size:13px'>{esc(w.definition)}</span>")
        self.answer.setText("<br>".join(parts))
        self.show_btn.setVisible(False)
        self.bad_btn.setVisible(True)
        self.good_btn.setVisible(True)

    def grade(self, correct: bool):
        w = self.current
        if w is None or not self.revealed:
            return
        try:
            self.vocab.review(w.id, correct)
        except Exception:
            pass                       # não conseguiu gravar: a revisão segue, a palavra volta da próxima vez
        self.right += int(correct)
        self.i += 1
        self._show_card()

    def _space(self):
        if self.current is None:
            self.accept()
        elif not self.revealed:
            self.reveal()

    def _answer(self, correct: bool):
        if self.revealed:
            self.grade(correct)

    def _play_scene(self):
        if self.scene and self.current is not None:
            self.scene.play(self.current)

    def _finish(self):
        self.scene_btn.hide()
        for b in (self.show_btn, self.bad_btn, self.good_btn):
            b.hide()
        total = len(self.words)
        self.progress.setText("")
        if total == 0:
            self.term.setText(f"<span style='color:{ACCENT};font-size:26px;font-weight:bold'>Tudo em dia!</span>")
            self.sentence.setText("<span style='color:#9a9aa6'>Nenhuma palavra para revisar agora.<br>"
                                  "Salve palavras no pop-up da legenda e elas aparecem aqui.</span>")
        else:
            self.term.setText(f"<span style='color:{ACCENT};font-size:26px;font-weight:bold'>Revisão concluída!</span>")
            self.sentence.setText(f"<span style='color:#d4d4dc;font-size:17px'>Você acertou {self.right} de {total}."
                                  "</span><br><span style='color:#9a9aa6'>As que você errou voltam ainda hoje; "
                                  "as que acertou, daqui a alguns dias.</span>")
