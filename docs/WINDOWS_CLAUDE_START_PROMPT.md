# Windows Claude başlangıç promptu
Bu dosya Windows'taki Claude Desktop/Claude Code oturumuna kopyalanabilir. Öncelikle `docs/WINDOWS_RADAR_HANDOFF.md` dosyasını oku.

## İstek
GitHub'daki `hcakil/atama-enrichment-mvp` reposunun Windows çalışma kopyasındayız. Bu iş, aile kullanımı için **AGS/ÖABT resmî duyuru takibi** ve **pozisyon bazlı KPSS/sınavsız kamu ilanı radarı** kurmak içindir. B2B satış deneyinden **tamamen bağımsızdır**.

Ben iki hattın ayrılmasını, yeni radar modülünü, yerel özel profil/veritabanını, ayrı Telegram botunu ve ilk etapta gölge modu onaylıyorum. Canlı eşe bildirim gönderimini ayrıca onaylayacağım.

Lütfen şu sırayı izle:

1. `docs/WINDOWS_RADAR_HANDOFF.md`, `README.md`, `docs/ops-windows-nightly.md`, ilgili `scripts/` ve `src/atama_mvp/` kodunu oku. `git status` ve işletim sistemi durumunu kontrol et. Mac'teki güncel ZIP ile GitHub main arasındaki araştırma dosyası farkına dikkat et.
2. **R0:** Yalnız `AtamaMvpNightly` görevini listele, mevcut halini raporla ve varsa devre dışı bırak; başka Windows görevlerini, veritabanlarını ya da bildirimleri silme.
3. Gerçek profil, bot tokenları, telefon, chat ID ve şifreleri ekrana/koda/commit'e asla koyma. Depo public. Bir şey gerekiyorsa kullanıcıya hangi Windows yerel dosyaya elle eklemesi gerektiğini söyle.
4. Önce resmî AGS duyuruları için küçük radar modülünü ve birim testlerini uygula. MEB Akademi, Personel ve ÖSYM kaynaklarını canlı doğrula; gerçek RSS yoksa uydurma kaynak ekleme. Hiçbir son kullanıcıya mesaj gönderme.
5. Ardından KK'nin yapısal alanlarını koruyan **pozisyon bazlı** veri modeli ve dört durumlu şart motorunu geliştir. Eski regex'in doğru yapısal alanı ezmesini engelle. KPSS'li ve sınavsız durumları ayır. SBB/ilan.gov/İŞKUR kapsam boşluklarını dürüstçe göster.
6. Testler: en az 50 etiketli pozisyon ve sentetik profiller; kaçırma, yanlış kesin uygun, kaynak hatası, iptal ve sessiz mod garantisi. Özellikle 657 kanun numarası, 18.00 saat/kontenjan hatası, Türkiye geneli yanlış şehir ve eksik şart 'uygun' sayılması vakalarını kapsa.
7. Windows Task Scheduler için ayrı `AtamaRadar` görevini hazırla; 08:00/18:00 koşu, oturum kapalıyken çalışma ve log testlerini planla. Profil/bot ayarlanmadıysa güvenli şekilde fail-closed ol.
8. Her aşama sonunda kısa checkpoint yaz: biten, eksik, risk, test sonucu, sonraki adım. Git commit/push yapmadan önce kişisel veri ve sır sızıntısı kontrolü yap. Kullanıcının mevcut ticari dosyalarını değiştirme.

İlk cevabında uzun teori değil, **(a) R0 durumu, (b) çalışma ağacı ve görevlerin mevcut hali, (c) bugün yapılacak 3 teknik adım** göster. Bu kontrolden sonra kod yazmaya devam edebilirsin; ancak son kullanıcıya canlı bildirim için mutlaka onay al.

Birinci hedef: güvenilir AGS shadow. İkinci hedef: kapsamı ve yanlış negatifleri ölçülebilen KPSS shadow. Ticari satış ve alan adı işleri bu Windows oturumunun kapsamı dışındadır.
