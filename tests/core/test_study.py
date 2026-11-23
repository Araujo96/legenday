"""Modo repetir frase e agenda da revisão."""
from datetime import datetime, timedelta

from legenday.core import study
from legenday.core.subtitles import Cue, SubtitleTrack

NOW = datetime(2026, 11, 16, 20, 0, 0)


def _cue_track(*cues):
    return SubtitleTrack([Cue(s, e, t) for s, e, t in cues])


def test_shadowing_pauses_near_the_end_of_each_line_once():
    track = _cue_track((1, 2, "a"), (3, 4, "b"))
    s = study.Shadowing()
    s.enabled = True
    assert [s.should_pause(track, t) for t in (1.2, 1.5, 1.95, 2.0, 2.5, 3.2, 3.94, 4.1)] == \
        [False, False, True, False, False, False, True, False]


def test_shadowing_consecutive_lines_and_late_ticks():
    track = _cue_track((1, 2, "a"), (2, 3, "b"))
    s = study.Shadowing()
    s.enabled = True
    s.should_pause(track, 1.5)
    assert s.should_pause(track, 2.03)          # o relógio passou do fim e já está na fala seguinte
    assert not s.should_pause(track, 2.5)
    assert s.should_pause(track, 2.95)


def test_shadowing_respects_subtitle_offset():
    track = _cue_track((1, 2, "a"))
    track.offset = 0.5
    s = study.Shadowing()
    s.enabled = True
    s.should_pause(track, 1.8)
    assert not s.should_pause(track, 2.0) and s.should_pause(track, 2.45)


def test_shadowing_disabled_or_without_subtitle():
    s = study.Shadowing()
    assert not s.should_pause(_cue_track((1, 2, "a")), 1.95)
    s.enabled = True
    assert not s.should_pause(None, 1.95)


def test_schedule_grows_on_success_and_restarts_on_error():
    assert study.schedule(0, True, NOW) == (1, NOW + timedelta(days=1))
    assert study.schedule(1, True, NOW) == (2, NOW + timedelta(days=3))
    assert study.schedule(5, True, NOW) == (5, NOW + timedelta(days=35))       # teto
    assert study.schedule(4, False, NOW) == (0, NOW + timedelta(minutes=10))
