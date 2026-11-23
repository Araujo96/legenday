"""Junta tradução, forma base e dicionário no resultado mostrado no pop-up.

O pop-up aparece em duas etapas, para não esperar a rede mais lenta:
  1) quick():   a tradução e os outros sentidos (e a forma base, que é offline) — chega primeiro;
  2) details(): tradução da fala inteira (contexto), da forma base, pronúncia e definições, em paralelo.

Contexto: uma palavra solta tem vários sentidos ("broke" = falido, quebrou, partiu). Por isso o pop-up
também mostra a fala inteira traduzida e, se um dos sentidos aparece nela, esse sentido vira o principal.
"""
import re
import socket
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from legenday.core import lemma
from legenday.services import dictionary, pronunciation, translator

_SINGLE = re.compile(r"^[A-Za-z]+(?:['-][A-Za-z]+)*$")


@dataclass
class Result:
    text: str
    translation: str = ""
    lemma: "str | None" = None
    lemma_translation: "str | None" = None
    phonetic: str = ""
    meanings: list = field(default_factory=list)  # [[classe, definição, exemplo], ...]
    alternatives: list = field(default_factory=list)  # outros sentidos da palavra/expressão
    context: str = ""                                 # fala inteira em que a palavra apareceu
    context_translation: "str | None" = None
    audio: str = ""                                   # link da pronúncia (dicionário)


@dataclass
class Details:
    lemma_translation: "str | None" = None
    phonetic: str = ""
    meanings: list = field(default_factory=list)
    context_translation: "str | None" = None
    audio: str = ""


def _main(value) -> str:
    """translate() pode devolver só o texto ou a lista [principal, alternativas...]."""
    return value[0] if isinstance(value, (list, tuple)) else value


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def pick_in_context(candidates: list, context_translation: str):
    """O sentido que aparece na fala traduzida, ou None. Compara sem acentos e pelo radical
    ("quebrou" combina com "quebrei"), para tolerar a conjugação diferente."""
    tokens = re.findall(r"\w+", _plain(context_translation or ""))
    if not tokens:
        return None
    for cand in candidates:
        words = [w for w in re.findall(r"\w+", _plain(cand)) if len(w) >= 4]
        if words and all(any(t.startswith(w[:max(4, len(w) - 2)]) for t in tokens) for w in words):
            return cand
    return None


def wants_context(text: str, context: str) -> bool:
    return bool(context) and _norm(context).lower() != _norm(text).lower()


def _norm(text: str) -> str:
    return text.strip().replace("’", "'")


def is_single(text: str) -> bool:
    """Palavra isolada: ganha forma base e dicionário. Expressões e frases só são traduzidas."""
    return bool(_SINGLE.match(_norm(text)))


def quick(text: str, *, translate=translator.senses, lemmatize=lemma.lemma_of) -> Result:
    """Etapa 1: só a tradução com os outros sentidos (uma consulta de rede) e a forma base (offline)."""
    text = _norm(text)
    found = translate(text)
    res = Result(text=text, translation=_main(found))
    if isinstance(found, (list, tuple)):
        res.alternatives = list(found[1:])
    if is_single(text):
        lem = lemmatize(text)
        if lem and lem != text.lower():
            res.lemma = lem
    return res


def _first_audio(pronounce, words) -> str:
    """Gravação da palavra clicada ou, se não houver, da forma base ("freaked" -> "freak")."""
    for w in words:
        url = pronounce(w)
        if url:
            return url
    return ""


def details(text: str, context: str = "", *, translate=translator.senses, define=dictionary.lookup,
            lemmatize=lemma.lemma_of, pronounce=pronunciation.find_audio) -> Details:
    """Etapa 2, tudo em paralelo: fala inteira traduzida (contexto) e, para palavra isolada, forma base
    traduzida, dicionário e pronúncia. Falhas aqui nunca atrapalham a tradução."""
    text = _norm(text)
    out = Details()
    lem, words = None, []
    if is_single(text):
        base = text.lower()
        lem = lemmatize(text)
        lem = lem if lem and lem != base else None
        words = list(dict.fromkeys([lem or base, base]))  # tenta a forma base e, se faltar, a palavra original
    with ThreadPoolExecutor(max_workers=5) as pool:
        f_ctx = pool.submit(translate, _norm(context)) if wants_context(text, context) else None
        f_lemma = pool.submit(translate, lem) if lem else None
        f_defs = [pool.submit(define, w) for w in words]
        f_audio = pool.submit(_first_audio, pronounce, [text.lower()] + ([lem] if lem else [])) if words else None
        for fut, attr in ((f_ctx, "context_translation"), (f_lemma, "lemma_translation"), (f_audio, "audio")):
            if fut:
                try:
                    setattr(out, attr, _main(fut.result()) or "")
                except Exception:
                    pass
        for f in f_defs:
            try:
                entry = f.result()
            except Exception:
                entry = None
            if entry:
                out.phonetic, out.meanings = entry.phonetic, entry.meanings
                break
    return out


def merge(res: Result, d: Details, context: str = "") -> Result:
    """Junta as duas etapas. Se um dos sentidos aparece na fala traduzida, ele passa a ser o principal."""
    res.lemma_translation, res.phonetic, res.meanings, res.audio = d.lemma_translation, d.phonetic, d.meanings, d.audio
    res.context, res.context_translation = context, d.context_translation
    senses = [res.translation, *res.alternatives]
    best = pick_in_context(senses, d.context_translation)
    if best and best != res.translation:
        res.translation, res.alternatives = best, [s for s in senses if s != best]
    return res


def run(text: str, context: str = "", *, translate=translator.senses, define=dictionary.lookup,
        lemmatize=lemma.lemma_of) -> Result:
    """Versão completa e síncrona (as duas etapas juntas)."""
    res = quick(text, translate=translate, lemmatize=lemmatize)
    if is_single(res.text) or wants_context(res.text, context):
        d = details(res.text, context, translate=translate, define=define, lemmatize=lemmatize)
        merge(res, d, context)
    return res


def warmup() -> None:
    """Roda em segundo plano ao abrir o app: carrega o lematizador e já resolve o endereço dos serviços,
    para o primeiro clique não pagar essa espera."""
    lemma.lemma_of("warm")
    for host in ("api.mymemory.translated.net", "api.dictionaryapi.dev", "commons.wikimedia.org"):
        try:
            socket.getaddrinfo(host, 443)
        except OSError:
            pass
