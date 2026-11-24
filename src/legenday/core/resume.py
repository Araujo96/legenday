"""Onde a pessoa parou em cada vídeo (resume.json), para oferecer "continuar de onde parou".

Não guarda o começo (menos de MIN_START segundos: nem vale perguntar) nem o fim (os créditos: o vídeo já foi
visto). Guarda no máximo MAX_ITEMS vídeos, os mais recentes.
"""
import time
from pathlib import Path

from legenday.core.settings import _JsonFile

MIN_START = 30          # s: parou antes disso = não pergunta
END_MARGIN = 120        # s: a menos disso do fim (créditos) = considera visto
MAX_ITEMS = 50

_FILE = _JsonFile("resume.json")


def _key(path: str) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return str(path)


def finished(t: float, duration: float | None) -> bool:
    """Chegou aos créditos: a menos de 5% do fim, e no máximo 2 min (num vídeo curto, 2 min seria quase tudo)."""
    return bool(duration) and t >= duration - min(END_MARGIN, duration * 0.05)


def save(path: str, t: float | None, duration: float | None) -> None:
    """Guarda (ou apaga, se não vale a pena lembrar) o ponto onde o vídeo está agora. Nunca levanta exceção."""
    if not path or t is None:
        return
    data = _FILE.read()
    key = _key(path)
    if t < MIN_START or finished(t, duration):
        if data.pop(key, None) is None:
            return
    else:
        data[key] = {"t": round(float(t), 1), "dur": round(float(duration or 0), 1), "at": time.time()}
        if len(data) > MAX_ITEMS:                       # esquece os mais antigos
            for old in sorted(data, key=lambda k: data[k].get("at", 0))[:len(data) - MAX_ITEMS]:
                data.pop(old)
    try:
        _FILE.write(data)
    except OSError:
        pass


def get(path: str) -> tuple[float, float] | None:
    """(onde parou, duração) neste vídeo, ou None."""
    item = _FILE.read().get(_key(path))
    try:
        return (float(item["t"]), float(item.get("dur") or 0)) if item else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def last() -> tuple[str, float, float] | None:
    """O vídeo visto por último que ficou pela metade e ainda existe no disco: (caminho, parou em, duração)."""
    data = _FILE.read()
    for key in sorted(data, key=lambda k: data[k].get("at", 0) if isinstance(data[k], dict) else 0, reverse=True):
        item = data[key]
        try:
            t, dur = float(item["t"]), float(item.get("dur") or 0)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if Path(key).is_file():
            return key, t, dur
    return None


def clock(sec: float) -> str:
    """42:13 ou 1:02:03."""
    sec = int(max(sec, 0))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"
