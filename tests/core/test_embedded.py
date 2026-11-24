"""Legendas embutidas (ffmpeg)."""
import subprocess

import pytest

from legenday.core import embedded
from legenday.core.subtitles import load_subtitles

SAMPLE = """Input #0, matroska,webm, from 'movie.mkv':
  Stream #0:0: Video: h264 (High), yuv420p, 1280x720
  Stream #0:1(eng): Audio: aac (LC), 48000 Hz, stereo
  Stream #0:2(eng): Subtitle: subrip (default)
    Metadata:
      title           : English SDH
  Stream #0:3(por): Subtitle: ass (forced)
  Stream #0:4(spa): Subtitle: hdmv_pgs_subtitle
  Stream #0:5[0x3](eng): Subtitle: mov_text (tx3g / 0x67337874)
At least one output file must be specified
"""


def test_parse_probe():
    t = embedded.parse_probe(SAMPLE)
    assert [(x.stream, x.lang, x.codec) for x in t] == [
        (2, "eng", "subrip"), (3, "por", "ass"), (4, "spa", "hdmv_pgs_subtitle"), (5, "eng", "mov_text")]
    assert t[0].title == "English SDH" and t[1].forced
    assert [x.text for x in t] == [True, True, False, True]
    assert embedded.pick_english(t) is t[0]
    assert t[0].label == "Inglês — English SDH"                  # sem "subrip": nada de termo técnico
    assert t[1].label == "Português (só trechos em outra língua)"


def test_label_of_a_track_without_language():
    assert embedded.SubTrack(2, "und", "subrip").label == "Idioma não informado"
    assert embedded.SubTrack(2, "eng", "subrip", "English").label == "Inglês"     # título que só repete


def test_unknown_language_tracks_are_candidates_but_other_languages_are_not():
    tracks = [embedded.SubTrack(2, "por", "subrip"), embedded.SubTrack(3, "und", "subrip"),
              embedded.SubTrack(4, "und", "subrip", "Signs"), embedded.SubTrack(5, "und", "hdmv_pgs_subtitle"),
              embedded.SubTrack(6, "und", "ass")]
    assert embedded.pick_english(tracks) is None
    assert [t.stream for t in embedded.unknown_candidates(tracks)] == [3, 6]


def srt_with(lines, tmp_path, name):
    body = "".join(f"{i}\n00:00:{i:02d},000 --> 00:00:{i:02d},900\n{text}\n\n" for i, text in enumerate(lines, 1))
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


ENGLISH = ["What are you doing here?", "<i>I don't know what you mean.</i>", "We have to get out of this place.",
           "It's not your fault, okay?", "Tell me the truth.", "Yeah, I know. Just go."] * 3
PORTUGUESE = ["O que você está fazendo aqui?", "<i>Eu não sei do que você está falando.</i>",
              "Temos que sair deste lugar.", "Não é sua culpa, tá bom?", "Me conte a verdade.",
              "É, eu sei. Só vai."] * 3


def test_looks_english_tells_english_from_portuguese(tmp_path):
    assert embedded.looks_english(srt_with(ENGLISH, tmp_path, "en.srt"))
    assert not embedded.looks_english(srt_with(PORTUGUESE, tmp_path, "pt.srt"))
    assert not embedded.looks_english(srt_with(["Hi."], tmp_path, "curta.srt"))      # pouco texto: não arrisca
    assert not embedded.looks_english(tmp_path / "nao-existe.srt")


def test_pick_english_none_when_only_other_languages():
    assert embedded.pick_english(embedded.parse_probe(SAMPLE)[1:3]) is None


def test_real_extraction(tmp_path):
    ff = embedded.find_ffmpeg()
    if not ff:
        pytest.skip("ffmpeg indisponível")
    srt = tmp_path / "in.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:03,000\nI'm <i>gonna</i> go.\n\n"
                   "2\n00:00:04,000 --> 00:00:05,000\nSecond line.\n", encoding="utf-8")
    mkv = tmp_path / "movie.mkv"
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=6", "-i", str(srt),
                    "-map", "0:v", "-map", "1:s", "-c:v", "mpeg4", "-c:s", "srt",
                    "-metadata:s:s:0", "language=eng", str(mkv)], check=True)
    tracks = embedded.probe(str(mkv))
    assert len(tracks) == 1 and tracks[0].lang == "eng" and tracks[0].text
    out = embedded.extract(str(mkv), tracks[0])
    track = load_subtitles(str(out))
    assert [c.text for c in track.cues] == ["I'm gonna go.", "Second line."]
    assert embedded.extract(str(mkv), tracks[0]) == out      # segunda vez usa o cache


def test_find_ffmpeg_inside_frozen_bundle(tmp_path, monkeypatch):
    import sys
    (tmp_path / "ffmpeg.exe").write_bytes(b"x")
    monkeypatch.delenv("LEGENDAY_FFMPEG", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert embedded.find_ffmpeg() == str(tmp_path / "ffmpeg.exe")


def test_pick_english_ignores_forced_and_signs_tracks():
    only_forced = [embedded.SubTrack(2, "eng", "subrip", "", True)]
    assert embedded.pick_english(only_forced) is None
    songs = [embedded.SubTrack(2, "eng", "ass", "Signs & Songs")]
    assert embedded.pick_english(songs) is None
