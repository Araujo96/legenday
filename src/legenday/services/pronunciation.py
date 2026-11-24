"""Pronúncia das palavras: gravações de pessoas reais do Wikimedia Commons (licença livre), com cache.

Os arquivos seguem o padrão "En-us-crush.ogg" (americano), "En-uk-..." (britânico) e "En-au-..." (australiano).
Uma consulta à API do Commons diz quais existem e devolve o link direto; o app prefere o americano.
Palavras sem arquivo nesse padrão (como "the", gravada como "en-us-the-unstressed.ogg") são procuradas nos áudios
que o Wiktionary usa na página da palavra. (Os links de áudio da Free Dictionary API apontam para arquivos que não
existem mais.)

O áudio é baixado pelo app e guardado no computador: a mesma palavra não depende mais da internet, e um "429"
(pedidos demais) do servidor de arquivos do Wikimedia é tentado de novo, em vez de o botão ficar mudo.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from legenday import __version__
from legenday.branding import REPO_URL
from legenday.core.paths import data_dir, db
from legenday.services import http

API = "https://commons.wikimedia.org/w/api.php"
WIKTIONARY = "https://en.wiktionary.org/w/api.php"
ACCENTS = ("us", "uk", "au")
MORE_ACCENTS = ("us", "uk", "au", "ca", "nz")
# o Wikimedia pede que programas se identifiquem com um contato; sem isso, recusa os pedidos ou limita bem mais
USER_AGENT = f"legenDay/{__version__} ({REPO_URL}; aplicativo de código aberto para estudar inglês com legendas)"
TIMEOUT = 5
AUDIO_DIR = "pronuncia"
TRIES = 3
MAX_WAIT = 3.0
# tabela nova: a antiga guardou "sem gravação" para palavras que agora são achadas pelo Wiktionary
_SCHEMA = "CREATE TABLE IF NOT EXISTS pronunciation2 (word TEXT PRIMARY KEY, url TEXT)"
_WORD = re.compile(r"^[a-z]+(?:['-][a-z]+)*$")
_AUDIO_EXT = r"\.(?:ogg|oga|wav|mp3|flac|opus)"


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with http.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def _fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with http.urlopen(req, timeout=TIMEOUT * 2) as resp:
        return resp.read()


def _api(base: str, **params) -> str:
    return base + "?" + urllib.parse.urlencode({"action": "query", "format": "json", "formatversion": "2", **params})


def query_url(word: str) -> str:
    titles = "|".join(f"File:En-{accent}-{word}.ogg" for accent in ACCENTS)
    return _api(API, titles=titles, prop="imageinfo", iiprop="url")


def _urls(data: dict) -> dict:
    """{título em minúsculas: link direto} dos arquivos que existem na resposta do Commons."""
    found = {}
    for page in (data.get("query") or {}).get("pages") or []:
        info = page.get("imageinfo") if isinstance(page, dict) else None
        if info and isinstance(info, list) and str(info[0].get("url", "")).startswith("https://"):
            found[str(page.get("title", "")).lower()] = info[0]["url"].split("?")[0]   # sem os parâmetros utm_
    return found


def pick(word: str, data: dict) -> str:
    """Link da gravação preferida (americana, depois britânica, depois australiana) ou vazio."""
    found = _urls(data)
    for accent in ACCENTS:
        url = found.get(f"file:en-{accent}-{word}.ogg")
        if url:
            return url
    return ""


def rank_wiktionary(word: str, titles: list[str]) -> list[str]:
    """Áudios em inglês da página do Wiktionary, do melhor para o pior: sotaque (americano primeiro), depois a
    forma comum, a átona ("the" como se fala no meio da frase) e a tônica; por último, as do Lingua Libre."""
    w = re.escape(word)
    plain = re.compile(rf"^file:en-({'|'.join(MORE_ACCENTS)})-{w}(-unstressed|-stressed)?{_AUDIO_EXT}$")
    libre = re.compile(rf"^file:ll-q1860 \(eng\)-.+-{w}{_AUDIO_EXT}$")       # Q1860 = inglês no Lingua Libre
    scored = []
    for title in titles:
        low = title.lower()
        m = plain.match(low)
        if m:
            form = {None: 0, "-unstressed": 1, "-stressed": 2}[m.group(2)]
            scored.append(((MORE_ACCENTS.index(m.group(1)), form), title))
        elif libre.match(low):
            scored.append(((len(MORE_ACCENTS), 0), title))
    return [t for _, t in sorted(scored)]


def from_wiktionary(word: str, fetch) -> str:
    # o título diferencia maiúsculas: "I'm" e nomes próprios ("Monday") só existem com a inicial maiúscula
    titles = "|".join(dict.fromkeys((word, word[:1].upper() + word[1:])))
    pages = (fetch(_api(WIKTIONARY, titles=titles, prop="images", imlimit="100")).get("query") or {}).get("pages") or []
    images = [i.get("title", "") for page in pages if isinstance(page, dict) for i in page.get("images") or []]
    candidates = rank_wiktionary(word, list(dict.fromkeys(images)))[:5]
    if not candidates:
        return ""
    found = _urls(fetch(_api(API, titles="|".join(candidates), prop="imageinfo", iiprop="url")))
    for title in candidates:                       # o Commons devolve o título com a 1ª letra maiúscula
        url = found.get(title.lower())
        if url:
            return url
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
            row = con.execute("SELECT url FROM pronunciation2 WHERE word = ?", (word,)).fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    url = pick(word, fetch(query_url(word))) or from_wiktionary(word, fetch)
    try:
        with db("cache.db") as con:
            con.execute(_SCHEMA)
            con.execute("INSERT OR REPLACE INTO pronunciation2 VALUES (?, ?)", (word, url))
    except Exception:
        pass
    return url


def _wait_for(exc: urllib.error.HTTPError, attempt: int) -> float:
    try:
        wait = float(exc.headers.get("Retry-After", ""))
    except (TypeError, ValueError, AttributeError):
        wait = attempt + 1.0
    return min(max(wait, 0.5), MAX_WAIT)


def local_file(url: str, fetch_bytes=None, sleep=time.sleep) -> Path:
    """O áudio no computador (baixa na primeira vez). Levanta exceção se não der para baixar."""
    name = re.sub(r"[^\w.\-()]+", "_", urllib.parse.unquote(url.rsplit("/", 1)[-1]))[-120:] or "audio.ogg"
    folder = data_dir() / AUDIO_DIR
    path = folder / name
    if path.is_file() and path.stat().st_size > 0:
        return path
    fetch_bytes = fetch_bytes or _fetch_bytes
    for attempt in range(TRIES):
        try:
            data = fetch_bytes(url)
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == TRIES - 1:
                raise
            sleep(_wait_for(exc, attempt))        # servidor ocupado: espera um pouco e tenta de novo
    if not data:
        raise OSError("áudio vazio")
    folder.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)
    return path


def find_and_download(word: str) -> str:
    """Para a consulta da palavra: acha a gravação e já deixa o arquivo baixado, para o clique tocar na hora.
    Se só o download falhar, devolve o link mesmo assim (o clique tenta de novo)."""
    url = find_audio(word)
    if url:
        try:
            local_file(url)
        except Exception:
            pass
    return url
