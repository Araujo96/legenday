"""Pop-up em duas etapas: tradução, contexto, forma base, dicionário e pronúncia."""
import time

import pytest

from legenday.services import lookup
from legenday.services.dictionary import Entry


def test_single_word_gets_lemma_and_definition():
    tr = {"went": "foi", "go": "ir"}
    res = lookup.run("went", translate=tr.get, lemmatize=lambda w: "go",
                     define=lambda w: Entry("/ɡəʊ/", [["verb", "To move.", ""]]) if w == "go" else None)
    assert (res.translation, res.lemma, res.lemma_translation) == ("foi", "go", "ir")
    assert res.phonetic == "/ɡəʊ/" and res.meanings[0][0] == "verb"


def test_expression_skips_dictionary():
    called = []
    res = lookup.run("give up", translate=lambda t: "desistir", lemmatize=lambda w: called.append(w),
                     define=lambda w: called.append(w))
    assert res.translation == "desistir" and res.lemma is None and not called


def test_dictionary_failure_keeps_translation():
    def boom(_):
        raise OSError("sem rede")
    res = lookup.run("hello", translate=lambda t: "olá", lemmatize=lambda w: w, define=boom)
    assert res.translation == "olá" and res.meanings == []


def test_is_single():
    assert lookup.is_single("went") and lookup.is_single("don’t") and lookup.is_single("well-known")
    assert not lookup.is_single("give up") and not lookup.is_single("Hello, there.") and not lookup.is_single("")


def test_quick_does_not_wait_for_dictionary():
    def slow_define(w):
        time.sleep(1.0)
    t0 = time.time()
    res = lookup.quick("went", translate=lambda t: "foi", lemmatize=lambda w: "go")
    assert time.time() - t0 < 0.3 and res.translation == "foi" and res.lemma == "go"   # forma base é offline


def test_details_run_in_parallel():
    def tr(t):
        time.sleep(0.3)
        return "ir"

    def df(w):
        time.sleep(0.3)
        return Entry("/x/", [["verb", "d", ""]]) if w == "go" else None
    t0 = time.time()
    d = lookup.details("went", translate=tr, define=df, lemmatize=lambda w: "go")
    assert time.time() - t0 < 0.7                       # em fila seriam 0,9 s (tradução + 2 consultas)
    assert d.lemma_translation == "ir" and d.meanings[0][0] == "verb"


def test_details_survive_every_failure():
    def boom(*a):
        raise OSError("sem rede")
    d = lookup.details("went", translate=boom, define=boom, lemmatize=lambda w: "go")
    assert d.lemma_translation is None and d.meanings == []


def test_details_falls_back_to_the_base_form_recording():
    found = {"freak": "https://upload.wikimedia.org/x/En-us-freak.ogg"}
    d = lookup.details("freaked", translate=lambda t: ["x"], define=lambda w: None, lemmatize=lambda w: "freak",
                       pronounce=lambda w: found.get(w, ""))
    assert d.audio.endswith("En-us-freak.ogg")


@pytest.mark.parametrize("candidates, sentence, expected", [
    (["falido", "rompeu", "quebrou"], "Você quebrou meu coração.", "quebrou"),
    (["falido", "rompeu", "quebrou"], "Você quebrei tudo.", "quebrou"),          # mesmo radical
    (["pública de aquisição", "suave"], "Seja gentil com ela.", None),
    (["esmagar"], "Eu deveria esmagar você.", "esmagar"),
    (["lição"], "Ha uma licao a ser aprendida.", "lição"),                     # sem acento também combina
])
def test_pick_in_context(candidates, sentence, expected):
    assert lookup.pick_in_context(candidates, sentence) == expected


def test_context_picks_the_sense_used_in_the_scene():
    table = {"broke": ["falido", "rompeu", "quebrou"], "You broke my heart.": ["Você quebrou meu coração."],
             "break": ["quebrar"]}
    res = lookup.run("broke", "You broke my heart.", translate=table.get,
                     lemmatize=lambda w: "break", define=lambda w: None)
    assert res.translation == "quebrou"                      # antes: "falido"
    assert res.alternatives == ["falido", "rompeu"]
    assert res.context_translation == "Você quebrou meu coração."


def test_expression_gets_context_but_no_dictionary():
    called = []
    table = {"freaked out": ["surtou"], "You're freaked out.": ["Você surtou."]}
    res = lookup.run("freaked out", "You're freaked out.", translate=table.get,
                     lemmatize=lambda w: called.append(w), define=lambda w: called.append(w))
    assert res.context_translation == "Você surtou." and not called


def test_full_sentence_does_not_translate_itself_twice():
    calls = []

    def tr(t):
        calls.append(t)
        return ["Olá, mundo."]
    lookup.run("Hello, world.", "Hello, world.", translate=tr)
    assert calls == ["Hello, world."]
