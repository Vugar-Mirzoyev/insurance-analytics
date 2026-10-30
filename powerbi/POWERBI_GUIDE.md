# Power BI raporu

İki yol var:

- **Hazır rapor:** `insurance_analytics.pbip`. Çift tıkla, Yenile'ye bas, rapor açılır.
- **Kendin kur:** aşağıdaki 0-8. adımlar aynı raporu sıfırdan kurmayı anlatıyor.
  Ölçülerin kodu [`DAX_measures.md`](DAX_measures.md) dosyasında. Öğrenmek için en iyi
  yol bu. Hazır rapor da cevap anahtarı gibi kullanılabilir.

---

## Hazır rapor: insurance_analytics.pbip

Bu bir **Power BI Project (PBIP)**: .pbix ile aynı rapor, ama tek bir ikili dosya
yerine metin dosyalarından oluşuyor. Bu yüzden GitHub'da okunabiliyor ve değişiklikler
satır satır görülebiliyor.

```
powerbi/
├── insurance_analytics.pbip                 # bunu aç
├── insurance_analytics.SemanticModel/       # model (TMDL)
│   └── definition/
│       ├── tables/*.tmdl                    # 11 tablo: kolonlar, 32 ölçü, Power Query kodu
│       ├── relationships.tmdl               # 11 ilişki
│       └── expressions.tmdl                 # DataFolder parametresi (CSV klasörü)
└── insurance_analytics.Report/              # rapor (PBIR)
    └── definition/pages/                    # 3 sayfa: market, portfolio, quality
```

### İlk açılış

