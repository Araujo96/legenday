"""Leitura e limpeza de legendas, falas simultâneas, sincronia e legendas ao lado do vídeo."""

import pytest

from legenday.core.subtitles import (
    Cue,
    SubtitleTrack,
    clean,
    find_sidecar,
    find_sidecar_pt,
    load_subtitles,
    split_chunk,
)

SRT = """1
00:00:01,000 --> 00:00:03,000
<i>I'm gonna</i>
give up.

2
00:00:04,000 --> 00:00:05,000
- Hello!
"""


def test_clean_removes_tags_and_keeps_line_breaks():
    assert clean("<i>Hello,\\Nworld!</i>{\\an8}") == "Hello,\nworld!"


def test_split_chunk_separates_punctuation():
    assert split_chunk('"Hello,"') == ('"', "Hello", ',"')
    assert split_chunk("don't") == ("", "don't", "")
    assert split_chunk("-") == ("-", "", "")


def test_load_and_find_active_cue(tmp_path):
    f = tmp_path / "a.srt"
    f.write_text(SRT, encoding="utf-8")
    track = load_subtitles(str(f))
    assert [c.text for c in track.cues] == ["I'm gonna\ngive up.", "- Hello!"]
    assert track.active_at(2) == 0
    assert track.active_at(3.5) == -1
    assert track.active_at(4.5) == 1


def test_detects_non_utf8_encoding(tmp_path):
    f = tmp_path / "b.srt"
    f.write_bytes(SRT.replace("Hello", "Café").encode("cp1252"))
    assert load_subtitles(str(f)).cues[1].text == "- Café!"


def test_sync_offset_shifts_cues(tmp_path):
    f = tmp_path / "c.srt"
    f.write_text(SRT, encoding="utf-8")
    track = load_subtitles(str(f))
    track.offset = 2.0                      # legenda aparece 2s mais tarde
    assert track.active_at(2.5) == -1 and track.active_at(3.5) == 0
    assert track.start_of(0) == 3.0 and track.index_at(3.0) == 0
    track.offset = -0.5                     # e 0,5s mais cedo
    assert track.active_at(0.6) == 0 and track.start_of(1) == 3.5


def _track(cues):
    from legenday.core.subtitles import Cue, SubtitleTrack
    return SubtitleTrack(sorted((Cue(a, b, t) for a, b, t in cues), key=lambda c: c.start))


def test_overlapping_cues_are_all_shown_in_start_order():
    t = _track([(2, 8, "A longa"), (4, 6, "B no meio"), (7, 11, "C"), (12, 15, "D"), (12, 15, "E")])

    def texts(x):
        return [t.cues[i].text for i in t.active_all(x)]
    assert texts(1) == [] and texts(3) == ["A longa"]
    assert texts(5) == ["A longa", "B no meio"]            # antes: só "B no meio"
    assert texts(7.5) == ["A longa", "C"] and texts(13) == ["D", "E"] and texts(11.5) == []


def test_long_cue_stays_visible_under_many_short_ones():
    t = _track([(5, 40, "LETREIRO")] + [(6 + i * 2.5, 7.5 + i * 2.5, f"curta {i}") for i in range(10)])
    shown = [t.cues[i].text for i in t.active_all(30)]
    assert "LETREIRO" in shown                              # antes sumia depois de 3 falas curtas
    assert t.active_all(41) == []


def test_stack_is_limited():
    t = _track([(0, 10, f"L{i}") for i in range(12)])
    assert len(t.active_all(5)) == t.MAX_STACK

SRT_SHORT = "1\n00:00:01,000 --> 00:00:03,000\nCafé ñandú olá!\n\n2\n00:00:04,000 --> 00:00:05,000\nSecond\n"


