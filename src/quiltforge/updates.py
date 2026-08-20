from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable
from urllib.request import Request, urlopen


RELEASE_API = "https://api.github.com/repos/Its-ze/quiltforge/releases/latest"


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    page_url: str
    installer_url: str


def version_tuple(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value.lstrip("vV"))
    return tuple(int(number) for number in numbers[:3]) or (0,)


def parse_release(payload: dict) -> ReleaseInfo:
    tag = str(payload.get("tag_name", "")).lstrip("vV")
    page_url = str(payload.get("html_url", ""))
    installer_url = ""
    for asset in payload.get("assets", []):
        name = str(asset.get("name", ""))
        if name.startswith("QuiltForge-Setup-") and name.lower().endswith(".exe"):
            installer_url = str(asset.get("browser_download_url", ""))
            break
    if not tag or not page_url:
        raise ValueError("GitHub returned an incomplete release record")
    return ReleaseInfo(tag, page_url, installer_url)


def fetch_latest_release(
    api_url: str = RELEASE_API,
    opener: Callable = urlopen,
) -> ReleaseInfo:
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "QuiltForge-Update-Checker",
        },
    )
    with opener(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_release(payload)


def update_available(current: str, latest: str) -> bool:
    return version_tuple(latest) > version_tuple(current)
