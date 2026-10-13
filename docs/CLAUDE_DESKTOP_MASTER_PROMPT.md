# Claude Desktop — ana görev / master prompt (Mac)
Tarih: 13 Ekim 2026

Bu görev, aynı anda üç **birbirinden bağımsız** işin koordinasyonudur: (1) eşimin AGS/KPSS radarı, (2) iki kaynaklı B2B demo + CRM/satış, (3) kurumsal tek sayfa web sitesi. Windows planını iptal ettik; **her şey Mac'teki Claude Desktop/Claude Code tarafından**, ayrı çalışma klasörlerinde yürütülecek.

Önce `docs/ACTIVE_HANDOFF_MAC.md` belgesinin tamamını oku. `research/lines/radar.md`, `research/lines/sales.md`, `research/sales-sprint-plan.md` ve `docs/SALES_SITE_AND_DEMOS_BRIEF.md` ile birlikte mevcut dosyaları denetle. macOS üzerinde gerçek dosya/Terminal/Git izinlerine erişebildiğini **önce doğrula**. Desktop doğrudan yerel kod çalıştıramıyorsa yüklü ve izinli Claude Code aracını kullanmak için net adımı bildir; erişimin varmış gibi yapma.

**Birincil güvenlik görevi (R0):** `com.hcakil.atama-mvp.nightly` isimli filtrelenmemiş Telegram gönderen eski LaunchAgent Mac'te aktif mi kontrol et. Varsa yalnız o görevi durdur, ilgisiz işleri bozma. Gizli anahtarları çıktı/log/committe gösterme.

Sonrasında bağımsız işler:
- **Radar:** önce sadece resmî AGS/ÖABT duyuruları, ayrı modül/SQLite, AGS shadow, sonra KK yapısal pozisyon çıkarma ve şart motoru, altın test kümesi, KPSS shadow, macOS launchd 08.00/18.00 + uyku/uyanma telafi. Kişisel gerçek profil yalnız yerel ve gitignored. Eski filtrelenmemiş Telegram mesajlarını eşime gönderme; 5/14 günlük test bitmeden canlı bildirim yok.
- **Demo 1:** ÖSYM 2025/2 gerçek resmî kadro tablolarından ve kurgusal profilden kaynak ve sayfa numaralı tercihe uygunluk PDF'i; en az 10 satırın görsel doğrulaması. Sahte kadro/sahte güncel ilan yazma.
- **Demo 2:** KK'den güncel beş farklı pozisyonun yapısal API + resmî ilan/kurum duyurusu çapraz kontrolü; PDF. Hataları gerçekten kanıtla; bizim eski scraper hatamızı rakiplerin hatası olarak sunma.
- **Stüdyo sitesi:** B2B yazılım/veri otomasyon hizmetleri için bir single-page landing. Domain ve marka henüz seçilmedi. `loiai.online` mevcut LOI ürünüyle çalışıyor; siteyi bozmadan yeni **ayrı** repo ve CI planı çıkar. Mock/sentetik demo önizlemeleriyle yerel preview üret; kamuya açık demo ve production deploy için onay iste. CI GitHub Actions ile lint/test/build + hosting deployment; Claude ajanlarının API üzerinden sürekli CI'da çalışması şart değil, planlama/kod Claude Desktop'ta. Kurumsal e-posta için tarafsız marka/domain ve sağlayıcı alternatiflerini karşılaştır, satın alma yapma.

**Yürütme biçimi:** Eğer alt ajanlar mevcutsa iş kollarına dağıt; hiçbir iki ajan aynı dosyayı eşzamanlı değiştirmesin. Site ayrı repo, radarı mevcut repoda yeni modül, raporları `research/demos/` klasöründe tut. Verimli modeller kullan, kullanım sınırına yaklaşırsa checkpoint yaz. Site çalışmalarını engelleyen domain seçimi varsa preview ile ilerle. Günlük kullanıcı yükünü yaklaşık bir saatle sınırla; ancak kendi geliştirme yürütmesini kullanıcı başında sürekli beklemeden otomasyonla yapabilirsin.

**Onay kapıları:** kullanıcı onayı olmadan ödeme, satın alma, e-posta/DM gönderimi, repo dışına kişisel veri yükleme, production site yayınlama ve son kullanıcıya canlı Telegram bildirimi yok. Üretim kodu değişikliklerinden önce kapsamı raporla; yeni radar modülü için yerel geliştirme/test onayı var.

**İlk cevabında raporla:** (1) Mac repo/çalışma ağacı ve aktif eski LaunchAgent durumu; (2) üç hat için iş dağılımı/ilk yapılacak işler; (3) kullanıcıdan gerçekten gerekli olan blokajlar (örn. yerel erişim veya tokenın kullanıcı tarafından girilmesi); (4) ilk 24 saatte üretilecek somut dosyalar. Sonra kod/test/preview ve kaynak doğrulama işlerine başla. Sadece uzun bir fikir raporu yazıp durma. 
