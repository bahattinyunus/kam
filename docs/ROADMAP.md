# KAM Stratejik Geliştirme Yol Haritası: Kısıtlı Donanımda Zirve Bilişsel Zihin (Edge-Apex)

Bu belge, **KAM** projesinin nihai mühendislik hedefi olan **"en kısıtlı bellek (512 MB – 8 GB RAM/VRAM) ve güç zarfında (5W – 45W TDP) dünyanın en yüksek muhakeme, Türkçe belâgat ve otonom onarım yeteneğine sahip modelini üretme"** yol haritasını tanımlar.

---

## I. Temel Mühendislik Problemi ve Hedef Zarfı

Klasik büyük dil modelleri (LLM), karesel dikkat karmaşıklığı ($O(N^2)$) ve doğrusal büyüyen KV-önbellek (KV-Cache) darboğazı nedeniyle uç donanımlarda bellek taşmasına (*OOM*) yol açar. KAM'ın hedefi, sunucu sınıfı muhakeme kalitesini mikro-uç donanım sınırlarına indirmektir:

| Hedef Donanım Sınıfı | Bellek Sınırı (RAM/VRAM) | Güç Zarfı (TDP) | Hedef Model Profili | Hedef Çıkarım Hızı | İlk Token Gecikmesi (TTFT) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Seviye-1: Mikro İHA / Sensör Düğümü** (ARM Cortex-A76 / RPi 5) | 1 GB – 2 GB | 5W – 10W | `KAM-Nano-0.8B` (BitNet b1.58 / IQ3_M) | > 45 token/sn | < 35 ms |
| **Seviye-2: Taktik SİHA / İKA Aviyoniği** (Jetson Orin Nano / NX) | 4 GB – 8 GB | 15W – 25W | `KAM-Edge-3B-MoE` (0.7B Aktif Parametre) | > 85 token/sn | < 18 ms |
| **Seviye-3: Mobil Komuta / RTX 5060** (8 GB GDDR7 Blackwell) | 6 GB – 8 GB | 35W – 45W | `KAM-7B-Apex` (Q4_K_M + Spekülatif Çözümleme) | > 110 token/sn | < 10 ms |

---

## II. Faz 1: Hibrit Sıvı-SSM ve İnce Taneli Seyrek MoE Mimarisi (`KAM-Edge-MoE`)

Standart yoğun (dense) Transformer katmanları yerine, her tokende yalnızca gerekli uzman nöronları ateşleyen hibrit bir omurga inşa edilecektir:

1. **Doğrusal Karmaşıklıklı Durum Uzayı (Mamba-2 / LFM) + Lokal Dikkat Hibriti:**
   - Her 4 katmanın 3'ü $O(N)$ karmaşıklıklı ve sabit durum bellekli (`O(1)` KV-Cache) **Sıvı Durum Uzayı (Liquid-SSM)** katmanından, yalnızca 1'i **GQA (Grouped-Query Attention)** katmanından oluşur.
   - Bu yapı, 16.384 tokenlik bağlam penceresinde KV-önbellek bellek tüketimini **%78 oranında düşürür**.
2. **İnce Taneli Seyrek Uzman Karışımı (Fine-Grained Sparse MoE):**
   - Toplam parametre sayısı `3.2B` iken, her tokende yalnızca 1 paylaşımlı uzman (*Shared Expert*: Türkçe dilbilgisi ve temel mantık) ve 2 yönlendirilmiş uzman (*Routed Experts*: C++20 derleyici, eBPF telemetri veya EKF seyrüsefer) aktifleşir (**0.75B aktif parametre/token**).

---

## III. Faz 2: Bilişsel Damıtma (Reasoning Distillation) ve Aktif Çıkarım GRPO Eğitimi

Küçük bir modelin kendisinden 10 kat büyük modellerden daha isabetli karar vermesi, **bilgi damıtma (distillation)** ve **deterministik ödül fonksiyonları** ile sağlanacaktır:

1. **Çok Adımlı Düşünce Damıtması (Token-Budget-Aware CoT Distillation):**
   - Öğretmen modellerden üretilen uzun `<think>` zincirleri, bilgi kaybı olmadan **sıkıştırılmış latent akıl yürütme adımlarına** damıtılır. Gereksiz dolgu kelimeler elenerek uç donanımda daha az token ile aynı sonuca ulaşılır.
2. **Aktif Çıkarım ve Derleyici Doğrulamalı GRPO (Group Relative Policy Optimization):**
   - Takviyeli öğrenme aşamasında insan tercihi yerine **deterministik mühendislik ödül fonksiyonu** ($R_{\text{total}}$) kullanılır:

