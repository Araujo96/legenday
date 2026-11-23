"""Legendas embutidas (MKV/MP4): lista as faixas e extrai a escolhida para .srt usando o ffmpeg."""
import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from legenday.core.paths import PROJECT_ROOT, data_dir

TEXT_CODECS = {"subrip", "srt", "ass", "ssa", "mov_text", "webvtt", "text", "subviewer", "microdvd", "ttml"}
LANGS = {"eng": "Inglês", "en": "Inglês", "por": "Português", "pt": "Português", "spa": "Espanhol",
         "es": "Espanhol", "fre": "Francês", "fra": "Francês", "fr": "Francês", "ger": "Alemão",
         "deu": "Alemão", "de": "Alemão", "ita": "Italiano", "it": "Italiano", "jpn": "Japonês",
         "ja": "Japonês", "kor": "Coreano", "chi": "Chinês", "zho": "Chinês", "rus": "Russo"}

_STREAM = re.compile(r"^\s*Stream #0:(\d+)(?:\[0x[0-9a-fA-F]+\])?(?:\((\w+)\))?: Subtitle: (\w+)(.*)$")


class FFmpegNotFound(RuntimeError):
    pass


@dataclass
class SubTrack:
    stream: int
    lang: str
    codec: str
    title: str = ""
    forced: bool = False

    @property
    def text(self) -> bool:
        return self.codec in TEXT_CODECS

    @property
    def label(self) -> str:
        name = LANGS.get(self.lang, "Idioma não informado" if self.lang == "und" else self.lang.upper())
        extra = f" — {self.title}" if self.title else ""
        flag = " [forçada]" if self.forced else ""
        return f"{name}{extra} ({self.codec}){flag}"


def find_ffmpeg():
    env = os.environ.get("LEGENDAY_FFMPEG")
    if env and Path(env).exists():
        return env
    dirs = [PROJECT_ROOT / "libs"]
    if getattr(sys, "frozen", False):          # executável gerado pelo PyInstaller
        dirs.insert(0, Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)))
        dirs.append(Path(sys.executable).parent)
    for d in dirs:
        for name in ("ffmpeg.exe", "ffmpeg"):
            if (d / name).exists():
                return str(d / name)
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _run(args, timeout):
    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, **kw)


def parse_probe(stderr: str) -> list:
    lines, tracks = stderr.splitlines(), []
    for i, line in enumerate(lines):
        m = _STREAM.match(line)
        if not m:
            continue
        stream, lang, codec, tail = m.groups()
        title = ""
        for nxt in lines[i + 1:]:
            if nxt.startswith("    Stream #") or re.match(r"^\s*Stream #", nxt) or re.match(r"^\S", nxt):
                break
            t = re.match(r"^\s*title\s*:\s*(.+)$", nxt)
            if t:
                title = t.group(1).strip()
                break
        forced = "(forced)" in tail or "forced" in title.lower()
        tracks.append(SubTrack(int(stream), lang or "und", codec, title, forced))
    return tracks


def probe(video: str) -> list:
    ff = find_ffmpeg()
    if not ff:
        raise FFmpegNotFound("ffmpeg não encontrado")
    return parse_probe(_run([ff, "-hide_banner", "-i", video], 30).stderr)  # sem saída: ffmpeg sai com erro, é normal


def pick_english(tracks):
    eng = [t for t in tracks if t.text and t.lang in ("eng", "en")]
    good = [t for t in eng if not t.forced and not re.search(r"sign|song|commentary", t.title, re.I)]
    return good[0] if good else None   # só forçadas/placas e letreiros: fica só no menu


def extract(video: str, track: SubTrack, out_dir=None) -> Path:
    ff = find_ffmpeg()
    if not ff:
        raise FFmpegNotFound("ffmpeg não encontrado")
    out_dir = Path(out_dir) if out_dir else data_dir() / "subs"
    out_dir.mkdir(parents=True, exist_ok=True)
    st = Path(video).stat()
    ident = f"{Path(video).resolve()}|{st.st_mtime_ns}|{st.st_size}|{track.stream}"
    key = hashlib.sha1(ident.encode()).hexdigest()[:12]
    stem = re.sub(r"[^\w.-]", "_", Path(video).stem)[:40]
    out = out_dir / f"{stem}.{track.lang}.{key}.srt"
    if out.exists() and out.stat().st_size > 0:
        return out
    proc = _run([ff, "-y", "-v", "error", "-i", video, "-map", f"0:{track.stream}", "-c:s", "srt", str(out)], 900)
    if proc.returncode != 0 or not out.exists():
        last = (proc.stderr.strip().splitlines() or ["erro desconhecido"])[-1]
        raise RuntimeError("Não consegui extrair a legenda: " + last)
    return out
