# LGS Strateji Uygulaması

LGS'de (Liselere Geçiş Sistemi) çıkmış tüm soruları konu ve **soru kalıbı** düzeyinde
etiketleyen bir soru bankası ile, bunun üzerine kurulacak **öğrenci cevap analiz
motoru**. Motorun amacı öğrencinin nerede takıldığını (konu, soru kalıbı, çeldirici
tipi, süre) bulup kalıba özgü taktik ve çalışma planı önermek.

## Durum

| Bileşen | Durum |
|---|---|
| Sınav yapısı ve yıl kataloğu (2018–2026, 9 sınav, 810 soru) | ✅ `src/lgs/data/sinav.yaml` |
| 8. sınıf konu/kazanım haritası (6 ders, kazanım kodlarıyla) | ✅ `src/lgs/data/mufredat.yaml` |
| Soru kalıbı taksonomisi: 51 kalıp, 13 çeldirici tipi, taktikler, hedef süreler | ✅ `src/lgs/data/soru_kaliplari.yaml` |
| PDF kitapçık → soru ayrıştırıcı (iki sütun, ders geçişleri, A/B eşleme) | ✅ `lgs isle` |
| Otomatik konu + kalıp etiketleyici | ✅ `lgs etiketle` |
| Cevap anahtarı işleme (A/B kitapçık, iptal soru) | ✅ `lgs anahtar` |
| Soru bankası içeriği (`data/bank/`) | ⏳ resmi PDF'ler bekleniyor |
| Öğrenci cevap analiz motoru | ⏳ sonraki aşama |

Resmi soru kitapçıkları ve cevap anahtarları MEB/ODSGM'de yayımlanıyor
(`odsgm.meb.gov.tr`). Bu depoyu geliştirdiğimiz bulut ortamının ağ politikası
`meb.gov.tr` alan adlarını engellediği için PDF'ler henüz indirilemedi.
Soruların metinleri uydurulmaz, yalnızca resmi PDF'lerden alınır.

## Kurulum

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Soru bankasını doldurma

1. **Otomatik indirme** (meb.gov.tr erişimi olan bir ortamda):
   ```bash
   lgs indir                       # sinav.yaml'daki resmi duyuru sayfaları
   lgs indir --sayfa <ODSGM duyuru URL'si>
   ```
2. **Elle eklenen PDF'ler:** Dosyaları `data/raw/<yil>/` altına koyun. Dosya adında
   yıl, oturum (`sozel`/`sayisal`) ve kitapçık (`A`/`B`) varsa bunlar otomatik algılanır:
   ```bash
   lgs isle data/raw/2025/*.pdf
   lgs isle kitapcik.pdf --yil 2023 --oturum sayisal --kitapcik A
   ```
   A kitapçığı kanoniktir. B kitapçığı işlendiğinde sorular metin benzerliğiyle A'daki
   eşlerine bağlanır (`kitapcik_no: {"A": 7, "B": 15}`).
3. **Cevap anahtarı:**
   ```bash
   lgs anahtar 2025 --sablon       # data/cevap_anahtarlari/2025.yaml şablonu
   # dosyayı doldurun, sonra:
   lgs anahtar 2025
   ```
4. **Kontrol ve analiz:**
   ```bash
   lgs durum                        # yıl bazında soru/cevap/etiket doluluğu
   lgs dagilim matematik            # yıllara göre konu dağılımı
   lgs dagilim turkce --alan kaliplar
   lgs kaliplar --ders fen          # kalıplar, taktikler, çeldiriciler
   ```

## Veri modeli

`data/bank/<yil>.jsonl` dosyasında her satır bir sorudur:

```json
{
  "id": "2025-MAT-07", "yil": 2025, "oturum": "sayisal", "ders": "matematik", "no": 7,
  "kok": "…", "secenekler": {"A": "…", "B": "…", "C": "…", "D": "…"},
  "kitapcik_no": {"A": 7, "B": 15}, "cevaplar": {"A": "C", "B": "A"}, "iptal": false,
  "gorsel": true,
  "uniteler": ["mat.karekoklu_ifadeler"],
  "kaliplar": ["MAT-GERCEK-HAYAT", "GEN-OLUMSUZ-KOK"],
  "etiket_kaynagi": "otomatik",
  "kaynak": {"dosya": "…pdf", "sayfa": 5, "kitapcik": "A"}
}
```

Etiketi elle düzeltilen soruda `etiket_kaynagi` alanını `"elle"` yapın; yeniden
etiketleme (`lgs etiketle`) bu sorulara dokunmaz.

## Bilgi tabanı

- **Soru kalıpları** her ders için ayrı (örn. `TUR-SOZEL-MANTIK`, `MAT-KATLAMA-KESME`,
  `FEN-DALLANMIS-AGAC`, `INK-KRONOLOJI`) ve dersler üstü (`GEN-OLUMSUZ-KOK`,
  `GEN-ONCULLU`, `GEN-KESINLIK`, `GEN-UZUN-METIN`) olarak tanımlıdır. Bir soru birden
  fazla kalıp taşıyabilir.
- **Çeldirici tipleri** (aşırı genelleme, ara sonuç, ters ilişki, kavram karışıklığı…)
  öğrencinin yanlış seçtiği şıkkın hangi tuzağa düştüğünü açıklamak için kullanılacak.
- Her kalıbın **hedef süresi** vardır (sözel oturum 75 dk/50 soru ≈ 90 sn, sayısal
  oturum 80 dk/40 soru ≈ 120 sn ortalamaya göre).

## Yol haritası: analiz motoru

Girdi: öğrencinin bir sınav/deneme için cevapları (kitapçık türü + şıklar, isteğe
bağlı soru başına süre). Çıktı:

- ders, konu ve kazanım bazında net ve başarı oranı
- soru kalıbı bazında hata profili ("olumsuz kökte %40 kayıp" gibi)
- çeldirici profili: yanlışların hangi tuzak tipinde yoğunlaştığı
- zaman yönetimi: hedef süreyi aşan kalıplar
- öncelik sıralı çalışma planı: puana etkisi (katsayı × kayıp net) en yüksek alanlar önce
