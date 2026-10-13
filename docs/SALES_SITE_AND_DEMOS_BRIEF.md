# B2B satış / marka / demo — Mac Claude çalışma notu
Bu metin public depoda saklanabilir; kişisel aday profili ve sır yoktur. **Windows radar işinden bağımsızdır.**

## İş modeli
İki teklif test ediliyor:
- **K1 danışmanlık arka ofisi:** KPSS-2026/2 tercih haftası için, resmî ÖSYM kılavuzuna dayanan nitelik kodu / mezuniyet / özel şart ön kontrol listesi; insan danışman son onayı verir.
- **K2 yayıncı veri doğruluğu:** Yayınlanan personel ilanlarındaki alanların resmî Kariyer Kapısı/kurum duyurusuyla karşılaştırılması. Kimsenin yazmadığı hatayı uydurma; şu ana kadarki regex hataları BİZİM prototipe aittir.

İlk başarı metriği mesaj sayısı değil, en az üç görüşme, üç müşteri problemi ve iki fiyat konuşması; bir ücretli pilot somut işaret olur. Hiçbir mail/DM müşteriye kullanıcının açık onayı olmadan gönderilmez. Otomatik kitle kampanyası yok.

## Marka ve domain
- Kullanıcının Natro hesabında **loiai.online** alan adı var. **loiai.com** sahibi olduğu doğrulanmadı.
- `loiai.online` canlıda başka bir ürün (Letter of Intent Assistant). Üzerine aceleyle yeni sayfa basma veya Firebase auth/hosting URL'lerini bozma.
- İlk seçenekte kurumsal marka için ayrı, tarafsız bir landing page ve posta kutusu planlanır. Mevcut site korunacaksa `studio.loiai.online` gibi bir alt alan adı değerlendirilebilir; ancak marka eşleşmesi zayıf olabilir. Alternatif: şirketin farklı projelerini kapsayacak tarafsız bir domain, satın alma ÖNCESİ isim/ticari marka/tescil/yenileme fiyatı kontrolü.
- Sağlayıcı adayları: Google Workspace, Zoho Mail, Natro kurumsal e-posta. Değerlendirirken teslimat güvenilirliği, SPF/DKIM/DMARC, IMAP, kolay kullanım, aylık/yıllık taahhüt ve toplam ücret kıyaslanır.
- İlk gönderim öncesi gelen e-posta çalışmalı (MX); SPF/DKIM/DMARC kontrolü, harici Gmail ve başka sağlayıcıdan test, imza ve ret yöntemi olmalı. 10–15 kişiye kişiselleştirilmiş erişim planlanıyor; otomatik toplu e-posta sistemi kurma.

## Demo 1 — ÖSYM tercih raporu (Mac)
- 2025/2 gerçek ÖSYM kılavuzu / Tablo-3 lisans / nitelikler / gerçekleşmiş 2025/2 taban puan verileriyle kurgusal aday örneği üret; gerçek kişiye ait veri kullanma.
- PDF kaynakları Mac'te `research/round2/osym-data/` klasöründe (bu klasörün tümü GitHub main'de olmayabilir). Kaynak: **ÖSYM resmî sitesi**, 2025/2 kadro kılavuzu, Tablo-3, nitelik kodları, sonuçlar.
- Örnek profil kurgusal: İşletme lisans, 2024 KPSS P3 78,00, Ankara + İç Anadolu. Uygun, kontrol gerektirir, uygun değil ayrımı; her satır resmî kadro kodu, özel koşul, sayfa ve kaynak ile.
- PDF'de en az on satırı gerçek sayfa görüntüsüyle doğrula; 4001 ve ilgili bölüm kodundaki bütün satırların kapsamasını kontrol et. '2026/2 tahmini' olarak sunma; bu 2025/2 geçmiş dönem örneğidir.

## Demo 2 — Beş gerçek ilan/pozisyon kalite denetimi (Mac)
- Kariyer Kapısı'nın **güncel**, kamuya açık beş ayrı pozisyonunu Mac/TR bağlantısından incele. Tarihli eski 12 Ekim snapshot'ını 'bugün canlı' diye kullanma.
- En az iki bağımsız resmî kaynak karşılaştır: (1) KK API'deki `basTarih`, `bitTarih`, `kontenjanList`, `degerlemeAsamaList` gibi yapılandırılmış alanlar; (2) aynı ilan metni; (3) varsa kurumun resmî duyurusu.
- Rapor her pozisyonda kurum, unvan, il/kontenjan, başvuru tarihleri, yıl/tür/eşik, diploma/bölüm, yaş/belge, seçim usulü; kaynak URL ve kontrol saatini kaydeder.
- İki resmî kaynak çelişmiyorsa **uyumlu** yaz; başka yayıncının hatası varmış gibi gösterme. Beşinin beşi uyumlu çıkabilir.
- Satış hedefinin aynı ilanına ulaşılabiliyorsa yayıncı karşılaştırmasını ayrıca ve kanıtlı yap; ekran görüntüsü alma hakkına/erişim koşullarına uy. Uygulama ekranı için kullanıcı izin verip kendi cihazından görüntü gönderebilir.
- Dışarıya 'otomatik canlı API', 'her zaman güncel', 'atanma olasılığı', '24 saatte teslim garantisi' gibi doğrulanmamış söz verme.

## Önceki Mac çalışmasından başlangıç noktaları
`research/sales-sprint-plan.md`, `research/lines/sales.md`, `research/crm/atama-b2b-crm.xlsx` ve `research/round2/`. Bu yollar kullanıcının son ZIP'inde var fakat GitHub main ile tam eşleşmeyebilir.

## Sonraki adım
1. Kullanıcının marka/domain kararını al.
2. İki demonun kaynaklı gerçek taslaklarını üret ve kullanıcıya onaylat.
3. İlk iki hedef: Kariyer Cepte ve Kamu Personeli Alım (kurumsal kanalların güncelliğini doğrula). Rehber Panda'yı şirket/ileti izni belirsizliği çözülmeden soğuk e-posta gönderimi için aktif sayma.
4. CRM'de onay kaydı oluştuktan sonra kullanıcının seçtiği **kurumsal** adresle elle gönderim.
