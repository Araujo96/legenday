"""Ponto de entrada: python -m legenday [video] [legenda]

Atalhos: Espaço/Enter = play/pause (e fecha o pop-up) | R = repetir frase | ← → = -5s / +5s | F11 = tela cheia
Clique = traduz a palavra | Shift+clique = estende a seleção (expressão)
"""
import locale
import platform
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from legenday import __version__
from legenday.branding import APP_NAME, app_icon, set_windows_app_id
from legenday.core import log
from legenday.playback.mpv_loader import MPV_ERROR, mpv
from legenday.ui.main_window import MainWindow


def selftest() -> int:
    """Verificação sem janela, usada ao montar o executável: confere se tudo que o app precisa está empacotado.
    Escreve o resultado em selftest.txt (o executável do Windows não tem console) e devolve 0 se tudo certo."""
    import os
    import platform
    import subprocess
    from pathlib import Path

    from legenday import __version__
    from legenday.core import embedded

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    locale.setlocale(locale.LC_NUMERIC, "C")
    lines = [f"{APP_NAME} {__version__} · Python {platform.python_version()} · {platform.platform()}"]
    state = {"ok": True}

    def check(name, fn, required=True):
        try:
            lines.append(f"OK     {name}: {fn()}")
        except Exception as exc:
            lines.append(f"{'FALHA ' if required else 'AVISO '} {name}: {exc!r}")
            if required:                         # de onde veio o erro: essencial para consertar uma build quebrada
                import traceback
                lines.extend("         " + x.strip() for x in traceback.format_exc(limit=-4).splitlines()[1:-1])
            state["ok"] = state["ok"] and not required

    def libmpv():
        if mpv is None:
            raise RuntimeError(MPV_ERROR)
        player = mpv.MPV(vo="null", ao="null")
        version = player.mpv_version
        player.terminate()
        return version

    def qt():
        app = QApplication.instance() or QApplication([])
        icon = app_icon()
        if icon.isNull():
            raise RuntimeError("ícone não encontrado dentro do pacote")
        return f"plataforma '{app.platformName()}', ícone {icon.availableSizes()[0].width()}px"

    def lemmas():
        from simplemma import lemmatize  # direto (e não lemma_of, que engole o erro): mostra a causa
        result = lemmatize("went", lang="en")
        if result != "go":
            raise RuntimeError(f"went -> {result}")
        return "went -> go"

    def subtitles():
        import pysubs2
        subs = pysubs2.SSAFile.from_string("1\n00:00:01,000 --> 00:00:02,000\nHello\n", format_="srt")
        return f"{len(subs)} fala lida"

    def ffmpeg():
        path = embedded.find_ffmpeg()
        if not path:
            raise RuntimeError("não encontrado (legendas embutidas ficam indisponíveis)")
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=20).stdout.splitlines()[0]
        return out[:60]

    check("libmpv (reprodução)", libmpv)
    check("Qt e ícone", qt)
    check("forma base das palavras", lemmas)
    check("leitura de legendas", subtitles)
    check("ffmpeg (legendas embutidas)", ffmpeg, required=False)
    lines.append("RESULTADO: " + ("tudo certo" if state["ok"] else "HÁ FALHAS"))
    text = "\n".join(lines)
    target = Path(sys.executable).parent / "selftest.txt" if getattr(sys, "frozen", False) else Path("selftest.txt")
    try:
        target.write_text(text, encoding="utf-8")
    except OSError:
        pass
    print(text)
    return 0 if state["ok"] else 1


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    if "--selftest" in argv:
        return selftest()
    log.setup()
    log.log.info("%s %s aberto (%s)", APP_NAME, __version__, platform.platform())
    set_windows_app_id()
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())
    locale.setlocale(locale.LC_NUMERIC, "C")  # exigido pelo libmpv
    if mpv is None:
        log.log.error("libmpv não encontrado: %s", MPV_ERROR)
        QMessageBox.critical(
            None, "libmpv não encontrado",
            "Coloque o arquivo libmpv-2.dll na pasta libs/ do projeto (veja o README).\n\n" + str(MPV_ERROR))
        return 1
    win = MainWindow()
    avail = app.primaryScreen().availableGeometry()   # abre num tamanho que cabe na tela
    win.resize(min(1280, int(avail.width() * 0.92)), min(800, int(avail.height() * 0.92)))
    win.show()
    if len(argv) > 1:
        win.open_video(argv[1])
    if len(argv) > 2:
        win.open_subtitle(argv[2])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
