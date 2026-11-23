"""Forma base das palavras."""
import pytest


def test_lemma_of():
    pytest.importorskip("simplemma")
    from legenday.core.lemma import lemma_of
    assert lemma_of("went") == "go" and lemma_of("Children") == "child"
    assert lemma_of("don't") == "don't"             # contrações ficam como estão
