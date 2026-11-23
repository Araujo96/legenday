"""Vocabulário salvo pelo usuário (SQLite), revisão espaçada e exportação para o Anki."""
import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from legenday.core import study
from legenday.core.paths import db

_SCHEMA = """CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    term TEXT NOT NULL,
    lemma TEXT DEFAULT '',
    translation TEXT NOT NULL,
    definition TEXT DEFAULT '',
    phonetic TEXT DEFAULT '',
    sentence TEXT DEFAULT '',
    video TEXT DEFAULT '',
    position REAL DEFAULT 0,
    created_at TEXT NOT NULL,
    box INTEGER DEFAULT 0,
    due TEXT DEFAULT '')"""

# colunas que versões antigas do app não tinham: são criadas sozinhas, sem perder o vocabulário
_ADDED = (("box", "INTEGER DEFAULT 0"), ("due", "TEXT DEFAULT ''"))
_COLUMNS = "id, term, lemma, translation, definition, phonetic, sentence, video, position, created_at, box, due"


@dataclass
class Word:
    id: int
    term: str
    lemma: str
    translation: str
    definition: str
    phonetic: str
    sentence: str
    video: str
    position: float
    created_at: str
    box: int = 0          # caixa da revisão espaçada (0 = nova ou errada)
    due: str = ""         # quando revisar de novo (vazio = ainda não revisada)


def make_key(term: str) -> str:
    return " ".join(term.replace("’", "'").lower().split())


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _field(text: str) -> str:
    return text.replace("\t", " ").replace("\r", "").replace("\n", "<br>")


def highlight(sentence: str, term: str) -> str:
    """Frase escapada para HTML, com a palavra em negrito ("don't" também acha "don’t")."""
    pattern = re.escape(_esc(term)).replace("'", "['’]")
    return re.sub(rf"(?i)\b({pattern})\b", r"<b>\1</b>", _esc(sentence))


class VocabStore:
    def __init__(self, name: str = "vocab.db"):
        self.name = name

    def _run(self, fn):
        """Abre o banco (garantindo a tabela e as colunas novas), executa fn(con) e grava."""
        with db(self.name) as con:
            con.execute(_SCHEMA)
            have = {row[1] for row in con.execute("PRAGMA table_info(words)")}
            for col, decl in _ADDED:
                if col not in have:
                    con.execute(f"ALTER TABLE words ADD COLUMN {col} {decl}")
            return fn(con)

    def add(self, term, translation, sentence="", video="", position=0.0,
            lemma="", definition="", phonetic="") -> bool:
        """Retorna True se salvou, False se a palavra já estava no vocabulário."""
        return self._run(lambda con: con.execute(
            "INSERT OR IGNORE INTO words (key, term, lemma, translation, definition, phonetic,"
            " sentence, video, position, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (make_key(term), term, lemma, translation, definition, phonetic, sentence, video,
             position, datetime.now().isoformat(timespec="seconds"))).rowcount > 0)

    def has(self, term: str) -> bool:
        return self._run(lambda con: con.execute(
            "SELECT 1 FROM words WHERE key = ?", (make_key(term),)).fetchone() is not None)

    def keys(self) -> set:
        """Termos e formas base salvos (minúsculos), para destacar palavras na legenda."""
        rows = self._run(lambda con: con.execute("SELECT key, lemma FROM words").fetchall())
        return {k for key, lem in rows for k in (key, make_key(lem)) if k}

    def all(self) -> list:
        rows = self._run(lambda con: con.execute(f"SELECT {_COLUMNS} FROM words ORDER BY id DESC").fetchall())
        return [Word(*r) for r in rows]

    def count(self) -> int:
        return self._run(lambda con: con.execute("SELECT COUNT(*) FROM words").fetchone()[0])

    def delete(self, ids) -> None:
        self._run(lambda con: con.executemany("DELETE FROM words WHERE id = ?", [(i,) for i in ids]))

    # ------------------------------------------------------------ revisão
    def due(self, now: "datetime | None" = None) -> list:
        """Palavras para revisar agora: as atrasadas primeiro, depois as nunca revisadas (mais antigas antes)."""
        now = now or datetime.now()
        words = [w for w in reversed(self.all()) if study.is_due(w.due, now)]
        return sorted(words, key=lambda w: (w.due == "", w.due, w.id))

    def due_count(self, now: "datetime | None" = None) -> int:
        return len(self.due(now))

    def review(self, word_id: int, correct: bool, now: "datetime | None" = None) -> None:
        now = now or datetime.now()
        row = self._run(lambda con: con.execute("SELECT box FROM words WHERE id = ?", (word_id,)).fetchone())
        if row is None:
            return
        box, when = study.schedule(row[0] or 0, correct, now)
        self._run(lambda con: con.execute("UPDATE words SET box = ?, due = ? WHERE id = ?",
                                          (box, when.isoformat(timespec="seconds"), word_id)))

    # ------------------------------------------------------------ Anki
    def export_anki(self, path, deck: str = "legenDay") -> int:
        """Gera um arquivo de texto (separado por tabs) que o Anki importa direto."""
        words = list(reversed(self.all()))  # mais antigas primeiro
        lines = ["#separator:tab", "#html:true", "#notetype:Basic", f"#deck:{deck}", "#tags column:3"]
        for w in words:
            front = f"<b>{_esc(w.term)}</b>"
            if w.phonetic:
                front += f"<br><small>{_esc(w.phonetic)}</small>"
            back = [f"<b>{_esc(w.translation)}</b>"]
            if w.lemma and make_key(w.lemma) != make_key(w.term):
                back.append(f"<i>forma base: {_esc(w.lemma)}</i>")
            if w.definition:
                back.append(_esc(w.definition))
            if w.sentence:
                back.append(f"<br><i>{highlight(w.sentence, w.term)}</i>")
            tag_video = re.sub(r"\W+", "_", Path(w.video).stem) if w.video else ""
            tags = " ".join(t for t in ("legenday", tag_video) if t)
            lines.append("\t".join([_field(front), _field("<br>".join(back)), tags]))
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return len(words)
