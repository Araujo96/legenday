"""Registro de erros em <pasta de dados>/legenday.log, para descobrir o que deu errado no PC de outra pessoa.

Fica só no computador (nada é enviado); o botão "Copiar informações para suporte" da ajuda inclui as últimas
linhas. O arquivo é limitado (LIMIT bytes + 1 cópia anterior) e nunca derruba o app se não puder ser gravado.
"""
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler

from legenday.core.paths import data_dir

FILE_NAME = "legenday.log"
LIMIT = 512_000

log = logging.getLogger("legenday")
log.propagate = False
log.addHandler(logging.NullHandler())      # registro desligado (testes, sem permissão): silêncio, nada no terminal
_hooks_installed = False


def setup() -> None:
    """Liga o registro (chamado ao abrir o app). Pode ser chamado de novo: troca o arquivo, sem duplicar."""
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()
    try:
        handler = RotatingFileHandler(data_dir() / FILE_NAME, maxBytes=LIMIT, backupCount=1, encoding="utf-8",
                                      delay=True)
    except OSError:
        log.addHandler(logging.NullHandler())    # sem permissão para gravar: segue sem registro
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    _install_hooks()


def _install_hooks() -> None:
    """Erros que ninguém tratou (num botão, num temporizador, numa thread) também vão para o registro."""
    global _hooks_installed
    if _hooks_installed:
        return
    previous = sys.excepthook

    def on_error(kind, value, tb):
        log.error("erro não tratado", exc_info=(kind, value, tb))
        if sys.stderr is not None:               # no .exe sem console não há onde mostrar
            previous(kind, value, tb)

    def on_thread_error(args):
        log.error("erro numa tarefa em segundo plano", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = on_error
    threading.excepthook = on_thread_error
    _hooks_installed = True


def problem(what: str, exc: BaseException) -> None:
    """Falha tratada pelo app: rede e arquivos (comuns) numa linha; o resto com o caminho do erro no código."""
    if isinstance(exc, OSError):
        log.warning("%s: %r", what, exc)
    else:
        log.warning("%s: %r", what, exc, exc_info=(type(exc), exc, exc.__traceback__))


def recent(lines: int = 30) -> str:
    """As últimas linhas do registro (para as informações de suporte); vazio se ainda não houver nada."""
    try:
        text = (data_dir() / FILE_NAME).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-lines:])
