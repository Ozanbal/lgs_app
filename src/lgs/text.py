"""Türkçe metin yardımcıları."""

from __future__ import annotations

import re

_TR_UPPER_TO_LOWER = str.maketrans({"I": "ı", "İ": "i"})


def tr_lower(text: str) -> str:
    """Türkçe kurallarına uygun küçük harfe çevirme (I -> ı, İ -> i)."""
    return text.translate(_TR_UPPER_TO_LOWER).lower()


def squash(text: str) -> str:
    """Satır içi boşlukları teke indirir, satır sonlarını korur."""
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
