"""Tour guiado: na primeira vez, escurece a janela e destaca cada parte com uma explicação curta.

É uma janela transparente por cima da principal, e não um widget filho: a área do vídeo é uma janela nativa do
mpv, e um widget comum não consegue ser desenhado por cima dela.
"""
from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from legenday.core import settings
from legenday.ui.style import ACCENT, DIALOG_STYLE, MUTED, TEXT

CARD_STYLE = DIALOG_STYLE + f"""
QFrame#card {{ background:#1d1d24; border:1px solid #3a3a46; border-radius:14px; }}
QLabel#counter {{ color:{ACCENT}; font-size:11px; font-weight:bold; }}
QLabel#title {{ color:{TEXT}; font-size:17px; font-weight:bold; }}
QLabel#body {{ color:#c8c8d2; font-size:13px; }}
QPushButton#flat {{ background:transparent; border:none; color:{MUTED}; padding:0 4px; }}
QPushButton#flat:hover {{ color:{TEXT}; }}
"""
SHADE = QColor(8, 8, 12, 190)      # o escuro em volta do destaque
GAP = 16                           # distância entre o destaque e o cartão
MARGIN = 14                        # o cartão nunca encosta na borda da janela


@dataclass
class Step:
    title: str
    text: str
    targets: Callable[[], list] = field(default=lambda: [])   # vazio = cartão no meio, sem destaque


def steps_for(win) -> list[Step]:
    c = win.controls
    return [
        Step("Bem-vindo ao legenDay! 👋",
             "Aqui você aprende inglês assistindo filmes: clique numa palavra da legenda e veja a tradução na "
             "hora.<br><br>Em 1 minuto eu mostro para que serve cada botão."),
        Step("1. Abra o filme",
             "Clique em <b>Vídeo</b> e escolha o arquivo do filme ou episódio.<br>"
             "Também dá para <b>arrastar o arquivo</b> para dentro da janela.",
             lambda: [c.btn_video]),
        Step("2. Abra a legenda em inglês",
             "Se o arquivo <b>.srt</b> tiver o mesmo nome do vídeo e estiver na mesma pasta, ele abre sozinho.<br>"
             "Senão, clique em <b>Legenda</b> e escolha o arquivo (ou arraste o .srt para a janela).",
             lambda: [c.btn_sub]),
        Step("3. Clique numa palavra",
             "A legenda aparece <b>aqui embaixo</b>, e não em cima do vídeo.<br>"
             "Clique em qualquer palavra: o vídeo pausa e mostra a tradução, a pronúncia 🔊 e a frase traduzida. "
             "<b>Espaço</b> continua o vídeo.<br><br>"
             "Dica: segure <b>Shift</b> e clique em várias palavras para traduzir uma expressão.",
             lambda: [win.subview]),
        Step("Controles do vídeo",
             "Play e pausa (<b>Espaço</b>), voltar e avançar 10 segundos e ir para a fala anterior ou a próxima.<br>"
             "Não entendeu o que falaram? A fala anterior (tecla <b>R</b>) toca de novo.",
             lambda: c.nav_buttons),
        Step("Modos de estudo",
             "<b>Repetir</b>: o vídeo pausa no fim de cada fala para você repetir em voz alta.<br>"
             "<b>PT</b>: mostra a fala em português embaixo da inglesa.",
             lambda: [c.btn_shadow, c.btn_dual]),
        Step("Suas palavras",
             "No pop-up da tradução, <b>Salvar no vocabulário</b> guarda a palavra junto com a frase do filme.<br>"
             "Aqui você vê todas, <b>revisa com cartões</b> e exporta para o Anki.",
             lambda: [c.btn_vocab]),
        Step("Legenda fora do tempo?",
             "Se a legenda aparece antes ou depois da fala, use <b>−</b> e <b>+</b> até alinhar. "
             "O app lembra o ajuste de cada filme.",
             lambda: [c.sync_btn.parentWidget()]),
        Step("Pronto!",
             "Ficou com dúvida? Clique no <b>?</b> (ou aperte <b>F1</b>) para ver a ajuda completa e os atalhos. "
             "Por lá você também pode rever este tour."
             + ("<br><br>Se o app te ajudar, o <b>♥</b> ao lado aceita um PIX de qualquer valor."
                if c.btn_donate.isVisibleTo(c) else "")
             + "<br><br>Bons estudos!",
             lambda: [c.btn_help, c.btn_donate]),
    ]


