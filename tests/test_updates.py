import json

from quiltforge.updates import fetch_latest_release, parse_release, update_available, version_tuple


PAYLOAD = {
    "tag_name": "v1.2.3",
    "html_url": "https://github.com/Its-ze/quiltforge/releases/tag/v1.2.3",
    "assets": [
        {
            "name": "QuiltForge-Setup-1.2.3.exe",
            "browser_download_url": "https://example.test/QuiltForge-Setup-1.2.3.exe",
        }
    ],
}


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(PAYLOAD).encode("utf-8")


def test_release_parser_and_comparison() -> None:
    release = parse_release(PAYLOAD)
    assert release.version == "1.2.3"
    assert release.installer_url.endswith(".exe")
    assert version_tuple("v1.10.0") == (1, 10, 0)
    assert update_available("1.1.0", "v1.2.0")
    assert not update_available("1.2.0", "v1.2.0")


def test_fetch_latest_release_uses_supplied_opener() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    release = fetch_latest_release(opener=opener)
    assert release.version == "1.2.3"
    assert captured["timeout"] == 8
    assert captured["url"].endswith("/releases/latest")
