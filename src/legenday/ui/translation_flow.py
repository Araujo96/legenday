"""Clique na palavra -> pop-up: tradução em duas etapas, pronúncia e salvar no vocabulário."""
from pathlib import Path

from PySide6.QtCore import QObject, QPoint

from legenday.core.lemma import lemma_of
from legenday.core.vocab import make_key
from legenday.services import lookup, pronunciation
from legenday.ui.popup import TranslationPopup


class TranslationFlow(QObject):
    """Cuida do pop-up. Recebe a janela principal para pausar o vídeo e saber qual fala está na tela."""

    def __init__(self, win, sound):
        super().__init__(win)
        self.win = win
        self.sound = sound
        self.popup = TranslationPopup()
        self.popup.closed.connect(self._closed)
        self.popup.save_requested.connect(self._save)
        self.popup.play_requested.connect(self.play)
        self._req = 0
        self._resume = False
        self._cur = None               # resultado da etapa 1 (tradução)
        self._details = None           # resultado da etapa 2 (contexto, forma base, dicionário)
        self._pending = False
        self._context = ""
        self.vocab_keys = set()

    # ------------------------------------------------------------ pronúncia
    def play(self, url: str) -> None:
        """Toca o áudio já baixado (a consulta da palavra adianta o download); se faltar, baixa agora."""
        self.popup.sound_loading(True)
        self.win.tasks.run(lambda: pronunciation.local_file(url), self._on_audio)

    def _on_audio(self, path) -> None:
        if isinstance(path, Exception) or not self.sound.play(str(path)):
            self.popup.sound_failed()
        else:
            self.popup.sound_loading(False)

    # ------------------------------------------------------------ pop-up
    def show(self, text: str, anchor: QPoint) -> None:
        player = self.win.player
        if not self.popup.isVisible():
            self._resume = not player.paused
        player.paused = True
        self._req += 1
        req = self._req
        context = self.win.subview.full_text    # a fala inteira: ajuda a escolher o sentido certo
        self._context = context
        self._cur, self._details = None, None
        self._pending = lookup.is_single(text) or lookup.wants_context(text, context)
        self.popup.show_at(anchor, text)
        self.win.tasks.run(lambda: lookup.quick(text), lambda r: self._on_quick(req, r))
        if self._pending:
            self.win.tasks.run(lambda: lookup.details(text, context), lambda r: self._on_details(req, r))

    def close_and_resume(self) -> bool:
        """Espaço/Enter com o pop-up aberto: fecha e continua o vídeo. Retorna False se não estava aberto."""
        if not self.popup.isVisible():
            return False
        self._resume = True
        self.popup.close()
        return True

    def _on_quick(self, req, payload):
        if req != self._req:
            return
        if isinstance(payload, Exception):
            self._pending = False
            self.popup.set_error(str(payload))
            return
        self._cur = payload
        self._render()
        try:
            saved = self.win.vocab.has(payload.text)
        except Exception:          # banco inacessível: mostra a tradução mesmo assim
            saved = False
        if saved:
            self.popup.mark_saved("✓  Já está no vocabulário")

    def _on_details(self, req, payload):
        if req != self._req:
            return
        self._pending = False
        if not isinstance(payload, Exception):       # falha no dicionário: segue só com a tradução
            self._details = payload
        self._render()

    def _render(self):
        if self._cur is None:                        # os detalhes chegaram antes da tradução: aguarda
            return
        if self._details is not None:
            lookup.merge(self._cur, self._details, self._context)
        self.popup.set_result(self._cur, loading=self._pending)

    def _closed(self):
        self.win.subview.clear_selection()
        if self._resume:
            self.win.player.paused = False
            self._resume = False

    # ------------------------------------------------------------ vocabulário
    def _save(self, res):
        win = self.win
        try:
            added = win.vocab.add(
                res.text, res.translation, sentence=self._context or win.subview.full_text,
                video=Path(win.video_path).name if win.video_path else "",
                position=win.line_start(), lemma=res.lemma or "",
                definition=res.meanings[0][1] if res.meanings else "", phonetic=res.phonetic)
        except Exception as exc:
            self.popup.set_error(f"Não foi possível salvar: {exc}")
            return
        self.popup.mark_saved("✓  Salvo no vocabulário" if added else "✓  Já estava salvo")
        win.refresh_vocab()

    def is_saved(self, word: str) -> bool:
        if not self.vocab_keys:
            return False
        w = make_key(word).strip("'")
        return w in self.vocab_keys or lemma_of(w) in self.vocab_keys
