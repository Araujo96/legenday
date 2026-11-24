"""Nome do app e ícone (imagens prontas em assets/icon.png e assets/icon.ico)."""
import sys
from pathlib import Path

from PySide6.QtGui import QIcon

APP_NAME = "legenDay"
APP_ID = "legenday.app"  # identifica o app na barra de tarefas do Windows
TAGLINE = "Pratique inglês assistindo filmes"
REPO_URL = "https://github.com/Araujo96/legenday"  # aparece em Ajuda > Sobre

# Doações por PIX (botão ♥ na barra). Com PIX_KEY vazia, o botão não aparece.
# Use uma chave aleatória ou de e-mail: a chave fica visível para quem doa (evite CPF e celular).
PIX_KEY = "araujo.dev996@gmail.com"
PIX_NAME = "Lucas Araujo"     # nome do recebedor no QR Code (até 25 letras, sem acento)
PIX_CITY = "Natal"            # cidade do recebedor (até 15 letras)

ASSETS = Path(__file__).resolve().parent / "assets"


def app_icon() -> QIcon:
    return QIcon(str(ASSETS / "icon.png"))


def set_windows_app_id():
    """Sem isso, o Windows agrupa a janela sob o ícone do Python na barra de tarefas."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass
