import pytest

from lgs.ingest.pdf_text import PageText


def make_question(no: int, stem: str, options=("10", "20", "30", "40")) -> str:
    opts = "\n".join(f"{label}) {text}" for label, text in zip("ABCD", options))
    return f"{no}. {stem}\n{opts}"


def booklet_text(session_counts: list[tuple[str, int]], stem_for=None) -> list[PageText]:
    """Ders başlıkları ve numaralı sorulardan oluşan sahte kitapçık sayfaları."""
    pages = [
        PageText(1, "ADAYIN DİKKATİNE\n1. Cevap kâğıdınızı kontrol ediniz.\n2. Kopya çekmek yasaktır.")
    ]
    page_no = 2
    for header, count in session_counts:
        lines = [header]
        for n in range(1, count + 1):
            stem = stem_for(header, n) if stem_for else f"{header} sorusu {n} için metin.\nBu metne göre hangisi doğrudur?"
            lines.append(make_question(n, stem))
        pages.append(PageText(page_no, "\n".join(lines) + "\nDiğer sayfaya geçiniz."))
        page_no += 1
    return pages


@pytest.fixture
def sayisal_pages():
    return booklet_text([("MATEMATİK", 20), ("FEN BİLİMLERİ", 20)])


@pytest.fixture
def sozel_pages():
    return booklet_text(
        [
            ("TÜRKÇE", 20),
            ("T.C. İNKILAP TARİHİ VE ATATÜRKÇÜLÜK", 10),
            ("DİN KÜLTÜRÜ VE AHLAK BİLGİSİ", 10),
            ("YABANCI DİL (İNGİLİZCE)", 10),
        ]
    )
