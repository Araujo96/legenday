"""Vocabulário: salvar, revisão espaçada, banco antigo e exportação para o Anki."""
import sqlite3
from datetime import datetime, timedelta

from legenday.core.paths import data_dir
from legenday.core.vocab import VocabStore


def test_add_dedupes_and_lists():
    v = VocabStore()
    assert v.add("Gonna", "vou", sentence="I'm gonna go.", video="movie.mkv", lemma="")
    assert not v.add("gonna", "outra")           # mesma palavra (sem diferenciar maiúsculas)
    assert v.count() == 1 and v.has("GONNA")


def test_keys_include_lemmas():
    v = VocabStore()
    v.add("went", "foi", lemma="go")
    assert v.keys() == {"went", "go"}


def test_delete():
    v = VocabStore()
    v.add("a", "x"), v.add("b", "y")
    v.delete([w.id for w in v.all() if w.term == "a"])
    assert [w.term for w in v.all()] == ["b"]


def test_export_anki(tmp_path):
    v = VocabStore()
    v.add("went", "foi", sentence="She went <home> & slept.", video="My Movie (2020).mkv",
          lemma="go", definition="to move", phonetic="/went/")
    v.add("give up", "desistir", sentence="Don't give up!")
    out = tmp_path / "anki.txt"
    assert v.export_anki(out) == 2
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[:5] == ["#separator:tab", "#html:true", "#notetype:Basic", "#deck:legenDay", "#tags column:3"]
    first, second = (line.split("\t") for line in lines[5:])
    assert len(first) == 3 and first[0].startswith("<b>went</b>")
    assert "<b>foi</b>" in first[1] and "forma base: go" in first[1]
    assert "She <b>went</b> &lt;home&gt; &amp; slept." in first[1]   # HTML escapado e palavra destacada
    assert first[2] == "legenday My_Movie_2020_"
    assert second[0] == "<b>give up</b>" and second[2] == "legenday"


def test_anki_bolds_word_with_curly_apostrophe(tmp_path):
    v = VocabStore()
    v.add("don't", "não", sentence="I don’t know.")
    out = tmp_path / "anki.txt"
    v.export_anki(out)
    assert "I <b>don’t</b> know." in out.read_text(encoding="utf-8")

NOW = datetime(2026, 11, 16, 20, 0, 0)


def test_due_words_and_review_flow():
    v = VocabStore()
    v.add("one", "um")
    v.add("two", "dois")
    assert [w.term for w in v.due(NOW)] == ["one", "two"]                     # nunca revisadas, mais antigas antes
    one = v.due(NOW)[0]
    v.review(one.id, True, NOW)
    assert [w.term for w in v.due(NOW)] == ["two"]
    assert [w.term for w in v.due(NOW + timedelta(days=1))] == ["one", "two"]  # atrasada vem primeiro
    v.review(one.id, False, NOW)
    assert v.due_count(NOW + timedelta(minutes=11)) == 2


def test_old_vocabulary_database_gets_the_new_columns():
    path = data_dir() / "vocab.db"
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE words (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE NOT NULL,
        term TEXT NOT NULL, lemma TEXT DEFAULT '', translation TEXT NOT NULL, definition TEXT DEFAULT '',
        phonetic TEXT DEFAULT '', sentence TEXT DEFAULT '', video TEXT DEFAULT '', position REAL DEFAULT 0,
        created_at TEXT NOT NULL)""")
    con.execute("INSERT INTO words (key, term, translation, created_at) VALUES ('went', 'went', 'foi', 'x')")
    con.commit()
    con.close()
    v = VocabStore()
    w = v.all()[0]
    assert (w.term, w.box, w.due) == ("went", 0, "")                          # nada se perdeu
    v.review(w.id, True, NOW)
    assert v.all()[0].box == 1