$$R_{\text{total}} = w_1 R_{\text{AST}} + w_2 R_{\text{Clang}} + w_3 \exp(-F) - w_4 P_{\text{dil\_sızıntısı}} - w_5 P_{\text{token\_israfı}}$$

   - $R_{\text{AST}} \in \{0, 1\}$: Üretilen C++20 kodunun statik güvenlik sandboxing'inden sıfır ihlalle geçmesi.
   - $R_{\text{Clang}} \in \{0, 1\}$: Kodun `-O3 -Wall -Wextra -Werror` ile hatasız derlenmesi.
   - $\exp(-F)$: Karl Friston Varyasyonel Serbest Enerji düşüşü (sistem entropisini azaltma başarısı).
   - $P_{\text{dil\_sızıntısı}}$: Türkçe dışı tek bir karakter veya çeviri kokan bozuk sözdizimi üretildiğinde uygulanan ağır ceza.

---

## IV. Faz 3: İleri Kuantizasyon, önem Matrisi (`imatrix`) ve BitNet b1.58

Model ağırlıklarını doğruluk kaybı olmadan dar bellek bant genişliğine sığdırmak için:

1. **Kalibrasyon Tabanlı Önem Matrisi (`imatrix`) Kuantizasyonu:**
   - Rastgele yuvarlama yerine; KAM'ın Türkçe hikmet, C++20 ve sibernetik külliyatı (`data/kam_master_dataset.json`, `data/kam_lore_dataset.json`) üzerinden Hessian aktivasyon önem matrisi çıkarılır.
   - Kritik yönlendirici (router) ve çıkış katmanları `Q6_K` / `FP16` hassasiyetinde korunurken, ara katmanlar `Q4_K_M` ve `IQ3_M` seviyesine sıkıştırılır.
2. **Üçlü Ağırlık Mimarisi (1.58-Bit Ternary / BitNet b1.58):**
   - Matris çarpımlarını (`FP16 MUL-ADD`) tamamen tamsayı toplama/çıkarma (`INT8 ADD/SUB`) işlemine indirgeyen $\{-1, 0, +1\}$ ağırlık eğitimi ile mikro-İHA işlemcilerinde (NPU olmadan saf ARM NEON üzerinde) **4.6x enerji tasarrufu** sağlanır.
3. **INT4 KV-Önbellek ve Dinamik Termal Kuantizasyon Geçişi:**
   - Linux eBPF termal kancası NPU sıcaklığının 85°C'yi aştığını algıladığında, çıkarım motorunu yeniden başlatmadan aktif katman hassasiyetini dinamik olarak `FP8 -> INT4`'e çeker.

---

## V. Faz 4: Spekülatif Çözümleme (Speculative Decoding) ve Özel C++20 Çekirdekleri

1. **Öz-Spekülatif Çözümleme (`kam:1.5b` Taslak + `kam:7b` Doğrulayıcı):**
   - Hafif uç model (`kam:1.5b`) ileriye dönük 5 aday tokeni milisaniyede tahmin eder; ana model (`kam:7b`) bu 5 tokeni tek bir paralel ileri besleme (*single forward pass*) adımında doğrular.
   - Matematiksel olarak **%0 doğruluk kaybıyla 2.6x çıkarım hızlanması** elde edilir.
2. **Sıfır Kopyalamalı C++20 SIMD / CUDA Çekirdek Birleştirmesi (`core/`):**
   - Kuantize ağırlık çözme (*dequantization*) ve matris-vektör çarpımı (*GEMV*) tek bir CUDA PTX / AVX-512 yazmaç (register) çekirdeğinde birleştirilerek VRAM bant genişliği darboğazı aşılır.

---

## VI. Uygulama Takvimi ve Kilometre Taşları

| Aşama | Odak Alanı | Çıktı ve Doğrulama Kriteri |
| :--- | :--- | :--- |
| **Adım 1 (Mevcut Temel)** | `kam:7b`, `kam:r1`, `kam:1.5b` GGUF Ailesi ve Yerel Komuta Merkezi | Hugging Face Hub yayını, RAG doğrulama ve 17/17 test başarısı **[TAMAMLANDI]** |
| **Adım 2** | Donanım Kısıtlı Çıkarım Planlayıcısı ve Dinamik Kuantizasyon Yönlendiricisi | Bellek/TDP bütçesine göre optimal model, bağlam ve KV-önbellek bit derinliğini seçen otonom planlayıcı (`edge_optimizer.py`) |
| **Adım 3** | `imatrix` Kalibrasyonlu Ultra-Sıkıştırılmış Ağırlıklar ve Spekülatif Çözümleme | Türkçe ve C++20 korpusuyla kalibre edilmiş `IQ3_M` / `Q4_K_M` ağırlıklar ve `kam:1.5b -> kam:7b` spekülatif çifti |
| **Adım 4** | Derleyici Ödüllü GRPO İnce Ayarı (Direct Compiler Feedback RL) | Clang `-O3` ve AST Sandbox geri bildirimiyle eğitilmiş LoRA adaptörlerinin ana GGUF ağırlıklarına kaynaştırılması |
| **Adım 5** | `KAM-Edge-MoE` Hibrit Sıvı-SSM Çekirdeği | 2 GB RAM altı uç donanımlarda >50 token/sn hızında çalışan yerli hibrit mimari |
