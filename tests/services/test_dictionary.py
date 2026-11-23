"""Dicionário (Free Dictionary API)."""
import urllib.error

import pytest

from legenday.services import dictionary

PAYLOAD = [{"word": "go", "phonetic": "/ɡəʊ/", "meanings": [
    {"partOfSpeech": "verb", "definitions": [{"definition": "To move.", "example": "Let's go."}]},
    {"partOfSpeech": "verb", "definitions": [{"definition": "Another verb sense."}]},
    {"partOfSpeech": "noun", "definitions": [{"definition": "An attempt."}]}]}]


def test_parse_keeps_one_meaning_per_part_of_speech():
    entry = dictionary.parse(PAYLOAD)
    assert entry.phonetic == "/ɡəʊ/"
    assert [m[0] for m in entry.meanings] == ["verb", "noun"]


@pytest.mark.parametrize("payload", [
    {"title": "No Definitions Found"}, [], None, "erro", ["a", 1], [{"meanings": None}], [{"phonetics": None}],
    [{"meanings": [{"partOfSpeech": "noun", "definitions": [{}]}]}], [{"meanings": ["x", None]}],
])
def test_dictionary_parse_never_crashes(payload):
    assert dictionary.parse(payload) is None


def test_lookup_caches_results_and_404():
    calls = []

    def fetch(word):
        calls.append(word)
        if word == "zzzz":
            raise urllib.error.HTTPError("u", 404, "nf", {}, None)
        return PAYLOAD

    assert dictionary.lookup("Go", fetch).meanings[0][1] == "To move."
    assert dictionary.lookup("go", fetch).phonetic == "/ɡəʊ/"
    assert dictionary.lookup("zzzz", fetch) is None and dictionary.lookup("zzzz", fetch) is None
    assert calls == ["go", "zzzz"]                  # segunda consulta veio do cache


def test_dictionary_stays_quiet_after_a_network_failure(monkeypatch):
    monkeypatch.setattr(dictionary, "_down_until", 0.0)
    calls = []

    def fetch(w):
        calls.append(w)
        raise urllib.error.URLError("sem rede")
    with pytest.raises(urllib.error.URLError):
        dictionary.lookup("alpha", fetch)
    assert dictionary.lookup("beta", fetch) is None          # nos próximos 60 s nem tenta: cliques não esperam à toa
    assert calls == ["alpha"]
    monkeypatch.setattr(dictionary, "_down_until", 0.0)
