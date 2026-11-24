"""Janela principal: junta vídeo (mpv), barra de controles, legenda clicável e os recursos de estudo.

As partes ficam em módulos próprios: controls (barra), translation_flow (pop-up e vocabulário),
dual (legenda em português), study (modo repetir frase e revisão) e player (acesso protegido ao mpv).
"""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from legenday import __version__
from legenday.branding import APP_NAME
from legenday.core import audio_tracks, embedded, settings
from legenday.core.paths import data_dir
from legenday.core.settings import load_offset, save_offset
from legenday.core.study import Shadowing
from legenday.core.subtitles import SUB_EXTS, SubtitleTrack, find_sidecar, find_sidecar_pt, load_subtitles
from legenday.core.vocab import VocabStore
from legenday.playback.player import SoundPlayer, create_video_player
from legenday.services import lookup, updates
from legenday.ui.controls import COMPACT_BELOW, ControlBar
from legenday.ui.donate_dialog import DonateDialog
from legenday.ui.dual import DualSubtitles
from legenday.ui.help_dialog import HelpDialog
from legenday.ui.review_dialog import ReviewDialog
from legenday.ui.style import main_style
from legenday.ui.subtitle_view import SubtitleView
from legenday.ui.tour import Tour
from legenday.ui.translation_flow import TranslationFlow
from legenday.ui.vocab_dialog import VocabDialog
from legenday.ui.workers import TaskRunner

SUB_FILTER = "Legendas (*.srt *.ass *.ssa *.vtt);;Todos (*)"


