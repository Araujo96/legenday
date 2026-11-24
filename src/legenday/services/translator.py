"""Tradução EN -> PT-BR: Argos (offline, se instalado) e MyMemory (online, gratuito) como reserva.
Resultados ficam em cache no SQLite para o pop-up ser instantâneo na segunda vez."""
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from legenday import __version__
from legenday.core.paths import db
from legenday.services import http

_SCHEMA = "CREATE TABLE IF NOT EXISTS translations (src TEXT PRIMARY KEY, pt TEXT)"


def _key(text: str) -> str:
    """Ignora maiúsculas só na 1ª letra (início de frase: "Went" = "went"), mas mantém siglas e nomes
    com maiúsculas no meio separados: "US" (EUA) não pode reaproveitar a tradução de "us" (nós)."""
    return text if any(c.isupper() for c in text[1:]) else text.lower()


def _cache_get(text: str):
    try:                      # o cache é um extra: se falhar, traduz mesmo assim
        with db("cache.db") as con:
            con.execute(_SCHEMA)
            row = con.execute("SELECT pt FROM translations WHERE src = ?", (_key(text),)).fetchone()
        return row[0] if row else None
    except Exception:
        return None


_ALTS = "CREATE TABLE IF NOT EXISTS alternatives (src TEXT PRIMARY KEY, alts TEXT)"


def _alts_get(text: str):
    """Alternativas guardadas (lista) ou None se esse texto ainda não foi consultado nesta versão."""
    try:
        with db("cache.db") as con:
            con.execute(_ALTS)
            row = con.execute("SELECT alts FROM alternatives WHERE src = ?", (_key(text),)).fetchone()
        return json.loads(row[0]) if row else None
    except Exception:
        return None


def _alts_put(text: str, alts: list):
    try:
        with db("cache.db") as con:
            con.execute(_ALTS)
            con.execute("INSERT OR REPLACE INTO alternatives VALUES (?, ?)", (_key(text), json.dumps(alts)))
    except Exception:
        pass


def _cache_put(text: str, pt: str):
    try:
        with db("cache.db") as con:
            con.execute(_SCHEMA)
            con.execute("INSERT OR REPLACE INTO translations VALUES (?, ?)", (_key(text), pt))
    except Exception:
        pass


_ARGOS = {"loaded": False, "tr": None}


def _argos_translation():
    """Localiza o modelo offline EN->PT uma única vez (antes, relia tudo a cada clique)."""
    if not _ARGOS["loaded"]:
        _ARGOS["loaded"] = True
        try:
            import argostranslate.translate as at
            langs = at.get_installed_languages()
            src = next((lang for lang in langs if lang.code == "en"), None)
            dst = next((lang for lang in langs if lang.code == "pt"), None)
            _ARGOS["tr"] = src.get_translation(dst) if src and dst else None
        except Exception:
            _ARGOS["tr"] = None
    return _ARGOS["tr"]


def _argos(text: str):
    tr = _argos_translation()
    if not tr:
        return None
    try:
        return tr.translate(text)
    except Exception:          # modelo offline com problema: cai para a tradução online
        return None


_REFUSED = ("MYMEMORY WARNING", "PLEASE SELECT", "INVALID", "QUERY LENGTH")
MAX_SENSES = 4          # tradução principal + até 3 alternativas


def _segment(text: str) -> str:
    return " ".join(re.sub(r"[^\w']+", " ", text.lower()).split())


def _quality(match: dict) -> int:
    try:
        return int(float(match.get("quality") or 0))
    except (TypeError, ValueError):
        return 0


def pick_senses(src: str, data: dict) -> list:
    """Tradução principal + alternativas, a partir da resposta do MyMemory.

    O MyMemory é uma memória de traduções: além da principal, devolve outras traduções humanas do mesmo
    trecho ("broke" -> falido, rompeu, quebrou). Aqui ficam só as do mesmo trecho e com qualidade > 0,
    limpas e sem repetição; a que só repete a palavra em inglês ("remind" -> "remind") vai para o fim."""
    rd = data.get("responseData") or {}
    raw = [rd.get("translatedText")]
    key = _segment(src)
    for m in data.get("matches") or []:
        if isinstance(m, dict) and _quality(m) > 0 and _segment(str(m.get("segment") or "")) == key:
            raw.append(m.get("translation"))
    found, untranslated, seen = [], [], set()
    for t in raw:
        t = html.unescape(str(t or "")).strip()
        if not t or t.upper().startswith(_REFUSED) or _is_junk(src, t):
            continue
        t = tidy(src, t)
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        (untranslated if _segment(t) == key else found).append(t)
    out = (found + untranslated)[:MAX_SENSES]
    if not out:
        raise RuntimeError("o serviço gratuito recusou o pedido (limite diário atingido?)")
    return out


def _mymemory_senses(text: str) -> list:
    url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(
        {"q": text, "langpair": "en|pt-BR"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": f"legenDay/{__version__}"})
    with http.urlopen(req, timeout=8) as resp:
        data = json.load(resp)
    if str(data.get("responseStatus")) != "200":
        raise RuntimeError(data.get("responseDetails", "erro na tradução"))
    return pick_senses(text, data)


def _mymemory(text: str) -> str:
    return _mymemory_senses(text)[0]


def tidy(src: str, out: str) -> str:
    """Limpa vícios das traduções automáticas: travessão de diálogo que não existe no original
    ("- Há uma lição") e maiúscula inventada numa palavra comum ("heart" -> "Coração")."""
    out = out.strip()
    if not src.lstrip().startswith(("-", "–", "—")):
        out = out.lstrip("-–— ").strip() or out
    if src[:1].islower() and out[:1].isupper() and (out[1:2].islower() or out[1:2] == " "):
        out = out[0].lower() + out[1:]                  # "Coração" -> "coração", "A paixão" -> "a paixão"
    if src.rstrip()[-1:].isalnum():                     # "changed" -> "mudou", não "mudou."
        out = out.rstrip(".!?;:… ").strip() or out
    return out


def _is_junk(src: str, out: str) -> bool:
    """Rótulos de programa que a memória de tradução às vezes devolve ("forgot" -> "ENVIAR")."""
    letters = [c for c in out if c.isalpha()]
    return len(letters) > 2 and out.isupper() and not src.isupper()


def senses(text: str) -> list:
    """[tradução principal, alternativas...]. Usa o cache; sem rede, devolve o que estiver guardado."""
    text = text.strip()
    cached, alts = _cache_get(text), _alts_get(text)
    if cached and alts is not None:
        return [tidy(text, cached), *alts]
    offline = _argos(text)
    if offline:
        result = [tidy(text, offline)]
    else:
        try:
            result = _mymemory_senses(text)
        except Exception as exc:
            if cached:                      # traduzido numa versão antiga (sem alternativas): serve assim
                return [tidy(text, cached)]
            raise _friendly(exc) from exc
    _cache_put(text, result[0])
    _alts_put(text, result[1:])
    return result


def _friendly(exc: Exception) -> RuntimeError:
    if isinstance(exc, urllib.error.HTTPError):          # o serviço respondeu, mas com erro (ex.: 429, 500)
        return RuntimeError(f"O serviço de tradução respondeu com erro {exc.code}")
    if isinstance(exc, (urllib.error.URLError, TimeoutError)):   # sem internet ou servidor fora do ar
        return RuntimeError("Sem conexão com o serviço de tradução (e sem modelo offline instalado)")
    return RuntimeError(f"Não foi possível traduzir: {exc}")


def translate(text: str) -> str:
    return senses(text)[0]
