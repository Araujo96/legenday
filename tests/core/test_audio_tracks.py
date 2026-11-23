from legenday.core import audio_tracks


def test_label_formats():
    assert audio_tracks.label({"lang": "eng", "codec": "ac3", "demux-channel-count": 6}) == "Inglês (AC3, 5.1)"
    dub = {"lang": "por", "title": "Português Dublado", "codec": "aac", "demux-channel-count": 2}
    assert audio_tracks.label(dub) == "Português Dublado (AAC, estéreo)"
    commentary = {"lang": "eng", "title": "Commentary", "codec": "opus", "demux-channel-count": 1}
    assert audio_tracks.label(commentary) == "Inglês — Commentary (OPUS, mono)"
    assert audio_tracks.label({"lang": None}) == "Idioma não informado"
    assert audio_tracks.label({"lang": "xyz", "codec": "aac", "demux-channel-count": 3}) == "XYZ (AAC, 3 canais)"


def test_audio_tracks_ignores_other_types_and_garbage():
    tl = [{"type": "video"}, {"type": "audio", "id": 1}, {"type": "sub"}, None, "x", {"type": "audio", "id": 2}]
    assert [t["id"] for t in audio_tracks.audio_tracks(tl)] == [1, 2]
    assert audio_tracks.audio_tracks(None) == []
