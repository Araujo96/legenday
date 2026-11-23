"""Pronúncia das palavras: gravações de pessoas reais do Wikimedia Commons (licença livre), com cache.

Os arquivos seguem o padrão "En-us-crush.ogg" (americano), "En-uk-..." (britânico) e "En-au-..." (australiano).
Uma consulta à API do Commons diz quais existem e devolve o link direto; o app prefere o americano.
(Os links de áudio que a Free Dictionary API devolve apontam para arquivos que não existem mais.)
"""
import json
import re
import urllib.parse
import urllib.request

from legenday import __version__
from legenday.core.paths import db

API = "https://commons.wikimedia.org/w/api.php"
ACCENTS = ("us", "uk", "au")
# o Wikimedia pede que programas se identifiquem; sem isso, recusa os pedidos
USER_AGENT = f"legenDay/{__version__} (aplicativo de código aberto para estudar inglês com legendas)"
TIMEOUT = 5
_SCHEMA = "CREATE TABLE IF NOT EXISTS pronunciation (word TEXT PRIMARY KEY, url TEXT)"
_WORD = re.compile(r"^[a-z]+(?:['-][a-z]+)*$")


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def query_url(word: str) -> str:
    titles = "|".join(f"File:En-{accent}-{word}.ogg" for accent in ACCENTS)
    return API + "?" + urllib.parse.urlencode({"action": "query", "titles": titles, "prop": "imageinfo",
                                               "iiprop": "url", "format": "json", "formatversion": "2"})


def pick(word: str, data: dict) -> str:
    """Link da gravação preferida (americana, depois britânica, depois australiana) ou vazio."""
    found = {}
    for page in (data.get("query") or {}).get("pages") or []:
        info = page.get("imageinfo") if isinstance(page, dict) else None
        if info and isinstance(info, list) and info[0].get("url"):
            found[str(page.get("title", "")).lower()] = info[0]["url"]
    for accent in ACCENTS:
        url = found.get(f"file:en-{accent}-{word}.ogg")
        if url and url.startswith("https://"):
            return url.split("?")[0]           # sem os parâmetros de rastreio (utm_...)
    return ""


def find_audio(word: str, fetch=None) -> str:
    """Link do áudio da pronúncia ou "" (sem gravação). Falha de rede levanta exceção e não vai para o cache."""
    fetch = fetch or _fetch
    word = word.replace("’", "'").lower().strip()
    if not _WORD.match(word):
        return ""
    try:
        with db("cache.db") as con:
            con.execute(_SCHEMA)
            row = con.execute("SELECT url FROM pronunciation WHERE word = ?", (word,)).fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    url = pick(word, fetch(query_url(word)))
    try:
        with db("cache.db") as con:
            con.execute(_SCHEMA)
            con.execute("INSERT OR REPLACE INTO pronunciation VALUES (?, ?)", (word, url))
    except Exception:
        pass
    return url
