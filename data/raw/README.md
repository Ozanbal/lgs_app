# Ham kaynaklar

Resmi LGS soru kitapçıklarını ve cevap anahtarlarını buraya yıl klasörleriyle koyun:

```
data/raw/2025/LGS_2025_sozel_A.pdf
data/raw/2025/LGS_2025_sayisal_A.pdf
data/raw/2025/LGS_2025_sozel_B.pdf
...
```

PDF dosyaları depoya alınmaz (`.gitignore`); `lgs indir` ile yeniden indirilebilir.
Dosya adında yıl, oturum (`sozel`/`sayisal`) ve kitapçık (`A`/`B`) bulunursa
`lgs isle data/raw/2025/*.pdf` bunları otomatik algılar.
