# Telegram private group (çoklu erişim)

Bot “takip edilmez”. 2–5 kişi için tek private group + tek bot.

## Kurulum

1. Telegram’da **private group** oluştur (örn. `Atama digests`).
2. Botu gruba **üye** ekle (admin olması şart değil; mesaj atabilmeli).
3. Grupta herhangi bir mesaj yaz (bot `getUpdates` görsün).
4. Chat id al:

```bash
export PYTHONPATH=src
python3 -m atama_mvp.cli telegram-chats
```

Çıktıdaki **group** satırındaki `chat_id` (genelde negatif, örn. `-100…`) değerini kopyala.

5. Mac + Windows `.env`:

```bash
TELEGRAM_BOT_TOKEN=...          # asla paylaşma / commit etme
TELEGRAM_CHAT_ID=-1001234567890 # group id
```

Birden fazla hedef (nadiren): virgülle ayır — bot her id’ye aynı mesajı yollar:

```bash
TELEGRAM_CHAT_ID=-1001234567890,123456789
```

6. Test:

```bash
python3 -m atama_mvp.cli notify-test --message "Atama digests group OK"
```

7. Partner’ları **sadece gruba** davet et. Token, `.env`, Turso, deploy **verme**.

## Güvenlik

| Yap | Yapma |
|-----|--------|
| Token sadece runner `.env` / secrets | Token’ı chat/email/git |
| Erişim = grup üyeliği | Partner’a BotFather |
| Revoke = gruptan çıkar | Public channel |

Ops triage: gruba pin “take / skip / deadline check”. Ham bot demo için: [b2b-feed-and-demo.md](b2b-feed-and-demo.md).
