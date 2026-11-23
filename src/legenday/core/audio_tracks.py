"""Faixas de áudio do vídeo (lista do mpv) e a preferência por inglês."""
from legenday.core.embedded import LANGS

PREFERRED_LANGS = "eng,en,english"   # o app é para praticar inglês: começa pela faixa em inglês, se existir

_CHANNELS = {1: "mono", 2: "estéreo", 6: "5.1", 8: "7.1"}


def audio_tracks(track_list) -> list:
    return [t for t in (track_list or []) if isinstance(t, dict) and t.get("type") == "audio"]


def label(track: dict) -> str:
    """Ex.: 'Inglês (AC3, 5.1)' ou 'Português Dublado (AAC, estéreo)'."""
    lang = track.get("lang") or "und"
    name = LANGS.get(lang, "Idioma não informado" if lang == "und" else lang.upper())
    title = (track.get("title") or "").strip()
    if title:
        name = title if name.lower() in title.lower() else f"{name} — {title}"
    channels = track.get("demux-channel-count")
    tech = ", ".join(x for x in ((track.get("codec") or "").upper(),
                                 _CHANNELS.get(channels, f"{channels} canais" if channels else "")) if x)
    return f"{name} ({tech})" if tech else name
