"""Acesso ao mpv com proteção: um erro do player nunca derruba a interface.

A janela fala com o `Player` (e não com o mpv direto); nos testes, ele recebe um player falso.
"""
from legenday.core import log
from legenday.playback.mpv_loader import mpv
from legenday.services.pronunciation import USER_AGENT


class Player:
    def __init__(self, raw):
        self.raw = raw

    def get(self, name: str, default=None):
        try:
            return getattr(self.raw, name)
        except Exception:
            return default

    def set(self, name: str, value) -> None:
        try:
            setattr(self.raw, name, value)
        except Exception as exc:
            log.problem(f"mpv: ajustar {name}={value!r}", exc)

    @property
    def time(self):
        """Posição atual em segundos, ou None se não houver vídeo tocando."""
        return self.get("time_pos")

    @property
    def duration(self):
        return self.get("duration")

    @property
    def paused(self) -> bool:
        return bool(self.get("pause", True))

    @paused.setter
    def paused(self, value: bool) -> None:
        self.set("pause", value)

    def seek(self, amount: float, ref: str = "absolute", precision: str = "exact") -> None:
        try:
            self.raw.seek(amount, ref, precision)
        except Exception as exc:
            log.problem(f"mpv: pular para {amount} ({ref})", exc)

    def command(self, *args) -> bool:
        try:
            self.raw.command(*args)
            return True
        except Exception:
            return False

    def play(self, path: str) -> None:
        self.raw.play(path)

    def terminate(self) -> None:
        try:
            self.raw.terminate()
        except Exception:
            pass


def create_video_player(wid: int) -> Player:
    raw = mpv.MPV(
        wid=str(wid),
        vo="gpu",
        sub_auto="no",       # a legenda é desenhada pelo app, não pelo mpv
        sid="no",
        osc=False,
        input_default_bindings=False,
        input_vo_keyboard=False,
        keep_open="yes",
    )
    player = Player(raw)
    for name, value in (("osd_font_size", 44), ("osd_bold", True), ("osd_align_x", "center"),
                        ("osd_align_y", "top"), ("osd_margin_y", 36), ("osd_border_size", 3)):
        player.set(name, value)   # avisos grandes, no topo e centralizados
    # arquivo arrastado sobre o vídeo: quem abre é o app (que também acha a legenda), não o mpv sozinho
    player.set("drag_and_drop", "no")
    return player


class SoundPlayer:
    """Toca a pronúncia das palavras (um mpv só de áudio, criado no primeiro uso)."""

    def __init__(self, factory=None):
        # o Wikimedia (de onde vêm as gravações) recusa programas que não se identificam
        self._factory = factory or (lambda: mpv.MPV(video=False, ytdl=False, input_default_bindings=False,
                                                    user_agent=USER_AGENT))
        self._raw = None

    def play(self, url: str) -> bool:
        try:
            if self._raw is None:
                self._raw = self._factory()
            self._raw.play(url)
            return True
        except Exception as exc:
            log.problem("pronúncia: tocar o áudio", exc)
            return False

    def terminate(self) -> None:
        if self._raw is not None:
            try:
                self._raw.terminate()
            except Exception:
                pass
