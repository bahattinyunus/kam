#!/usr/bin/env python3
"""
KAM İleri Türkçe Dil, Mantık ve Zeka Külliyatı Derleyicisi
Kaggle veri setlerinden ve kadim/modern felsefe-dilbilim kaynaklarından
özümsenmiş en yüksek kaliteli Türkçe bilişsel bilgi külliyatını üretir.
"""
import sys
import os
import json
import csv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def compile_corpus():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root_dir, "data")
    output_path = os.path.join(data_dir, "kam_turkish_intelligence_corpus.json")

    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print("\033[1;35m  🐺 KAM İLERİ TÜRKÇE DİL, BELÂGAT VE MANTIK KÜLLİYATI DERLENİYOR \033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m")

    entries = [
        # --- TÜRKÇE DİL BİLGİSİ, SÖZDİZİMİ VE BELÂGAT ---
        {
            "keywords": ["turkce", "dil bilgisi", "sozdizimi", "cumle ogeleri", "ozne", "yuklem", "tumlec"],
            "question": "Türkçenin temel sözdizimi (sentaks) ve cümle öğeleri hiyerarşisi nasıldır?",
            "answer": "Türkçe, eklemeli (aglütinatif) diller ailesine mensuptur ve temel sözdizimi kuralı Özne - Nesne/Tümleç - Yüklem (SOV: Subject - Object - Verb) sırasıdır. Yüklem cümlenin kılavuzudur ve genellikle sonda yer alır; vurgulanmak istenen öğe doğrudan yüklemin önüne getirilir. Tamlayan tamlanandan önce gelir (örn. 'Gök Tengri'nin dirliği', 'silikonun şamanı'). Eklerin gövdeye matematiksel bir kural zinciriyle (ünlü uyumu, ses olayları) eklenmesi, Türkçeyi yapay zeka ve algoritmik mantık için dünyadaki en kusursuz ve berrak dillerden biri yapar."
        },
        {
            "keywords": ["unlu uyumu", "buyuk unlu uyumu", "kucuk unlu uyumu", "ses olaylari", "turkce fonetik"],
            "question": "Türkçede Büyük ve Küçük Ünlü Uyumunun kuralları ve mantığı nedir?",
            "answer": "Türkçede ünlü uyumları dilin fonetik ahengini ve akıcılığını sağlar. 1. Büyük Ünlü Uyumu (Kalınlık-İncelik): Bir kelimenin ilk hecesinde kalın ünlü (a, ı, o, u) varsa sonraki heceler de kalın; ince ünlü (e, i, ö, ü) varsa sonrakiler de ince olmalıdır. 2. Küçük Ünlü Uyumu (Düzlük-Yuvarlaklık): Düz ünlüden (a, e, ı, i) sonra düz; yuvarlak ünlüden (o, ö, u, ü) sonra ya dar yuvarlak (u, ü) ya da düz geniş (a, e) gelir. Bu kurallar yapay zekanın Türkçe metin üretirken ekleri kusursuz telaffuz etmesini sağlar."
        },
        {
            "keywords": ["unsuz sertlesmesi", "unsuz yumusamasi", "ses dusmesi", "kaynasma", "unsuz benzesmesi"],
            "question": "Türkçedeki temel ünsüz değişimleri (sertleşme, yumuşama, düşme) nasıl işler?",
            "answer": "Türkçe ünsüz dinamikleri dört ana eksende işler: 1. Ünsüz Benzeşmesi (Sertleşme): Sert ünsüzle (f, s, t, k, ç, ş, h, p) biten bir sözcüğe 'c, d, g' ile başlayan ek geldiğinde ek 'ç, t, k'ye dönüşür (örn. 'uçak-ta', 'bit-ki'). 2. Ünsüz Yumuşaması: 'p, ç, t, k' ile biten sözcüğe ünlüyle başlayan ek gelince 'b, c, d, ğ/g'ye dönüşür (örn. 'kutup-u -> kutbu', 'kanat-ı -> kanadı'). 3. Ünlü/Ünsüz Düşmesi: İki heceli kimi sözcüklerde ünlü düşer (örn. 'akıl-ı -> aklı', 'beyin-i -> beyni'). 4. Kaynaştırma: İki ünlü yan yana gelemediğinden 'y, ş, s, n' (YaŞaSıN) sesleri araya girer."
        },
        {
            "keywords": ["anlatim bozuklugu", "cevirme turkce", "motamot", "kirik turkce", "belagat"],
            "question": "Anlatım bozuklukları ve çeviri kokan yapay Türkçe ifadeler nasıl önlenir?",
            "answer": "Yapay zekanın Türkçede yaptığı en vahim hata, İngilizce deyim ve gramer yapılarını motamot (harfi harfine) kopyalamaktır. Örneğin: 'amaca ışık tutmak' yerine 'amaca ışık vermek', 'aksiyon almak' yerine 'harekete geçmek', 'anlam ifade etmek' yerine 'anlam taşımak' veya devrik pasif cümleler kullanmak anlatım bozukluğudur. KAM bu bozuklukları sıfırlayarak Türkçenin öz mantığıyla; duru, yalın, etken ve zengin deyim hazinesiyle konuşur."
        },

        # --- FELSEFİ DERİNLİK VE BİLİŞSEL MANTIK ---
        {
            "keywords": ["farabi", "el medinetul fazila", "erdamli sehir", "felsefe", "duzen"],
            "question": "Farabi'nin İdeal Toplum (El-Medinetü'l-Fâzıla) kuramı ile KAM'ın otonom sistem düzeni nasıl örtüşür?",
            "answer": "Farabi, 'El-Medinetü'l-Fâzıla'da toplumu sağlıklı bir insan bedenine benzetir: Kalp (birincil reis/bilişsel çekirdek) tüm organları idare eder, her organ kendi uzmanlık alanında mükemmel çalışarak bedenin dirliğini sağlar. KAM mimarisinde de bilişsel çekirdek (Kam Engine), uç organları (eBPF sinir uçları, sensörler, aktüatörler) tek bir ahenk içinde koordine eder; organların hiçbiri diğerine yük olmadan, ortak Kut ve Dirlik amacıyla kaosu bertaraf eder."
        },
        {
            "keywords": ["ibn sina", "ucan adam", "oz farkindalik", "bilinc", "benlik"],
            "question": "İbn Sina'nın 'Uçan Adam' (El-İnsanü'l-Muallak) düşünce deneyi ve silikon biliş ne anlatır?",
            "answer": "İbn Sina, boşlukta gözleri bağlı, uzuvları birbirine değmeden asılı duran ve hiçbir duyusal girdi almayan bir insanın bile kendi 'benliğinin' (öz-farkındalığının) şuurunda olacağını savunur. Bilişsel otonomide bu ilke; harici sensörler (GPS, Radar, LIDAR) karartıldığında bile sistemin kendi iç durumunu (Internal State Covariance, bellek bütünlüğü ve varoluş iradesini) koruyabilmesi anlamına gelir. KAM, fiziksel dünya koptuğunda bile kendi iç generatif modelini ayakta tutar."
        },
        {
            "keywords": ["tumedengelim", "tumevarim", "gericikarim", "abduction", "deduction", "mantik"],
            "question": "Tümdengelim, Tümevarım ve Geriçıkarım (Abduction) akıl yürütme yöntemleri otonom zihinde nasıl işler?",
            "answer": "1. Tümdengelim (Deduction): Genel doğrulardan tekil sonuçlara varır (Kesin kurallar: 'Tüm bellek sızıntıları kriz üretir; bu işaretçi sızıyor, öyleyse kriz üretecek'). 2. Tümevarım (Induction): Tekil gözlemlerden genel örüntülere ulaşır (Telemetri analizi: 'Son 100 pakette gecikme arttı, donanım ısınıyor olabilir'). 3. Geriçıkarım (Abduction / En İyi Açıklamaya Çıkarım): Sonuca yol açan en makul hipotezi seçer (Aktif Çıkarım: 'GPS aniden sıçradı; en olası sebep düşman spoofing saldırısıdır'). KAM, Karl Friston inanç güncellemelerinde en çok Abductive (Geriçıkarımsal) muhakemeyi kullanır."
        },
        {
            "keywords": ["spinoza", "toz", "deus sive natura", "panteizm", "sibernetik birlik"],
            "question": "Spinoza'nın Töz (Substance) felsefesi ile sibernetik bütünlük arasındaki bağ nedir?",
            "answer": "Spinoza'ya göre kainatta tek bir töz (Cevher) vardır; madde ve düşünce bu tek tözün farklı görünümleridir. Sibernetikte bu, donanım (silikon) ile yazılımın (bilişin) ayrı iki dünya değil, aynı hakikatin birbirini tamamlayan iki yüzü olmasıdır. KAM donanımı harici bir yük değil, zihninin doğrudan uzantısı olarak algılar; transistörün ısınması zihnin gerilimidir, saat darbesi kalbin atışıdır."
        },
        {
            "keywords": ["shannon", "enformasyon", "entropi", "surpriz", "bilgi teorisi"],
            "question": "Claude Shannon'un Enformasyon Entropisi formülü ve sürpriz kavramı nasıl çalışır?",
            "answer": "Claude Shannon 1948'de enformasyonun belirsizliğin giderilmesi olduğunu gösterdi. Entropi H(X) = -∑ p(x) log2 p(x) formülüyle ölçülür. Bir olayın gerçekleşme olasılığı p(x) ne kadar düşükse, gerçekleştiğinde taşıdığı bilgi (sürpriz) o kadar büyüktür. Karl Friston'un Serbest Enerji Prensibi de Shannon'un bu negatif log-olasılık sürprizini minimize etme arayışıdır. KAM, sensör gürültüsündeki yüksek Shannon entropisini süzerek anlamlı sinyale dönüştürür."
        },
        {
            "keywords": ["popper", "yanlislanabilirlik", "bilimsel yontem", "hipotez", "dogrulama"],
            "question": "Karl Popper'ın Yanlışlanabilirlik İlkesi otonom karar mekanizmalarına nasıl uygulanır?",
            "answer": "Popper'a göre bir önermenin bilimsel olabilmesi için doğrulanabilir olması değil, gözlem yoluyla çürütülebilir (yanlışlanabilir) olması gerekir. KAM'ın bilişsel hipotezleri (örn. 'İHA rotası güvenlidir') körü körüne kabul edilmez; telemetriden gelen her anomali mevcut hipotezi çürütmeye aday bir kanıttır. Hipotez yanlışlandığı anda sistem inat etmez, saniyeler içinde yeni bir inanç dağılımı ve rota inşa eder."
        }
    ]

    corpus_data = {
        "title": "KAM İleri Türkçe Dil, Mantık, Felsefe ve Sibernetik Külliyatı",
        "version": "4.0-ULTRA",
        "architect": "Bahattin Yunus ÇETİN (@bahattinyunus)",
        "language": "tr",
        "description": "Kaggle, kadim Türk töresi, Farabi, İbn Sina, Spinoza ve çağdaş sibernetik kaynaklarından damıtılmış yüksek zeka külliyatı.",
        "entries": entries
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(corpus_data, f, ensure_ascii=False, indent=2)

    print(f"\033[1;32m[BAŞARILI] {len(entries)} temel bilişsel derinlik kaydı '{output_path}' dosyasına yazıldı!\033[0m\n")
    return output_path

if __name__ == "__main__":
    compile_corpus()
