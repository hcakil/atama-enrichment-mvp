# B2B feed + partner demo

## Ekmek (özet)

- **Primary:** dağıtım app’lerine / koçlara **zenginleştirilmiş read-only feed** (JSON/CSV). Bildirio API’sine yazma.
- **Secondary (sonra):** profil filtresi + eşleşmeli Telegram alert (`match-alert`).
- Ham Telegram botunu “adama gösterme” — kaynaklar, format ve enrichment derinliği kopyalanır.

## Partner’a ne gösterilir?

Önceden enrich edilmiş, iç kanıt/prompt’suz sample:

```bash
export PYTHONPATH=src
python3 -m atama_mvp.cli export-feed \
  --status all \
  --min-confidence 0.45 \
  --demo \
  --limit 50 \
  --out data/demo/feed
```

Üretir:

- `data/demo/feed.json` — satırlar
- `data/demo/feed.csv` — aynı alanlar
- `data/demo/feed.metrics.json` — coverage / kaynak dağılımı / conf histogramı

Konuşma dili: “manuel giriş günlerini kısaltıyoruz” → pilot ücret veya revenue share. Equity için screenshot turu yok.

## Production / pilot feed (redact yok)

```bash
python3 -m atama_mvp.cli export-feed --status approved --min-confidence 0.5 --out data/feed/pilot
```

Pilot SLA: günlük refresh, min confidence, kaynak listesi (KK / SBB / ilan.gov).

## Eşleşmeli alert (secondary)

```bash
cp examples/alert-profile.example.json data/alert-profile.json
# iller / eğitim / yaş / kpss düzenle
python3 -m atama_mvp.cli match-alert --profile data/alert-profile.json --notify-telegram
```

Sadece profile uyan ilanlar digeste girer; gürültülü “her ilanı bas” bot değildir.
