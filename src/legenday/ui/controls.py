"""Barra de controles do player: botões, barra de tempo, velocidade, sincronia e volume.

Não sabe nada do mpv: só emite sinais (o que o usuário pediu) e mostra o estado que a janela informa.
"""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
)

from legenday.ui.icons import make_icon, toggle_icon

SPEEDS = (0.5, 0.75, 1.0, 1.25, 1.5)
COMPACT_BELOW = 1440      # abaixo dessa largura, os botões da esquerda mostram só o ícone


def fmt(sec: float) -> str:
    sec = int(max(sec, 0))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def sync_step() -> float:
    """0,1 s; com Shift pressionado, 1 s."""
    return 1.0 if QApplication.keyboardModifiers() & Qt.ShiftModifier else 0.1


class ControlBar(QFrame):
    open_video = Signal()
    show_vocab = Signal()
    show_help = Signal()
    play_pause = Signal()
    prev_line = Signal()
    next_line = Signal()
    skip = Signal(int)                  # segundos (negativo = voltar)
    seek = Signal(int, bool)            # (milissegundos, soltou o mouse)
    speed_changed = Signal(float)
    sync_changed = Signal(float)        # quanto adiantar (-) ou atrasar (+) a legenda
    sync_reset = Signal()
    volume_changed = Signal(int)
    shadow_toggled = Signal(bool)       # modo repetir frase
    dual_toggled = Signal(bool)         # legenda dupla (português embaixo)

    def __init__(self, sub_menu: QMenu, audio_menu: QMenu):
        super().__init__()
        self.setObjectName("controls")
        self._compact = False
        self._vocab_n = None
        self.icon_play = make_icon("play", "#111")
        self.icon_pause = make_icon("pause", "#111")

        col = QVBoxLayout(self)
        col.setContentsMargins(16, 8, 16, 10)
        col.setSpacing(4)

        seek_row = QHBoxLayout()
        self.time_cur, self.time_tot = QLabel("0:00"), QLabel("0:00")
        self.time_cur.setObjectName("time")
        self.time_tot.setObjectName("time")
        self.time_tot.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.slider = SeekSlider()
        self.slider.seek.connect(self._on_seek)
        seek_row.addWidget(self.time_cur)
        seek_row.addWidget(self.slider, 1)
        seek_row.addWidget(self.time_tot)
        col.addLayout(seek_row)

        # esquerda: [Vídeo | Legenda | Áudio]  (Palavras)  [Repetir | PT]  (?)
        left = QHBoxLayout()
        left.setSpacing(8)
        self.btn_video = self._button("folder", "Vídeo", "Abrir vídeo", self.open_video.emit)
        self.btn_sub = self._button("subs", "Legenda",
                                    "Legendas: abrir arquivo, usar uma embutida ou a 2ª em português", menu=sub_menu)
        self.btn_audio = self._button("audio", "Áudio", "Escolher a faixa de áudio", menu=audio_menu)
        left.addWidget(self._segment(self.btn_video, self.btn_sub, self.btn_audio))
        self.btn_vocab = BadgeButton(make_icon("list"), " Palavras")
        self._setup(self.btn_vocab, "Palavras salvas: revisar, excluir e exportar para o Anki", self.show_vocab.emit)
        self.btn_vocab.setObjectName("pill")
        left.addWidget(self.btn_vocab)
        self.btn_shadow = self._toggle("repeat", "Repetir",
                                       "Modo repetir frase (P): o vídeo pausa no fim de cada fala para você repetir"
                                       " em voz alta.\nEspaço continua, R ouve a fala de novo.", self.shadow_toggled)
        self.btn_dual = self._toggle("dual", "PT", "Legenda dupla (T): mostra a fala em português embaixo da inglesa",
                                     self.dual_toggled)
        left.addWidget(self._segment(self.btn_shadow, self.btn_dual))
        self.btn_help = QToolButton()
        self.btn_help.setText("?")
        self.btn_help.setObjectName("help")
        self.btn_help.setFixedSize(34, 34)
        self._setup(self.btn_help, "Ajuda e atalhos (F1)", self.show_help.emit)
        left.addWidget(self.btn_help)
        left.addStretch()
        self._labels = {self.btn_video: " Vídeo", self.btn_sub: " Legenda", self.btn_audio: " Áudio",
                        self.btn_shadow: " Repetir", self.btn_dual: " PT"}

        # centro: frase anterior, -10 s, play, +10 s, próxima frase
        center = QHBoxLayout()
        center.setSpacing(6)
        btn_prev = self._tool("prev", "Repetir / frase anterior (R)", self.prev_line.emit)
        btn_back = self._tool("back", "Voltar 10s", lambda: self.skip.emit(-10))
        center.addWidget(btn_prev)
        center.addWidget(btn_back)
        self.btn_play = self._tool("play", "Play / pause (Espaço)", self.play_pause.emit, size=26, box=48, name="play")
        self.btn_play.setIcon(self.icon_play)
        glow = QGraphicsDropShadowEffect(self.btn_play)     # brilho amarelo suave em volta do play
        glow.setBlurRadius(26)
        glow.setOffset(0, 2)
        glow.setColor(QColor(255, 213, 74, 95))
        self.btn_play.setGraphicsEffect(glow)
        center.addSpacing(4)
        center.addWidget(self.btn_play)
        center.addSpacing(4)
        btn_fwd = self._tool("fwd", "Avançar 10s", lambda: self.skip.emit(10))
        btn_next = self._tool("next", "Próxima frase", self.next_line.emit)
        center.addWidget(btn_fwd)
        center.addWidget(btn_next)
        self.nav_buttons = [btn_prev, btn_back, self.btn_play, btn_fwd, btn_next]   # o tour destaca o grupo todo

        # direita: velocidade  [− | ⏱ +0,0s | +]  volume
        right = QHBoxLayout()
        right.setSpacing(8)
        right.addStretch()
        self.speed = QComboBox()
        self.speed.setToolTip("Velocidade")
        self.speed.setFocusPolicy(Qt.NoFocus)
        self.speed.setCursor(Qt.PointingHandCursor)
        self.speed.setFixedWidth(80)
        self.speed.addItems([f"{s:g}x".replace(".", ",") for s in SPEEDS])
        self.speed.setCurrentIndex(SPEEDS.index(1.0))
        self.speed.currentIndexChanged.connect(lambda i: self.speed_changed.emit(SPEEDS[i]))
        right.addWidget(self.speed)
        minus = self._step("−", "Adiantar a legenda 0,1s (G) · Shift+G: 1s\nUse se ela aparece depois da fala.",
                           lambda: self.sync_changed.emit(-sync_step()))
        plus = self._step("+", "Atrasar a legenda 0,1s (H) · Shift+H: 1s\nUse se ela aparece antes da fala.",
                          lambda: self.sync_changed.emit(sync_step()))
        self.sync_btn = QToolButton()
        self.sync_btn.setObjectName("sync")
        self.sync_btn.setIcon(make_icon("sync", "#9a9aa6"))
        self.sync_btn.setIconSize(QSize(14, 14))
        self.sync_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._setup(self.sync_btn, "Sincronia da legenda (clique para zerar)\n"
                    "Tecla Y: alinhar com a fala que você acabou de ouvir", self.sync_reset.emit)
        right.addWidget(self._segment(minus, self.sync_btn, plus))
        right.addWidget(self._separator())
        self.btn_mute = self._tool("volume", "Silenciar / voltar o som", self._toggle_mute, size=20, box=34)
        right.addWidget(self.btn_mute)
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setValue(100)
        self.vol.setFixedWidth(84)
        self.vol.setFocusPolicy(Qt.NoFocus)
        self.vol.setCursor(Qt.PointingHandCursor)
        self.vol.valueChanged.connect(self._on_volume)
        self._vol_before_mute = 100
        right.addWidget(self.vol)
        self.set_sync(0.0)

        row = QHBoxLayout()
        row.addLayout(left, 1)
        row.addLayout(center)
        row.addLayout(right, 1)
        col.addLayout(row)

    # ------------------------------------------------------------ fábrica de botões
    @staticmethod
    def _tool(kind, tip, slot, size=22, box=40, name=None) -> QToolButton:
        b = QToolButton()
        b.setIcon(make_icon(kind))
        b.setIconSize(QSize(size, size))
        b.setFixedSize(box, box)
        b.setToolTip(tip)
        b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus)
        if name:
            b.setObjectName(name)
        b.clicked.connect(slot)
        return b

    @staticmethod
    def _setup(b, tip, slot=None):
        b.setToolTip(tip)
        b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus)
        if slot:
            b.clicked.connect(slot)
        return b

    def _step(self, text, tip, slot) -> QToolButton:
        """O "−" e o "+" da sincronia."""
        b = QToolButton()
        b.setText(text)
        b.setObjectName("step")
        return self._setup(b, tip, slot)

    def _button(self, kind, text, tip, slot=None, icon=None, menu=None) -> QPushButton:
        """Botão com ícone e texto, para ir dentro de um grupo segmentado."""
        b = QPushButton(icon or make_icon(kind), " " + text)
        b.setIconSize(QSize(17, 17))
        if menu is not None:
            b.setMenu(menu)
            b.setProperty("hasMenu", True)          # abre espaço para a setinha desenhada pelo app
        return self._setup(b, tip, slot)

    def _toggle(self, kind, text, tip, signal) -> QPushButton:
        b = self._button(kind, text, tip, icon=toggle_icon(kind))
        b.setCheckable(True)
        b.toggled.connect(signal.emit)
        return b

    @staticmethod
    def _segment(*buttons) -> QFrame:
        """Trilho com botões irmãos dentro (Vídeo|Legenda|Áudio, Repetir|PT, sincronia)."""
        box = QFrame()
        box.setObjectName("segment")
        box.setFixedHeight(36)                      # mesma altura das pílulas, sem esticar até o play
        lay = QHBoxLayout(box)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        for b in buttons:
            lay.addWidget(b)
        return box

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setObjectName("sep")
        line.setFixedSize(1, 22)
        return line

    # ------------------------------------------------------------ volume
    def _on_volume(self, value: int) -> None:
        self.btn_mute.setIcon(make_icon("volume_off" if value == 0 else "volume"))
        self.volume_changed.emit(value)

    def _toggle_mute(self) -> None:
        if self.vol.value() > 0:
            self._vol_before_mute = self.vol.value()
            self.vol.setValue(0)
        else:
            self.vol.setValue(self._vol_before_mute or 100)

    # ------------------------------------------------------------ estado mostrado
    def _on_seek(self, ms: int, final: bool):
        self.time_cur.setText(fmt(ms / 1000))
        self.seek.emit(ms, final)

    def set_paused(self, paused: bool) -> None:
        self.btn_play.setIcon(self.icon_play if paused else self.icon_pause)

    def set_position(self, t: float, duration: float) -> None:
        if duration and not self.slider.isSliderDown():
            ms = int(duration * 1000)
            if self.slider.maximum() != ms:
                self.slider.setRange(0, ms)
            self.slider.setValue(int(t * 1000))
            self.time_cur.setText(fmt(t))
        self.time_tot.setText(fmt(duration or 0))

    def set_sync(self, offset: float) -> None:
        self.sync_btn.setText(f" {offset:+.1f}s".replace(".", ","))

    def set_vocab_count(self, n) -> None:
        self._vocab_n = n
        self._update_vocab_text()

    def set_checked(self, button: QPushButton, on: bool) -> None:
        """Liga/desliga um botão sem disparar o sinal de novo (quando o atalho de teclado muda o estado)."""
        button.blockSignals(True)
        button.setChecked(on)
        button.blockSignals(False)

    def _update_vocab_text(self) -> None:
        self.btn_vocab.setText("" if self._compact else " Palavras")
        self.btn_vocab.set_badge("" if not self._vocab_n else str(self._vocab_n))

    def set_compact(self, on: bool) -> None:
        if on == self._compact:
            return
        self._compact = on
        for btn, text in self._labels.items():
            btn.setText("" if on else text)
        self._update_vocab_text()


