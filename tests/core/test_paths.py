"""Pasta de dados, migração do nome antigo e banco de dados corrompido."""
import sqlite3
from pathlib import Path

import pytest

from legenday.core.paths import data_dir, db
from legenday.core.vocab import VocabStore


def test_old_data_folder_is_migrated(tmp_path, monkeypatch):
    monkeypatch.delenv("LEGENDAY_DATA_DIR")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    old = tmp_path / ".legendario"
    old.mkdir()
    (old / "marcador.txt").write_text("dados antigos")
    assert data_dir() == tmp_path / ".legenday"
    assert (tmp_path / ".legenday" / "marcador.txt").read_text() == "dados antigos"
    assert not old.exists()


def test_existing_new_folder_is_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.delenv("LEGENDAY_DATA_DIR")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".legendario").mkdir()
    (tmp_path / ".legenday").mkdir()
    (tmp_path / ".legenday" / "novo.txt").write_text("x")
    data_dir()
    assert (tmp_path / ".legendario").exists() and (tmp_path / ".legenday" / "novo.txt").exists()


def test_vocabulary_survives_migration(tmp_path, monkeypatch):
    monkeypatch.setenv("LEGENDAY_DATA_DIR", str(tmp_path / "x"))
    VocabStore().add("went", "foi")
    assert VocabStore().has("went")


def test_corrupted_database_is_backed_up_and_recreated():
    (data_dir() / "cache.db").write_bytes(b"isto nao e um banco" * 50)
    with db("cache.db") as con:
        con.execute("CREATE TABLE t (x)")
    assert list(data_dir().glob("cache.db.corrompido-*"))          # cópia guardada
    with db("cache.db") as con:
        assert con.execute("SELECT count(*) FROM t").fetchone()[0] == 0


def test_unwritable_home_falls_back_to_temp(monkeypatch, tmp_path):
    blocker = tmp_path / "arquivo"
    blocker.write_text("x")
    monkeypatch.setenv("LEGENDAY_DATA_DIR", str(blocker / "sub"))      # impossível criar dentro de um arquivo
    assert data_dir().exists()


def test_other_sqlite_errors_are_not_swallowed(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise sqlite3.OperationalError("unable to open database file")
    monkeypatch.setattr("legenday.core.paths.sqlite3.connect", boom)
    with pytest.raises(sqlite3.OperationalError):
        with db("x.db"):
            pass
