"""Preferências e sincronia guardadas em JSON."""
from legenday.core import settings
from legenday.core.paths import data_dir


def test_settings_roundtrip_and_defaults():
    assert settings.get("help_seen") is None and settings.get("x", 5) == 5
    settings.put("help_seen", True)
    settings.put("outra", "valor")
    assert settings.get("help_seen") is True and settings.get("outra") == "valor"


def test_settings_survive_corrupted_file():
    (data_dir() / "settings.json").write_text("{quebrado", encoding="utf-8")
    assert settings.get("help_seen") is None
    settings.put("help_seen", True)                      # reescreve do zero
    assert settings.get("help_seen") is True


def test_subtitle_offsets_are_remembered_per_file():
    assert settings.load_offset("C:/filmes/a.srt") == 0.0
    settings.save_offset("C:/filmes/a.srt", 1.5)
    settings.save_offset("C:/filmes/b.srt", -0.3)
    assert settings.load_offset("C:/filmes/a.srt") == 1.5 and settings.load_offset("C:/filmes/b.srt") == -0.3
    settings.save_offset("C:/filmes/a.srt", 0)           # zerar apaga a entrada
    assert "C:/filmes/a.srt" not in (data_dir() / "offsets.json").read_text(encoding="utf-8")


def test_offsets_survive_garbage():
    (data_dir() / "offsets.json").write_text('{"x.srt": "abc"}', encoding="utf-8")
    assert settings.load_offset("x.srt") == 0.0
    (data_dir() / "offsets.json").write_text("[1, 2]", encoding="utf-8")
    assert settings.load_offset("x.srt") == 0.0
