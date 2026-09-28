"""Soru bankası veri modeli.

JSON anahtarları Türkçedir; soru bankası dosyaları (data/bank/<yil>.jsonl)
elle de düzenlenebilsin diye alan adları okunur tutulmuştur.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .knowledge import subjects


def question_id(year: int, subject: str, number: int) -> str:
    """Kanonik kimlik: A kitapçığı numarasıyla, örn. 2025-MAT-07."""
    return f"{year}-{subjects()[subject].code}-{number:02d}"


@dataclass
class Question:
    id: str
    yil: int
    oturum: str
    ders: str
    no: int  # A kitapçığındaki numara (ders içinde 1'den başlar)
    kok: str = ""  # soru kökü (metin + soru cümlesi)
    secenekler: dict[str, str] = field(default_factory=dict)
    kitapcik_no: dict[str, int] = field(default_factory=dict)  # {"A": 7, "B": 15}
    cevaplar: dict[str, str] = field(default_factory=dict)  # {"A": "C", "B": "A"}
    iptal: bool = False
    gorsel: bool = False
    uniteler: list[str] = field(default_factory=list)
    kaliplar: list[str] = field(default_factory=list)
    etiket_kaynagi: str = "yok"  # yok | otomatik | elle
    kaynak: dict = field(default_factory=dict)
    notlar: str = ""

    @property
    def answer(self) -> str | None:
        return self.cevaplar.get("A")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})
