# Canliya Alma Rehberi

Bu proje Django tabanli oldugu icin GoDaddy bu planda domain/DNS tarafinda kullanilir. Uygulamayi Render uzerinde calistirip GoDaddy'deki domaini Render'a yonlendirmek en kontrollu yoldur.

## 1. Kod deposu

1. `.env`, `db.sqlite3`, `media/`, `venv/` ve `staticfiles/` dosyalarini GitHub'a yukleme.
2. Kodu GitHub reposuna gonder.
3. Render'a GitHub hesabini bagla.

## 2. Render deploy

1. Render Dashboard'da New Blueprint Instance sec.
2. Bu repoyu sec. Klasor kokundeki `render.yaml` web servisini ve PostgreSQL veritabanini olusturur.
3. Ilk deploy oncesi Render servisinin Environment bolumunde su degerleri doldur:
   - `DOMAIN`: GoDaddy'deki alan adin, ornek `siteniz.com`
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`
   - `GEMINI_API_KEY` (AI destek sohbetinde gerçek LLM yanıtı için ana sağlayıcı)
   - `GEMINI_SUPPORT_MODEL` (opsiyonel, varsayılan: `gemini-3.5-flash`)
   - `OPENAI_API_KEY` (opsiyonel yedek AI sağlayıcı)
   - `OPENAI_SUPPORT_MODEL` (opsiyonel, varsayılan: `gpt-4.1-mini`)
4. Render deploy tamamlandiginda verilen `*.onrender.com` adresinden siteyi kontrol et.

## 3. GoDaddy DNS

Render'da servis ayarlarindan Custom Domains bolumune once `siteniz.com`, sonra `www.siteniz.com` ekle.

GoDaddy Domain Portfolio icinde domainini ac, DNS bolumune gir ve asagidaki kayitlari hazirla:

| Type | Name | Value |
| --- | --- | --- |
| A | @ | 216.24.57.1 |
| CNAME | www | Render servis adresin, ornek `corelogic-store.onrender.com` |

Varsa ayni `@` veya `www` icin baska web yonlendirme kayitlarini kaldir. Render, `AAAA` kayitlarinin da kaldirilmasini onerir.

DNS degisikligi genelde kisa surede yayilir ama kuresel olarak 48 saate kadar surebilir. Render Custom Domains ekraninda Verify butonuyla dogrula.

## 4. Ilk yayin kontrolu

1. `https://siteniz.com` ve `https://www.siteniz.com` aciliyor mu?
2. `/admin/` sayfasi aciliyor mu?
3. Kayit/giris akisi calisiyor mu?
4. Urun ve kategori gorseli yuklenince Cloudinary uzerinden gorunuyor mu?
5. Sepete ekleme ve checkout sayfasi hata vermiyor mu?

Admin kullanicisini Render Shell uzerinden olustur:

```bash
python manage.py createsuperuser
```

Domain ve HTTPS birkac gun sorunsuz calistiktan sonra daha siki HSTS icin su degerler acilabilir:

```env
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

Bunu ancak tum alt alan adlarinin HTTPS ile calisacagindan emin olduktan sonra yap.

## 5. Bilerek ertelenen temizlikler

`staticfiles/` klasoru daha once Git'e alinmis. Bu deployu engellemez, ama sonraki temizlikte Git takibinden cikarilmasi iyi olur. Once canliya alma akisini dogrulamak daha guvenli.
