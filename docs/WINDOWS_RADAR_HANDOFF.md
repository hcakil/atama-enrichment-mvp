# Windows Claude — Atama Radar devir notu
Güncelleme: 13 Ekim 2026. Bu dosya herkese açık GitHub deposu içindir; **kişisel profil veya sır içermez**.

## Amaç ve yetki
Bu projede iki AYRI iş var: (A) bir aile üyesine yönelik **kişisel ve sessiz AGS/ÖABT + kamu personeli duyuru radarı**, (B) B2B kamu ilanı veri/tercih danışmanlığı satış deneyi. Windows'ta yalnızca **A** ile çalış. B'nin kodunu, durumunu, kampanyasını değiştirme. Hermes/API aboneliği, VPS, toplu scraping veya ücretli hizmet açma. Kullanıcı Windows Claude ile kod geliştirme ve testleri yapmayı onayladı; **canlı alıcıya bildirim, mesaj veya ödeme** onaysız yok.

## Mevcut kod tabanı
- Repo: https://github.com/hcakil/atama-enrichment-mvp (public), dal: main.
- CLI: `python -m atama_mvp.cli`, Python stdlib, `src/atama_mvp/`.
- Windows eski zamanlama: `AtamaMvpNightly`, `scripts/install-windows-task.ps1` ve `scripts/local-nightly.ps1`; yaklaşık 00:05'te `fetch --notify-telegram` çalışabilir.
- Bu eski görev **profil filtresiz** Telegram özeti gönderiyor. Güvenilir kişisel radar DEĞİL. Eski komutun başka hizmetlere etkisini not etmeden yenisini bağlama.
- Kaynaklar: Kariyer Kapısı RSS ve ayrıntı API; SBB ayrıntı bağlantılarında sorun; ilan.gov.tr erişimi/izin durumu belirsiz. İlk kapsamda ilan.gov.tr otomasyonunu ekleme.
- Bugünkü çıkarımda hatalar: kanun numarası 657'nin kontenjan olarak okunması, sınav saatinin son tarih sayılması, "Türkiye geneli"nin tek şehir gibi algılanması; eksik şartı eşleşme sayma; ilan yerine pozisyon bazlı kayıt tutmama; değişiklik/iptal geçmişi yok.
- Kariyer Kapısı yapılandırılmış alanlarını metin regex'inden ÖNCE tercih et: `basTarih`, `bitTarih`, `kontenjanList`, `degerlemeAsamaList`, `unvan`; alt ilanları ayrı pozisyon olarak işle.
- Kaynak belgeleri: `docs/ops-windows-nightly.md`, `docs/data-pipeline.md`, `docs/handoff-claude-review.md`, `docs/telegram-private-group.md`. **Uyarı:** Mac'ten yüklenmiş en güncel araştırma ZIP'inde `research/lines/radar.md` ve `research/lines/sales.md` var, ancak 13 Ekim itibarıyla GitHub main'de bu iki dosya henüz bulunmuyordu. Bu not Windows için kendi başına yeterli olacak şekilde yazılmıştır; eksik dosyaları varmış gibi varsayma.

## Gizlilik
Depo **public**. GERÇEK kişinin doğum tarihi, KPSS puanları, bölüm, yaş, telefon, sohbet kimlikleri, bot anahtarı, API anahtarı ve yerel veritabanı GitHub'a gönderilemez. Profil yerelde örn. `config/radar_profile.local.json`; gerçekteki değerleri yalnızca kullanıcının Windows oturumundan ve onayıyla al. `.gitignore`'a yerel profil/SQLite/log yollarını ekle; `.env` yazdırma veya modele sır taşımayı isteme. Testte sentetik aday profilleri kullan. Gerçek aday puanını bu dosyaya veya commit mesajına ekleme.

## Önce R0: eski bildirimi güvenli şekilde durdur
1. Windows'ta doğru repo klasörüne geç, `git status --short` ve Git remote'u kontrol et; var olan `.env` ve yerel DB'yi silme.
2. Aşağıdaki komutlar yalnızca **AtamaMvpNightly** görevi varsa uygulanır:
```powershell
Get-ScheduledTask -TaskName AtamaMvpNightly -ErrorAction SilentlyContinue
Get-ScheduledTaskInfo -TaskName AtamaMvpNightly -ErrorAction SilentlyContinue | Select-Object LastRunTime,LastTaskResult,NextRunTime
Disable-ScheduledTask -TaskName AtamaMvpNightly
Get-ScheduledTask -TaskName AtamaMvpNightly | Select-Object TaskName,State
```
3. Başka görevleri durdurma. Çıktıda token/ID veya sır gösterme. Görev zaten yoksa yalnızca raporla.
4. Eski `TELEGRAM_CHAT_ID` birden fazla sohbet içeriyor olabilir. Hiçbir mevcut sohbeti 'gölge test' alıcısı olarak güvenli kabul etme; **ayrı bot + ayrı, yalnız operatöre ait test sohbeti** kullan.
5. R0'dan sonra kullanıcıya kısa durum raporu yaz.