class BadgeButton(QPushButton):
    """Botão com um selo amarelo de contagem à direita (ex.: Palavras  8)."""

    def __init__(self, icon, text):
        super().__init__(icon, text)
        self.setIconSize(QSize(17, 17))
        self.badge = QLabel(self)
        self.badge.setObjectName("badge")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedHeight(18)
        self.badge.setAttribute(Qt.WA_TransparentForMouseEvents)   # o clique vai para o botão
        self.badge.hide()

    def set_badge(self, text: str) -> None:
        self.badge.setText(text)
        self.badge.setVisible(bool(text))
        self.badge.adjustSize()
        # o estilo (style.py) reserva espaço à direita quando há selo; uma propriedade, e não um setStyleSheet
        # aqui, porque o estilo do botão também valeria para o selo, que é filho dele
        self.setProperty("badge", bool(text))
        self.style().unpolish(self)
        self.style().polish(self)
        self._place_badge()

    def _place_badge(self) -> None:
        self.badge.move(self.width() - self.badge.width() - 10, (self.height() - self.badge.height()) // 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_badge()


class SeekSlider(QSlider):
    """Barra de tempo: clique pula direto para o ponto; arrastar também funciona.
    Emite seek(ms, final): final=False durante o arrasto, True ao soltar."""
    seek = Signal(int, bool)

    def __init__(self):
        super().__init__(Qt.Horizontal)
        self.setFixedHeight(22)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def _value_at(self, x: float) -> int:
        span = max(self.width() - 14, 1)  # 14 = largura do botão deslizante
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), int(x - 7), span)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or self.maximum() == 0:
            return
        self.setSliderDown(True)
        v = self._value_at(e.position().x())
        self.setValue(v)
        self.seek.emit(v, False)

    def mouseMoveEvent(self, e):
        if self.isSliderDown():
            v = self._value_at(e.position().x())
            self.setValue(v)
            self.seek.emit(v, False)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.isSliderDown():
            self.setSliderDown(False)
            self.seek.emit(self.value(), True)
