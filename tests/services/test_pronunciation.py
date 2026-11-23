"""Pronúncia (gravações do Wikimedia Commons)."""
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
