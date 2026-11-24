import re
import ssl
from pathlib import Path

from legenday.services import http


def test_context_trusts_windows_and_certifi_authorities():
    ctx = http.ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    import certifi
    only_certifi = ssl.create_default_context(cafile=certifi.where()).cert_store_stats()["x509_ca"]
    only_system = ssl.create_default_context().cert_store_stats()["x509_ca"]
    # a lista do certifi entrou (no Linux ela costuma ser igual à do sistema; no Windows, soma às dele)
    assert ctx.cert_store_stats()["x509_ca"] >= max(only_certifi, only_system)
    assert only_certifi > 100


def test_every_service_connects_through_the_shared_context():
    """Ninguém chama urllib.request.urlopen direto (sem o certifi, o GitHub falhava no Windows)."""
    services = Path(http.__file__).parent
    direct = [p.name for p in services.glob("*.py")
              if p.name != "http.py" and re.search(r"urllib\.request\.urlopen\(", p.read_text(encoding="utf-8"))]
    assert direct == []
