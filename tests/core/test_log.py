import sys
import threading

import pytest

from legenday.core import log
from legenday.core.paths import data_dir


@pytest.fixture
def logging_on(monkeypatch):
    """Liga o registro na pasta de dados do teste e devolve os ganchos globais ao normal no fim."""
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)
    monkeypatch.setattr(log, "_hooks_installed", False)
    log.setup()
    yield
    for handler in list(log.log.handlers):
        log.log.removeHandler(handler)
        handler.close()
    log.log.addHandler(log.logging.NullHandler())


def read():
    return (data_dir() / log.FILE_NAME).read_text(encoding="utf-8")


def test_network_problems_are_one_line_and_bugs_keep_the_traceback(logging_on):
    log.problem("tradução", ConnectionError("sem internet"))
    try:
        {}["chave"]
    except KeyError as exc:
        log.problem("abrir o vocabulário", exc)
    text = read()
    assert "WARNING: tradução: ConnectionError('sem internet')" in text
    assert "Traceback" in text and "KeyError" in text and "test_log.py" in text   # de onde veio o erro


def test_unhandled_errors_are_recorded(logging_on, monkeypatch):
    monkeypatch.setattr(sys, "stderr", None)               # como no .exe sem console
    try:
        raise ValueError("botão quebrado")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    assert "erro não tratado" in read() and "ValueError: botão quebrado" in read()


def test_recent_returns_the_last_lines_and_setup_does_not_duplicate(logging_on):
    log.setup()                                            # chamado de novo: não pode gravar tudo em dobro
    for i in range(5):
        log.log.info("linha %d", i)
    assert read().count("linha 4") == 1
    assert log.recent(2).splitlines()[-1].endswith("linha 4")
    assert len(log.recent(2).splitlines()) == 2


def test_recent_is_empty_without_a_log():
    assert log.recent() == ""
