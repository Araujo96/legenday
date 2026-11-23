"""Legenda dupla: a fala em português aparece menor, embaixo da inglesa.

Usa uma legenda em português (arquivo .srt ao lado do vídeo ou aberto pelo menu) quando houver: é melhor e não
gasta a cota diária do serviço de tradução gratuito. Sem ela, traduz cada fala na hora (com cache), e já
adianta a tradução da próxima fala para ela aparecer sem espera.
"""
from PySide6.QtCore import QObject

from legenday.services import translator


class DualSubtitles(QObject):
    def __init__(self, win, translate=translator.translate):
        super().__init__(win)
        self.win = win
        self.translate = translate
        self.enabled = False
        self.track = None          # legenda em português (SubtitleTrack) ou None = tradução automática
        self.path = None
        self._shown = None         # texto em inglês cuja tradução está (ou vai estar) na tela
        self._failed = False

    @property
    def source(self) -> str:
        return "arquivo" if self.track else "tradução automática"

    def set_track(self, track, path=None) -> None:
        self.track, self.path = track, path
        self._shown = None

    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        self._shown = None
        self._failed = False
        if not on:
            self.win.subview.set_translation("")

    def update(self, english: str, t: float) -> None:
        """Chamado quando a legenda em inglês muda."""
        if not self.enabled or not english:
            return
        if self.track is not None:
            self.track.offset = self.win.track.offset if self.win.track else 0.0   # mesma sincronia da inglesa
            self.win.subview.set_translation(self.track.text_at(t))
            return
        self._shown = english
        self.win.subview.set_translation("…")
        self.win.tasks.run(lambda: self.translate(english), lambda r: self._on_done(english, r))
        nxt = self._next_text(t)
        if nxt:                                      # adianta a próxima fala (fica no cache)
            self.win.tasks.run(lambda: self.translate(nxt))

    def _next_text(self, t: float) -> str:
        track = self.win.track
        if track is None:
            return ""
        i = track.index_at(t) + 1
        return track.cues[i].text if 0 <= i < len(track.cues) else ""

    def _on_done(self, english: str, result) -> None:
        if not self.enabled or english != self._shown:
            return                                   # a legenda já mudou: resposta atrasada
        if isinstance(result, Exception):
            self.win.subview.set_translation("")
            if not self._failed:                     # avisa uma vez só, sem encher a tela
                self._failed = True
                self.win.notify(f"Legenda em português indisponível:\n{result}", 4000)
            return
        self.win.subview.set_translation(result)
