from lgs.models import Question
from lgs.tagger import tag_question


def q(ders: str, kok: str, secenekler=None, oturum="sozel") -> Question:
    question = Question(id="x", yil=2025, oturum=oturum, ders=ders, no=1, kok=kok, secenekler=secenekler or {})
    tag_question(question)
    return question


def test_turkce_main_idea_maps_to_paragraph_unit():
    r = q("turkce", "Kitap okumak insanın ufkunu genişletir...\nBu metinde asıl anlatılmak istenen aşağıdakilerden hangisidir?")
    assert r.kaliplar[0] == "TUR-ANA-DUSUNCE"
    assert "tur.paragraf" in r.uniteler
    assert r.etiket_kaynagi == "otomatik"


def test_negative_stem_is_flagged():
    r = q("turkce", "Bu metinden aşağıdakilerin hangisi çıkarılamaz?")
    assert "TUR-CIKARIM" in r.kaliplar
    assert "GEN-OLUMSUZ-KOK" in r.kaliplar


def test_premise_question_is_flagged():
    r = q(
        "fen",
        "Buna göre,\nI. DNA çift zincirlidir.\nII. Gen, DNA'nın bir bölümüdür.\nIII. Kromozom DNA içerir.\nyargılarından hangileri doğrudur?",
        {"A": "Yalnız I", "B": "I ve II", "C": "II ve III", "D": "I, II ve III"},
        oturum="sayisal",
    )
    assert "GEN-ONCULLU" in r.kaliplar
    assert r.uniteler[0] == "fen.dna_genetik"


def test_math_square_root_unit():
    r = q("matematik", "√48 + √27 işleminin sonucu kaçtır? Karekök içindeki sayıları a√b biçiminde yazınız.", oturum="sayisal")
    assert r.uniteler[0] == "mat.karekoklu_ifadeler"


def test_short_keyword_does_not_match_inside_other_words():
    # "gen" anahtar kelimesi "genellikle" içinde eşleşmemeli.
    r = q("fen", "Kaldıraçlar genellikle kuvvetten kazanç sağlar. Destek noktası nerededir?", oturum="sayisal")
    assert r.uniteler == ["fen.basit_makineler"]


def test_crossbreeding_pattern():
    r = q("fen", "Saf döl sarı tohumlu bezelye ile yeşil tohumlu bezelye çaprazlanıyor. Yavruların fenotipi nedir?", oturum="sayisal")
    assert "FEN-KALITIM" in r.kaliplar


def test_english_dialogue():
    r = q("ingilizce", "Which of the following best completes the dialogue?\nTom: Would you like to come to my party?\nAyşe: ____")
    assert r.kaliplar[0] == "ING-DIYALOG"
    assert "ing.friendship" in r.uniteler


def test_manual_tags_are_preserved():
    question = Question(id="x", yil=2025, oturum="sozel", ders="turkce", no=1, kok="Bu metnin ana düşüncesi nedir?",
                        kaliplar=["TUR-YAZIM"], etiket_kaynagi="elle")
    assert tag_question(question) is False
    assert question.kaliplar == ["TUR-YAZIM"]
