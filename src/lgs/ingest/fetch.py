"""MEB/ODSGM duyuru sayfalarındaki PDF bağlantılarını toplayıp indirir.

Not: Bu işlem meb.gov.tr alan adlarına ağ erişimi gerektirir.
"""

from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin

USER_AGENT = "Mozilla/5.0 (lgs-app soru bankasi)"
_YEAR = re.compile(r"20(1[89]|2\d)")


@dataclass
class PdfLink:
    url: str
    label: str

    @property
    def year(self) -> int | None:
        m = _YEAR.search(unquote(self.url) + " " + self.label)
        return int(m.group(0)) if m else None


class _LinkParser(HTMLParser):
    def __init__(self, base: str):
        super().__init__()
        self.base = base
        self.links: list[PdfLink] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            if ".pdf" in self._href.lower():
                self.links.append(PdfLink(urljoin(self.base, self._href), " ".join(self._text).strip()))
            self._href = None


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def find_pdf_links(page_url: str) -> list[PdfLink]:
    html = _get(page_url).decode("utf-8", errors="replace")
    parser = _LinkParser(page_url)
    parser.feed(html)
    seen, unique = set(), []
    for link in parser.links:
        if link.url not in seen:
            seen.add(link.url)
            unique.append(link)
    return unique


def download(link: PdfLink, raw_dir: str | Path) -> Path:
    folder = Path(raw_dir) / (str(link.year) if link.year else "_yil_belirsiz")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / Path(unquote(link.url)).name
    if not target.exists():
        target.write_bytes(_get(link.url))
    return target
