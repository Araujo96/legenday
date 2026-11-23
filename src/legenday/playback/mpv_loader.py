"""Localiza e carrega o libmpv (no Windows, o libmpv-2.dll).

Procura, nesta ordem: variável LEGENDAY_MPV_DIR, pasta do executável (versão empacotada),
pasta libs/ do projeto e raiz do projeto. (A pasta atual fica de fora de propósito: abrir o app de dentro de
uma pasta baixada não pode fazer ele carregar uma DLL estranha que esteja lá.)
"""
import os
import sys
from pathlib import Path

from legenday.core.paths import PROJECT_ROOT


def _candidates():
    env = os.environ.get("LEGENDAY_MPV_DIR")
    if env:
        yield Path(env)
    if getattr(sys, "frozen", False):
        yield Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        yield Path(sys.executable).parent
    root = PROJECT_ROOT
    yield root / "libs"
    yield root


for _dir in reversed(list(_candidates())):  # o primeiro candidato fica na frente do PATH
    if _dir.is_dir():
        os.environ["PATH"] = str(_dir) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(_dir))
            except OSError:
                pass

try:
    import mpv
    MPV_ERROR = None
except (ImportError, OSError) as exc:
    mpv = None
    MPV_ERROR = str(exc)
