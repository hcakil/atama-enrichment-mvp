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

# ilan.gov detay inceleme (Telegram yok; research dump → data/inspect/)
python3 -m atama_mvp.cli inspect-ilan --id 2188158
# veya listedeki ilk ilan:
python3 -m atama_mvp.cli inspect-ilan

# Bildirio public referans snapshot (→ data/refs/, gitignore)
python3 scripts/snapshot_bildirio_refs.py

# Yeni aday varsa Telegram at (env gerekir)
python3 -m atama_mvp.cli fetch --source all --notify-telegram

# Durum
python3 -m atama_mvp.cli status

# İnsan onayı
python3 -m atama_mvp.cli review --limit 10

# Onaylıları dışa aktar
python3 -m atama_mvp.cli export --status approved --out data/approved.json

# Merkezi JSONL dump (paylaşılabilir şema)
python3 -m atama_mvp.cli export-central --status all --out data/central/listings.jsonl

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

## Cron — kullanılmayan Windows PC (önerilen, sıfır maliyet + TR IP)

Evde boşta duran Windows makine TR ISP IP’si ile SBB’yi açabilir (`ilan.gov` cloud’da kalabilir).

1. **Python 3** kur ([python.org](https://www.python.org/downloads/)) — **Add to PATH** işaretle; PowerShell’i yeniden aç.  
2. Repoyu klonla, `.env` oluştur (commit etme):

```powershell
cd C:\src
git clone https://github.com/hcakil/atama-enrichment-mvp.git
cd atama-enrichment-mvp
copy .env.example .env
notepad .env
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_CHAT_ID=...
```

3. IP / SBB testi:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\probe-sources.ps1
# beklenen: kariyer_kapisi + sbb_kamuilan http=200, ok_sources=2/2
```

4. Görev zamanlayıcı (her gün **00:05**):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows-task.ps1
Start-ScheduledTask -TaskName AtamaMvpNightly
Get-Content .\logs\local-nightly.log -Wait
```

5. **Uyku = Never** (Power Options). Kapalı/uykuda job kaçırır.

Ne olur?
- Önce **KK** → Telegram 1  
- Sonra **SBB** → Telegram 2  
- Log: `logs\local-nightly.log`  
- `ilan` bu script’te yok (bilinçli; cloud Actions’ta)

### Cron — lokal Mac (opsiyonel)

GitHub’ın bulut IP’si SBB’yi sık timeout’a düşürüyor. Gece işi **senin Mac’inden** (TR IP) gitsin:

1. `.env` oluştur (commit etme):

```bash
cp .env.example .env
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_CHAT_ID=...
```

2. LaunchAgent kur (her gün **00:05** yerel saat):

```bash
chmod +x scripts/*.sh
./scripts/install-local-launchd.sh
```

3. Hemen bir kez dene:

```bash
launchctl kickstart -k "gui/$(id -u)/com.hcakil.atama-mvp.nightly"
tail -f logs/local-nightly.log
```

Ne olur?
- Önce **KK** çekilir → Telegram rapor 1  
- Sonra **SBB** çekilir → Telegram rapor 2  
- Biri fail olsa diğeri yine çalışır (ayrı process)  
- Log: `logs/local-nightly.log`

Mac uyku / kapalıysa o gece job kaçabilir — uzun vadede TR VPS / self-hosted runner daha stabil.

### VPS notu (sıfır maliyet vs TR IP)

Kalıcı **ücretsiz + güvenilir Türkiye IP** pratikte yok. Karar ağacı:

1. **$0 deneme:** Oracle Always Free (EU home region mümkünse) → VPS’te `./scripts/probe-sources.sh`  
   - SBB **200** → ücretsiz bulut yeter, TR şart değil  
   - SBB **timeout** → TR lokasyon şart  
2. **Ucuz TR VPS** (~aylık birkaç USD, örn. Turhost Istanbul): cron + Telegram; stabil yol  
3. “Bedava VDS Türkiye” reklam siteleri → genelde güvenilmez, önerme

```bash
chmod +x scripts/probe-sources.sh
./scripts/probe-sources.sh
```

### GitHub Actions (opsiyonel smoke)

Schedule **kapalı** (çift Telegram olmasın). İstersen Actions → “Nightly fetch” → **Run workflow** ile sadece cloud KK testi.

## Kaynaklar

| Kaynak | Endpoint |
|--------|----------|
| Kariyer Kapısı | `https://kariyerkapisi.gov.tr/RSS` |
| SBB Kamu İlan | `https://kamuilan.sbb.gov.tr/` |
| ilan.gov.tr | `POST …/Ad/AdsByFilter` (personel `txv` kategorileri) |

Veri akışı / merkezi dump: [docs/data-pipeline.md](docs/data-pipeline.md)  
ilan.gov detay sınıflandırma: [docs/classify-matrix-ilan-gov.md](docs/classify-matrix-ilan-gov.md)

### Turso (tek remote DB)

`.env` / GitHub Secrets:

```bash
TURSO_DATABASE_URL=libsql://...
TURSO_AUTH_TOKEN=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

`TURSO_*` doluysa Windows + Mac + Actions **aynı** DB’ye yazar (`Store` otomatik seçer).

## Sonraki adımlar

1. Telegram secrets (local env + GitHub Secrets)  
2. `notify-test` + Actions “Run workflow”  
3. (İleride) diğer resmi kaynaklar / kalıcı DB
