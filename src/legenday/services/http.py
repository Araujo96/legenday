"""Conexões HTTPS dos serviços (tradução, dicionário, pronúncia e aviso de versão nova).

Confia nas autoridades certificadoras do Windows E nas do certifi. Só as do Windows não bastam: o Windows baixa
algumas autoridades raiz apenas quando um navegador pede, e o Python não pede. Foi assim que a consulta de versão
nova ao GitHub passou a falhar com "unable to get issuer certificate" enquanto os outros serviços funcionavam.
"""
import ssl
import urllib.request
from functools import lru_cache


@lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()           # autoridades do sistema (Windows)
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())   # + a lista do certifi, que já vem com o app
    except Exception:
        pass
    return ctx


def urlopen(req, timeout: float):
    return urllib.request.urlopen(req, timeout=timeout, context=ssl_context())
