"""Soru bankası deposu: her sınav yılı için bir JSONL dosyası (data/bank/<yil>.jsonl)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from .knowledge import exam_years, subjects
from .models import Question
from .text import one_line, tr_lower

# Farklı kitapçıklardaki aynı sorunun eşleşmesi için gereken en düşük benzerlik.
BOOKLET_MATCH_THRESHOLD = 0.8


def _sort_key(q: Question) -> tuple:
    s = subjects()[q.ders]
    return (s.session != "sozel", s.order, q.no)


class QuestionBank:
    def __init__(self, root: str | Path = "data"):
        self.root = Path(root)
        self.dir = self.root / "bank"

    def path(self, year: int) -> Path:
        return self.dir / f"{year}.jsonl"

    def load(self, year: int) -> list[Question]:
        path = self.path(year)
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as f:
            return [Question.from_dict(json.loads(line)) for line in f if line.strip()]

    def save(self, year: int, questions: list[Question]) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.path(year)
        with path.open("w", encoding="utf-8") as f:
            for q in sorted(questions, key=_sort_key):
                f.write(json.dumps(q.to_dict(), ensure_ascii=False) + "\n")
        return path

    def years(self) -> list[int]:
        return sorted(int(p.stem) for p in self.dir.glob("*.jsonl")) if self.dir.exists() else []

    def all(self) -> list[Question]:
        return [q for y in self.years() for q in self.load(y)]

    def merge(self, year: int, incoming: list[Question]) -> tuple[int, int]:
        """A kitapçığı sorularını ekler/günceller; elle girilmiş alanları korur.

        Dönüş: (yeni, güncellenen)
        """
        existing = {q.id: q for q in self.load(year)}
        added = updated = 0
        for q in incoming:
            old = existing.get(q.id)
            if old is None:
                existing[q.id] = q
                added += 1
                continue
            old.kok, old.secenekler, old.gorsel, old.kaynak = q.kok, q.secenekler, q.gorsel, q.kaynak
            old.kitapcik_no.update(q.kitapcik_no)
            updated += 1
        self.save(year, list(existing.values()))
        return added, updated

    def merge_other_booklet(self, year: int, incoming: list[Question], booklet: str) -> list[str]:
        """B (veya başka) kitapçık sorularını metin benzerliğiyle A kitapçığına eşler
        ve `kitapcik_no[booklet]` alanını doldurur."""
        questions = self.load(year)
        if not questions:
            return [f"{year}: önce A kitapçığı işlenmeli"]
        warnings = []
        for q in incoming:
            candidates = [a for a in questions if a.ders == q.ders]
            best, score = None, 0.0
            for a in candidates:
                r = SequenceMatcher(None, _fingerprint(a), _fingerprint(q)).ratio()
                if r > score:
                    best, score = a, r
            if best is None or score < BOOKLET_MATCH_THRESHOLD:
                warnings.append(f"{booklet} {q.ders} {q.no}: A kitapçığında eşi bulunamadı ({score:.2f})")
                continue
            best.kitapcik_no[booklet] = q.no
        self.save(year, questions)
        return warnings

    # ------------------------------------------------------------ raporlar
    def coverage(self) -> list[dict]:
        """Yıl x ders bazında soru, cevap ve etiket doluluk durumu."""
        rows = []
        for year in exam_years():
            by_subject = defaultdict(list)
            for q in self.load(year):
                by_subject[q.ders].append(q)
            for s in sorted(subjects().values(), key=lambda s: (s.session != "sozel", s.order)):
                qs = by_subject.get(s.id, [])
                rows.append(
                    {
                        "yil": year,
                        "ders": s.id,
                        "beklenen": s.question_count,
                        "soru": len(qs),
                        "cevapli": sum(1 for q in qs if q.answer or q.iptal),
                        "etiketli": sum(1 for q in qs if q.kaliplar or q.uniteler),
                    }
                )
        return rows

    def distribution(self, subject: str, field: str = "uniteler") -> dict[str, Counter]:
        """Bir dersin yıllara göre ünite veya kalıp dağılımı: {etiket: Counter({yil: adet})}."""
        dist: dict[str, Counter] = defaultdict(Counter)
        for q in self.all():
            if q.ders != subject:
                continue
            for tag in getattr(q, field) or ["(etiketsiz)"]:
                dist[tag][q.yil] += 1
        return dist


def _fingerprint(q: Question) -> str:
    return tr_lower(one_line(q.kok + " " + " ".join(q.secenekler.values())))[:400]
