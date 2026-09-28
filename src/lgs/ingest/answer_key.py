"""Cevap anahtarı dosyalarını okur ve soru bankasına uygular.

Dosya biçimi (data/cevap_anahtarlari/<yil>.yaml):

    yil: 2025
    A:
      turkce: "ABCD ABCD ABCD ABCD ABCD"   # boşluklar isteğe bağlı
      matematik: "..."
    B:
      turkce: "..."

"X" iptal edilen soruyu gösterir.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..knowledge import exam_spec, subjects
from ..models import Question

CANCELLED = "X"


def parse_answers(raw: str, count: int, label: str) -> list[str]:
    answers = [c for c in str(raw).upper() if not c.isspace() and c not in ",-"]
    if len(answers) != count:
        raise ValueError(f"{label}: {count} cevap beklenirken {len(answers)} bulundu")
    bad = sorted({a for a in answers if a not in "ABCD" + CANCELLED})
    if bad:
        raise ValueError(f"{label}: geçersiz cevap harfleri {bad}")
    return answers


def load_answer_key(path: str | Path) -> tuple[int, dict[str, dict[str, list[str]]]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    year = int(data["yil"])
    key: dict[str, dict[str, list[str]]] = {}
    for booklet in exam_spec()["format"]["kitapciklar"]:
        for subject, raw in (data.get(booklet) or {}).items():
            if not raw:
                continue
            if subject not in subjects():
                raise ValueError(f"Bilinmeyen ders: {subject}")
            count = subjects()[subject].question_count
            key.setdefault(booklet, {})[subject] = parse_answers(
                raw, count, f"{year} {booklet} {subject}"
            )
    return year, key


def apply_answer_key(questions: list[Question], key: dict[str, dict[str, list[str]]]) -> list[str]:
    """Cevapları sorulara işler; eşleşmeyen durumlar için uyarı döndürür."""
    warnings = []
    for booklet, by_subject in key.items():
        for q in questions:
            answers = by_subject.get(q.ders)
            if answers is None:
                continue
            no = q.kitapcik_no.get(booklet)
            if no is None:
                warnings.append(f"{q.id}: {booklet} kitapçığındaki numarası bilinmiyor")
                continue
            answer = answers[no - 1]
            if answer == CANCELLED:
                q.iptal = True
                q.cevaplar.pop(booklet, None)
            else:
                q.cevaplar[booklet] = answer
    return warnings


def template(year: int) -> str:
    lines = [
        f"yil: {year}",
        "# Her ders için cevapları soru sırasıyla yazın (boşluk serbest). İptal edilen soru: X",
    ]
    for booklet in exam_spec()["format"]["kitapciklar"]:
        lines.append(f"{booklet}:")
        for s in sorted(subjects().values(), key=lambda s: (s.session != "sozel", s.order)):
            lines.append(f'  {s.id}: ""   # {s.question_count} soru')
    return "\n".join(lines) + "\n"