## Ayrı radar tasarımı
- `src/atama_mvp/radar/` veya mevcut pakete uyumlu **ayrı modül**, ayrı SQLite, ayrı yapılandırma, ayrı bot.
- Önce **AGS duyuru radarı**: MEB Akademi RSS, MEB Personel duyuruları, ÖSYM resmî AGS/ÖABT duyuruları. Kaynak ve sayfa yapısını canlı kontrol et; RSS mevcut değilse uydurma adres kullanma. Link/başlık kimliğiyle tekrarları ayıkla; başlık + resmî kaynak bağlantısını taşı.
- Sonra **KPSS / sınavsız pozisyon radarı**: ilan→alt ilan→pozisyon; sınav yılı ve türü, taban puan, mezuniyet/nitelik kodu, yaşın hangi tarihte hesaplandığı, sertifika/ehliyet ve kontenjanı kaynaklarıyla denetle.
- Şart başına: `sagliyor | saglamiyor | belirtilmemis | okunamadi`. Genel sonuç `uygun | muhtemel | belirsiz | uygunsuz`. `belirtilmemis` hiçbir zaman kendiliğinden `uygun` olamaz. Tereddütte yanlış 'kesin uygun' iddiası verme, ama muhtemel gerçek fırsatları sessizce eleme.
- Değişiklik, iptal ve uzatma takibi. Kaynak hata/eksikliği 'yeni ilan yok' diye raporlanmaz.
- Modlar: `shadow` (operatöre etiketli çıktı, son kullanıcıya sıfır mesaj) ve `live` (yalnız ayrıca izin ve başarı kapıları sonrası).
- Planlanan Windows görevi günde 2 kez 08:00/18:00, oturum kapalıyken çalışabilmeli; start-when-available, log döndürme, arıza uyarısı; uyanık PC ve TR bağlantısı. Oturum kapalıyken çalışmayı gerçekten deneyerek doğrula.

## Test ve canlıya geçiş kapıları
- En az 50 etiketlenmiş pozisyon; en az 2 sentetik test profili.
- P3 sınır, P1/P2 alternatif puan türü, puan yılı, yaş son başvuru tarihi, özel bölüm, sertifika/ehliyet yok/bilinmiyor, PDF okunamadı, Türkiye geneli, çoklu pozisyon, 657 kanun numarası, tarih-saat karışması.
- Hedef: kaçırılan uygun/muhtemel örnek **0**; yanlış kesin uygun en çok %10. Ölçümde altın kümeye ve kaynak kapsamına ilişkin sınırlamayı belirt.
- 14 gün **shadow** ve hedef kaynak başarısı %95+; shadow'da son kullanıcıya **0** mesaj testle ispatlanmalı.
- AGS duyuruları daha az riskli olsa da öneri 5 gün shadow; KPSS eşleşmesi 14 gün shadow; her iki canlıya geçiş de **ayrı açık onay** gerektirir.

## Çalışma sırası ve çıktı
1. R0 durum ve gerekiyorsa mevcut görevi durdur.
2. Repo/Windows/Python/Task Scheduler sağlık denetimi; mevcut veriyi bozma.
3. Teknik değişiklikleri küçük commit'lere ayır, test ekle.
4. Ayrı bot/profil için kullanıcının yerelde yapacağı kurulum adımlarını hazırla, tokenları isteme veya loglama.
5. AGS'yi shadow moduna al; KPSS için altın kümeyi doğrula; 14 günlük shadow'u başlat.
6. Kullanıcıya değişen dosyaları, testleri, kalan riskleri, kurulu görevleri, sonraki kararı özetle.

Bir sorunla karşılaşınca diğer hat üzerinde çalışmaya geçme; eksik kanıtı raporla. GitHub main dalı Mac'ten gelen ZIP'ten geri olabilir; **git pull** ile son araştırma belgelerinin geldiğini varsayma.