class Tour(QWidget):
    finished = Signal()

    def __init__(self, win):
        # Dialog (e não Tool): com Tool, os atalhos da janela principal continuariam valendo e a seta avançaria o
        # vídeo em vez do tour. Sem moldura e "dona" da janela principal: fica por cima dela e fora da barra de tarefas.
        super().__init__(win, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self.win = win
        self.steps = steps_for(win)
        self.i = 0
        self.hole = QRect()

        self.card = card = QFrame(self)
        card.setObjectName("card")
        card.setStyleSheet(CARD_STYLE)
        card.setFixedWidth(370)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        card.setGraphicsEffect(shadow)

        self.counter = QLabel(objectName="counter")
        self.title = QLabel(objectName="title")
        self.title.setWordWrap(True)
        self.body = QLabel(objectName="body")
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.RichText)
        self.skip_btn = QPushButton("Pular tour", objectName="flat")
        self.back_btn = QPushButton("Voltar")
        self.next_btn = QPushButton("Próximo", objectName="primary")
        for b, slot in ((self.skip_btn, self.finish), (self.back_btn, self.back), (self.next_btn, self.next)):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)          # as teclas ficam com o tour (setas, Enter, Esc)
            b.clicked.connect(slot)

        buttons = QHBoxLayout()
        buttons.addWidget(self.skip_btn)
        buttons.addStretch()
        buttons.addWidget(self.back_btn)
        buttons.addWidget(self.next_btn)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(8)
        lay.addWidget(self.counter)
        lay.addWidget(self.title)
        lay.addWidget(self.body)
        lay.addSpacing(6)
        lay.addLayout(buttons)

        win.installEventFilter(self)              # acompanha a janela quando ela muda de lugar ou de tamanho

    # ------------------------------------------------------------ navegação
    def start(self):
        self._follow()
        self.go(0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def go(self, i: int):
        self.i = i
        step = self.steps[i]
        last = i == len(self.steps) - 1
        self.counter.setText(f"{i + 1} DE {len(self.steps)}")
        self.title.setText(step.title)
        self.body.setText(step.text)
        self.back_btn.setVisible(i > 0)
        self.skip_btn.setVisible(not last)
        self.next_btn.setText("Começar a usar" if last else ("Vamos lá" if i == 0 else "Próximo"))
        self._place()

    def next(self):
        if self.i == len(self.steps) - 1:
            self.finish()
        else:
            self.go(self.i + 1)

    def back(self):
        if self.i > 0:
            self.go(self.i - 1)

    def finish(self):
        settings.put("tour_seen", True)
        self.win.removeEventFilter(self)
        self.close()
        self.win.activateWindow()
        self.finished.emit()

    # ------------------------------------------------------------ posição
    def _follow(self):
        self.setGeometry(QRect(self.win.mapToGlobal(QPoint(0, 0)), self.win.size()))

    def _target_rect(self) -> QRect:
        rect = QRect()
        for w in self.steps[self.i].targets():
            if w is not None and w.isVisible():
                rect = rect.united(QRect(w.mapTo(self.win, QPoint(0, 0)), w.size()))
        return rect.adjusted(-8, -8, 8, 8) if not rect.isNull() else QRect()

    def _place(self):
        """Destaque em volta do alvo; cartão logo acima dele (ou abaixo, se não couber), sempre dentro da janela."""
        self.hole = self._target_rect()
        card = self.card
        # altura exata para o texto com quebra de linha (adjustSize sobra espaço em cartões de texto curto)
        w = card.width()
        h = card.layout().totalHeightForWidth(w)
        card.resize(w, h)
        if self.hole.isNull():
            x, y = (self.width() - w) // 2, (self.height() - h) // 2
        else:
            x = self.hole.center().x() - w // 2
            y = self.hole.top() - GAP - h
            if y < MARGIN:
                y = self.hole.bottom() + GAP
            if y + h > self.height() - MARGIN:
                y = max(MARGIN, (self.height() - h) // 2)
        x = max(MARGIN, min(x, self.width() - w - MARGIN))
        card.move(x, y)
        self.update()

    def eventFilter(self, obj, event):
        if obj is self.win:
            kind = event.type()
            if kind in (QEvent.Move, QEvent.Resize, QEvent.WindowStateChange):
                self._follow()
                self._place()
            elif kind == QEvent.Close:
                self.close()
        return False

    # ------------------------------------------------------------ desenho e teclas
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        shade = QPainterPath()
        shade.setFillRule(Qt.OddEvenFill)
        shade.addRect(QRectF(self.rect()))
        if not self.hole.isNull():
            hole = QRectF(self.hole)
            shade.addRoundedRect(hole, 12, 12)
            # quase transparente, mas não 100%: um pixel totalmente transparente deixaria o clique passar para o
            # botão embaixo no meio do tour
            p.fillRect(hole, QColor(0, 0, 0, 1))
        p.fillPath(shade, SHADE)
        if not self.hole.isNull():
            p.setPen(QPen(QColor(ACCENT), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(self.hole), 12, 12)

    def mousePressEvent(self, event):
        event.accept()                            # clicar fora do cartão não faz nada (nem mexe no app embaixo)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Right, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.next()
        elif key in (Qt.Key_Left, Qt.Key_Backspace):
            self.back()
        elif key == Qt.Key_Escape:
            self.finish()
        else:
            super().keyPressEvent(event)
