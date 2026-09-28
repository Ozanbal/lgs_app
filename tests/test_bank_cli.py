from lgs.bank import QuestionBank
from lgs.cli import main
from lgs.ingest.parser import parse_booklet


def test_merge_keeps_answers_and_manual_tags(tmp_path, sayisal_pages):
    bank = QuestionBank(tmp_path)
    questions = parse_booklet(sayisal_pages, 2025, "sayisal").questions
    assert bank.merge(2025, questions) == (40, 0)

    stored = bank.load(2025)
    stored[0].cevaplar["A"] = "C"
    stored[0].etiket_kaynagi = "elle"
    bank.save(2025, stored)

    again = parse_booklet(sayisal_pages, 2025, "sayisal").questions
    assert bank.merge(2025, again) == (0, 40)
    first = bank.load(2025)[0]
    assert first.cevaplar == {"A": "C"} and first.etiket_kaynagi == "elle"


def test_other_booklet_is_matched_by_text(tmp_path, sayisal_pages):
    bank = QuestionBank(tmp_path)
    bank.merge(2025, parse_booklet(sayisal_pages, 2025, "sayisal").questions)
    b_questions = parse_booklet(sayisal_pages, 2025, "sayisal", booklet="B").questions
    # B kitapçığında sıralama farklı: matematik 1 ile 2 yer değiştirsin.
    b_questions[0].no, b_questions[1].no = 2, 1
    warnings = bank.merge_other_booklet(2025, b_questions, "B")
    assert warnings == []
    stored = {q.id: q for q in bank.load(2025)}
    assert stored["2025-MAT-01"].kitapcik_no == {"A": 1, "B": 2}
    assert stored["2025-MAT-02"].kitapcik_no == {"A": 2, "B": 1}


def test_cli_status_and_answer_key_template(tmp_path, capsys, sayisal_pages):
    QuestionBank(tmp_path).merge(2024, parse_booklet(sayisal_pages, 2024, "sayisal").questions)
    assert main(["--veri", str(tmp_path), "durum"]) == 0
    out = capsys.readouterr().out
    assert "2024    40/90" in out
    assert "TOPLAM  40/810" in out

    assert main(["--veri", str(tmp_path), "anahtar", "2024", "--sablon"]) == 0
    key = tmp_path / "cevap_anahtarlari" / "2024.yaml"
    text = key.read_text(encoding="utf-8")
    text = text.replace('matematik: ""', 'matematik: "' + "ABCD" * 5 + '"', 1)
    key.write_text(text, encoding="utf-8")
    assert main(["--veri", str(tmp_path), "anahtar", "2024"]) == 0
    assert "20/40 soruya cevap" in capsys.readouterr().out


def test_cli_distribution(tmp_path, capsys, sayisal_pages):
    QuestionBank(tmp_path).merge(2025, parse_booklet(sayisal_pages, 2025, "sayisal").questions)
    assert main(["--veri", str(tmp_path), "etiketle"]) == 0
    assert main(["--veri", str(tmp_path), "dagilim", "matematik", "--alan", "kaliplar"]) == 0
    assert "2025" in capsys.readouterr().out


def test_filename_inference():
    from pathlib import Path

    from lgs.cli import _infer_booklet, _infer_session, _infer_year

    p = Path("data/raw/2025/LGS_2025_Sozel_A_Kitapcigi.pdf")
    assert (_infer_year(p), _infer_session(p), _infer_booklet(p)) == (2025, "sozel", "A")
    p = Path("2019-sayısal-kitapçık-b.pdf")
    assert (_infer_year(p), _infer_session(p), _infer_booklet(p)) == (2019, "sayisal", "B")
    assert _infer_booklet(Path("2024_sayisal.pdf")) is None
