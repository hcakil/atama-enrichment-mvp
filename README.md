# Atama Enrichment MVP

Kariyer Kapısı **resmi RSS** + SBB **kamuilan** listesini çeker, normalize eder, **insan onayına** bırakır.

Bildirio kopyası değil. Onların API’sini kullanmaz.

## Basit akış

```text
1) Cron her gece kaynaklara bakar
2) Yeni ilan görürse → "aday" olarak kaydeder (pending)
3) Telegram'a "şu kadar yeni aday var" yazar
4) Sen `review` ile onaylarsın
5) Onaylananlar export edilir
```

**Telegram bildirimi nedir?**  
Kullanıcıya app push değil. Operatöre / ekibe giden kısa mesaj: “Bu gece N yeni ilan adayı…”. Sonra `review` ile bakılır. Otomatik yayın yok.

## Neden şimdilik Firebase değil?

Firebase Cloud Functions bu MVP için fazla ağır.  
İlk adım: **GitHub Actions cron**.

## Kurulum

```bash
export PYTHONPATH=src
```

Harici paket yok (stdlib). Secret’ları asla commit etme (repo public).

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

### Telegram (local)

1. [@BotFather](https://t.me/BotFather) → `/newbot` → token al  
2. Bota bir mesaj at; `getUpdates` ile `chat_id` bul  
3. Shell’de (değerleri chat’e / commit’e yazma):

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
python3 -m atama_mvp.cli notify-test
```

### Telegram (GitHub Actions — public repo)

Repo → **Settings → Secrets and variables → Actions** → iki secret ekle:

| Secret adı | Değer |
|------------|--------|
| `TELEGRAM_BOT_TOKEN` | BotFather token |
| `TELEGRAM_CHAT_ID` | chat id |

Kod ve workflow sadece `secrets.*` okur; token README’ye veya issue’ya yazılmaz.

## Cron (GitHub Actions) — hibrit

Dosya: `.github/workflows/nightly-fetch.yml`  
Zaman: her gün **00:05 TR** (`cron: "5 21 * * *"` UTC)

**Hibrit model (şu an):**
- **GitHub Actions** → sadece Kariyer Kapısı (`--source kk`) + Telegram  
- **Lokal (TR IP)** → SBB: `python3 -m atama_mvp.cli fetch --source sbb --notify-telegram`

Sebep: `kamuilan.sbb.gov.tr` GitHub’ın yurtdışı/bulut IP’lerinden sık timeout veriyor; senin makineden açılıyor.

Actions → “Nightly fetch” → **Run workflow** ile test (~birkaç saniye sürmeli).

Not: Actions her seferinde temiz makine; SQLite artifact olarak saklanır.

## Kaynaklar

| Kaynak | Endpoint |
|--------|----------|
| Kariyer Kapısı | `https://kariyerkapisi.gov.tr/RSS` |
| SBB Kamu İlan | `https://kamuilan.sbb.gov.tr/` |

## Sonraki adımlar

1. Telegram secrets (local env + GitHub Secrets)  
2. `notify-test` + Actions “Run workflow”  
3. (İleride) diğer resmi kaynaklar / kalıcı DB