1. Önce `python run_pipeline.py` çalıştır (CSV'ler `data/processed/` içinde olmalı).
2. `insurance_analytics.pbip` dosyasına çift tıkla. Power BI Desktop bu bilgisayarda
   kurulu (Microsoft Store sürümü).
3. Görseller boş gelir: PBIP veriyi dosyaların içinde saklamaz. **Giriş > Yenile**'ye
   bas. Yaklaşık 10 saniye sürer.
4. **Ctrl+S** ile kaydet. Desktop veriyi `.pbi/cache.abf` dosyasına yazar (bu dosya
   `.gitignore`'da) ve bir sonraki açılışta görseller dolu gelir. Desktop kaydederken
   dosyaları kendi biçiminde yeniden yazar (ör. `lineageTag` satırları ekler), bu normal.
5. Tek dosya olarak göndermek istersen: **Dosya > Farklı kaydet** ve tür olarak `.pbix`.

Proje başka bir klasöre taşınırsa: **Giriş > Veri dönüştürme > Parametreleri düzenle**
ve `DataFolder` değerini yeni `data\processed` yolu yap.

### Sayfalar

| Sayfa | İçerik |
|---|---|
| Market | 2026'nın 9 ayı için 4 kart (prim, ödeme, ödeme oranı, YoY), aylık trend, çeyreklik ödeme oranı, sigortacı tablosu (segment payı), sınıf bazında ödeme oranı |
| Portfolio | Araç tipi, bölge ve kanal dilimleyicileri. Kartlar: bitmiş yılların loss ratio'su, 2018'in kazanılmış ve yazılan prim bazındaki loss ratio'su, yenileme oranı. Kazanılmış/yazılan loss ratio trendi, yenileme trendi, kanal karşılaştırması, yıl tablosu |
| Data quality | 17 kontrolün sonucu ve anomali kurallarının işaretlediği aylar |

### Nasıl doğrulandı

- Model dosyaları Power BI'ın kendi kütüphanesindeki `TmdlSerializer` ile hatasız
  okundu.
- Rapordaki 35 JSON dosyası Microsoft'un yayımladığı şemalara (`microsoft/json-schemas`)
  karşı doğrulandı: 0 hata.
- Proje Power BI Desktop 2.159'da açıldı, veri yenilendi ve ölçüler DAX sorgusuyla
  README'deki rakamlarla karşılaştırıldı:

| Kontrol | Power BI | README |
|---|---|---|
| Prim / ödeme, 2026 9 ay (mln AZN) | 1.248,5 / 882,7 | 1,248.5 / 882.7 |
| Ödeme oranı / prim YoY, 2026 9 ay | %70,7 / %7,9 | 70.7% / +7.9% |
| Ödeme oranı 2026 Q3 | %87,4 | 87.4% |
| PAŞA Sığorta: prim, segment payı, YoY | 308,9 / %56,8 / %13,2 | 308.9 / 56.8% / +13.2% |
| 2018 loss ratio: yazılan / kazanılmış | %20,8 / %39,7 | 20.8% / 39.7% |
| 2017 loss ratio / frekans | %47,1 / 0,375 | 47.1% / 0.375 |
| Yenileme oranı (genel) | %77,9 | 77.9% |
| Broker / acente: bitmiş yıllar loss ratio | %70,2 / %58,3 | 70.2% / 58.3% |

### Elle kurulan rapordan farkları

- Ölçü adları `Total Premiums` ve `Total Claims Paid`. `Premiums` adı `premiums`
  kolonuyla çakışıyor, çünkü Power BI adlarda büyük-küçük harf ayırmıyor.
- `Date` tablosu Power Query'de kuruluyor ve `market_monthly.csv`'deki son ayda bitiyor.
  Yeni CBAR dosyası gelince kendiliğinden uzar, YoY tuzağı (aşağıda 7. adım) oluşmaz.
- `Loss Ratio (Finished)`: segmentler sadece bitmiş poliçe yılları üzerinden
  karşılaştırılıyor.
- Sigortacı tablosunda ve yıl tablosunda toplam satırı kapalı. Sigortacı tablosu
  lisansı iptal edilen şirketleri gizliyor, bu yüzden toplamı kartlarla tutmazdı. Yıl
  tablosunun toplamı da bitmiş yılları yarısı kazanılmış 2018 ile karıştırırdı.

---

# Raporu kendin kur: adım adım

Toplam süre: yaklaşık 2-3 saat.

---

## 0. Hazırlık

1. Proje klasöründe `python run_pipeline.py` çalıştır. `data/processed/` içinde 13 CSV
   oluşur.
2. Power BI Desktop'ı aç. **File > Options > Regional settings** altında
   "Locale for import" değerini **English (United States)** yap. CSV'lerde ondalık
   ayırıcı nokta (`0.4196`). Başka bir locale seçili olursa sayılar metin ya da
   10.000 kat büyük gelebilir.

## 1. Veriyi al

**Home > Get data > Text/CSV** ile şu dosyaları tek tek al ve her birinde **Load**'a bas:

| Dosya | Ne için |
|---|---|
| `fact_portfolio.csv` | Poliçe KPI'ları (prim, hasar, exposure) |
| `fact_renewal.csv` | Yenileme oranı |
| `insurer_quarterly.csv` | Piyasa: çeyrek, sigortacı, pazar payı |
| `class_quarterly.csv` | Piyasa: sigorta sınıfları |
| `market_monthly.csv` | Piyasa: aylık trend grafiği |
| `market_anomalies.csv` | İşaretlenen aylar (isteğe bağlı) |
| `data_quality.csv` | Veri kalitesi sayfası |

Kontrol: **Transform data**'yı aç. `month_start` kolonunun tipi **Date**, `premiums`,
`written_premium`, `loss_ratio` gibi kolonların tipi **Decimal number** olmalı.
Değilse kolonun başlığındaki tip simgesine tıklayıp düzelt, sonra **Close & Apply**.

## 2. Tarih tablosu ve ilişkiler

1. **Modeling > New table** ile `DAX_measures.md` içindeki `Date` tablosunu oluştur.
   Sonra **Table tools > Mark as date table** ile `Date` kolonunu seç.
2. `insurer_quarterly` ve `class_quarterly` tablolarına **New column** ile
   `quarter_start` kolonunu ekle (kod `DAX_measures.md` içinde).
3. **Model** görünümüne geç ve şu ilişkileri sürükleyerek kur (hepsi bire-çok,
   `Date` tarafı "1"):
   - `Date[Date]` → `fact_portfolio[month_start]`
   - `Date[Date]` → `fact_renewal[month_start]`
   - `Date[Date]` → `market_monthly[month_start]`
   - `Date[Date]` → `insurer_quarterly[quarter_start]`
   - `Date[Date]` → `class_quarterly[quarter_start]`
4. Segment dilimleyicisi (slicer) iki tabloyu birden süzsün diye üç küçük tablo oluştur
   (**New table**):

   ```dax
   Vehicle Type = DISTINCT ( fact_portfolio[vehicle_type] )
   Area = DISTINCT ( fact_portfolio[area] )
   Channel = DISTINCT ( fact_portfolio[channel] )
   ```

   Her birini hem `fact_portfolio` hem `fact_renewal` tablosundaki aynı adlı kolona
   bağla (örnek: `Channel[channel]` → `fact_portfolio[channel]` ve
   `Channel[channel]` → `fact_renewal[channel]`).

Neden: Bir slicer'ı doğrudan `fact_portfolio[channel]` üzerine kurarsan
`fact_renewal` süzülmez. Loss ratio "Broker" için değişir ama yenileme oranı tüm
portföyü göstermeye devam eder.

## 3. Ölçüler

`DAX_measures.md` içindeki her bloğu, başlığındaki tabloya **New measure** ile ekle
(hazır rapordaki gibi: portföy ölçüleri `fact_portfolio`'ya, piyasa ölçüleri
`insurer_quarterly`'ye). İstersen hepsini `_Measures` adlı ayrı bir tabloda da
toplayabilirsin. Önemli olan, ölçü adının aynı tablodaki bir kolonla aynı olmaması:
Power BI adlarda büyük-küçük harf ayırmaz, `Premiums` ölçüsü `premiums` kolonuyla
çakışır. Bu yüzden ölçünün adı `Total Premiums`.

Biçim (**Measure tools**):
- Loss Ratio, Loss Ratio (Written), Loss Ratio (Finished), Earned Share, Renewal Rate,
  Payout Ratio, QoQ %, YoY %, Claims YoY %, Market Share, Segment Share,
  Class Payout Ratio: **Percentage**, 1 ondalık.
- Frequency: Decimal, 3 ondalık. Severity: Whole number.
- (mln AZN) ölçüleri: Decimal, 1 ondalık.

## 4. Sayfa 1: Azərbaycan sığorta bazarı

1. **Card** × 4: `Premiums (mln AZN)`, `Claims Paid (mln AZN)`, `Payout Ratio`, `YoY %`.
   Her kartın **Filters** panelinde `Date[Year]` = 2026 seç.
2. **Line chart**: X ekseni `market_monthly[month_start]`, değerler
   `Monthly Premiums (mln AZN)` ve `Monthly Claims (mln AZN)`. Filtre yok, tüm
   2016-2026 görünsün. 2022 Ağustos-Eylül boş görünecek: bu bir hata değil, CBAR o
   ayları yayımlamadı.
3. **Clustered column chart**: X ekseni `Date[Quarter Label]` (Q1-24 gibi kısa
   etiket), değer `Payout Ratio`. Filtre: `Date[Year]` = 2024, 2025, 2026. X eksenine
   göre artan sırala. **Data labels** açık olsun.
4. **Table**: `insurer_quarterly[insurer]`, `insurer_quarterly[segment]`,
   `Premiums (mln AZN)`, `Segment Share`, `YoY %`, `Payout Ratio`. Filtreler:
   `Date[Year]` = 2026 ve `insurer_quarterly[licence_revoked]` = 0. `Premiums`'a göre
   büyükten küçüğe sırala. **Format > Totals** kapalı olsun: lisansı iptal edilen
   şirketler gizli olduğu için toplam satırı kartlarla tutmaz (%8,6 ve %7,9).
5. **Bar chart**: Y ekseni `class_quarterly[line_label]` (kısa etiketler), değer
   `Class Payout Ratio`. Bu görselin **Filters** panelinde `Date[Year]` = 2026 ve
   `line_code` için şunları seç: `C_MOTOR_TPL`, `V_MOTOR_KASKO`, `V_MEDICAL`, `V_FIRE`,
   `C_REAL_ESTATE`, `V_LIFE`. (`TOTAL`, `V_NONLIFE` gibi ara toplamları seçme, yoksa
   aynı prim iki kez sayılır.)

## 5. Sayfa 2: Portfel (poliçe səviyyəsi)

1. **Slicer** × 3: `Vehicle Type`, `Area`, `Channel` (2. adımdaki küçük tablolardan).
2. **Card** × 4: `Loss Ratio (Finished)`, `Loss Ratio` (filtre `Date[Year]` = 2018),
   `Loss Ratio (Written)` (filtre `Date[Year]` = 2018), `Renewal Rate`.
3. **Line chart** (ana hikaye): X ekseni `fact_portfolio[month_start]`, değerler
   `Loss Ratio` ve `Loss Ratio (Written)`. Filtre: `Date[Year]` = 2017, 2018. 2018'de
   iki çizgi ayrılır: yazılan prim bazındaki oran sıfıra yaklaşırken kazanılmış prim
   bazındaki oran daha yavaş düşer.
4. **Line chart**: X ekseni `fact_renewal[month_start]`, değer `Renewal Rate`.
5. **Clustered bar chart**: Y ekseni `Channel[channel]`, değerler
   `Loss Ratio (Finished)` ve `Renewal Rate`. Kanalları sadece bitmiş yıllar üzerinden
   karşılaştırmak için `Loss Ratio` değil `Loss Ratio (Finished)` kullanılıyor.
6. **Table**: `Date[Year]`, `Written Premium`, `Earned Premium`, `Earned Share`,
   `Loss Ratio (Written)`, `Loss Ratio`, `Frequency`, `Severity`. Filtre:
   `Date[Year]` = 2015-2018. Toplam satırı kapalı olsun: bitmiş yılları yarısı
   kazanılmış 2018 ile karıştırır.

## 6. Sayfa 3: Data keyfiyyəti

1. **Table**: `data_quality[area]`, `data_quality[check]`, `data_quality[rows]`,
   `data_quality[why]`. Metin kolonunda **Format > Values > Text wrap** açık olsun.
2. İsteğe bağlı: `market_anomalies` için **Table**, `z_flag` veya `iqr_flag` = True
   olan satırlar.

## 7. Kontrol: rakamlar README ile aynı mı?

Raporu bitirince şu değerleri kontrol et. Farklıysa en sık sebep: kolon tipi metin
kalmış, ilişki eksik ya da `class_quarterly` filtresiz toplanmış.

| Yer | Filtre | Beklenen |
|---|---|---|
| Sayfa 1 kartları | Year = 2026 | Premiums 1,248.5, Claims Paid 882.7, Payout Ratio 70.7% |
| Sayfa 1 kart `YoY %` | Year = 2026 | 7.9% (2026'nın 9 ayı, 2025'in aynı 9 ayı ile) |
| Sayfa 1 sütun grafiği | Q3-26 | Payout Ratio 87.4% |
| Sayfa 1 tablo, Paşa Sığorta | Year = 2026 | Premiums 308.9, Segment Share 56.8%, YoY 13.2% |
| Sayfa 2 kart `Loss Ratio (Finished)` | filtre yok | 63.9% |
| Sayfa 2 tablo | Year = 2018 | Loss Ratio (Written) 20.8%, Loss Ratio 39.7% |
| Sayfa 2 tablo | Year = 2017 | Loss Ratio 47.1%, Frequency 0.375 |
| Sayfa 2 kart `Renewal Rate` | filtre yok | 77.9% |
| Sayfa 2 kanal grafiği | filtre yok | Broker 70.2% / 73.1%, Agent 58.3% / 81.8% |

**YoY tuzağı.** `YoY %` kartında 7.9% yerine -17.0% görürsen `Date` tablosu 31 Aralık
2026'ya kadar gidiyor demektir. `SAMEPERIODLASTYEAR`, 2026'nın seçili bütün
tarihlerini bir yıl geri kaydırır. Tablo Aralık'a kadar uzanıyorsa 2025'in 12 ayı
gelir ve 2026'nın 9 ayı 2025'in 12 ayıyla karşılaştırılır. Çözüm: `Date` tablosunu
verinin son günü olan 30 Eylül 2026'da bitirmek (`DAX_measures.md` böyle). Mülakatta
anlatılacak iyi bir örnek: "YoY'un neyi neyle karşılaştırdığını her zaman kontrol ederim."

## 8. Ekran görüntüleri

README'deki görüntüler (`docs/images/powerbi_market.png`, `powerbi_portfolio.png`,
`powerbi_quality.png`) hazır rapordan alındı. Raporu kendin kurar ya da değiştirirsen,
her sayfanın görüntüsünü (**File > Export > Export to PDF** ya da ekran görüntüsü) aynı
adlarla kaydet. README güncel kalır.
