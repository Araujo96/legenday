# -*- mode: python ; coding: utf-8 -*-
# Receita do PyInstaller: gera a pasta dist/legenDay (com legenDay.exe no Windows).
#   pyinstaller packaging/legenday.spec --noconfirm
# Antes, coloque libs/libmpv-2.dll (e, se quiser legendas embutidas, libs/ffmpeg.exe).
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent
datas, binaries, hiddenimports = [], [], []

d, b, h = collect_all("simplemma")            # dicionários do lematizador
datas += d; binaries += b; hiddenimports += h

datas += [
    (str(ROOT / "src/legenday/assets"), "legenday/assets"),   # ícone
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
]
for name in ("libmpv-2.dll", "mpv-2.dll"):
    f = ROOT / "libs" / name
    if f.exists():
        binaries.append((str(f), "."))
ffmpeg = ROOT / "libs" / "ffmpeg.exe"
if ffmpeg.exists():
    datas.append((str(ffmpeg), "."))           # como dado: o PyInstaller não tenta analisar o executável

a = Analysis(
    [str(ROOT / "packaging/run_legenday.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    # imageio_ffmpeg traria um ffmpeg com licença GPL; o pacote usa só o ffmpeg LGPL de libs/
    excludes=["tkinter", "pytest", "imageio_ffmpeg", "argostranslate"],
)
# Partes do Qt que o app não usa (só widgets; o vídeo é desenhado pelo mpv): tirar deixa o pacote bem menor.
# opengl32sw = OpenGL por software (20 MB); Quick/Qml/Pdf vêm arrastados por plugins que nunca carregam aqui.
UNUSED_QT = ("opengl32sw", "qt6quick", "qt6qml", "qt6pdf", "qt6virtualkeyboard", "qt6network",
             "qpdf", "qtvirtualkeyboard", "qtquick", "qml")


def _used(entry) -> bool:
    name = Path(entry[0]).name.lower()
    return not any(name.startswith(u) for u in UNUSED_QT)


a.binaries = [b for b in a.binaries if _used(b)]
a.datas = [d for d in a.datas if not d[0].replace("\\", "/").lower().startswith("pyside6/qml/")]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="legenDay",
    console=False,                              # sem janela preta de terminal
    icon=str(ROOT / "src/legenday/assets/icon.ico"),
    upx=False,                                  # UPX aumenta falsos alertas de antivírus
)
coll = COLLECT(exe, a.binaries, a.datas, name="legenDay", upx=False)
