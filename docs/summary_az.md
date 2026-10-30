# Sığorta analitikası: Azərbaycan bazarı və avtomobil sığortası portfeli

**Qısa xülasə (1 səhifə)** - Vüqar Mirzoyev, oktyabr 2026

## Biznes sualı

Azərbaycan sığorta bazarında nə dəyişir və şirkət öz portfelinin gəlirliliyini necə
düzgün ölçməlidir? Layihə iki hissədən ibarətdir:

1. **Bazar:** Mərkəzi Bankın 2016-2026-cı illər üzrə rəsmi aylıq statistikası
   (sığortaçılar və sığorta sinifləri üzrə haqlar və ödənişlər).
2. **Portfel:** real avtomobil sığortası portfeli (İspaniya, 105 555 polis-il,
   2015-2018). Burada zərər əmsalı, tezlik, orta zərər və yenilənmə səviyyəsi polis
   səviyyəsində hesablanır.

## Əsas nəticələr

**Bazar: 2026-cı ilin 9 ayı, 2025-ci ilin eyni dövrü ilə müqayisədə**

- Sığorta haqları 7,9% artıb (1 248,5 mln AZN), ödənişlər isə 29,1% (882,7 mln AZN).
  Ödəniş əmsalı 59,1%-dən 70,7%-ə qalxıb.
- Ödənişlərin 73%-i (643,4 mln AZN) həyatın yaşam sığortasına aiddir. Bu, zərər
  deyil: müddəti bitən yığım müqavilələri üzrə ödənişlərdir. İyun aylarında görünən
  sıçrayışlar da buradan gəlir.
- Qeyri-həyat sığortasında da xərclər artır. KASKO üzrə ödəniş əmsalı 43,1%-dən
  54,6%-ə, icbari avto məsuliyyət üzrə 73,5%-dən 78,8%-ə yüksəlib.
- PAŞA Sığorta qeyri-həyat sığortaçılarının haqlarının 56,8%-ni toplayır (2016-cı
  ildə 29,5%).
- Mətbuatda 2026-cı ilin I rübü kimi təqdim olunan "399,1 mln AZN haqq və 164 mln AZN
  ödəniş" rəqəmi əslində 2025-ci ilin I rübünə aiddir. 2026-cı ilin I rübündə bu
  rəqəmlər 417,8 və 218,5 mln AZN olub.

**Portfel**

- Hələ bitməmiş polis illəri hesablanmış haqqa bölünəndə zərərsiz görünür. 2018-ci
  il üçün zərər əmsalı hesablanmış haqq əsasında 20,8%, qazanılmış haqq əsasında isə
  39,7%-dir (2017: 47,1%). Qalan fərq hələ bildirilməmiş zərərlərlə (IBNR) uyğundur.
- Broker kanalı agent kanalından həm az gəlirli (zərər əmsalı 70,2% və 58,3%), həm
  də müştərini az saxlayır (yenilənmə 73,1% və 81,8%).
- Yenilənmə səviyyəsi hər il artıb: 73,1%, 77,2% və 79,3%.

**Data keyfiyyəti:** 17 yoxlama hər dəfə avtomatik işləyir. Məsələn, Mərkəzi Bankın
6.1 cədvəlindəki yekun sətir 2024-cü ilə qədər lisenziyası ləğv edilmiş AtaSığortanı
daxil etmir (ildə 22,4 mln AZN-ə qədər). 2022-ci ilin yanvar-avqust sütunu yoxdur.
Portfeldə 404 polisin ləğv tarixi dövrün başlanğıcından əvvəldir. Hər problem üçün
test yazılıb.

## Tövsiyələr

1. Gəlirliliyi ödəniş əmsalı ilə deyil, qazanılmış haqq və ehtiyatların dəyişməsi
   daxil olmaqla zərər əmsalı ilə izləmək. Yeni dövrlərin nəticələrinə IBNR əlavə
   olunana qədər ehtiyatla baxmaq.
2. Bazar monitorinqində həyat sığortası üzrə yığım ödənişlərini qeyri-həyat
   zərərlərindən ayrı göstərmək.
3. KASKO və icbari avto məsuliyyət üzrə ödəniş əmsalını aylıq izləmək və illik artım
   üzrə sadə anomaliya qaydası (IQR) ilə işarələmək.
4. Öz portfelində kanal üzrə zərər əmsalı və yenilənməni birlikdə yoxlamaq. İspaniya
   portfelində broker kanalı hər iki göstəricidə zəifdir.
5. Yenilənmə səviyyəsini yalnız yenilənmə tarixi çatmış polislər üzrə hesablamaq.

## Məhdudiyyətlər

Mərkəzi Bankın rəqəmləri operativ məlumatdır: ödənilmiş zərərləri göstərir,
ehtiyatları yox. Portfel İspaniyaya aiddir və valyutası göstərilməyib. 2026-cı ilin
IV rübü üçün proqnoz (haqlar təxminən 347, ödənişlər təxminən 330 mln AZN) sadə baza
xəttidir, büdcə deyil.

**Alətlər:** Python (pandas), SQL (SQLite: CTE, window functions), pytest, Power BI (DAX).
