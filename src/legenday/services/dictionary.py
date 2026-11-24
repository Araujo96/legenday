"""Definições em inglês via Free Dictionary API (gratuita, sem chave), com cache local."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field

from legenday import __version__
from legenday.core.paths import db
from legenday.services import http

API = "https://api.dictionaryapi.dev/api/v2/entries/en/"
_SCHEMA = "CREATE TABLE IF NOT EXISTS dictionary (word TEXT PRIMARY KEY, data TEXT)"
TIMEOUT = 4          # o dicionário é um extra: não vale esperar mais que isso
_down_until = 0.0    # se o serviço falhar, fica 60 s sem tentar (os próximos cliques não esperam à toa)


@dataclass
class Entry:
    phonetic: str = ""
    meanings: list = field(default_factory=list)  # [[classe gramatical, definição, exemplo], ...]


def parse(payload) -> "Entry | None":
    if not isinstance(payload, list) or not payload:
        return None
    entry, seen = Entry(), set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        if not entry.phonetic:
            entry.phonetic = item.get("phonetic") or next(
                (p["text"] for p in (item.get("phonetics") or []) if isinstance(p, dict) and p.get("text")), "")
        for m in item.get("meanings") or []:
            if not isinstance(m, dict):
                continue
            pos = m.get("partOfSpeech") or ""
            defs = [d for d in (m.get("definitions") or []) if isinstance(d, dict) and d.get("definition")]
            if defs and pos not in seen:
                seen.add(pos)
                entry.meanings.append([pos, defs[0]["definition"], defs[0].get("example") or ""])
    entry.meanings = entry.meanings[:3]
    return entry if (entry.meanings or entry.phonetic) else None


def _fetch(word: str):
    req = urllib.request.Request(API + urllib.parse.quote(word), headers={"User-Agent": f"legenDay/{__version__}"})
    with http.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def lookup(word: str, fetch=_fetch) -> "Entry | None":
    word = word.lower().strip()
    try:                      # o cache é um extra: se falhar, consulta mesmo assim
        with db("cache.db") as con:
            con.execute(_SCHEMA)
            row = con.execute("SELECT data FROM dictionary WHERE word = ?", (word,)).fetchone()
        if row:
            data = json.loads(row[0])
            return Entry(**data) if data else None
    except Exception:
        pass
    global _down_until
    if time.monotonic() < _down_until:
        return None
    try:
        entry = parse(fetch(word))
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            _down_until = time.monotonic() + 60
            raise
        entry = None          # palavra inexistente: guarda no cache para não consultar de novo
    except Exception:
        _down_until = time.monotonic() + 60
        raise
    try:
        with db("cache.db") as con:
            con.execute(_SCHEMA)
            con.execute("INSERT OR REPLACE INTO dictionary VALUES (?, ?)",
                        (word, json.dumps(asdict(entry) if entry else None)))
    except Exception:
        pass
    return entry
