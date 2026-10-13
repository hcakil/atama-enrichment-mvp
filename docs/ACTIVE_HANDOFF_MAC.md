# ACTIVE HANDOFF — Mac / Claude Desktop (13 Ekim 2026)

**Bu proje için geçerli yön: Mac.** Önceki `docs/WINDOWS_RADAR_HANDOFF.md` ve `docs/WINDOWS_CLAUDE_START_PROMPT.md` belgeleri arşiv/alternatif niteliğindedir; Mac'e Windows Task Scheduler kurma, Windows talimatlarını uygulama.

## 0. Bağlam
- Mevcut repo: `hcakil/atama-enrichment-mvp`, public GitHub. Python stdlib CLI: `PYTHONPATH=src python3 -m atama_mvp.cli`.
- Kullanıcı Claude Desktop/Claude Code aracılığıyla Mac üzerinde geliştirme ve yerel çalışma istiyor.
- Üç **ayrı iş hattı** var:
  1. **Radar (kişisel, Mac):** MEB AGS/ÖABT duyuruları ve KPSS'li/KPSS'siz kamu ilanları için sessiz uygunluk kontrolü; gerçek profil yalnız yerelde. Ticari ödeme beklemez.
  2. **Satış demoları + B2B:** Gerçek kaynaklı ÖSYM 2025/2 tercih örneği (Demo 1); Kariyer Kapısı resmî kaynaklarıyla beş gerçek pozisyon denetimi (Demo 2); onaylı kurumsal outreach ve CRM. Demo sonuçları elle doğrulanacak.
  3. **Kurumsal single-page website:** Henüz alan adı/marka seçilmedi; **ayrı repo** ve CI/CD. Mevcut `loiai.online` tıp ihtisası LOI Assistant ürününü bozma veya onun yerine yeni site deploy etme.

## Yetki / sınırlar
- **Radar için yerel Mac geliştirmesi ve shadow testleri onaylıdır.** Son kullanıcıya gerçek bildirim, toplu mesaj, herhangi bir ücretli abonelik/API açma veya üretimde ilan yayını için ayrıca kullanıcı onayı gerekir.
- **Satış**: İzin/onay olmadan kurumsal e-posta/DM gönderme, ödeme/alan adı satın alma. B2B ilk test 14–27 Ekim 2026; K1 (white-label tercih listesi), K2 (veri denetim).
- **Site**: Kaynak kodu ve preview/deploy tasarımı oluşturulabilir. Kullanıcının domain, hosting ve production yayın onayı olmadan mevcut domain DNS/Firebase ayarlarını değiştirme ve public production deploy etme.
- Public repo: gerçek adayın puanları, doğum tarihi, iletişim bilgileri, Telegram chat_id, API token, hesap bilgileri, gizli çevre değişkenleri, kişiye ait yerel DB **commit edilmez**. Sentetik test profilleri kullan.
- Bağımsız iş kolları aynı dosyalara eşzamanlı yazmasın. Site kodu **ayrı repo**, radar `src/atama_mvp/radar/` ve ayrı scriptler, demo dosyaları `research/demos/`.

## A. Mac radar (öncelik 1 güvenlik)
### R0: Mevcut otomatik gönderimi kontrol et
`scripts/install-local-launchd.sh` macOS `com.hcakil.atama-mvp.nightly` adlı LaunchAgent oluşturuyor. `scripts/local-nightly.sh` KK/SBB için `--notify-telegram` kullanıyor, dolayısıyla **profil filtresiz** Telegram mesajı atabilir. Mac'te kurulu olup olmadığını doğrula:
```bash
launchctl print "gui/$(id -u)/com.hcakil.atama-mvp.nightly" 2>&1 | head -30
ls -l "$HOME/Library/LaunchAgents/com.hcakil.atama-mvp.nightly.plist"
```
Kurulu/aktifse kullanıcının kişisel radar planı doğrultusunda **yalnız bu eski görevi** `launchctl bootout "gui/$(id -u)/com.hcakil.atama-mvp.nightly"` ile durdur; ilgisiz görevleri durdurma, konfigürasyon veya DB silme. `.env` içeriğini yazdırma. Kurulu değilse sorun yok.

