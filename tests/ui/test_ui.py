"""Testes da interface (pytest-qt), com um player falso no lugar do mpv."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl  # noqa: E402
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
    qtbot.mouseClick(win.popup.sound_btn, Qt.LeftButton)
    assert win.sound.played == ["https://x/broke-us.mp3"]


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