class MainWindow(QMainWindow):
    def __init__(self, player=None, sound=None):
        """`player`/`sound`: nos testes, versões falsas; no app, None (cria o mpv de verdade)."""
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setStyleSheet(main_style())
        self.setAcceptDrops(True)      # arrastar um vídeo ou uma legenda para a janela abre o arquivo
        self.track: SubtitleTrack | None = None
        self.video_path = None
        self._sub_key = None
        self._shown_ids = None         # falas na tela (para só redesenhar quando mudam)
        self._shown_paused = None
        self._stop_at = None           # "ouvir a fala no filme": pausa sozinho no fim dela
        self._tracks = None            # None = ainda procurando; lista = faixas embutidas encontradas
        self._embedded_error = None
        self._auto_embedded = False
        self._help = None
        self._tour = None
        self.vocab = VocabStore()
        self.tasks = TaskRunner(self)
        self.shadow = Shadowing()

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.video = QWidget()
        self.video.setAttribute(Qt.WA_NativeWindow)
        self.video.setStyleSheet("background:black;")
        self.video.setMinimumHeight(360)
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v.addWidget(self.video, 1)

        self.sub_menu = QMenu(self)
        self.audio_menu = QMenu(self)
        self.audio_menu.aboutToShow.connect(self._rebuild_audio_menu)
        self.controls = ControlBar(self.sub_menu, self.audio_menu)
        v.addWidget(self.controls)
        self._connect_controls()

        self.subview = SubtitleView()
        v.addWidget(self.subview)
        self.statusBar().setSizeGripEnabled(False)

        self.player = player or create_video_player(int(self.video.winId()))
        self.player.set("alang", audio_tracks.PREFERRED_LANGS)   # começa pelo áudio em inglês, se o vídeo tiver
        self.sound = sound or SoundPlayer()
        self.flow = TranslationFlow(self, self.sound)
        self.popup = self.flow.popup
        self.subview.is_saved = self.flow.is_saved
        self.subview.request_translation.connect(self.flow.show)
        self.dual = DualSubtitles(self)

        self._install_shortcuts()
        self._rebuild_sub_menu()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)   # ~25 vezes por segundo: a legenda troca no máximo 40 ms depois do mpv
        self.refresh_vocab()
        self._update_hint()
        if not settings.get("tour_seen"):          # primeira vez: tour guiado pelos botões
            QTimer.singleShot(700, self.start_tour)
        else:
            QTimer.singleShot(800, self._announce_reviews)
        self.tasks.run(lookup.warmup)              # lematizador e endereço dos serviços, antes do primeiro clique
        self.update_btn = None
        self.tasks.run(updates.check, self._on_update_check)   # saiu versão nova no GitHub?

    def _connect_controls(self):
        c = self.controls
        c.open_video.connect(lambda: self.open_video())
        c.show_vocab.connect(self.show_vocab)
        c.show_help.connect(self.show_help)
        c.show_donate.connect(self.show_donate)
        c.play_pause.connect(self.toggle_pause)
        c.prev_line.connect(self.prev_line)
        c.next_line.connect(self.next_line)
        c.skip.connect(self.skip)
        c.seek.connect(lambda ms, final: self._seek(ms / 1000, "absolute", "exact" if final else "keyframes"))
        c.speed_changed.connect(self._on_speed)
        c.sync_changed.connect(self.adjust_sync)
        c.sync_reset.connect(self.reset_sync)
        c.volume_changed.connect(lambda x: self.player.set("volume", x))
        c.shadow_toggled.connect(self.set_shadowing)
        c.dual_toggled.connect(self.set_dual)

    def _install_shortcuts(self):
        shortcuts = (
            (Qt.Key_Space, self.toggle_pause), (Qt.Key_Return, self.toggle_pause), (Qt.Key_Enter, self.toggle_pause),
            (Qt.Key_R, self.repeat_line), (Qt.Key_Left, lambda: self.skip(-5)), (Qt.Key_Right, lambda: self.skip(5)),
            (Qt.Key_F11, self.toggle_fullscreen), (Qt.Key_F1, self.show_help),
            (Qt.Key_G, lambda: self.adjust_sync(-0.1)), (Qt.Key_H, lambda: self.adjust_sync(0.1)),
            (QKeySequence("Shift+G"), lambda: self.adjust_sync(-1.0)),
            (QKeySequence("Shift+H"), lambda: self.adjust_sync(1.0)), (Qt.Key_Y, self.align_here),
            (Qt.Key_P, lambda: self.set_shadowing(not self.shadow.enabled)),
            (Qt.Key_T, lambda: self.set_dual(not self.dual.enabled)),
        )
        # Valem na janela principal e no pop-up (que é outra janela), mas não em diálogos como o de
        # vocabulário: lá as setas e o Espaço navegam na tabela em vez de mexer no vídeo.
        self._shortcuts = []
        for owner in (self, self.popup):
            for key, fn in shortcuts:
                sc = QShortcut(QKeySequence(key), owner)
                sc.setContext(Qt.WindowShortcut)
                sc.activated.connect(fn)
                self._shortcuts.append(sc)

    # ------------------------------------------------------------ helpers
    def _seek(self, amount, ref="absolute", precision="exact"):
        self.shadow.reset()            # depois de um pulo, a fala pode pausar de novo
        self._stop_at = None
        self.player.seek(amount, ref, precision)

    def notify(self, text: str, ms: int = 2500):
        """Aviso grande e bem visível, desenhado pelo mpv no topo do vídeo (aparece até em tela cheia).
        Sem vídeo em reprodução, usa a barra de status no rodapé."""
        if self.player.time is not None and self.player.command("show-text", text.replace("$", "$$"), str(ms)):
            return
        self.statusBar().showMessage(text.replace("\n", " — "), ms)

    def clear_notice(self):
        if self.player.time is not None:
            self.player.command("show-text", "", "1")
        self.statusBar().clearMessage()

    def line_start(self) -> float:
        """Início da fala atual (no tempo do vídeo); usado para voltar a ela na revisão."""
        t = self.player.time or 0.0
        if self.track:
            i = self.track.active_at(t)
            i = i if i >= 0 else self.track.index_at(t)
            if i >= 0:
                return self.track.start_of(i)
        return t

    # ------------------------------------------------------------ vídeo e legendas
    def open_video(self, path: str | bool = False):
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Escolher vídeo", "", "Vídeos (*.mkv *.mp4 *.avi *.mov *.webm);;Todos (*)")
        if not path:
            return
        self.player.play(path)
        self.player.paused = False
        self.video_path, self._tracks, self._embedded_error = path, None, None
        self.dual.set_track(None)
        self._update_hint()
        sub = find_sidecar(path)
        self._auto_embedded = sub is None       # sem legenda ao lado: tenta a embutida em inglês
        if sub:
            self.open_subtitle(str(sub), notice=False)   # o aviso espera o vídeo começar a tocar
            QTimer.singleShot(1200, lambda n=sub.name: self.notify(f"Legenda carregada:\n{n}", 3000))
        pt = find_sidecar_pt(path)
        if pt:
            self.open_pt_subtitle(str(pt), notice=False)
        self._rebuild_sub_menu()
        self.tasks.run(lambda: embedded.probe(path), lambda r: self._on_probe(path, r))
        QTimer.singleShot(3200, self._announce_audio)

    def open_subtitle(self, path: str | bool = False, notice: bool = True):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Escolher legenda", "", SUB_FILTER)
        if not path:
            return
        try:
            track = load_subtitles(path)
        except Exception as exc:
            QMessageBox.warning(self, "Legenda", str(exc))
            return
        track.offset = load_offset(path)
        self.track, self._sub_key = track, path
        self._shown_ids = None                  # força redesenhar a legenda
        self.shadow.reset()
        self._update_hint()
        self.controls.set_sync(track.offset)
        if notice:
            self.notify(f"Legenda carregada:\n{Path(path).name}", 3000)

    def open_pt_subtitle(self, path: str | bool = False, notice: bool = True):
        """Legenda em português para a 2ª linha (legenda dupla)."""
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Escolher legenda em português", "", SUB_FILTER)
        if not path:
            return
        try:
            self.dual.set_track(load_subtitles(path), path)
        except Exception as exc:
            QMessageBox.warning(self, "Legenda em português", str(exc))
            return
        self._shown_ids = None
        self._rebuild_sub_menu()
        if notice:
            if not self.dual.enabled:
                self.set_dual(True)
            self.notify(f"Legenda em português (2ª linha):\n{Path(path).name}", 3000)

    def _rebuild_sub_menu(self):
        m = self.sub_menu
        m.clear()
        m.addAction("Abrir arquivo de legenda…").triggered.connect(lambda _=False: self.open_subtitle())
        m.addAction("Abrir legenda em português (2ª linha)…").triggered.connect(
            lambda _=False: self.open_pt_subtitle())
        if self.dual.track is not None:
            m.addAction(f"Usar tradução automática na 2ª linha (em vez de {Path(self.dual.path).name})"
                        ).triggered.connect(lambda _=False: self._drop_pt_subtitle())
        m.addSeparator()

        def note(text):
            m.addAction(text).setEnabled(False)

        if not self.video_path:
            note("Abra um vídeo para ver as legendas embutidas")
        elif self._tracks is None:
            note("Procurando legendas embutidas…")
        elif self._embedded_error == "ffmpeg":
            note("Legendas embutidas: ffmpeg não encontrado (veja o README)")
        elif self._embedded_error:
            note("Não foi possível ler as legendas embutidas")
        else:
            text_tracks = [t for t in self._tracks if t.text]
            for t in text_tracks:
                m.addAction("Embutida: " + t.label).triggered.connect(
                    lambda _=False, t=t: self.load_embedded(t))
            if not text_tracks:
                note("Nenhuma legenda embutida em texto")
            image_tracks = len(self._tracks) - len(text_tracks)
            if image_tracks:
                note(f"({image_tracks} faixa(s) em imagem, não suportada(s))")

    def _drop_pt_subtitle(self):
        self.dual.set_track(None)
        self._shown_ids = None
        self._rebuild_sub_menu()

    def _on_probe(self, video, payload):
        if video != self.video_path:
            return
        if isinstance(payload, embedded.FFmpegNotFound):
            self._tracks, self._embedded_error = [], "ffmpeg"
        elif isinstance(payload, Exception):
            self._tracks, self._embedded_error = [], str(payload)
        else:
            self._tracks, self._embedded_error = payload, None
        self._rebuild_sub_menu()
        if self._auto_embedded and self._tracks:
            pick = embedded.pick_english(self._tracks)
            if pick:
                self.load_embedded(pick)

    def load_embedded(self, track):
        video = self.video_path
        self.notify("Extraindo a legenda embutida…\nPode levar alguns segundos", 600000)
        self.tasks.run(lambda: embedded.extract(video, track), lambda r: self._on_extracted(video, r))

    def _on_extracted(self, video, payload):
        if video != self.video_path:
            return
        if isinstance(payload, Exception):
            self.clear_notice()
            QMessageBox.warning(self, "Legenda embutida", str(payload))
            return
        self.open_subtitle(str(payload), notice=False)
        self.notify("Legenda embutida carregada", 3000)

    # ------------------------------------------------------------ áudio
    def _audio_tracks(self) -> list:
        return audio_tracks.audio_tracks(self.player.get("track_list"))

    def _rebuild_audio_menu(self):
        m = self.audio_menu
        m.clear()
        tracks = self._audio_tracks()
        if not self.video_path or not tracks:
            m.addAction("Abra um vídeo para escolher o áudio" if not self.video_path
                        else "Este vídeo não tem faixas de áudio").setEnabled(False)
            return
        for t in tracks:
            mark = "✓  " if t.get("selected") else "      "
            m.addAction(mark + audio_tracks.label(t)).triggered.connect(lambda _=False, t=t: self.set_audio(t))

    def set_audio(self, track: dict):
        self.player.set("aid", track["id"])
        self.notify(f"Áudio: {audio_tracks.label(track)}", 2500)

    def _announce_audio(self):
        """Avisa qual áudio está tocando, quando o vídeo tem mais de uma faixa."""
        tracks = self._audio_tracks()
        if len(tracks) > 1:
            current = next((t for t in tracks if t.get("selected")), tracks[0])
            self.notify(f"Áudio: {audio_tracks.label(current)}\nOutras faixas: botão Áudio", 3000)

    # ------------------------------------------------------------ ajuda
    def _update_hint(self):
        """Orientação na área da legenda enquanto ainda falta o vídeo ou a legenda."""
        if self.track:
            hint = ""
        elif self.video_path:
            hint = "Agora escolha a legenda no botão de legendas (ou aguarde, se o vídeo tiver legenda embutida)."
        else:
            hint = "Para começar, abra um filme com o botão da pasta (Vídeo).\nDúvidas? Clique no ? ou aperte F1."
        self.subview.hint_text = hint
        if not self.subview.words:      # só redesenha se não houver legenda na tela
            self.subview.set_text(self.subview.full_text)

    def diagnostics(self) -> str:
        import platform

        import PySide6
        return "\n".join([
            f"{APP_NAME} {__version__}",
            f"Python {platform.python_version()} · {platform.platform()}",
            f"PySide6 {PySide6.__version__} · {self.player.get('mpv_version', 'mpv ?')}",
            f"ffmpeg: {embedded.find_ffmpeg() or 'não encontrado'}",
            f"Dados: {data_dir()}",
        ])

    def show_help(self, *_):
        if self._help is not None and self._help.isVisible():
            self._help.raise_()
            self._help.activateWindow()
            return
        self._help = HelpDialog(self, self.diagnostics(), on_tour=self.start_tour)
        self._help.show()

    def show_donate(self, *_):
        DonateDialog(self).exec()

    def _on_update_check(self, result):
        """Versão nova no GitHub: botão no rodapé que abre a página de download. Sem internet, não faz nada."""
        if not isinstance(result, updates.Update) or self.update_btn is not None:
            return
        self.update_btn = QPushButton(f"⬆  Nova versão {result.version} disponível · Baixar")
        self.update_btn.setObjectName("update")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setFocusPolicy(Qt.NoFocus)
        self.update_btn.setToolTip(f"Você está usando a {__version__}. Clique para abrir a página de download.")
        self.update_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(result.url)))
        self.statusBar().addPermanentWidget(self.update_btn)

    def start_tour(self, *_):
        """Tour guiado pelos botões (sozinho na primeira vez; depois, pela ajuda)."""
        if self._tour is not None or not self.isVisible():
            return
        self.popup.close()
        for sc in self._shortcuts:          # durante o tour, setas/Espaço/Enter são do tour, não do vídeo
            sc.setEnabled(False)
        self._tour = Tour(self)
        self._tour.finished.connect(self._tour_done)
        self._tour.start()

    def _tour_done(self):
        self._tour = None
        for sc in self._shortcuts:
            sc.setEnabled(True)

    def _announce_reviews(self):
        try:
            n = self.vocab.due_count()
        except Exception:
            return
        if n:
            self.statusBar().showMessage(f"Você tem {n} palavra(s) para revisar hoje: botão Palavras → Revisar", 10000)

    # ------------------------------------------------------------ sincronia
    def adjust_sync(self, delta: float):
        if not self.track:
            return
        self.track.offset = round(self.track.offset + delta, 2)
        self._after_sync_change(delta)

    def align_here(self):
        """Alinha a legenda com a fala: aperte Y no instante em que ouvir o início de uma frase.
        A fala da legenda mais próxima desse instante passa a começar exatamente agora."""
        t = self.player.time
        if not self.track or t is None:
            return
        i = self.track.index_at(t)
        near = min({max(i, 0), min(i + 1, len(self.track.cues) - 1)}, key=lambda k: abs(self.track.start_of(k) - t))
        delta = t - self.track.start_of(near)
        if abs(delta) > 60:
            self.notify("Diferença grande demais (mais de 60 s).\nAjuste com os botões − e +", 3000)
            return
        self.track.offset = round(self.track.offset + delta, 2)
        self._after_sync_change(aligned=True)

    def reset_sync(self):
        if self.track:
            self.track.offset = 0.0
            self._after_sync_change()

    def _after_sync_change(self, delta=None, aligned=False):
        try:
            save_offset(self._sub_key, self.track.offset)
        except OSError:
            pass                      # não conseguiu lembrar o ajuste, mas ele vale nesta sessão
        self.controls.set_sync(self.track.offset)
        self._shown_ids = None
        self.shadow.reset()
        total = f"{self.track.offset:+.1f}".replace(".", ",")
        if aligned:
            self.notify(f"Legenda alinhada com a fala\nSincronia: {total}s", 2500)
        elif delta is None:
            self.notify("Sincronia da legenda zerada", 2000)
        else:
            what = "adiantada" if delta < 0 else "atrasada"
            self.notify(f"Legenda {what} {abs(delta):.1f}s\nSincronia: {total}s".replace(".", ","), 2500)

    # ------------------------------------------------------------ controles
    def toggle_pause(self):
        if self.flow.close_and_resume():   # Espaço/Enter com o pop-up aberto: fecha e continua o vídeo
            return
        self.player.paused = not self.player.paused

    def _on_speed(self, speed: float):
        self.player.set("speed", speed)
        self.notify(f"Velocidade {speed:g}x".replace(".", ","), 1500)

    def skip(self, seconds: int):
        self._seek(seconds, "relative")
        self.notify(f"{'+' if seconds > 0 else '-'}{abs(seconds)}s", 900)

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def repeat_line(self):
        t = self.player.time
        if self.track and t is not None:
            self._seek(self.track.start_of(max(self.track.index_at(t), 0)))
            self.player.paused = False
            self.notify("Repetindo a frase", 1200)

    def prev_line(self):
        """Como em players de música: se já passou de 1,5s da frase, repete ela; senão volta uma."""
        t = self.player.time
        if not self.track or t is None:
            return
        i = self.track.index_at(t)
        target = i if i >= 0 and t - self.track.start_of(i) > 1.5 else max(i - 1, 0)
        self._seek(self.track.start_of(target))
        self.notify("Repetindo a frase" if target == i else "Frase anterior", 1200)

    def next_line(self):
        t = self.player.time
        if not self.track or t is None:
            return
        i = self.track.index_at(t) + 1
        if i < len(self.track.cues):
            self._seek(self.track.start_of(i))
            self.notify("Próxima frase", 1200)

    # ------------------------------------------------------------ recursos de estudo
    def set_shadowing(self, on: bool):
        self.shadow.enabled = on
        self.shadow.reset()
        self.controls.set_checked(self.controls.btn_shadow, on)
        self.notify("Modo repetir frase: ligado\nO vídeo pausa no fim de cada fala · Espaço continua"
                    if on else "Modo repetir frase: desligado", 2500)

    def set_dual(self, on: bool):
        self.dual.set_enabled(on)
        self.controls.set_checked(self.controls.btn_dual, on)
        if on:
            self.dual.update(self.subview.full_text, self.player.time or 0.0)
        self.notify(f"Legenda em português: ligada ({self.dual.source})" if on else
                    "Legenda em português: desligada", 2000)

    def play_line(self, position: float):
        """Toca só a fala que começa em `position` e pausa no fim dela (usado na revisão)."""
        self._seek(max(position - 0.2, 0.0))
        i = self.track.index_at(position + 0.05) if self.track else -1
        self._stop_at = self.track.end_of(i) + 0.2 if i >= 0 else position + 4.0
        self.player.paused = False

    # interface usada pela revisão para "ouvir a fala no filme"
    def can_play(self, word) -> bool:
        return bool(word.video and self.video_path and Path(self.video_path).name == word.video)

    def play(self, word) -> None:
        self.play_line(word.position)

    # ------------------------------------------------------------ relógio
    def _tick(self):
        player = self.player
        t, paused = player.time, player.paused
        if paused != self._shown_paused:
            self._shown_paused = paused
            self.controls.set_paused(paused)
        if t is None:
            return
        self.controls.set_position(t, player.duration or 0)
        if not paused and self._stop_at is not None and t >= self._stop_at:
            self._stop_at = None
            player.paused = True
        if not self.track:
            return
        if not paused and self.shadow.should_pause(self.track, t):
            player.paused = True
            self.notify("Sua vez: repita a frase em voz alta\nEspaço continua · R ouve de novo", 2500)
        ids = tuple(self.track.active_all(t))
        if ids != self._shown_ids:
            self._shown_ids = ids
            if self.popup.isVisible():
                self.popup.close()
            text = "\n".join(dict.fromkeys(self.track.cues[i].text for i in ids))
            self.subview.set_text(text)
            self.dual.update(text, t)

    # ------------------------------------------------------------ vocabulário
    def refresh_vocab(self):
        try:
            self.flow.vocab_keys = self.vocab.keys()
            n = self.vocab.count()
        except Exception as exc:     # banco inacessível: o app segue funcionando, sem vocabulário
            self.flow.vocab_keys, n = set(), None
            self.statusBar().showMessage(f"Vocabulário indisponível: {exc}", 8000)
        self.controls.set_vocab_count(n)
        self.subview.refresh_saved()

    def show_vocab(self, *_):
        was_playing = not self.player.paused
        self.player.paused = True
        try:
            dlg = VocabDialog(self.vocab, self, on_review=self.show_review)
        except Exception as exc:
            QMessageBox.warning(self, "Vocabulário", f"Não foi possível abrir o vocabulário: {exc}")
            self.player.paused = not was_playing
            return
        dlg.changed.connect(self.refresh_vocab)
        dlg.exec()
        self.refresh_vocab()
        self.player.paused = not was_playing

    def show_review(self, parent=None):
        ReviewDialog(self.vocab, parent or self, scene=self).exec()
        self.player.paused = True
        self.refresh_vocab()

    # ------------------------------------------------------------ janela
    @staticmethod
    def _dropped_files(event) -> list[str]:
        md = event.mimeData()
        return [str(Path(u.toLocalFile())) for u in md.urls() if u.isLocalFile()] if md.hasUrls() else []

    def dragEnterEvent(self, event):
        if self._dropped_files(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Solta um vídeo (abre e acha a legenda ao lado) e/ou uma legenda (.srt, .ass...)."""
        files = self._dropped_files(event)
        subs = [f for f in files if Path(f).suffix.lower() in SUB_EXTS]
        videos = [f for f in files if f not in subs]
        if videos:
            self.open_video(videos[0])
        if subs:
            self.open_subtitle(subs[0])
        event.acceptProposedAction()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.controls.set_compact(self.width() < COMPACT_BELOW)

    def closeEvent(self, event):
        self.timer.stop()
        self.popup.close()
        self.tasks.wait(1000)
        self.player.terminate()
        self.sound.terminate()
        super().closeEvent(event)