### Aşamalar
1. **AGS shadow:** MEB Akademi, Personel GM, ÖSYM resmî kaynaklarını doğrula; yeni duyuru kimliği, tekrar/iptal değişikliği, kaynak hatası. İlk 5 gün yalnız operatöre sessiz test/yerel log. ÖSYM kaynak akışı yoksa olmayan RSS uydurma.
2. **KPSS shadow:** Kariyer Kapısı yapısal alanlarını koru; ilan → alt ilan → pozisyon. Her koşul `sagliyor / saglamiyor / belirtilmemis / okunamadi`, sonuç `uygun / muhtemel / belirsiz / uygunsuz`. Puan türü-yılı, taban, bölüm/nitelik, son başvuru tarihindeki yaş, sertifika, sınavsız kura/şartlar. Eksik bilgi otomatik 'uygun' değildir, belirsiz durumdaki muhtemel ilanlar sessizce kaybolmamalı. SBB ve ilan.gov kapsam/izin sınırlamalarını ayrı raporla.
3. **Test:** >=50 altın etiketli pozisyon + sentetik profiller; özellikle 657 kontenjan, 18.00 kontenjan, Türkiye geneli, P1/P2/P3 puan türü, yaş/süre, iptal/güncelleme, kötü PDF, alt ilanlar. Altın kümede yanlış negatif hedefi sıfır (bu tüm dünyada sıfır risk anlamına gelmez).
4. **Zamanlama:** Mac'te yeni ayrı `com.hcakil.atama-radar` LaunchAgent ve ayrı SQLite/log/bot. Günde 08.00 ve 18.00 hedefi. **Mac uyuyorsa çalıştırma garantisi yok:** güç/uyku ayarı, uyanışta telafi, geçmiş başarısız koşu ve heartbeat testi; asla 'Mac kapalıyken de çalışır' deme.
5. **Canlı kapısı:** AGS >=5 gün shadow, KPSS >=14 gün shadow; tüm testler ve kullanıcıdan ayrı onay. Shadow modda eşe 0 bildirim kuralını testle zorla.

## B. Demolar / satış
- Referans: `research/lines/sales.md`, `research/sales-sprint-plan.md`, `docs/SALES_SITE_AND_DEMOS_BRIEF.md`. Dikkat: en güncel araştırma bazı ZIP yerel dosyalarında olup GitHub main'de henüz olmayabilir; Mac çalışma kopyasını doğrula.
- Demo 1: Resmî **KPSS-2025/2** ÖSYM kılavuzu, kadro Tablo-3, nitelik kodları ve min-max sonuçları. Gerçek kişi değil sentetik profil. 10 satır manuel görsel doğrulama, kaynak ve sayfa numarası. Önce belgeyi, sonra PDF'yi üret.
- Demo 2: Mac/TR erişimiyle beş **güncel** Kariyer Kapısı pozisyonunun kaynaklı doğruluk raporu. Kendi prototip hatalarımızı üçüncü taraf hatasıymış gibi anlatma. Her satırda kaynak, kontrol tarihi, belirsiz alan.
- CRM: `research/crm/atama-b2b-crm.xlsx`. Onaysız mail/DM yok. Hedefler: Kariyer Cepte, Kamu Personeli Alım, Rehber Panda (işletme/6563 belirsizliği nedeniyle beklet), diğerleri.

## C. Site (öncelik: site kodu demoları beklemeden hazırlanabilir)
- Marka/alan adı **henüz seçilmedi**. Öneri: geniş kapsamlı yazılım/veri/otomasyon stüdyosu kimliği. Mevcut `loiai.online` LOI uygulamasının kullanıcı girişini/hostingini veya alan adı ayarlarını bozma.
- **Ayrı yeni repo**: tek sayfa, hızlı, mobil uyumlu; hero, hizmetler (data quality, automation, software), doğrulanmış demo önizlemeleri, çalışma yöntemi, iletişim. Türkçe öncelikli; referanssız müşteri logoları, sahte kazanım ve doğrulanmamış 'anlık otomasyon' vaadi yok.
- Demo 1/2 PDF'lerini yalnız kullanıcı doğrulayıp yayın onayı verirse public siteye ekle. ÖSYM kaynaklarına referans ve "örnek/ön değerlendirme" uyarısı.
- CI/CD: GitHub Actions yalnız bağımlılık güvenlik kontrolleri, lint/test/build ve preview; **Claude API anahtarı koyup her push'ta AI çalıştırma**. Production deploy hedefi (Cloudflare Pages, Vercel, GitHub Pages vb.) ve domain kullanıcıyla seçilecek; production publish ayrıca onaylı.
- Kurumsal mail: seçilecek domain üzerinden `hello@` ya da `partnerships@`; Zoho/Google Workspace/Natro tekliflerini yıllık maliyet, MX/SPF/DKIM/DMARC ve teslimat testi ile karşılaştır. DNS/ödemeye kullanıcı onayı şart.

## Durum/görevler
- `research/lines/radar.md` ve `research/lines/sales.md` Mac ZIP'in 13.10 sürümünde bulunur. Eski Windows planı içindeki durum/kod parçalarını **yeni Mac planına** uyarla.
- Üç hat için ayrı `research/lines/mac-radar-progress.md`, `research/lines/demo-sales-progress.md`, `research/lines/site-progress.md` checkpoint dosyaları (gizli veri içermeden).
- Önce **env audit** ve R0, sonra AGS shadow; Demo 1/2 paralel; site preview sonrası domain kararı.
