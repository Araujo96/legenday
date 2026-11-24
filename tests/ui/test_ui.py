"""Testes da interface (pytest-qt), com um player falso no lugar do mpv."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QEvent, QMimeData, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDropEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from legenday.core import settings  # noqa: E402
from legenday.playback.player import Player  # noqa: E402
from legenday.services import lookup, updates  # noqa: E402
from legenday.services.lookup import Details, Result  # noqa: E402
from legenday.ui.main_window import MainWindow  # noqa: E402
from legenday.ui.review_dialog import ReviewDialog  # noqa: E402
from legenday.ui.vocab_dialog import VocabDialog  # noqa: E402

SRT = """1
00:00:01,000 --> 00:00:02,000
You broke my heart.

2
00:00:03,000 --> 00:00:04,000
I know.

3
00:00:05,000 --> 00:00:06,000
Be tender to her.
"""
SRT_PT = SRT.replace("You broke my heart.", "Você partiu meu coração.").replace("I know.", "Eu sei.")


class FakeMpv:
    """Imita o que o app usa do python-mpv."""

    def __init__(self):
        self.pause, self.time_pos, self.duration = True, None, None
        self.track_list, self.mpv_version = [], "mpv falso"
        self.commands, self.played = [], []

    def play(self, path):
        self.played.append(path)
        self.time_pos, self.duration = 0.0, 100.0

    def seek(self, amount, ref="absolute", precision="exact"):
        self.time_pos = amount if ref == "absolute" else (self.time_pos or 0) + amount

    def command(self, *args):
        self.commands.append(args)

    def terminate(self):
        pass


class FakeSound:
    def __init__(self):
        self.played = []

    def play(self, url):
        self.played.append(url)
        return True

    def terminate(self):
        pass


@pytest.fixture
def win(qtbot, tmp_path):
    settings.put("tour_seen", True)
    raw = FakeMpv()
    w = MainWindow(player=Player(raw), sound=FakeSound())
    w.raw = raw
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    qtbot.waitExposed(w)
    video = tmp_path / "Filme.mkv"
    video.write_bytes(b"")
    (tmp_path / "Filme.srt").write_text(SRT, encoding="utf-8")
    w.open_video(str(video))                         # a legenda ao lado abre sozinha
    yield w
    w.popup.close()


def at(win, t):
    win.raw.time_pos = t
    win._tick()


def fake_lookup(monkeypatch, translation="partiu", audio="https://x/broke-us.mp3"):
    monkeypatch.setattr(lookup, "quick", lambda text: Result(text=text, translation=translation,
                                                             alternatives=["falido"]))
    monkeypatch.setattr(lookup, "details", lambda text, context="": Details(
        phonetic="/bɹəʊk/", meanings=[["verb", "To break.", ""]], context_translation="Você partiu meu coração.",
        audio=audio))


def click_word(qtbot, win, word):
    label = next(w for w in win.subview.words if w.text() == word)
    qtbot.mouseClick(label, Qt.LeftButton)


def drop(win, *paths):
    data = QMimeData()
    data.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    event = QDropEvent(QPointF(10, 10), Qt.CopyAction, data, Qt.LeftButton, Qt.NoModifier)
    win.dropEvent(event)


# ---------------------------------------------------------------- tour guiado
def test_first_run_shows_the_tour_once(qtbot):
    w = MainWindow(player=Player(FakeMpv()), sound=FakeSound())    # pasta de dados nova: nunca viu o tour
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    qtbot.waitUntil(lambda: w._tour is not None and w._tour.isVisible(), timeout=3000)
    tour = w._tour
    for _ in tour.steps:                          # seta para a direita até o fim
        qtbot.keyClick(tour, Qt.Key_Right)
    assert w._tour is None and not tour.isVisible()
    assert settings.get("tour_seen") is True


def test_tour_highlights_each_part_and_keeps_the_card_on_screen(win):
    win.start_tour()
    tour = win._tour
    assert tour.geometry().size() == win.size()
    for i, step in enumerate(tour.steps):
        tour.go(i)
        card = tour.card.geometry()
        assert tour.rect().contains(card), step.title                     # cartão inteiro dentro da janela
        if step.targets():
            assert not tour.hole.isNull() and tour.rect().contains(tour.hole.center()), step.title
            assert not card.intersects(tour.hole), step.title             # o cartão não cobre o que explica
        else:
            assert tour.hole.isNull()
    win._tour.finish()


def test_tour_shows_the_translate_line_button_even_without_a_film(qtbot):
    settings.put("tour_seen", True)
    w = MainWindow(player=Player(FakeMpv()), sound=FakeSound())      # recém-aberto: sem filme, sem legenda
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    btn = w.subview.btn
    assert not btn.isVisible()
    w.start_tour()
    tour = w._tour
    i = next(k for k, s in enumerate(tour.steps) if "frase inteira" in s.title)
    tour.go(i)
    assert btn.isVisible()
    spot = btn.geometry().translated(btn.parentWidget().mapTo(w, btn.geometry().topLeft()) - btn.pos())
    assert tour.hole.contains(spot.center())                     # o destaque cai no botão
    tour.finish()
    assert not btn.isVisible()                                   # sem legenda, volta a ficar escondido


def test_tour_back_and_escape(qtbot, win):
    win.start_tour()
    tour = win._tour
    qtbot.keyClick(tour, Qt.Key_Right)
    qtbot.keyClick(tour, Qt.Key_Right)
    qtbot.keyClick(tour, Qt.Key_Left)
    assert tour.i == 1 and tour.back_btn.isVisible()
    assert not any(sc.isEnabled() for sc in win._shortcuts)    # as setas eram do tour, não do vídeo
    qtbot.keyClick(tour, Qt.Key_Escape)
    assert win._tour is None
    assert all(sc.isEnabled() for sc in win._shortcuts)        # e voltam a ser do vídeo


def test_help_can_replay_the_tour(qtbot, win):
    win.show_help()
    win._help.tour_btn.click()
    assert not win._help.isVisible()
    assert win._tour is not None and win._tour.isVisible()
    win._tour.finish()


# ---------------------------------------------------------------- versão nova e doação
def test_new_version_shows_a_download_button(qtbot, win, monkeypatch):
    opened = []
    monkeypatch.setattr("legenday.ui.main_window.QDesktopServices.openUrl", lambda url: opened.append(url.toString()))
    win._on_update_check(updates.Update("9.9.9", "https://github.com/Araujo96/legenday/releases/tag/v9.9.9"))
    assert win.update_btn.isVisible() and "9.9.9" in win.update_btn.text()
    win.update_btn.click()
    assert opened == ["https://github.com/Araujo96/legenday/releases/tag/v9.9.9"]


def test_no_internet_or_up_to_date_shows_nothing(win):
    win._on_update_check(OSError("sem internet"))
    win._on_update_check(None)
    assert win.update_btn is None


def test_donate_dialog_has_a_valid_pix_code(qtbot):
    from legenday.ui.donate_dialog import DonateDialog
    dlg = DonateDialog(key="doe@exemplo.com", name="Lucas Araujo", city="Natal")
    qtbot.addWidget(dlg)
    assert dlg.code.startswith("000201") and "0115doe@exemplo.com" in dlg.code
    dlg.copy_code_btn.click()
    assert QApplication.clipboard().text() == dlg.code
    assert dlg.copy_code_btn.text() == "Copiado ✓"
    dlg.deleteLater()                                  # fechar logo depois de copiar não pode dar erro
    qtbot.wait(2200)


def test_donate_button_only_appears_with_a_pix_key(win):
    from legenday.branding import PIX_KEY
    assert win.controls.btn_donate.isVisibleTo(win.controls) == bool(PIX_KEY)


# ---------------------------------------------------------------- traduzir a frase
def test_translate_whole_line_button_and_key(qtbot, win, monkeypatch):
    asked = []
    monkeypatch.setattr(win.flow, "show", lambda text, pos: asked.append(text))
    win.subview.request_translation.disconnect()
    win.subview.request_translation.connect(win.flow.show)
    at(win, 1.5)
    btn = win.subview.btn
    assert btn.isVisible() and btn.text().strip().endswith("Traduzir a frase")
    btn.click()
    qtbot.keyClick(win, Qt.Key_F)
    assert asked == ["You broke my heart.", "You broke my heart."]


def test_subtitle_area_does_not_jump_between_lines(qtbot, win):
    """O botão some entre as falas mas guarda o lugar; a última linha da legenda fica sempre na mesma altura."""
    win.raw.pause = False
    sv = win.subview

    def layout_at(t):
        at(win, t)
        sv.layout().activate()
        qtbot.wait(20)
        bottom = max((w.geometry().bottom() for w in sv.words), default=None)
        return sv.btn.geometry(), bottom

    btn1, line1 = layout_at(1.5)                 # "You broke my heart."
    btn_gap, _ = layout_at(2.5)                  # intervalo: sem legenda, botão escondido
    assert not sv.btn.isVisible()
    btn2, line2 = layout_at(3.5)                 # "I know."
    assert btn1 == btn_gap == btn2               # o botão não sai do lugar
    assert line1 == line2                        # a linha da legenda também não


def test_two_line_subtitles_do_not_push_the_controls(qtbot, win):
    """Fala de 2 linhas e de 1 linha alternando: a barra de controles (e o play) fica parada."""
    sv, bar = win.subview, win.controls

    def show(text):
        sv.set_text(text)
        win.centralWidget().layout().activate()
        qtbot.wait(20)
        return bar.geometry().y(), sv.height()

    assert sv.minimumHeight() == sv.maximumHeight()           # altura fixa: o layout não pode encolher o painel
    one = show("I know.")
    two = show("Why don't you just admit that you're\nfreaked out by my robot hand?")
    none = show("")
    again = show("I know.")
    assert one == two == none == again
    # uma fala maior que tudo (3+ linhas) aumenta o painel uma vez, e ele não volta a encolher
    big = show("One\nTwo\nThree\nFour")
    assert big[1] >= one[1]
    assert show("") == big and show("I know.") == big


# ---------------------------------------------------------------- pasta do último vídeo
def test_choose_video_opens_in_the_last_folder_used(qtbot, win, tmp_path, monkeypatch):
    seen = []

    def fake_dialog(parent, title, start, filters):
        seen.append((title, start))
        return "", ""                                   # pessoa cancelou
    monkeypatch.setattr("legenday.ui.main_window.QFileDialog.getOpenFileName", fake_dialog)

    films = tmp_path / "Filmes" / "Serie"
    films.mkdir(parents=True)
    (films / "Ep1.mkv").write_bytes(b"")
    win.open_video(str(films / "Ep1.mkv"))              # abriu um vídeo desta pasta (pelo arrastar, por exemplo)
    win.open_video()
    win.open_subtitle()
    assert seen == [("Escolher vídeo", str(films)), ("Escolher legenda", str(films))]

    fresh = MainWindow(player=Player(FakeMpv()), sound=FakeSound())   # app aberto de novo: lembra a pasta
    qtbot.addWidget(fresh)
    fresh.open_video()
    assert seen[-1] == ("Escolher vídeo", str(films))


def test_without_history_the_video_dialog_never_starts_in_the_program_folder(win, monkeypatch):
    settings.put("last_video_dir", "C:/pasta/que/sumiu")
    start = win._video_dir()
    assert start != "" and "system32" not in start.lower() and os.path.isdir(start)


# ---------------------------------------------------------------- continuar de onde parou
def test_reopening_a_half_watched_video_offers_to_continue(qtbot, win, tmp_path, monkeypatch):
    from legenday.core import resume
    asked = []
    monkeypatch.setattr("legenday.ui.main_window.ResumeDialog.ask",
                        lambda parent, path, at, dur, on_start=False: asked.append((at, on_start)) or True)
    film = tmp_path / "Serie" / "Ep2.mkv"
    film.parent.mkdir()
    film.write_bytes(b"")
    win.open_video(str(film))
    win.raw.time_pos, win.raw.duration = 61.0, 100.0
    win.save_position()                                  # assistiu até 1:01 e parou
    win.open_video(str(tmp_path / "Filme.mkv"))          # foi para outro vídeo...
    win.open_video(str(film))                            # ...e voltou: pergunta
    assert asked == [(61.0, False)]
    win._tick()                                          # o vídeo carregou: pula para 3 s antes de onde parou
    assert win.raw.time_pos == 58.0
    assert resume.get(str(film))[0] == 61.0              # e o ponto salvo não foi apagado pelo pulo


def test_app_start_offers_the_last_half_watched_video(qtbot, tmp_path, monkeypatch):
    from legenday.core import resume
    settings.put("tour_seen", True)
    film = tmp_path / "Filme.mkv"
    film.write_bytes(b"")
    resume.save(str(film), 2533.0, 6300.0)
    asked = []
    monkeypatch.setattr("legenday.ui.main_window.ResumeDialog.ask",
                        lambda parent, path, at, dur, on_start=False: asked.append((path, at, on_start)) or True)
    raw = FakeMpv()
    w = MainWindow(player=Player(raw), sound=FakeSound())
    qtbot.addWidget(w)
    w.show()
    qtbot.waitUntil(lambda: bool(asked), timeout=3000)
    assert asked == [(str(film.resolve()), 2533.0, True)]
    assert raw.played == [str(film.resolve())]


def test_closing_the_app_remembers_where_it_stopped(qtbot, win, tmp_path):
    from legenday.core import resume
    win.raw.time_pos, win.raw.duration = 45.0, 100.0
    win.close()
    assert resume.get(str(tmp_path / "Filme.mkv"))[0] == 45.0


# ---------------------------------------------------------------- informações para suporte
def test_support_info_includes_the_recent_log(win):
    assert "Últimos registros (legenday.log):\n(nenhum)" in win.diagnostics()
    from legenday.core import log
    log.setup()
    try:
        log.problem("tarefa de teste", ConnectionError("sem internet"))
        assert "tarefa de teste: ConnectionError('sem internet')" in win.diagnostics()
    finally:
        for handler in list(log.log.handlers):
            log.log.removeHandler(handler)
            handler.close()
        log.log.addHandler(log.logging.NullHandler())


# ---------------------------------------------------------------- tela cheia
def test_fullscreen_button_and_escape(qtbot, win):
    btn = win.controls.btn_fullscreen
    assert btn.isVisible() and "Tela cheia" in btn.toolTip()
    btn.click()
    qtbot.waitUntil(win.isFullScreen, timeout=2000)
    assert "Sair da tela cheia" in btn.toolTip()
    qtbot.keyClick(win, Qt.Key_Escape)
    qtbot.waitUntil(lambda: not win.isFullScreen(), timeout=2000)
    assert "Tela cheia" in btn.toolTip()


def test_click_on_video_pauses_and_double_click_goes_fullscreen(qtbot, win, monkeypatch):
    """O mpv deixa a janela dele desativada dentro do app: o clique chega na área de vídeo do Qt."""
    toggled = []
    monkeypatch.setattr(win, "toggle_fullscreen", lambda: toggled.append(1))   # a tela cheia já tem teste próprio
    win.player.paused = False
    qtbot.mouseClick(win.video, Qt.LeftButton)
    assert win.player.paused
    qtbot.mouseClick(win.video, Qt.LeftButton)
    assert not win.player.paused
    qtbot.mouseClick(win.video, Qt.RightButton)           # botão direito não mexe no vídeo
    assert not win.player.paused
    # o Windows manda: aperta, solta, "duplo" (no lugar do 2º aperto), solta
    from PySide6.QtGui import QMouseEvent
    qtbot.mouseClick(win.video, Qt.LeftButton)            # 1º clique pausa...
    assert win.player.paused
    pos = QPointF(20, 20)
    QApplication.sendEvent(win.video, QMouseEvent(QEvent.MouseButtonDblClick, pos, win.video.mapToGlobal(pos),
                                                  Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    assert toggled == [1] and not win.player.paused       # ...o duplo desfaz e põe em tela cheia


def test_click_without_video_does_not_pause(qtbot, win):
    win.video_path = None
    win.player.paused = True
    win._on_video_click(False)
    assert win.player.paused


# ---------------------------------------------------------------- legendas dentro do vídeo
def test_untagged_embedded_subtitles_pick_the_english_one(qtbot, win, tmp_path):
    import subprocess

    from legenday.core import embedded
    ff = embedded.find_ffmpeg()
    if not ff:
        pytest.skip("ffmpeg indisponível")
    def srt(lines, name):
        path = tmp_path / name
        path.write_text("".join(f"{i}\n00:00:{i:02d},000 --> 00:00:{i:02d},900\n{t}\n\n"
                                for i, t in enumerate(lines, 1)), encoding="utf-8")
        return path
    pt = srt(["O que você está fazendo aqui?", "Eu não sei do que você está falando.",
              "Temos que sair deste lugar.", "Não é sua culpa, tá bom?"] * 4, "pt.srt")
    en = srt(["What are you doing here?", "I don't know what you mean.", "We have to get out of this place.",
              "It's not your fault, okay?"] * 4, "en.srt")
    mkv = tmp_path / "baixado" / "Filme.mkv"                    # sem .srt ao lado; faixas sem idioma
    mkv.parent.mkdir()
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=20", "-i", str(pt),
                    "-i", str(en), "-map", "0:v", "-map", "1:s", "-map", "2:s", "-c:v", "mpeg4", "-c:s", "srt",
                    str(mkv)], check=True)
    win.open_video(str(mkv))
    qtbot.waitUntil(lambda: win._embedded_stream is not None, timeout=20000)
    assert win._embedded_stream == 2                            # a 2ª legenda (inglês), não a 1ª (português)
    actions = {a.text(): a for a in win.sub_menu.actions()}
    assert "Legendas dentro do vídeo:" in actions
    assert not actions["Legenda 1 · Idioma não informado (não parece inglês)"].isChecked()
    assert actions["Legenda 2 · Idioma não informado (parece inglês)"].isChecked()
    assert not any("subrip" in x for x in actions)


# ---------------------------------------------------------------- abrir arquivos
def test_dropping_a_video_opens_it_with_its_subtitle(tmp_path, win):
    other = tmp_path / "outro"
    other.mkdir()
    (other / "Serie.mp4").write_bytes(b"")
    (other / "Serie.srt").write_text(SRT.replace("I know.", "Dropped in."), encoding="utf-8")
    drop(win, other / "Serie.mp4")
    assert win.raw.played[-1] == str(other / "Serie.mp4")
    at(win, 3.5)
    assert [w.text() for w in win.subview.words] == ["Dropped", "in"]


def test_dropping_a_subtitle_replaces_the_current_one(tmp_path, win):
    sub = tmp_path / "nova.srt"
    sub.write_text(SRT.replace("I know.", "New line."), encoding="utf-8")
    played = list(win.raw.played)
    drop(win, sub)
    assert win.raw.played == played                  # o vídeo não foi reaberto
    at(win, 3.5)
    assert [w.text() for w in win.subview.words] == ["New", "line"]


# ---------------------------------------------------------------- legenda e pop-up
def test_sidecar_subtitle_is_loaded_and_shown(win):
    win.raw.pause = False
    at(win, 1.5)
    assert [w.text() for w in win.subview.words] == ["You", "broke", "my", "heart"]
    at(win, 3.5)
    assert [w.text() for w in win.subview.words] == ["I", "know"]


def test_click_word_pauses_and_shows_translation_with_context(qtbot, win, monkeypatch):
    fake_lookup(monkeypatch)
    win.raw.pause = False
    at(win, 1.5)
    click_word(qtbot, win, "broke")
    assert win.popup.isVisible() and win.raw.pause is True
    qtbot.waitUntil(lambda: "na frase" in win.popup.extra.text(), timeout=3000)
    assert "partiu" in win.popup.pt.text() and "falido" in win.popup.pt.text()
    assert "Você partiu meu coração." in win.popup.extra.text()


def test_space_closes_popup_and_resumes(qtbot, win, monkeypatch):
    fake_lookup(monkeypatch)
    win.raw.pause = False
    at(win, 1.5)
    click_word(qtbot, win, "broke")
    win.toggle_pause()
    assert not win.popup.isVisible() and win.raw.pause is False


def test_pronunciation_button_plays_audio(qtbot, win, monkeypatch):
    fake_lookup(monkeypatch)
    at(win, 1.5)
    click_word(qtbot, win, "broke")
    qtbot.waitUntil(lambda: win.popup.sound_btn.isVisible(), timeout=3000)
    from legenday.services import pronunciation
    asked = []
    monkeypatch.setattr(pronunciation, "local_file", lambda url: asked.append(url) or Path("C:/audio/broke-us.mp3"))
    qtbot.mouseClick(win.popup.sound_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: bool(win.sound.played), timeout=3000)
    assert asked == ["https://x/broke-us.mp3"]
    assert win.sound.played == [str(Path("C:/audio/broke-us.mp3"))]       # toca o arquivo baixado
    assert win.popup.sound_btn.text() == "🔊"


def test_pronunciation_button_shows_when_audio_cannot_be_downloaded(qtbot, win, monkeypatch):
    fake_lookup(monkeypatch)
    at(win, 1.5)
    click_word(qtbot, win, "broke")
    qtbot.waitUntil(lambda: win.popup.sound_btn.isVisible(), timeout=3000)
    from legenday.services import pronunciation

    def busy(url):
        raise OSError("HTTP Error 429: Too Many Requests")
    monkeypatch.setattr(pronunciation, "local_file", busy)
    qtbot.mouseClick(win.popup.sound_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: win.popup.sound_btn.text() == "🔇", timeout=3000)
    assert win.sound.played == [] and "tentar de novo" in win.popup.sound_btn.toolTip()


def test_save_word_highlights_it_and_records_the_line_start(qtbot, win, monkeypatch):
    fake_lookup(monkeypatch)
    at(win, 1.7)
    click_word(qtbot, win, "broke")
    qtbot.waitUntil(lambda: win.popup.save_btn.isEnabled(), timeout=3000)
    qtbot.mouseClick(win.popup.save_btn, Qt.LeftButton)
    word = win.vocab.all()[0]
    assert (word.term, word.translation, word.position) == ("broke", "partiu", 1.0)
    assert word.sentence == "You broke my heart." and word.video == "Filme.mkv"
    assert next(w for w in win.subview.words if w.text() == "broke").property("saved")
    badge = win.controls.btn_vocab.badge
    assert badge.text() == "1" and not badge.isHidden()          # o selo amarelo do botão Palavras


def test_mute_button_silences_and_restores_the_volume(qtbot, win):
    c = win.controls
    c.vol.setValue(60)
    qtbot.mouseClick(c.btn_mute, Qt.LeftButton)
    assert c.vol.value() == 0 and win.raw.volume == 0
    qtbot.mouseClick(c.btn_mute, Qt.LeftButton)
    assert c.vol.value() == 60 and win.raw.volume == 60


# ---------------------------------------------------------------- atalhos
def test_arrow_keys_move_the_vocab_table_not_the_video(qtbot, win):
    win.vocab.add("a", "x")
    win.vocab.add("b", "y")
    at(win, 10.0)
    dlg = VocabDialog(win.vocab, win)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.waitExposed(dlg)
    dlg.activateWindow()
    dlg.table.setFocus()
    dlg.table.setCurrentCell(0, 0)
    qtbot.keyClick(dlg.table, Qt.Key_Down)
    assert dlg.table.currentRow() == 1 and win.raw.time_pos == 10.0


# ---------------------------------------------------------------- modo repetir frase
def test_shadowing_pauses_once_at_the_end_of_each_line(win):
    win.set_shadowing(True)
    assert win.controls.btn_shadow.isChecked()
    win.raw.pause = False
    at(win, 1.5)
    at(win, 1.95)                                    # fim da fala 1 (termina em 2,0 s)
    assert win.raw.pause is True
    win.raw.pause = False
    at(win, 2.5)
    assert win.raw.pause is False                    # a mesma fala não pausa de novo
    at(win, 3.5)
    at(win, 3.95)
    assert win.raw.pause is True                     # a próxima fala pausa


def test_repeat_line_plays_the_line_again_and_pauses_again(win):
    win.set_shadowing(True)
    win.raw.pause = False
    at(win, 1.5)
    at(win, 1.95)
    win.repeat_line()
    assert win.raw.time_pos == 1.0 and win.raw.pause is False
    at(win, 1.5)
    at(win, 1.95)
    assert win.raw.pause is True


def test_shadowing_off_never_pauses(win):
    win.raw.pause = False
    for t in (1.5, 1.95, 2.5, 3.95):
        at(win, t)
    assert win.raw.pause is False


# ---------------------------------------------------------------- legenda dupla
def test_dual_subtitles_translate_the_line(qtbot, win, monkeypatch):
    monkeypatch.setattr(win.dual, "translate", lambda text: {"You broke my heart.": "Você partiu meu coração."}
                        .get(text, "?"))
    at(win, 1.5)
    win.set_dual(True)
    qtbot.waitUntil(lambda: win.subview.trans.text() == "Você partiu meu coração.", timeout=3000)
    assert win.subview.trans.isVisible()
    win.set_dual(False)
    assert not win.subview.trans.isVisible()


def test_dual_subtitles_prefer_a_portuguese_file(tmp_path, win, monkeypatch):
    monkeypatch.setattr(win.dual, "translate", lambda text: pytest.fail("não deveria traduzir"))
    pt = tmp_path / "Filme.pt-BR.srt"
    pt.write_text(SRT_PT, encoding="utf-8")
    win.open_pt_subtitle(str(pt))
    assert win.dual.enabled
    at(win, 3.5)
    assert win.subview.trans.text() == "Eu sei."


# ---------------------------------------------------------------- revisão
def test_review_cards_grade_and_reschedule(qtbot, win):
    win.vocab.add("broke", "partiu", sentence="You broke my heart.", video="Filme.mkv", position=1.0)
    win.vocab.add("tender", "gentil", sentence="Be tender to her.", video="Outro.mkv", position=5.0)
    dlg = ReviewDialog(win.vocab, win, scene=win)
    qtbot.addWidget(dlg)
    assert "broke" in dlg.term.text() and "<b>broke</b>" in dlg.sentence.text()
    assert not dlg.bad_btn.isVisibleTo(dlg) and dlg.answer.text() == ""
    dlg.reveal()
    assert "partiu" in dlg.answer.text()
    dlg.grade(True)
    assert "tender" in dlg.term.text()
    dlg.reveal()
    dlg.grade(False)
    assert "Revisão concluída" in dlg.term.text() and "1 de 2" in dlg.sentence.text()
    due = {w.term for w in win.vocab.due()}
    assert due == set()                              # "tender" volta daqui a 10 min; "broke", amanhã


def test_review_plays_the_scene_of_the_open_film(qtbot, win):
    win.vocab.add("broke", "partiu", sentence="You broke my heart.", video="Filme.mkv", position=1.0)
    win.vocab.add("other", "outro", video="Outro.mkv", position=5.0)
    dlg = ReviewDialog(win.vocab, win, scene=win)
    qtbot.addWidget(dlg)
    dlg.show()
    assert dlg.scene_btn.isVisible()
    qtbot.mouseClick(dlg.scene_btn, Qt.LeftButton)
    assert win.raw.time_pos == pytest.approx(0.8) and win.raw.pause is False
    at(win, 2.3)                                     # fim da fala (2,0 s) + folga
    assert win.raw.pause is True
    dlg.reveal()
    dlg.grade(True)
    assert not dlg.scene_btn.isVisible()             # "other" é de outro filme


def test_review_with_nothing_due(qtbot, win):
    dlg = ReviewDialog(win.vocab, win)
    qtbot.addWidget(dlg)
    assert "Tudo em dia" in dlg.term.text()
