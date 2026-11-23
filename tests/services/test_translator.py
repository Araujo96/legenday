"""Tradução: MyMemory, Argos, cache, sentidos alternativos e limpeza dos resultados."""
import io
import json
import urllib.error

import pytest

from legenday.core.paths import data_dir
from legenday.services import translator


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_mymemory(monkeypatch, text, status=200):
    body = json.dumps({"responseStatus": status, "responseData": {"translatedText": text}}).encode()
    monkeypatch.setattr(translator.urllib.request, "urlopen", lambda *a, **k: _Resp(body))


def test_mymemory_decodes_entities(monkeypatch):
    _fake_mymemory(monkeypatch, "n&#39;est-ce pas &amp; você")
    assert translator._mymemory("x") == "n'est-ce pas & você"


@pytest.mark.parametrize("text", [
    "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS", "PLEASE SELECT TWO DISTINCT LANGUAGES", "",
])
def test_mymemory_error_texts_are_not_shown_or_cached(monkeypatch, text):
    _fake_mymemory(monkeypatch, text)
    with pytest.raises(RuntimeError):
        translator.translate("hello")
    assert translator._cache_get("hello") is None


def test_translation_works_with_broken_cache(monkeypatch):
    (data_dir() / "cache.db").write_bytes(b"lixo" * 100)
    _fake_mymemory(monkeypatch, "olá")
    assert translator.translate("hello") == "olá"


def test_offline_model_is_looked_up_only_once(monkeypatch):
    from legenday.services import translator
    monkeypatch.setitem(translator._ARGOS, "loaded", False)
    monkeypatch.setitem(translator._ARGOS, "tr", None)
    translator._argos("hello")
    assert translator._ARGOS["loaded"] is True


def test_cache_keeps_acronyms_apart_but_ignores_sentence_case(monkeypatch):
    monkeypatch.setattr(translator, "_argos", lambda s: None)
    translator._cache_put("US", "EUA")
    assert translator._cache_get("us") is None
    assert translator._cache_get("US") == "EUA"
    translator._cache_put("Went", "foi")                 # início de frase vale para a palavra minúscula
    assert translator._cache_get("went") == "foi"


def test_broken_offline_model_falls_back_to_online(monkeypatch):
    class Broken:
        def translate(self, text):
            raise RuntimeError("modelo corrompido")
    monkeypatch.setitem(translator._ARGOS, "loaded", True)
    monkeypatch.setitem(translator._ARGOS, "tr", Broken())
    monkeypatch.setattr(translator, "_mymemory_senses", lambda s: ["olá"])
    assert translator.translate("hello") == "olá"


@pytest.mark.parametrize("error, expected", [
    (urllib.error.URLError("getaddrinfo failed"), "Sem conexão"),
    (urllib.error.HTTPError("u", 429, "Too Many", {}, None), "erro 429"),
    (RuntimeError("o serviço gratuito recusou o pedido (limite diário atingido?)"), "limite diário"),
])
def test_translation_error_messages_say_what_happened(monkeypatch, error, expected):
    monkeypatch.setattr(translator, "_argos", lambda s: None)

    def fail(text):
        raise error
    monkeypatch.setattr(translator, "_mymemory_senses", fail)
    with pytest.raises(RuntimeError, match=expected):
        translator.translate("hello")


@pytest.mark.parametrize("src, out, expected", [
    ("There's a lesson to be learned from this.", "- Há uma lição a ser aprendida.", "Há uma lição a ser aprendida."),
    ("- Run!", "- Corra!", "- Corra!"),                       # o travessão existe no original: fica
    ("heart", "Coração", "coração"),
    ("rockstar", "Estrela do rock", "estrela do rock"),
    ("Paris", "Paris", "Paris"),
    ("us", "EUA", "EUA"),                                     # sigla não vira minúscula
])
def test_tidy_cleans_machine_translation_quirks(src, out, expected):
    assert translator.tidy(src, out) == expected


def _response(main, matches):
    """Formato real da resposta do MyMemory (resumido)."""
    return {"responseStatus": 200, "responseData": {"translatedText": main},
            "matches": [{"translation": t, "quality": q, "segment": seg} for t, q, seg in matches]}


def test_senses_keep_alternatives_of_the_same_word():
    data = _response("falido", [("falido", 74, "broke"), ("rompeu", 74, "broke"), ("Quebrou", 74, "Broke")])
    assert translator.pick_senses("broke", data) == ["falido", "rompeu", "quebrou"]


def test_senses_skip_zero_quality_and_other_segments():
    data = _response("pública de aquisição", [("edital de licitação", 0, "tender"), ("Suave", 74, "Tender"),
                                             ("para lembrá-lo", 74, "to remind you")])
    assert translator.pick_senses("tender", data) == ["pública de aquisição", "suave"]


def test_untranslated_word_is_not_the_main_sense():
    data = _response("remind", [("remind", 74, "remind"), ("Lembrar", 74, "Remind")])
    assert translator.pick_senses("remind", data) == ["lembrar", "remind"]


def test_refusal_texts_are_never_senses():
    with pytest.raises(RuntimeError):
        translator.pick_senses("hello", _response("MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS", []))


def test_junk_and_punctuation_are_cleaned_from_word_senses():
    data = _response("esqueci", [("ENVIAR", 74, "forgot"), ("Esqueceu.", 74, "Forgot")])
    assert translator.pick_senses("forgot", data) == ["esqueci", "esqueceu"]
    data = _response("esmagar", [("A paixão súbita", 74, "Crush")])
    assert translator.pick_senses("crush", data) == ["esmagar", "a paixão súbita"]


def test_sentence_keeps_its_final_punctuation():
    assert translator.tidy("We're done.", "Terminamos.") == "Terminamos."
    assert translator.tidy("OK", "OK") == "OK"                                   # siglas continuam iguais


def test_senses_are_cached_with_alternatives(monkeypatch):
    calls = []

    def fetch(text):
        calls.append(text)
        return ["falido", "quebrou"]
    monkeypatch.setattr(translator, "_argos", lambda s: None)
    monkeypatch.setattr(translator, "_mymemory_senses", fetch)
    assert translator.senses("broke") == ["falido", "quebrou"]
    assert translator.senses("broke") == ["falido", "quebrou"] and calls == ["broke"]
    assert translator.translate("broke") == "falido"


def test_old_cache_without_alternatives_still_works_offline(monkeypatch):
    translator._cache_put("hello", "olá")                       # gravado por uma versão anterior

    def offline(text):
        raise OSError("sem rede")
    monkeypatch.setattr(translator, "_argos", lambda s: None)
    monkeypatch.setattr(translator, "_mymemory_senses", offline)
    assert translator.senses("hello") == ["olá"]
