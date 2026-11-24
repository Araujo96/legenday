"""Confere no GitHub se saiu uma versão mais nova do que a instalada (uma consulta pequena, ao abrir o app)."""
import json
import re
import urllib.request
from dataclasses import dataclass

from legenday import __version__
from legenday.branding import REPO_URL
from legenday.services import http

API_URL = "https://api.github.com/repos/" + REPO_URL.split("github.com/", 1)[1] + "/releases/latest"
DOWNLOAD_URL = REPO_URL + "/releases/latest"
TIMEOUT = 6


@dataclass
class Update:
    version: str        # "0.6.0"
    url: str            # página da versão, com o .zip para baixar


def parse_version(text: str) -> tuple[int, ...]:
    """'v0.10.2' -> (0, 10, 2). Compara número a número (0.10 é mais nova que 0.9)."""
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3])


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"legenDay/{__version__}",      # o GitHub recusa pedidos sem identificação
    })
    with http.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def check(current: str = __version__, fetch=None) -> Update | None:
    """A versão mais nova publicada, se for maior que `current`; None se já está em dia.
    Falhas de rede levantam exceção (quem chama ignora: o aviso é só uma gentileza)."""
    data = (fetch or _fetch)(API_URL)
    if data.get("draft") or data.get("prerelease"):
        return None
    latest = parse_version(data.get("tag_name", ""))
    if latest and latest > parse_version(current):
        return Update(version=".".join(map(str, latest)), url=data.get("html_url") or DOWNLOAD_URL)
    return None
