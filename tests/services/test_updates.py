from legenday.services import updates
from legenday.services.updates import check, parse_version


def release(tag, **extra):
    return lambda url: {"tag_name": tag, "html_url": f"https://github.com/x/releases/tag/{tag}", **extra}


def test_parse_version_compares_number_by_number():
    assert parse_version("v0.10.2") == (0, 10, 2)
    assert parse_version("v0.10.0") > parse_version("0.9.9")
    assert parse_version("") == ()


def test_newer_release_is_offered():
    up = check("0.5.0", fetch=release("v0.6.0"))
    assert up.version == "0.6.0"
    assert up.url.endswith("/v0.6.0")


def test_same_or_older_release_is_not_offered():
    assert check("0.5.0", fetch=release("v0.5.0")) is None
    assert check("0.5.0", fetch=release("v0.4.9")) is None


def test_drafts_prereleases_and_garbage_are_ignored():
    assert check("0.5.0", fetch=release("v9.0.0", prerelease=True)) is None
    assert check("0.5.0", fetch=release("nightly")) is None


def test_asks_the_github_api_of_this_repo():
    seen = []
    check("0.5.0", fetch=lambda url: seen.append(url) or {"tag_name": "v0.5.0"})
    assert seen == ["https://api.github.com/repos/Araujo96/legenday/releases/latest"]
    assert updates.DOWNLOAD_URL == "https://github.com/Araujo96/legenday/releases/latest"
