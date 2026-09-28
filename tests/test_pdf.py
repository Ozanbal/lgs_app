"""Gerçek bir iki sütunlu PDF üretip uçtan uca ayrıştırma testi."""

from pathlib import Path

import pytest

reportlab = pytest.importorskip("reportlab")
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from lgs.ingest.parser import parse_booklet  # noqa: E402
from lgs.ingest.pdf_text import extract_pages  # noqa: E402

FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def _write_two_column_pdf(path: Path, blocks: list[list[str]]) -> None:
    pdfmetrics.registerFont(TTFont("DejaVu", str(FONT)))
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    columns = [40, width / 2 + 20]
    col, y = 0, height - 50
    for block in blocks:
        needed = 14 * len(block) + 10
        if y - needed < 50:
            col += 1
            y = height - 50
            if col == 2:
                c.setFont("DejaVu", 9)
                c.drawString(width / 2 - 5, 25, str(c.getPageNumber()))
                c.showPage()
                col = 0
        c.setFont("DejaVu", 9)
        for line in block:
            c.drawString(columns[col], y, line)
            y -= 14
        y -= 10
    c.showPage()
    c.save()


@pytest.mark.skipif(not FONT.exists(), reason="DejaVuSans yok")
def test_two_column_pdf_round_trip(tmp_path):
    blocks = [["MATEMATİK"]]
    for n in range(1, 21):
        blocks.append([f"{n}. √{n * 4} ifadesinin değeri hangi iki", "doğal sayı arasındadır?", "A) 1 ve 2", "B) 2 ve 3", "C) 3 ve 4", "D) 4 ve 5"])
    blocks.append(["FEN BİLİMLERİ"])
    for n in range(1, 21):
        blocks.append([f"{n}. Çaprazlama sonucu oluşan", "yavruların genotipi nedir?", "A) AA", "B) Aa", "C) aa", "D) AB"])
    pdf = tmp_path / "2025_sayisal_A.pdf"
    _write_two_column_pdf(pdf, blocks)

    pages = extract_pages(pdf)
    result = parse_booklet(pages, 2025, "sayisal", source=pdf.name)
    assert result.warnings == []
    assert len(result.questions) == 40
    first, last = result.questions[0], result.questions[-1]
    assert first.id == "2025-MAT-01"
    assert first.kok.startswith("√4 ifadesinin")
    assert first.secenekler == {"A": "1 ve 2", "B": "2 ve 3", "C": "3 ve 4", "D": "4 ve 5"}
    assert last.id == "2025-FEN-20" and last.secenekler["D"] == "AB"
