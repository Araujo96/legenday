from legenday.core import resume


def video(tmp_path, name="Filme.mkv"):
    p = tmp_path / name
    p.write_bytes(b"")
    return str(p)


def test_saves_and_returns_where_it_stopped(tmp_path):
    v = video(tmp_path)
    resume.save(v, 2533.4, 6300)
    assert resume.get(v) == (2533.4, 6300)
    assert resume.last() == (str((tmp_path / "Filme.mkv").resolve()), 2533.4, 6300)


def test_does_not_remember_the_beginning_or_the_credits(tmp_path):
    v = video(tmp_path)
    resume.save(v, 12, 6300)                     # mal começou
    assert resume.get(v) is None
    resume.save(v, 3000, 6300)
    resume.save(v, 6250, 6300)                   # nos créditos: já assistiu, esquece
    assert resume.get(v) is None


def test_short_videos_are_remembered_too(tmp_path):
    v = video(tmp_path, "Curto.mkv")
    resume.save(v, 61, 100)                      # 2 min antes do fim seria o vídeo todo: vale a margem de 5%
    assert resume.get(v) == (61, 100)
    resume.save(v, 96, 100)
    assert resume.get(v) is None


def test_last_is_the_most_recent_that_still_exists(tmp_path):
    a, b = video(tmp_path, "A.mkv"), video(tmp_path, "B.mkv")
    resume.save(a, 100, 1000)
    resume.save(b, 200, 1000)
    assert resume.last()[0].endswith("B.mkv")
    (tmp_path / "B.mkv").unlink()                # apagou o arquivo: oferece o anterior
    assert resume.last()[0].endswith("A.mkv")


def test_two_saves_in_the_same_clock_tick_keep_their_order(tmp_path, monkeypatch):
    monkeypatch.setattr(resume.time, "time", lambda: 5000.0)          # relógio parado (como no Windows)
    a, b = video(tmp_path, "A.mkv"), video(tmp_path, "B.mkv")
    resume.save(a, 100, 1000)
    resume.save(b, 200, 1000)
    assert resume.last()[0].endswith("B.mkv")


def test_keeps_only_the_most_recent_videos(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, "MAX_ITEMS", 3)
    paths = [video(tmp_path, f"E{i}.mkv") for i in range(5)]
    for i, p in enumerate(paths):
        monkeypatch.setattr(resume.time, "time", lambda i=i: 1000.0 + i)
        resume.save(p, 100, 1000)
    assert [resume.get(p) is not None for p in paths] == [False, False, True, True, True]


def test_clock():
    assert resume.clock(2533) == "42:13"
    assert resume.clock(3723) == "1:02:03"
