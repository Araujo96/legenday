"""Pronúncia (gravações do Wikimedia Commons)."""
import io
import urllib.error

import pytest

from legenday.services import pronunciation


def _commons(*files):
    """Resposta da API do Commons (formato real, resumido): arquivos que existem e os que faltam."""
    pages = []
    for title, exists in files:
        page = {"title": title}
        if exists:
            page["imageinfo"] = [{"url": f"https://upload.wikimedia.org/x/{title[5:]}?utm_source=commons"}]
        else:
            page["missing"] = True
        pages.append(page)
    return {"query": {"pages": pages}}


def test_pronunciation_prefers_american_recording():
    data = _commons(("File:En-us-crush.ogg", True), ("File:En-uk-crush.ogg", True), ("File:En-au-crush.ogg", False))
    assert pronunciation.pick("crush", data) == "https://upload.wikimedia.org/x/En-us-crush.ogg"
    data = _commons(("File:En-us-change.ogg", False), ("File:En-uk-change.ogg", True))
    assert pronunciation.pick("change", data).endswith("En-uk-change.ogg")
    assert pronunciation.pick("rockstar", _commons(("File:En-us-rockstar.ogg", False))) == ""


def test_pronunciation_is_cached_and_network_errors_are_not():
    calls = []

    def fetch(url):
        calls.append(url)
        return _commons(("File:En-us-heart.ogg", True))
    assert pronunciation.find_audio("Heart", fetch).endswith("En-us-heart.ogg")
    assert pronunciation.find_audio("heart", fetch).endswith("En-us-heart.ogg") and len(calls) == 1
    assert "En-us-heart.ogg" in calls[0] and "En-uk-heart.ogg" in calls[0]       # uma consulta para os 3 sotaques

    def offline(url):
        raise OSError("sem rede")
    with pytest.raises(OSError):
        pronunciation.find_audio("lesson", offline)
    assert pronunciation.find_audio("lesson", lambda u: _commons(("File:En-us-lesson.ogg", True)))


def test_pronunciation_ignores_expressions_and_odd_text():
    def boom(url):
        raise AssertionError("não deveria consultar")
    assert pronunciation.find_audio("give up", boom) == "" and pronunciation.find_audio("", boom) == ""


def test_words_without_the_usual_file_use_the_wiktionary_recordings():
    """"the" não tem En-us-the.ogg; o Wiktionary usa en-us-the-unstressed.ogg (o "the" falado no meio da frase)."""
    images = ["File:LL-Q1860 (eng)-Back ache-The.wav", "File:LL-Q9199 (vie)-Penn Zero MSSJ-the.wav",
              "File:Wikipedia-logo.svg", "File:en-ca-the.ogg", "File:en-uk-the-stressed.ogg",
              "File:en-us-the-stressed.ogg", "File:en-us-the-unstressed.ogg", "File:en-us-thee.ogg"]
    ranked = pronunciation.rank_wiktionary("the", images)
    assert ranked[:3] == ["File:en-us-the-unstressed.ogg", "File:en-us-the-stressed.ogg", "File:en-uk-the-stressed.ogg"]
    assert ranked[-1] == "File:LL-Q1860 (eng)-Back ache-The.wav"
    assert not any("vie" in t or "thee" in t or "logo" in t for t in ranked)

    def fetch(url):
        if "commons" in url and "En-us-the.ogg" in url:
            return _commons(("File:En-us-the.ogg", False), ("File:En-uk-the.ogg", False), ("File:En-au-the.ogg", False))
        if "wiktionary" in url:
            return {"query": {"pages": [{"title": "the", "images": [{"title": t} for t in images]}]}}
        return _commons(("File:En-us-the-unstressed.ogg", True), ("File:En-us-the-stressed.ogg", True))
    assert pronunciation.find_audio("the", fetch) == "https://upload.wikimedia.org/x/En-us-the-unstressed.ogg"


def test_audio_is_downloaded_once_and_busy_server_is_retried():
    calls, waits = [], []

    def busy_then_ok(url):
        calls.append(url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {"Retry-After": "1"}, io.BytesIO())
        return b"OggS-audio"
    url = "https://upload.wikimedia.org/wikipedia/commons/0/06/En-us-off.ogg"
    path = pronunciation.local_file(url, busy_then_ok, sleep=waits.append)
    assert path.read_bytes() == b"OggS-audio" and path.name == "En-us-off.ogg"
    assert waits == [1.0] and len(calls) == 2
    assert pronunciation.local_file(url, busy_then_ok) == path and len(calls) == 2     # já está no computador


def test_audio_download_gives_up_after_a_few_tries():
    def always_busy(url):
        raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, io.BytesIO())
    with pytest.raises(urllib.error.HTTPError):
        pronunciation.local_file("https://upload.wikimedia.org/x/En-us-run.ogg", always_busy, sleep=lambda s: None)

    def not_found(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())
    with pytest.raises(urllib.error.HTTPError):                       # 404 não adianta repetir
        pronunciation.local_file("https://upload.wikimedia.org/x/En-us-walk.ogg", not_found,
                                 sleep=lambda s: pytest.fail("não deveria esperar"))


def test_wikimedia_sees_who_is_asking():
    """A política do Wikimedia pede um contato no User-Agent; sem ele, o servidor de áudio recusa com 429."""
    assert "github.com/Araujo96/legenday" in pronunciation.USER_AGENT


def test_wiktionary_is_asked_with_capital_letter_too():
    """A página do Wiktionary é "I'm", não "i'm" (o título diferencia maiúsculas)."""
    asked = []

    def fetch(url):
        asked.append(url)
        return {"query": {"pages": []}}
    assert pronunciation.from_wiktionary("i'm", fetch) == ""
    assert "i%27m%7CI%27m" in asked[0]
