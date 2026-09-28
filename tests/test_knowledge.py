import re

from lgs import knowledge


def test_exam_has_90_questions_split_50_40():
    subjects = knowledge.subjects()
    assert sum(s.question_count for s in subjects.values()) == 90
    assert sum(s.question_count for s in knowledge.session_subjects("sozel")) == 50
    assert sum(s.question_count for s in knowledge.session_subjects("sayisal")) == 40
    assert [s.id for s in knowledge.session_subjects("sozel")] == ["turkce", "inkilap", "din", "ingilizce"]


def test_exam_catalog_covers_2018_to_2026():
    assert knowledge.exam_years() == list(range(2018, 2027))


def test_units_are_unique_and_prefixed_by_subject():
    seen = set()
    for subject, units in knowledge.curriculum().items():
        assert subject in knowledge.subjects()
        prefix = {"turkce": "tur", "matematik": "mat", "fen": "fen", "inkilap": "ink", "din": "din", "ingilizce": "ing"}[subject]
        for u in units:
            assert u["id"].startswith(prefix + "."), u["id"]
            assert u["id"] not in seen
            seen.add(u["id"])
            assert u["anahtar_kelimeler"], u["id"]


def test_patterns_reference_known_units_and_distractors():
    units = knowledge.unit_index()
    distractors = knowledge.distractor_index()
    ids = [p["id"] for p in knowledge.patterns()]
    assert len(ids) == len(set(ids))
    for p in knowledge.patterns():
        assert p["ders"] in set(knowledge.subjects()) | {"genel"}
        assert p["taktikler"], p["id"]
        for uid in p.get("uniteler") or []:
            assert uid in units, (p["id"], uid)
        for cid in p["celdiriciler"]:
            assert cid in distractors, (p["id"], cid)
        for cue in p["ipuclari"]:
            re.compile(cue)


def test_every_subject_has_patterns():
    for subject in knowledge.subjects():
        assert [p for p in knowledge.patterns(subject) if p["ders"] == subject], subject
