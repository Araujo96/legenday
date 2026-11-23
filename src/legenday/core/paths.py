"""Pasta de dados do usuário (~/.legenday) e acesso ao SQLite."""
import os
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

# raiz do repositório (src/legenday/core/paths.py -> 3 pastas acima); lá fica a pasta libs/
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _migrate_old_dir(new: Path) -> None:
    """Quem usou o app quando ele se chamava 'Legendário' mantém vocabulário, cache e ajustes."""
    old = new.with_name(".legendario")
    try:
        if old.is_dir() and not new.exists():
            old.rename(new)
    except OSError:
        pass


def data_dir() -> Path:
    custom = os.environ.get("LEGENDAY_DATA_DIR")
    d = Path(custom) if custom else Path.home() / ".legenday"
    if not custom:
        _migrate_old_dir(d)
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:   # sem permissão na pasta do usuário: o app continua, usando a pasta temporária
        d = Path(tempfile.gettempdir()) / ".legenday"
        d.mkdir(parents=True, exist_ok=True)
    return d


@contextmanager
def db(name: str):
    """Abre o banco, confirma (commit) ao sair e sempre fecha a conexão.
    Se o arquivo estiver corrompido, guarda uma cópia (*.corrompido-<hora>) e recomeça do zero."""
    path = data_dir() / name
    con = sqlite3.connect(path)
    try:
        con.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlite3.DatabaseError as exc:
        if "not a database" not in str(exc) and "malformed" not in str(exc):
            con.close()
            raise
        con.close()
        path.replace(path.with_name(f"{path.name}.corrompido-{int(time.time())}"))
        con = sqlite3.connect(path)
    try:
        with con:
            yield con
    finally:
        con.close()
