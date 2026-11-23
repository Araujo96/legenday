"""Leitura e limpeza de legendas (SRT, ASS, VTT...) usando pysubs2."""
import html
import re
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

import pysubs2

_TAGS = re.compile(r"<[^>]+>|\{[^}]*\}")
_CHUNK = re.compile(r"^(\W*)(.*?)(\W*)$", re.DOTALL)


@dataclass
class Cue:
    start: float  # segundos
    end: float
    text: str


def clean(text: str) -> str:
    text = text.replace("\\N", "\n").replace("\\n", "\n").replace("\\h", " ")
    text = _TAGS.sub("", text)
    text = html.unescape(text)   # &amp; &lt; &quot; &nbsp; ...
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def split_chunk(chunk: str) -> tuple[str, str, str]:
    """'"Hello,"' -> ('"', 'Hello', ',"'): pontuação à esquerda, palavra, pontuação à direita."""
    return _CHUNK.match(chunk).groups()


class SubtitleTrack:
    MAX_STACK = 4   # no máximo 4 falas empilhadas ao mesmo tempo

    def __init__(self, cues: list[Cue]):
        self.cues = cues
        self._starts = [c.start for c in cues]
        self._max_end, biggest = [], float("-inf")
        # maior fim até cada posição: permite achar falas longas que ainda não acabaram
        for c in cues:
            biggest = max(biggest, c.end)
            self._max_end.append(biggest)
        self.offset = 0.0  # segundos; positivo = legenda aparece mais tarde

    def index_at(self, t: float) -> int:
        """Índice da última legenda que já começou (ou -1)."""
        return bisect_right(self._starts, t - self.offset) - 1

    def active_all(self, t: float) -> list:
        """Índices de TODAS as falas visíveis em t, da mais antiga para a mais nova (como o mpv mostra)."""
        t -= self.offset
        i, found, steps = bisect_right(self._starts, t) - 1, [], 0
        while i >= 0 and self._max_end[i] > t and steps < 300:
            if self.cues[i].end > t:
                found.append(i)
            i, steps = i - 1, steps + 1
        found.reverse()
        return found[-self.MAX_STACK:]

    def active_at(self, t: float) -> int:
        """Índice da fala mais recente visível em t (ou -1)."""
        ids = self.active_all(t)
        return ids[-1] if ids else -1

    def start_of(self, i: int) -> float:
        """Instante (já com o ajuste de sincronia) em que a legenda i começa."""
        return self.cues[i].start + self.offset

    def end_of(self, i: int) -> float:
        """Instante (já com o ajuste de sincronia) em que a legenda i termina."""
        return self.cues[i].end + self.offset

    def text_at(self, t: float) -> str:
        """Texto de todas as falas visíveis em t (vazio se nenhuma)."""
        return "\n".join(dict.fromkeys(self.cues[i].text for i in self.active_all(t)))


SUB_EXTS = (".srt", ".ass", ".ssa", ".vtt")
_ENGLISH = {"en", "eng", "english", "en-us", "en-gb", "enus", "engb"}
_PORTUGUESE = {"pt", "por", "pob", "portuguese", "pt-br", "ptbr", "pt_br", "brazilian", "portugues", "português"}
_BAD_FORMAT = "Não consegui ler essa legenda. Ela está num formato suportado (SRT, ASS, SSA ou VTT)?"


def _sidecars(video: str):
    """(arquivo, marcadores) de cada legenda ao lado do vídeo: 'Filme.en.sdh.srt' -> {'en', 'sdh'}."""
    v = Path(video)
    try:
        names = sorted(v.parent.iterdir())
    except OSError:
        return
    for p in names:
        if p.suffix.lower() not in SUB_EXTS or not p.name.lower().startswith(v.stem.lower()):
            continue
        rest = p.name[len(v.stem):-len(p.suffix)]
        if rest and not rest.startswith("."):               # "Show S01E10.srt" não é legenda de "Show S01E1.mkv"
            continue
        yield p, {t.lower() for t in rest.split(".") if t}


def find_sidecar_pt(video: str):
    """Legenda em português ao lado do vídeo ('Filme.pt.srt', 'Filme.pt-BR.srt'...), para a 2ª linha."""
    found = [p for p, tokens in _sidecars(video) if tokens & _PORTUGUESE and "forced" not in tokens]
    return found[0] if found else None


def find_sidecar(video: str):
    """Procura a legenda ao lado do vídeo: 'Filme.srt' e, se não houver, 'Filme.en.srt' / 'Filme.English.srt'."""
    exact, english = [], []
    for p, tokens in _sidecars(video):
        if not tokens:
            exact.append(p)
        elif tokens & _ENGLISH and "forced" not in tokens:
            english.append(p)
    exact.sort(key=lambda p: SUB_EXTS.index(p.suffix.lower()))
    return (exact or english or [None])[0]


def _encodings(raw: bytes) -> list:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return ["utf-16"]
    if b"\x00" in raw[:200]:                 # UTF-16 sem BOM
        return ["utf-16-le", "utf-16-be"]
    return ["utf-8-sig", "cp1252", "latin-1"]


def load_subtitles(path: str) -> SubtitleTrack:
    subs, bad_format = None, None
    for enc in _encodings(Path(path).read_bytes()):
        try:
            subs = pysubs2.load(path, encoding=enc)
            break
        except UnicodeError:
            continue
        except Exception as exc:       # decodificou, mas o conteúdo não é legenda: tenta a próxima codificação
            bad_format = exc
    if subs is None:
        if bad_format is not None:
            raise ValueError(_BAD_FORMAT) from bad_format
        raise ValueError("Não consegui detectar a codificação da legenda.")

    raw = []
    for ev in subs:
        if ev.is_comment:
            continue
        text = clean(ev.text)
        if text and ev.end != ev.start:                  # duração zero: o mpv também não mostra
            raw.append((ev.start / 1000, ev.end / 1000, text))
    raw.sort(key=lambda r: r[0])
    cues = []
    for i, (start, end, text) in enumerate(raw):
        if end < start:                                  # fim antes do início: o mpv mostra até a próxima fala
            end = raw[i + 1][0] if i + 1 < len(raw) else start + 3.0
        if end > start:
            cues.append(Cue(start, end, text))
    if not cues:
        raise ValueError("A legenda está vazia ou em formato não reconhecido.")
    return SubtitleTrack(cues)
