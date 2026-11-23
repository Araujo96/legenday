"""Arquivos JSON pequenos na pasta de dados: preferências (settings.json) e a sincronia de cada legenda
(offsets.json). Leitura nunca falha (arquivo ausente ou estragado = vazio)."""
import json

from legenday.core.paths import data_dir


class _JsonFile:
    def __init__(self, name: str):
        self.name = name

    def read(self) -> dict:
        try:
            data = json.loads((data_dir() / self.name).read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def write(self, data: dict) -> None:
        (data_dir() / self.name).write_text(json.dumps(data, indent=1), encoding="utf-8")


_SETTINGS = _JsonFile("settings.json")
_OFFSETS = _JsonFile("offsets.json")


# ---------------------------------------------------------------- preferências (ex.: "já mostrei a ajuda")
def get(key: str, default=None):
    return _SETTINGS.read().get(key, default)


def put(key: str, value) -> None:
    data = _SETTINGS.read()
    data[key] = value
    try:
        _SETTINGS.write(data)
    except OSError:
        pass          # sem permissão para gravar: segue sem lembrar


# ---------------------------------------------------------------- sincronia de cada legenda
def load_offset(key: str) -> float:
    try:
        return float(_OFFSETS.read().get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def save_offset(key: str, value: float) -> None:
    """Levanta OSError se não conseguir gravar (a janela avisa que o ajuste vale só nesta sessão)."""
    data = _OFFSETS.read()
    if value == 0:
        data.pop(key, None)
    else:
        data[key] = value
    _OFFSETS.write(data)
