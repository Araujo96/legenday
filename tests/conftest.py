import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Cada teste usa uma pasta de dados vazia, sem tocar em ~/.legenday."""
    monkeypatch.setenv("LEGENDAY_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture(autouse=True)
def no_pronunciation_network(monkeypatch):
    """Os testes nunca consultam o Wikimedia de verdade (quem precisa, injeta uma resposta falsa)."""
    from legenday.services import pronunciation

    def offline(url):
        raise OSError("rede desligada nos testes")
    monkeypatch.setattr(pronunciation, "_fetch", offline)
