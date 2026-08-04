# Atama Enrichment MVP

Konum: `/Users/hazimrentready/VSCodeProjects/atama-enrichment-mvp`

Kariyer Kapısı **resmi RSS** + SBB **kamuilan** listesini çeker, normalize eder, **insan onayına** bırakır.

Bildirio kopyası değil. Onların API’sini kullanmaz.

## Basit akış (bunu aklında tut)

```text
1) Cron her gece kaynaklara bakar
2) Yeni ilan görürse → "aday" olarak kaydeder (pending)
3) Telegram'a "şu kadar yeni aday var" yazar  ← seni uyandırır
4) Sen `review` ile onaylarsın
5) Onaylananlar export edilir
```

**Telegram bildirimi nedir?**  
Kullanıcıya app push değil. **Sana / ekibe** giden kısa mesaj: “Bu gece 7 yeni ilan adayı çıktı, linkleri şöyle…”. Sonra sen `review` ile bakarsın. Otomatik yayın yok.

## Neden şimdilik Firebase değil?

Firebase Cloud Functions bu MVP için fazla ağır (Python + Scheduler + secret + deploy).  
İlk adım: **GitHub Actions cron** — ücretsiz, zaten bildiğin tooling, 5 dakikada ayağa kalkar.

Firebase’e geçmek istersen sonraki adım: Cloud Scheduler → Cloud Run/Functions. Şart değil.

## Kurulum

```bash
cd ~/VSCodeProjects/atama-enrichment-mvp
export PYTHONPATH=src
```

Harici paket yok (stdlib).

## Komutlar

```bash
# Kaynakları çek
python3 -m atama_mvp.cli fetch --source all

# Yeni aday varsa Telegram at (env gerekir)
python3 -m atama_mvp.cli fetch --source all --notify-telegram

# Durum
python3 -m atama_mvp.cli status

# İnsan onayı
python3 -m atama_mvp.cli review --limit 10

# Onaylıları dışa aktar
python3 -m atama_mvp.cli export --status approved --out data/approved.json

# Telegram test
python3 -m atama_mvp.cli notify-test
```

### Telegram kurulumu (opsiyonel, 3 dk)

1. Telegram’da [@BotFather](https://t.me/BotFather) → `/newbot` → **token** al  
2. Bota bir mesaj at; sonra `https://api.telegram.org/bot<TOKEN>/getUpdates` ile **chat_id** bul  
3. Shell’de:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
python3 -m atama_mvp.cli notify-test
```

## Cron (GitHub Actions)

Dosya: `.github/workflows/nightly-fetch.yml`  
Zaman: her gün **00:05 TR** (`cron: "5 21 * * *"` UTC)

```bash
cd ~/VSCodeProjects/atama-enrichment-mvp
git init   # henüz yoksa
# GitHub'a repo açıp push et
# Settings → Secrets → TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (opsiyonel)
```

Actions → “Nightly fetch” → **Run workflow** ile hemen test edebilirsin.

Not: Actions her seferinde temiz makine açar; SQLite artifact olarak saklanır. Kalıcı DB istersen sonra Firestore/Postgres ekleriz.

## Kaynaklar

| Kaynak | Endpoint |
|--------|----------|
| Kariyer Kapısı | `https://kariyerkapisi.gov.tr/RSS` |
| SBB Kamu İlan | `https://kamuilan.sbb.gov.tr/` |

## Sonraki adımlar

1. Telegram botunu bağla + `notify-test`  
2. Repo’yu GitHub’a push et → cron çalışsın  
3. (İleride) Detay tarihi parse / Firebase’e taşıma
