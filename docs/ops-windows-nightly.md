# Windows nightly ops checklist

Her gece **00:05** `AtamaMvpNightly` görevinin KK + SBB + ilan + Gemini enrich + Telegram digest üretmesi için.

## İlk kurulum / pull sonrası

```powershell
cd C:\src\atama-enrichment-mvp   # kendi path'iniz
git pull
copy .env.example .env           # yoksa
notepad .env
python -m pip install -r requirements.txt
```

`.env` zorunlu anahtarlar (değerleri commit etme):

| Key | Not |
|-----|-----|
| `TELEGRAM_BOT_TOKEN` | BotFather; sadece bu makinede |
| `TELEGRAM_CHAT_ID` | **Private group** id (negatif) — [telegram-private-group.md](telegram-private-group.md) |
| `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` | Mac + Windows aynı DB |
| `GEMINI_API_KEY` | Detail PDF/HTML structured extract |
| `GEMINI_MODEL` | varsayılan `gemini-2.5-flash` |
| `ATAMA_LLM_FORCE` | `1` = her detayda Gemini (free tier ~5 RPM → uzun koşu) |

Smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\probe-sources.ps1
$env:PYTHONPATH="src"
python -m atama_mvp.cli notify-test
python -m atama_mvp.cli status --recent 5
```

Görev:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-windows-task.ps1
Start-ScheduledTask -TaskName AtamaMvpNightly
Get-Content .\logs\local-nightly.log -Wait
```

Power Options → Sleep = **Never**. Kapalı/uykuda job kaçar.

## Kalite izleme (sabah 2 dk)

1. Telegram private group’ta gece digest’lerine bak.
2. `python -m atama_mvp.cli status --recent 10` — `enrich_status=detail`, `confidence`, KPSS/yaş alanları.
3. Kırmızı bayraklar: yaş 65 gibi absürt değerler, KK’de KPSS yokken “var”, SBB soft-404, Gemini 429 / uzun boşluk.
4. B2B demo için ham bot değil:

```powershell
python -m atama_mvp.cli export-feed --status all --min-confidence 0.45 --demo --out data/demo/feed
```

Detay: [b2b-feed-and-demo.md](b2b-feed-and-demo.md).
