from lgs.ingest.parser import parse_booklet, split_options, split_questions
from lgs.ingest.pdf_text import PageText


def test_split_options_on_separate_lines():
    stem, opts = split_options("Soru metni\nHangisidir?\nA) bir\nB) iki\nC) üç\nD) dört")
    assert stem == "Soru metni\nHangisidir?"
    assert opts == {"A": "bir", "B": "iki", "C": "üç", "D": "dört"}


def test_split_options_inline():
    stem, opts = split_options("2^3 kaçtır? A) 6 B) 8 C) 9 D) 12")
    assert stem == "2^3 kaçtır?"
    assert opts == {"A": "6", "B": "8", "C": "9", "D": "12"}


def test_split_options_uses_last_complete_sequence():
    text = "Tabloda A) bölümü ve B) bölümü var.\nHangisi doğrudur?\nA) x\nB) y\nC) z\nD) w"
    stem, opts = split_options(text)
    assert stem.endswith("Hangisi doğrudur?")
    assert opts["A"] == "x" and opts["D"] == "w"


def test_split_options_missing_returns_empty():
    stem, opts = split_options("Görsel seçenekli soru")
    assert opts == {}


def test_sayisal_booklet_splits_into_subjects(sayisal_pages):
    raws, warnings = split_questions(sayisal_pages, "sayisal")
    assert warnings == []
    assert [r.subject for r in raws] == ["matematik"] * 20 + ["fen"] * 20
    assert [r.number for r in raws[:3]] == [1, 2, 3]


def test_instruction_page_numbers_are_not_questions(sozel_pages):
    raws, warnings = split_questions(sozel_pages, "sozel")
    assert warnings == []
    assert len(raws) == 50
    assert "Cevap kâğıdınızı" not in raws[0].text


def test_numbered_lines_inside_question_do_not_split():
    text = "TÜRKÇE\n1. Metin başlıyor.\n3. paragrafta yazar ne diyor?\nA) a\nB) b\nC) c\nD) d\n2. İkinci soru\nA) a\nB) b\nC) c\nD) d"
    raws, _ = split_questions([PageText(1, text)], "sozel")
    assert [r.number for r in raws[:2]] == [1, 2]
    assert "3. paragrafta" in raws[0].text


def test_missing_question_is_skipped_with_warning():
    lines = ["MATEMATİK"]
    for n in [1, 2, 4, 5]:
        lines += [f"{n}. soru {n}", "A) 1", "B) 2", "C) 3", "D) 4"]
    raws, warnings = split_questions([PageText(1, "\n".join(lines))], "sayisal")
    assert [r.number for r in raws] == [1, 2, 4, 5]
    assert any("3-3" in w for w in warnings)


def test_header_of_later_subject_forces_switch():
    lines = ["MATEMATİK", "1. m1", "A) 1", "B) 2", "C) 3", "D) 4", "FEN BİLİMLERİ", "1. f1", "A) 1", "B) 2", "C) 3", "D) 4"]
    raws, warnings = split_questions([PageText(1, "\n".join(lines))], "sayisal")
    assert [(r.subject, r.number) for r in raws] == [("matematik", 1), ("fen", 1)]
    assert any("matematik" in w for w in warnings)


def test_parse_booklet_builds_questions(sayisal_pages):
    result = parse_booklet(sayisal_pages, 2025, "sayisal", source="x.pdf")
    q = result.questions[0]
    assert q.id == "2025-MAT-01"
    assert q.secenekler["B"] == "20"
    assert q.kitapcik_no == {"A": 1}
    assert result.questions[-1].id == "2025-FEN-20"


def test_subject_name_inside_question_table_does_not_switch_subject():
    lines = ["TÜRKÇE", "1. Tabloda derslere ayrılan süreler var:", "İngilizce", "Türkçe", "Buna göre hangisi doğrudur?",
             "A) a", "B) b", "C) c", "D) d", "2. İkinci soru", "A) a", "B) b", "C) c", "D) d"]
    raws, _ = split_questions([PageText(1, "\n".join(lines))], "sozel")
    assert [(r.subject, r.number) for r in raws] == [("turkce", 1), ("turkce", 2)]
    assert "İngilizce" in raws[0].text