@pytest.mark.parametrize("name,raw", [
    ("utf8-bom", b"\xef\xbb\xbf" + SRT_SHORT.encode()),
    ("crlf", SRT_SHORT.replace("\n", "\r\n").encode()),
    ("cp1252", SRT_SHORT.encode("cp1252")),
    ("utf16-bom", SRT_SHORT.encode("utf-16")),
    ("utf16-le-sem-bom", SRT_SHORT.encode("utf-16-le")),
    ("utf16-be-sem-bom", SRT_SHORT.encode("utf-16-be")),
])
def test_encodings(tmp_path, name, raw):
    f = tmp_path / "a.srt"
    f.write_bytes(raw)
    assert load_subtitles(str(f)).cues[0].text == "Café ñandú olá!"


@pytest.mark.parametrize("raw", [b"", b"   \n\n", bytes(range(256)) * 3, "isto não é legenda\n".encode()])
def test_invalid_files_give_friendly_error(tmp_path, raw):
    f = tmp_path / "x.srt"
    f.write_bytes(raw)
    with pytest.raises(ValueError) as exc:
        load_subtitles(str(f))
    assert "legenda" in str(exc.value).lower()          # mensagem em português, não "No suitable formats"


def test_clean_html_entities_and_ass_hard_space():
    assert clean("Tom &amp; Jerry &lt;3 &quot;hi&quot;&nbsp;there") == 'Tom & Jerry <3 "hi" there'
    assert clean("Hello\\hthere\\Nnext") == "Hello there\nnext"


def test_zero_duration_ignored_and_inverted_cue_lasts_until_next_like_mpv(tmp_path):
    f = tmp_path / "z.srt"
    f.write_text("1\n00:00:01,000 --> 00:00:01,000\nZero\n\n2\n00:00:03,000 --> 00:00:02,000\nInvertida\n\n"
                 "3\n00:00:04,000 --> 00:00:05,000\nNormal\n", encoding="utf-8")
    cues = load_subtitles(str(f)).cues
    # a invertida dura até a próxima fala
    assert [(c.text, c.start, c.end) for c in cues] == [("Invertida", 3.0, 4.0), ("Normal", 4.0, 5.0)]


def test_find_sidecar(tmp_path):
    v = tmp_path / "Filme [1080p] (2020).mkv"
    v.touch()
    assert find_sidecar(str(v)) is None
    (tmp_path / "Filme [1080p] (2020).pt-BR.srt").touch()
    (tmp_path / "Filme [1080p] (2020).en.forced.srt").touch()
    assert find_sidecar(str(v)) is None                       # só português e forçada: não carrega
    (tmp_path / "Filme [1080p] (2020).en.srt").touch()
    assert find_sidecar(str(v)).name.endswith(".en.srt")
    (tmp_path / "Filme [1080p] (2020).SRT").touch()           # nome exato (e extensão maiúscula) tem prioridade
    assert find_sidecar(str(v)).name == "Filme [1080p] (2020).SRT"


def test_sidecar_of_other_episode_is_not_loaded(tmp_path):
    v = tmp_path / "Show S01E1.mkv"
    v.write_bytes(b"")
    (tmp_path / "Show S01E10.en.srt").write_text("x")
    (tmp_path / "Show S01E12.srt").write_text("x")
    assert find_sidecar(str(v)) is None
    (tmp_path / "Show S01E1.en.srt").write_text("x")
    assert find_sidecar(str(v)).name == "Show S01E1.en.srt"


def test_find_portuguese_sidecar(tmp_path):
    v = tmp_path / "Filme.mkv"
    v.write_bytes(b"")
    assert find_sidecar_pt(str(v)) is None
    (tmp_path / "Filme.en.srt").write_text("x")
    (tmp_path / "Filme.pt-BR.srt").write_text("x")
    assert find_sidecar_pt(str(v)).name == "Filme.pt-BR.srt"
    assert find_sidecar(str(v)).name == "Filme.en.srt"                        # a principal continua a inglesa


def _cue_track(*cues):
    return SubtitleTrack([Cue(s, e, t) for s, e, t in cues])


def test_text_at_and_end_of():
    track = _cue_track((1, 3, "A"), (2, 4, "B"))
    track.offset = 1.0
    assert track.text_at(3.5) == "A\nB" and track.end_of(0) == 4.0
