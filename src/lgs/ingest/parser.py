"""Kitapçık metnini derslere ve sorulara ayırır.

LGS kitapçıklarında her dersin numaralandırması 1'den başlar ve ders sırası
sabittir (sözel: Türkçe, İnkılap, Din, Yabancı Dil; sayısal: Matematik, Fen).
Ayrıştırıcı bu yapıyı kullanır: soru başlangıcı yalnızca beklenen sıradaki
numarayla eşleşen satırlarda kabul edilir, böylece metin içindeki
"2. paragraf" gibi ifadeler yeni soru sanılmaz.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..knowledge import session_subjects
from ..models import Question, question_id
from ..text import one_line, squash, tr_lower
from .pdf_text import PageText

# Ders içinde kaç numara atlanabileceği (metin çıkarımında kaybolan soru için).
MAX_SKIP = 2

_QUESTION_START = re.compile(r"^\s*(\d{1,2})\s*[.)]\s*(.*)$")
_OPTION = re.compile(r"(?:(?<=\s)|^)([A-D])\)\s*")
_VISUAL_CUES = re.compile(
    r"şekil|görsel|grafik|tablo|harita|model|resim|fotoğraf|afiş|karikatür|chart|table|graph|picture|poster"
)

_SUBJECT_HEADERS = {
    "turkce": r"türkçe( testi)?",
    "inkilap": r"(t\.\s?c\.\s?)?inkılap tarihi ve atatürkçülük( testi)?",
    "din": r"din kültürü ve ahlak bilgisi( testi)?",
    "ingilizce": r"(yabancı dil|ingilizce)( testi)?( \(?ingilizce\)?)?",
    "matematik": r"matematik( testi)?",
    "fen": r"fen bilimleri( testi)?",
}

_NOISE = [
    r"diğer sayfaya geçiniz\.?",
    r"test bitti\b.*",
    r"cevaplarınızı.*işaretle.*",
    r"(sözel|sayısal) bölüm",
    r"[ab] kitapçık türü|kitapçık türü:? ?[ab]|[ab] kitapçığı",
    r"\d\.?\s*oturum",
    r"t\.\s?c\.\s?mill[iî] eğitim bakanlığı|mill[iî] eğitim bakanlığı",
    r"8\.\s*sınıf",
    r"lgs|merkez[iî] sınav",
]
_NOISE_RE = re.compile("|".join(f"(?:{p})" for p in _NOISE))

_INSTRUCTION_WORDS = (
    "adayın dikkatine",
    "adayların dikkatine",
    "açıklamalar",
    "sınav görevli",
    "cevap kâğıdı",
    "cevap kağıdı",
    "yasaktır",
)


@dataclass
class RawQuestion:
    subject: str
    number: int
    page: int
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass
class ParseResult:
    questions: list[Question]
    warnings: list[str]


def _header(low_line: str) -> str | None:
    for subject, pattern in _SUBJECT_HEADERS.items():
        if re.fullmatch(pattern, low_line):
            return subject
    return None


def _has_all_options(text: str) -> bool:
    return bool(split_options(text)[1])


def is_instruction_page(text: str) -> bool:
    """Kapak/açıklama sayfası mı? (numaralı yönergeler soru sanılmasın diye)"""
    low = tr_lower(text)
    has_options = len(_OPTION.findall(text)) >= 4
    hits = sum(word in low for word in _INSTRUCTION_WORDS)
    return hits >= 2 and not has_options


def split_questions(pages: list[PageText], session: str) -> tuple[list[RawQuestion], list[str]]:
    subjects = session_subjects(session)
    order = [s.id for s in subjects]
    expected = {s.id: s.question_count for s in subjects}
    got = {s: 0 for s in order}
    warnings: list[str] = []

    raws: list[RawQuestion] = []
    idx = 0
    next_no = 1
    current: RawQuestion | None = None

    for page in pages:
        if current is None and is_instruction_page(page.text):
            continue
        for line in squash(page.text).splitlines():
            low = tr_lower(line).strip()
            header = _header(low)
            if header in order:
                target = order.index(header)
                if target == idx:
                    continue  # aynı dersin sayfa başlığı
                # Sonraki bir dersin başlığı: eksik soru olsa bile o derse geç. Önceki
                # soru henüz seçeneklerine ulaşmadıysa satır büyük olasılıkla soru içindeki
                # bir tablo satırıdır ("İngilizce" gibi), metin olarak kalır.
                if target > idx and (current is None or _has_all_options(current.text)):
                    subject = order[idx]
                    if current is not None and got[subject] < expected[subject]:
                        warnings.append(
                            f"{subject}: {expected[subject]} soru beklenirken {got[subject]} bulundu"
                        )
                    idx = target
                    next_no = 1
                    current = None  # ders girişindeki açıklamalar önceki soruya eklenmesin
                    continue
            if _NOISE_RE.fullmatch(low):
                continue

            m = _QUESTION_START.match(line)
            if m:
                n = int(m.group(1))
                subject = order[idx]
                accepted = False
                in_window = next_no <= n <= next_no + MAX_SKIP
                # Numara atlanıyorsa, önceki soru seçenekleriyle tamamlanmış olmalı;
                # aksi hâlde satır büyük olasılıkla soru içindeki "3. paragraf" gibi bir ifadedir.
                if in_window and n != next_no and current is not None and not _has_all_options(current.text):
                    in_window = False
                if got[subject] < expected[subject] and in_window:
                    if n != next_no:
                        warnings.append(f"{subject}: {next_no}-{n - 1} numaralı soru(lar) okunamadı")
                    accepted = True
                elif n == 1 and current is not None and idx + 1 < len(order) and (
                    got[subject] >= expected[subject]
                ):
                    idx += 1
                    subject = order[idx]
                    accepted = True
                if accepted:
                    current = RawQuestion(subject, n, page.page, [m.group(2)] if m.group(2) else [])
                    raws.append(current)
                    got[subject] += 1
                    next_no = n + 1
                    continue
            if current is not None:
                current.lines.append(line)
        last = order[-1]
        if current is not None and current.subject == last and current.number >= expected[last]:
            # Son dersin son sorusunun sayfası bitti; sonrası (diğer diller,
            # cevap anahtarı sayfası vb.) bankaya alınmaz.
            break

    for s in order:
        if got[s] != expected[s]:
            msg = f"{s}: {expected[s]} soru beklenirken {got[s]} bulundu"
            if msg not in warnings:
                warnings.append(msg)
    return raws, warnings


def split_options(text: str) -> tuple[str, dict[str, str]]:
    """Soru metnini kök ve A-D seçeneklerine ayırır.

    Metin içinde birden fazla "A)" olabileceği için, ardından sırayla B), C),
    D) gelen en son "A)" seçenek başlangıcı kabul edilir.
    """
    marks = [(m.group(1), m.start(), m.end()) for m in _OPTION.finditer(text)]
    for i in range(len(marks) - 1, -1, -1):
        if marks[i][0] != "A":
            continue
        seq = [marks[i]]
        for label, start, end in marks[i + 1 :]:
            want = "ABCD"[len(seq)]
            if label == want:
                seq.append((label, start, end))
                if len(seq) == 4:
                    break
        if len(seq) == 4:
            stem = text[: seq[0][1]].strip()
            options = {}
            for j, (label, _start, end) in enumerate(seq):
                stop = seq[j + 1][1] if j + 1 < 4 else len(text)
                options[label] = one_line(text[end:stop])
            return stem, options
    return text.strip(), {}


def parse_booklet(
    pages: list[PageText],
    year: int,
    session: str,
    booklet: str = "A",
    source: str = "",
) -> ParseResult:
    raws, warnings = split_questions(pages, session)
    questions = []
    for raw in raws:
        stem, options = split_options(raw.text)
        if not options:
            warnings.append(f"{raw.subject} {raw.number}: seçenekler ayrıştırılamadı")
        visual = (
            bool(_VISUAL_CUES.search(tr_lower(stem)))
            or not options
            or any(not v for v in options.values())
        )
        questions.append(
            Question(
                id=question_id(year, raw.subject, raw.number),
                yil=year,
                oturum=session,
                ders=raw.subject,
                no=raw.number,
                kok=stem,
                secenekler=options,
                kitapcik_no={booklet: raw.number},
                gorsel=visual,
                kaynak={"dosya": source, "sayfa": raw.page, "kitapcik": booklet},
            )
        )
    return ParseResult(questions, warnings)
