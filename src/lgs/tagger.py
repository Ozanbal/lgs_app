"""Soruları konu (ünite) ve soru kalıbına göre kural tabanlı etiketler.

Etiketler "otomatik" olarak işaretlenir; elle düzeltilen sorular
(etiket_kaynagi == "elle") yeniden etiketlemede korunur.
"""

from __future__ import annotations

import re
from functools import lru_cache

from .knowledge import pattern_index, patterns, units
from .models import Question
from .text import tr_lower

# Bir soruya en fazla kaç ders-özel kalıp ve ünite atanacağı.
MAX_SUBJECT_PATTERNS = 2
MAX_UNITS = 2


@lru_cache(maxsize=None)
def _keyword_regex(keyword: str) -> re.Pattern:
    """`/.../` biçimindeki anahtar kelime ham regex'tir; diğerleri kelime
    başında önek olarak aranır (Türkçe ekler için: "üçgen" -> "üçgenin")."""
    if len(keyword) > 2 and keyword.startswith("/") and keyword.endswith("/"):
        return re.compile(keyword[1:-1])
    return re.compile(r"(?<!\w)" + re.escape(tr_lower(keyword)))


@lru_cache(maxsize=None)
def _cue_regex(cue: str) -> re.Pattern:
    return re.compile(cue)


def question_text(q: Question) -> str:
    text = q.kok + "\n" + "\n".join(q.secenekler.values())
    # İngilizce metinde "I'm" gibi ifadeler Türkçe kuralla "ı'm" olmasın.
    return text.lower() if q.ders == "ingilizce" else tr_lower(text)


def match_patterns(q: Question) -> list[str]:
    text = question_text(q)
    stem_len = len(q.kok)
    scored: list[tuple[int, int, str, bool]] = []
    for order, p in enumerate(patterns(q.ders)):
        if stem_len < (p.get("min_uzunluk") or 0):
            continue
        score = sum(1 for cue in p["ipuclari"] if _cue_regex(cue).search(text))
        if score:
            scored.append((score, order, p["id"], p["ders"] == "genel"))
    subject_hits = sorted((s for s in scored if not s[3]), key=lambda s: (-s[0], s[1]))
    general_hits = [s for s in scored if s[3]]
    chosen = subject_hits[:MAX_SUBJECT_PATTERNS] + general_hits
    return [s[2] for s in chosen]


def match_units(q: Question, pattern_ids: list[str]) -> list[str]:
    text = question_text(q)
    scores: dict[str, int] = {}
    for u in units(q.ders):
        score = sum(len(_keyword_regex(k).findall(text)) for k in u["anahtar_kelimeler"])
        if score:
            scores[u["id"]] = score
    # Konuya bağlı kalıplar (örn. TUR-FIILIMSI -> tur.fiilimsiler) güçlü sinyaldir.
    index = pattern_index()
    for pid in pattern_ids:
        for uid in index[pid].get("uniteler") or []:
            scores[uid] = scores.get(uid, 0) + 3
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    top = ranked[0][1]
    return [uid for uid, s in ranked[:MAX_UNITS] if s >= max(1, top / 2)]


def tag_question(q: Question, force: bool = False) -> bool:
    """Soruyu etiketler; elle etiketlenmiş soruya `force` olmadan dokunmaz."""
    if q.etiket_kaynagi == "elle" and not force:
        return False
    q.kaliplar = match_patterns(q)
    q.uniteler = match_units(q, q.kaliplar)
    q.etiket_kaynagi = "otomatik"
    return True
