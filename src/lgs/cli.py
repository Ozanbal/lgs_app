"""lgs komut satırı arayüzü.

Örnekler:
    lgs durum
    lgs indir
    lgs isle data/raw/2025/*.pdf          # yıl/oturum/kitapçık dosya adından
    lgs anahtar 2025 --sablon
    lgs anahtar 2025
    lgs dagilim matematik
    lgs kaliplar --ders turkce
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import knowledge
from .bank import QuestionBank
from .tagger import tag_question
from .text import tr_lower


def _print_table(headers: list[str], rows: list[list]) -> None:
    widths = [max(len(str(x)) for x in [h] + [r[i] for r in rows]) for i, h in enumerate(headers)]
    print("  ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(str(x).ljust(w) for x, w in zip(r, widths)))


def cmd_durum(args) -> int:
    bank = QuestionBank(args.veri)
    status = {e["yil"]: e for e in knowledge.exam_spec()["sinavlar"]}
    per_year: dict[int, list[int]] = {}
    for row in bank.coverage():
        acc = per_year.setdefault(row["yil"], [0, 0, 0, 0])
        acc[0] += row["beklenen"]
        acc[1] += row["soru"]
        acc[2] += row["cevapli"]
        acc[3] += row["etiketli"]
    rows = []
    total = [0, 0, 0, 0]
    for year, (exp, n, ans, tagged) in per_year.items():
        total = [a + b for a, b in zip(total, (exp, n, ans, tagged))]
        state = "islendi" if n else status[year]["durum"]
        rows.append([year, f"{n}/{exp}", ans, tagged, state])
    rows.append(["TOPLAM", f"{total[1]}/{total[0]}", total[2], total[3], ""])
    _print_table(["Yıl", "Soru", "Cevaplı", "Etiketli", "Durum"], rows)
    return 0


def cmd_indir(args) -> int:
    from .ingest.fetch import download, find_pdf_links

    pages = args.sayfa or knowledge.exam_spec()["kaynaklar"]["resmi"]
    failures = 0
    for page in pages:
        try:
            links = find_pdf_links(page)
        except OSError as e:
            print(f"HATA {page}: {e}", file=sys.stderr)
            failures += 1
            continue
        print(f"{page}: {len(links)} PDF")
        for link in links:
            try:
                path = download(link, Path(args.veri) / "raw")
                print(f"  + {path}")
            except OSError as e:
                print(f"  HATA {link.url}: {e}", file=sys.stderr)
                failures += 1
    return 1 if failures else 0


def _infer_session(path: Path) -> str | None:
    name = tr_lower(path.stem)
    if re.search(r"s[oö]zel", name):
        return "sozel"
    if re.search(r"say[ıi]sal", name):
        return "sayisal"
    return None


def _infer_year(path: Path) -> int | None:
    m = re.search(r"20(1[89]|2\d)", str(path))
    return int(m.group(0)) if m else None


def _infer_booklet(path: Path) -> str | None:
    """Dosya adından kitapçık türü: "..._A.pdf", "A_kitapcik", "kitapcik-b" gibi."""
    name = tr_lower(path.stem)
    m = re.search(r"(?:^|[_\-\s])([ab])(?:[_\-\s]|$)|([ab])[_\-\s]?kitap|kitap[cç][ıi]k[_\-\s]?([ab])\b", name)
    return next(g for g in m.groups() if g).upper() if m else None


def cmd_isle(args) -> int:
    from .ingest.parser import parse_booklet
    from .ingest.pdf_text import extract_pages

    jobs = []
    for raw in args.pdf:
        pdf = Path(raw)
        session = args.oturum or _infer_session(pdf)
        year = args.yil or _infer_year(pdf)
        booklet = (args.kitapcik or _infer_booklet(pdf) or "A").upper()
        if session is None or year is None:
            print(f"{pdf}: oturum (--oturum sozel|sayisal) ve yıl (--yil) belirlenemedi.", file=sys.stderr)
            return 2
        jobs.append((year, session, booklet, pdf))

    bank = QuestionBank(args.veri)
    # B kitapçığı A'ya eşlendiği için önce A kitapçıkları işlenir.
    for year, session, booklet, pdf in sorted(jobs, key=lambda j: (j[0], j[2] != "A", j[1])):
        pages = extract_pages(pdf, columns=args.sutun)
        result = parse_booklet(pages, year, session, booklet=booklet, source=pdf.name)
        if booklet == "A":
            for q in result.questions:
                tag_question(q)
            added, updated = bank.merge(year, result.questions)
            print(f"{year} {session} {booklet}: {len(result.questions)} soru ({added} yeni, {updated} güncellendi)")
        else:
            unmatched = bank.merge_other_booklet(year, result.questions, booklet)
            matched = len(result.questions) - len(unmatched)
            result.warnings.extend(unmatched)
            print(f"{year} {session} {booklet}: {matched}/{len(result.questions)} soru A kitapçığıyla eşlendi")
        for w in result.warnings:
            print(f"  uyarı: {w}")
    return 0


def cmd_anahtar(args) -> int:
    from .ingest.answer_key import apply_answer_key, load_answer_key, template

    path = Path(args.dosya or Path(args.veri) / "cevap_anahtarlari" / f"{args.yil}.yaml")
    if args.sablon:
        if path.exists():
            print(f"{path} zaten var; üzerine yazılmadı.", file=sys.stderr)
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template(args.yil), encoding="utf-8")
        print(f"Şablon yazıldı: {path}")
        return 0
    year, key = load_answer_key(path)
    bank = QuestionBank(args.veri)
    questions = bank.load(year)
    if not questions:
        print(f"{year} için soru bankası boş; önce `lgs isle` çalıştırın.", file=sys.stderr)
        return 1
    warnings = apply_answer_key(questions, key)
    bank.save(year, questions)
    answered = sum(1 for q in questions if q.answer or q.iptal)
    print(f"{year}: {answered}/{len(questions)} soruya cevap işlendi")
    for w in warnings:
        print(f"  uyarı: {w}")
    return 0


def cmd_etiketle(args) -> int:
    bank = QuestionBank(args.veri)
    years = [args.yil] if args.yil else bank.years()
    for year in years:
        questions = bank.load(year)
        changed = sum(tag_question(q, force=args.zorla) for q in questions)
        bank.save(year, questions)
        print(f"{year}: {changed}/{len(questions)} soru etiketlendi")
    return 0


def cmd_dagilim(args) -> int:
    bank = QuestionBank(args.veri)
    dist = bank.distribution(args.ders, field=args.alan)
    if not dist:
        print(f"{args.ders} için etiketli soru yok.")
        return 0
    names = {**{u["id"]: u["ad"] for u in knowledge.units(args.ders)},
             **{p["id"]: p["ad"] for p in knowledge.patterns(args.ders)}}
    years = sorted({y for c in dist.values() for y in c})
    rows = []
    for tag, counts in sorted(dist.items(), key=lambda kv: -sum(kv[1].values())):
        rows.append([names.get(tag, tag)] + [counts.get(y, 0) for y in years] + [sum(counts.values())])
    _print_table(["Etiket"] + [str(y) for y in years] + ["Toplam"], rows)
    return 0


def cmd_kaliplar(args) -> int:
    distractors = knowledge.distractor_index()
    for p in knowledge.patterns(args.ders):
        if args.ders and p["ders"] == "genel" and not args.genel:
            continue
        sure = f" | hedef {p['hedef_sure_sn']} sn" if p.get("hedef_sure_sn") else ""
        print(f"[{p['id']}] {p['ad']} ({p['ders']}{sure})")
        for t in p["taktikler"]:
            print(f"   • {t}")
        if p["celdiriciler"]:
            print("   çeldiriciler: " + ", ".join(distractors[c]["ad"] for c in p["celdiriciler"]))
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="lgs", description="LGS soru bankası araçları")
    ap.add_argument("--veri", default="data", help="veri klasörü (varsayılan: data)")
    sub = ap.add_subparsers(dest="komut", required=True)

    sub.add_parser("durum", help="yıllara göre soru bankası doluluğu").set_defaults(func=cmd_durum)

    p = sub.add_parser("indir", help="resmi PDF kitapçıklarını indir (meb.gov.tr erişimi gerekir)")
    p.add_argument("--sayfa", action="append", help="PDF bağlantılarının toplanacağı duyuru sayfası")
    p.set_defaults(func=cmd_indir)

    p = sub.add_parser("isle", help="PDF kitapçık(lar)ı ayrıştırıp soru bankasına ekle")
    p.add_argument("pdf", nargs="+", help="yıl/oturum/kitapçık dosya adından çıkarılabilir")
    p.add_argument("--yil", type=int)
    p.add_argument("--oturum", choices=["sozel", "sayisal"])
    p.add_argument("--kitapcik", help="A veya B (varsayılan: dosya adından, yoksa A)")
    p.add_argument("--sutun", type=int, default=2, help="sayfadaki sütun sayısı (varsayılan 2)")
    p.set_defaults(func=cmd_isle)

    p = sub.add_parser("anahtar", help="cevap anahtarını soru bankasına uygula")
    p.add_argument("yil", type=int)
    p.add_argument("--dosya")
    p.add_argument("--sablon", action="store_true", help="boş cevap anahtarı şablonu oluştur")
    p.set_defaults(func=cmd_anahtar)

    p = sub.add_parser("etiketle", help="soruları konu ve kalıba göre yeniden etiketle")
    p.add_argument("--yil", type=int)
    p.add_argument("--zorla", action="store_true", help="elle etiketlenenleri de yeniden etiketle")
    p.set_defaults(func=cmd_etiketle)

    p = sub.add_parser("dagilim", help="bir dersin yıllara göre konu/kalıp dağılımı")
    p.add_argument("ders", choices=sorted(knowledge.subjects()))
    p.add_argument("--alan", choices=["uniteler", "kaliplar"], default="uniteler")
    p.set_defaults(func=cmd_dagilim)

    p = sub.add_parser("kaliplar", help="soru kalıpları ve taktikleri listele")
    p.add_argument("--ders", choices=sorted(knowledge.subjects()))
    p.add_argument("--genel", action="store_true", help="ders süzülünce genel kalıpları da göster")
    p.set_defaults(func=cmd_kaliplar)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
