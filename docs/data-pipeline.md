# Data pipeline — sources, formats, central dump

## Bugün ne çekiyoruz?

| Kaynak | Nerede çalışır | Ne alınır | Detay içerik |
|--------|----------------|-----------|--------------|
| **Kariyer Kapısı** | Windows (TR) + cloud OK | RSS liste kartı | Link çalışır (`IlanDetay?i=…`) |
| **SBB kamuilan** | Windows (TR) only | Ana sayfa carousel kartı | `ilanDetay.aspx?kod=…` şu an **soft-404** (site); Telegram’da liste URL’si |
| **ilan.gov.tr** | Cloud Actions | `AdsByFilter` liste + `GetAdDetail` HTML | Detay API ile şart metni parse edilebilir |

## Nerede tutuluyor?

```text
Windows PC                         GitHub Actions
─────────                          ──────────────
data/mvp.sqlite3  (local)          ephemeral runner DB + artifact
data/central/listings.jsonl        (manuel/opsiyonel export)
     │
     └─ şimdilik makine-yerel “kaynak gerçeği” (SBB için şart)
```

SQLite şema: `listings` + `enrichment_drafts` + `review_events`  
([`store.py`](../src/atama_mvp/store.py))

Canonical satır (`export-central`):

```json
{
  "schema": "atama_mvp.central_listing.v1",
  "fingerprint": "sbb_kamuilan:abc…",
  "source": "sbb_kamuilan",
  "title": "…",
  "institution_name": "…",
  "external_url": "https://kamuilan.sbb.gov.tr/",
  "application_window": "…",
  "review_status": "pending",
  "draft": { },
  "raw": { }
}
```

```bash
export PYTHONPATH=src
python3 -m atama_mvp.cli export-central --status all --out data/central/listings.jsonl
```

Windows nightly bu export’u her koşudan sonra yazar.

## Neden Telegram’da sadece “link” vardı?

1. Digest şu ana kadar liste kartı alanlarını yazıyordu (başlık + URL).  
2. SBB detay sayfası içerik vermiyor (404) → şartname parse edilemiyor.  
3. `ilan.gov` detay enrichment (`inspect-ilan` / `StructuredCriteria`) henüz nightly Telegram’a bağlanmadı.

## SBB 404

Doğrulandı: ana sayfadan taze `kod=` linkleri bile soft-404 HTML dönüyor. Bizim encode hatası değil; SBB tarafı. Geçici çözüm: Telegram’da ana liste + kurum/başlık/süre.

## Merkezi data — yol haritası

1. **Şimdi (yapıldı):** her makinede aynı JSONL şeması (`export-central`).  
2. **Kısa vadede:** Windows `data/central/` klasörünü OneDrive/Dropbox ile paylaş **veya** gece JSONL’i private GitHub Release / R2’ye yükle.  
3. **Orta vadede:** tek remote DB (Turso / Postgres / Firestore) — Windows + Actions aynı `DATABASE_URL`’e yazar.  
4. **Sonra:** detay enrichment (`StructuredCriteria`) → review → kullanıcı eşleştirme.

Önerilen varsayılan: Windows = SBB+KK yazarı; Actions = `ilan` yazarı; ikisi de aynı central JSONL/DB şemasına export eder.
