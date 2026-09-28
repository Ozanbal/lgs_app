"""PDF kitapçıklarından sayfa sayfa, sütun sırasına uygun metin çıkarma."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

_PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")


@dataclass
class PageText:
    page: int  # 1'den başlar
    text: str


def extract_pages(pdf_path: str | Path, columns: int = 2) -> list[PageText]:
    """Her sayfayı `columns` eşit sütuna bölüp soldan sağa okur.

    LGS kitapçıkları iki sütunludur; sütun kırpılmadan okunursa iki sütunun
    satırları birbirine karışır.
    """
    pages: list[PageText] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            parts = []
            width = page.width / columns
            for c in range(columns):
                region = page.crop((c * width, 0, (c + 1) * width, page.height))
                text = region.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                parts.append(_drop_page_number(text))
            pages.append(PageText(i, "\n".join(parts)))
    return pages


def _drop_page_number(text: str) -> str:
    lines = text.rstrip().splitlines()
    while lines and _PAGE_NUMBER.match(lines[-1]):
        lines.pop()
    return "\n".join(lines)
