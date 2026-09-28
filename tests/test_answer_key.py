import pytest
import yaml

from lgs.ingest.answer_key import apply_answer_key, load_answer_key, parse_answers, template
from lgs.models import Question


def test_parse_answers_ignores_spaces():
    assert parse_answers("AB CD", 4, "t") == ["A", "B", "C", "D"]


def test_parse_answers_rejects_wrong_length_and_letters():
    with pytest.raises(ValueError, match="4 cevap"):
        parse_answers("ABC", 4, "t")
    with pytest.raises(ValueError, match="geçersiz"):
        parse_answers("ABCE", 4, "t")


def test_template_is_valid_yaml_with_all_subjects():
    data = yaml.safe_load(template(2025))
    assert data["yil"] == 2025
    assert set(data["A"]) == {"turkce", "inkilap", "din", "ingilizce", "matematik", "fen"}


def test_apply_answer_key_for_both_booklets_and_cancelled(tmp_path):
    path = tmp_path / "2025.yaml"
    path.write_text(
        "yil: 2025\nA:\n  inkilap: 'ABCD ABCD AX'\nB:\n  inkilap: 'DCBA DCBA DC'\n",
        encoding="utf-8",
    )
    year, key = load_answer_key(path)
    assert year == 2025
    q1 = Question(id="2025-INK-01", yil=2025, oturum="sozel", ders="inkilap", no=1, kitapcik_no={"A": 1, "B": 3})
    q10 = Question(id="2025-INK-10", yil=2025, oturum="sozel", ders="inkilap", no=10, kitapcik_no={"A": 10})
    warnings = apply_answer_key([q1, q10], key)
    assert q1.cevaplar == {"A": "A", "B": "B"}
    assert q10.iptal and "A" not in q10.cevaplar
    assert warnings == ["2025-INK-10: B kitapçığındaki numarası bilinmiyor"]
