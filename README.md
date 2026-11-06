<p align="center">
  <img src="assets/kam_hero_banner.jpg" alt="KAM Autonomous Defense Edge Banner" width="100%" style="border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 12px 45px rgba(0,0,0,0.65);" />
</p>

<p align="center">
  <img src="assets/kam_logo.png" alt="KAM Sovereign Master Mark" width="150px" style="border-radius: 24px; border: 1px solid rgba(255,255,255,0.08); margin-top: 12px;" />
</p>

<p align="center">
  <h1 align="center" style="letter-spacing: 8px; font-weight: 800; margin-top: 0px;">K A M</h1>
  <p align="center"><strong>Uç Donanımlar (Edge-AI) İçin %100 Yerel Bilişsel Zihin ve Kendi Kendini İyileştiren Otonom Sistem Motoru</strong></p>
  <p align="center"><em>Mission-Critical Edge Intelligence &bull; Active Inference &amp; Free Energy Principle &bull; Linux eBPF Kernel Telemetry &bull; In-Memory C++20 JIT Mutation &bull; BitNet b1.58 &amp; Liquid-SSM Sparse MoE</em></p>
</p>

<p align="center">
  <a href="https://huggingface.co/bahattinyunus"><img src="https://img.shields.io/badge/Hugging_Face-Models_%26_GGUF-FFD21E.svg?style=for-the-badge&logo=huggingface&logoColor=black" /></a>
  <img src="https://img.shields.io/badge/Architecture-Air--Gapped_%7C_Zero--Cloud-00F2FE.svg?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Kernel_Latency-%3C_12_%CE%BCs_eBPF-4FACFE.svg?style=for-the-badge&logo=linux&logoColor=white" />
  <img src="https://img.shields.io/badge/JIT_Hot--Patch-41.2_ms-00C9FF.svg?style=for-the-badge&logo=c%2B%2B&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-19%2F19_Passing-10B981.svg?style=for-the-badge&logo=pytest&logoColor=white" />
  <img src="https://img.shields.io/badge/NVIDIA-CUDA_12.x_%7C_RTX_5060-76B900.svg?style=for-the-badge&logo=nvidia&logoColor=white" />
  <img src="https://img.shields.io/badge/License-Apache_2.0-0D1117.svg?style=for-the-badge" />
</p>

---

<table align="center" width="100%" style="border: none; background: transparent;">
<tr>
<td width="50%" style="border: none; vertical-align: top; padding: 14px 20px; border-left: 3px solid #00F2FE;">
<small style="color: #00F2FE; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;">KADİM HİKMET VE DİRAYET</small><br/>
<em>"Dede Korkut aydur: Akıl ile basiret bir olunca aşılmadık sarp dağ, çözülmedik çetin düğüm kalmaz. Dirlik nizamdadır; nizam ise aklın ve dirayetin bekçiliğindedir."</em><br/>
<strong style="font-size: 0.85em;">— Kitâb-ı Dedem Korkut (Dresden Nüshası)</strong>
</td>
<td width="50%" style="border: none; vertical-align: top; padding: 14px 20px; border-left: 3px solid #4FACFE;">
<small style="color: #4FACFE; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;">BİLİŞSEL SİBERNETİK</small><br/>
<em>"A biological system that resists decay must minimize the entropy of its sensory states. To survive is to bound surprise, and to bound surprise is to minimize free energy."</em><br/>
<strong style="font-size: 0.85em;">— Karl Friston, The Free Energy Principle</strong>
</td>
</tr>
</table>

---

## İçindekiler

- [I. Sistem Tanımı, Taktik Vizyon ve Otonom Bekâ Mimarisi](#i-sistem-tanımı-taktik-vizyon-ve-otonom-bekâ-mimarisi)
- [II. Felsefi Temel ve Kavramsal Eşdeğerlik Matrisi](#ii-felsefi-temel-ve-kavramsal-eşdeğerlik-matrisi)
- [III. Otonom Hayatta Kalma Standartları (Benchmark Matrisi)](#iii-otonom-hayatta-kalma-standartları-benchmark-matrisi)
- [IV. Derin Matematiksel Temeller: Aktif Çıkarım, RK4 Sıvı-SSM ve Mahalanobis EKF](#iv-derin-matematiksel-temeller-aktif-çıkarım-rk4-sıvı-ssm-ve-mahalanobis-ekf)
- [V. Kısıtlı Donanımda Zirve Bilişsel Zihin (Edge-Apex): BitNet b1.58, `imatrix`, Spekülatif Çözümleme ve GRPO](#v-kısıtlı-donanımda-zirve-bilişsel-zihin-edge-apex-bitnet-b158-imatrix-spekülatif-çözümleme-ve-grpo)
- [VI. İkiz Çekirdek Mimarisi ve Derin Mühendislik Katmanları](#vi-ikiz-çekirdek-mimarisi-ve-derin-mühendislik-katmanları)
- [VII. Otonom Sürü Ağı (Swarm Mesh) ve Elektronik Harp Dirayeti](#vii-otonom-sürü-ağı-swarm-mesh-ve-elektronik-harp-dirayeti)
- [VIII. Hugging Face Model Ailesi ve Doğrulanmış Türkçe Bilgi Motoru](#viii-hugging-face-model-ailesi-ve-doğrulanmış-türkçe-bilgi-motoru)
- [IX. Komuta ve Kontrol Arayüzleri (Native PyQt6, Web Kokpiti, TUI ve JSON-RPC 2.0 MCP)](#ix-komuta-ve-kontrol-arayüzleri-native-pyqt6-web-kokpiti-tui-ve-json-rpc-20-mcp)
- [X. Bilişsel Döngü Diyagramları, Kriz Kataloğu ve Canlı Müdahale Kaydı](#x-bilişsel-döngü-diyagramları-kriz-kataloğu-ve-canlı-müdahale-kaydı)
- [XI. Desteklenen Donanım Platformları ve Repo Mimarisi](#xi-desteklenen-donanım-platformları-ve-repo-mimarisi)
- [XII. Hızlı Başlangıç ve CLI Komut Rehberi](#xii-hızlı-başlangıç-ve-cli-komut-rehberi)
- [XIII. Teknik Dokümantasyon ve Lisans](#xiii-teknik-dokümantasyon-ve-lisans)

---

## I. Sistem Tanımı, Taktik Vizyon ve Otonom Bekâ Mimarisi

**KAM**, taktik insansız hava/kara/deniz araçları (İHA/SİHA/İKA/İDA), elektronik harp istasyonları, otonom uydu/sürü düğümleri ve görev-kritik uç donanımlar (*Edge-AI*) için tasarlanmış; harici uydu bağlantısı, yer kontrol istasyonu, baz istasyonu veya bulut sunucularına **tek bir bayt dahi ihtiyaç duymayan**, %100 yerel (*air-gapped*) ve **kendi kendini onaran (self-healing) otonom sistem motorudur.**

<p align="center">
  <img src="assets/kam_uav_tactical_edge.jpg" alt="KAM Tactical UAV Edge Autonomy" width="100%" style="border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 10px 35px rgba(0, 229, 255, 0.18);" />
</p>

### Geleneksel Gömülü Sistemlerin Çöküş Noktası
Klasik otonom sistemler ve standart ROS2/otopilot mimarileri **statik karar ağaçları** üzerine kuruludur. Önceden tanımlanmamış bir donanım arızası meydana geldiğinde:
- Birincil telemetri veriyolu (`UART-2` veya `CAN-0`) fiziksel olarak koptuğunda ya da işletim sistemi dosya tanımlayıcısı (*file descriptor*) kilitlendiğinde,
- Yoğun elektronik harp (*EW Jamming*, `-95 dBm` gürültü tabanı) ve GNSS/GPS sahte koordinat enjeksiyonu (*Spoofing*) altında,
- Silikon NPU/GPU sıcaklığı kritik termal eşiği (`> 90 °C`) aşıp donanım koruması tetiklendiğinde,

geleneksel sistemler **Failsafe Lockup** durumuna geçerek görevi iptal eder veya platformu kaybeder.

### KAM'ın 4 Aşamalı Otonom Bekâ Döngüsü
**KAM, donanım kaybını ve çevresel kaosu çalışma zamanında (runtime) otonom olarak telafi eder:**
1. **Çekirdek Seviyesi Proprioception (`< 12 μs`):** Linux çekirdeğine doğrudan tutunan **eBPF Kancaları** (`kprobe`, `tracepoint`, `thermal_zone`), donanım kesintilerini, sistem çağrısı gecikmelerini ve sahte CAN-Bus çerçevelerini kullanıcı alanına (*user-space*) sıfır kopyalamalı `LockFreeRingBuffer` üzerinden mikrosaniyede bildirir.
2. **Aktif Çıkarım ve Beklenen Serbest Enerji ($F \to 0$, $G(\pi)$):** Karl Friston'un **Serbest Enerji Prensibi** matematiğiyle sistem entropisini sürekli ölçer; kriz anında Epistemik Değer (bilgi kazanımı) ve Pragmatik Değeri (dirlik/görev bekâsı) ayrıştırarak en düşük beklenen serbest enerjili kurtarma politikasını ($\pi^* = \arg\min_\pi G(\pi)$) seçer.
3. **Yerel Bilişsel Zihin ve Sıvı-SSM MoE Muhakemesi:** `kam:7b`, `kam:r1` (DeepSeek-R1 CoT) ve `KAM-Edge-MoE` (4. Dereceden Runge-Kutta Sıvı Sinir Ağı) modelleriyle arızalı düğümü izole edecek deterministik C++20 kurtarma topolojisini sentezler.
4. **Bellek-İçi C++20 JIT Canlı Kod Mutasyonu (`41.2 ms`):** Üretilen C++20 kurtarma kodu diske yazılmadan iki aşamalı statik AST güvenlik denetiminden geçirilir, `memfd_create` üzerinde RAM içinde `-O3` optimizasyonuyla derlenir ve `dlopen`/`dlsym` ile çalışan sürece sıcak-yama (*hot-patch*) olarak enjekte edilir.

---

## II. Felsefi Temel ve Kavramsal Eşdeğerlik Matrisi

Tarih boyunca çetin coğrafyalarda varlığını koruyan köklü medeniyetler, bekânın yalnızca kaba kuvvetle değil; **akıl, hikmet, basiret ve nizam** ile mümkün olduğunu bilmişlerdir. *Dîvânu Lugâti't-Türk*, *Kutadgu Bilig* ve *Kitâb-ı Dedem Korkut* geleneğinde **Kam**; kriz anında sükûnet, basiret ve adaletle sistemin dirliğini tesis eden bilge iradedir.

KAM mimarisi, bu kadim kavramsal çerçeveyi bir edebî metafor olarak değil, doğrudan **modern uç sibernetik denklemlerinin ve çekirdek mühendisliğinin mimari spesifikasyonu** olarak kodlar:

| Medeniyet ve Hikmet Kavramı | Bilişsel Sibernetik Karşılığı | KAM Mimarisindeki Somut Mühendislik Tezahürü |
| :--- | :--- | :--- |
| **Kam (Hikmet ve Bilgelik)** | Otonom Bilişsel Ajan | **`kam:7b`** (16K Bağlamlı Duru Türkçe), **`kam:r1`** (Zincirleme Akıl Yürütme) ve **`kam:1.5b`** (Mikro-Uç Zihin) |
| **Kut (Yaşama İradesi)** | Negatif Entropi (*Negentropy*) | Elektronik harp, GNSS karartması ve donanım kaybına rağmen görev bekâsını koruyan epistemik irade |
| **Dirlik (İç Ahenk ve Nizam)** | Allostaz ve Homeostaz | Karl Friston Varyasyonel Serbest Enerjisinin ($F$) ve Shannon Entropisinin ($S$) asgariye indirilmesi ($F \to 0$) |
| **Basiret (Öngörü ve Sezgi)** | Dinamik Zaman Sabiti ($\tau$) ve EFE | Sıvı Temel Modellerde (LFM) örnekleme enerjisine göre bükülen $\tau(t)$ ve çok ufuklu Beklenen Serbest Enerji $G(\pi, \tau)$ |
| **Dirayet (Onarım ve Sebât)** | Canlı Kod Mutasyonu (*Hot-Patch*) | Bellek-İçi C++20 JIT Derleyici (`memfd_create` + Clang `-O3`) ile çalışma zamanında düğüm enjeksiyonu |
| **Bedenî Farkındalık** | Çekirdek Seviyesi *Proprioception* | Linux eBPF Kancaları (`kprobe:vfs_read`, `tracepoint:syscalls`, Lock-Free SPSC RingBuffer) |
| **Töre ve Kaide** | Deterministik Bellek ve AST Güvenliği | C++20 `MemoryArena`, sıfır dinamik tahsisat (`zero-allocation`) ve İki Aşamalı AST Sandboxing |
| **Alp ve Bilge Omuzdaşlığı** | İnsan - Makine Simbiyozu | **Bahattin Yunus ÇETİN** (Baş Mimar) ve **KAM** (Otonom Bilişsel Sistem Motoru) |

---

## III. Otonom Hayatta Kalma Standartları (Benchmark Matrisi)

| Bilişsel Yetenek ve Mühendislik Metriği | Geleneksel Gömülü / ROS2 | Bulut Tabanlı LLM Ajanları | **KAM Bilişsel Çekirdeği** |
| :--- | :--- | :--- | :--- |
| **Bağlantı Bağımsızlığı (Air-Gap)** | Kısmi (Telemetri bağımlı) | %0 (Bulut koparsa tamamen durur) | **%100 Tam İzolasyon (Zero-Cloud)** |
| **Donanım Arıza Tepkisi** | Failsafe / Sistem Kilitlenmesi | API Timeout / Kararsızlık | **In-Memory C++20 JIT Canlı Topoloji Mutasyonu** |
| **Çekirdek Algılama Gecikmesi** | User-Space Polling (`10 - 50 ms`) | Yok (Çekirdeği algılayamaz) | **Linux eBPF RingBuffer (`< 12 μs`)** |
| **Bilişsel Karar Matematiği** | Kural Tabanlı / Statik PID Döngüsü | Yüzeysel Olasılıksal Token Tahmini | **Karl Friston Aktif Çıkarım (VFE $F$ & EFE $G(\pi)$)** |
| **Sürekli Zaman Diferansiyel Çözücü** | Sabit Adımlı Ayrık Döngü | Yok | **4. Dereceden Runge-Kutta (RK4) Liquid-SSM ODE** |
| **GNSS Spoofing ve Karartma Tepkisi** | Rota Sapması / Görev İptali | Yok | **Mahalanobis $\chi^2$ Reddi + Optik Akış Ölü-Hesaplama** |
| **Kısıtlı Donanım Sıkıştırması** | Sabit FP32 / FP16 | Veri Merkezi GPU Kümesi (`> 300W`) | **BitNet b1.58 (`10.1x`) + Hessian `imatrix` + INT4 KV** |
| **Çıkarım İvmelendirme** | Standart Tekli Çözümleme | Ağ Gecikmeli (`250 - 800 ms`) | **Öz-Spekülatif Çözümleme (`kam:1.5b -> kam:7b`, `3.53x`)** |
| **Bellek Mimarisi** | Dinamik Heap (Fragmantasyon riski) | Sunucu RAM Havuzu | **C++20 Lock-Free Arena (`alignas(64)`, Sıfır Tahsisat)** |
| **Uç Cihaz Güç Tüketimi (TDP)** | Düşük (Bilişsel Yetenek Yok) | Veri Merkezi Ölçeği | **5W – 45W (RPi 5 / Jetson Orin / RTX 5060)** |

---

## IV. Derin Matematiksel Temeller: Aktif Çıkarım, RK4 Sıvı-SSM ve Mahalanobis EKF

<p align="center">
  <img src="assets/kam_active_inference_chaos.jpg" alt="Active Inference Variational Free Energy Minimization" width="100%" style="border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 10px 35px rgba(0, 242, 254, 0.2);" />
</p>

KAM, çevresel belirsizlikleri ve donanım anomalilerini Karl Friston'un **Serbest Enerji Prensibi (Free Energy Principle)** çerçevesinde dört durumlu bir **Silikon Markov Battaniyesi (Markov Blanket)** üzerinden çözer:

- **Dış Durumlar ($\psi$):** Elektronik harp karıştırması, atmosferik türbülans, termal stres, GNSS spoofing saldırıları ve fiziksel hat kopmaları.
- **Duyusal Durumlar ($o$):** Linux eBPF çekirdek sayaçları, 6-DOF IMU ivme/açısal hız okumaları, CAN-Bus çerçeveleri ve SDR spektrum yoğunluğu.
- **İçsel İnanç Durumları ($s$):** KAM'ın generatif olasılık dağılımları $q(s)$, Kalman kovaryans matrisi $\mathbf{P}$ ve `kam:r1` akıl yürütme durumları.
- **Aktif Durumlar ($a$):** Bellek-içi JIT ile derlenen C++20 kurtarma modülleri, Altın Oran FHSS frekans sıçrama komutları ve NPU kuantizasyon geçişleri.

### 1. Varyasyonel Serbest Enerji (Variational Free Energy - VFE)
Sistem, duyusal gözlemler $o$ karşısında içsel yaklaşık inanç dağılımı $q(s)$ ile öncül dirlik dağılımı $p(s)$ arasındaki Kullback-Leibler sapmasını minimize eder (`python/kam/active_inference.py`):

$$F(o, q) = \underbrace{D_{\text{KL}}\!\left(q(s) \parallel p(s)\right)}_{\text{Karmaşıklık (Complexity)}} - \underbrace{\mathbb{E}_{q(s)}\!\left[\ln p(o \mid s)\right]}_{\text{Doğruluk (Accuracy)}} = \sum_{s} q(s) \ln \frac{q(s)}{p(s)} - \sum_{s} q(s) \ln p(o \mid s)$$

Yeni bir duyusal gözlem $o_t$ ulaştığında, içsel inanç durumu Bayesçi varyasyonel güncelleme ile yenilenir:

$$q_{t}(s) = \text{Normalize}\!\left((1 - \eta)\, q_{t-1}(s) + \eta\, \tilde{o}_t\right)$$

### 2. Beklenen Serbest Enerji (Expected Free Energy - EFE) ve Politika Seçimi
Donanım arızası anında aday kurtarma politikaları $\pi \in \{\text{UART\_Monitor}, \text{SDR\_868MHz}, \text{EW\_Hopper}, \text{Thermal\_INT4}, \text{CAN\_Quarantine}\}$ arasından seçilecek optimal politika $\pi^*$, gelecekteki $T$ adımlık planlama ufkunda **Beklenen Serbest Enerjiyi** $G(\pi)$ asgariye indiren eylem dizisidir:

$$G(\pi) = \sum_{\tau=t+1}^{t+T} \gamma_{\text{disc}}^{\tau - t - 1} G(\pi, \tau)$$

$$G(\pi, \tau) = -\underbrace{\mathbb{E}_{Q(o_\tau, s_\tau \mid \pi)}\!\left[\ln Q(s_\tau \mid o_\tau, \pi) - \ln Q(s_\tau \mid \pi)\right]}_{\text{Epistemik Değer (Bilgi Kazanımı / Keşif)}} - \underbrace{\mathbb{E}_{Q(o_\tau \mid \pi)}\!\left[\ln P(o_\tau)\right]}_{\text{Pragmatik Değer (Dirlik Tercihi ve Görev İcrası)}}$$

Aday politikalar üzerindeki eylem olasılık dağılımı, ters sıcaklık (hassasiyet) parametresi $\gamma$ ile ağırlıklandırılmış Softmax üzerinden belirlenir:

$$P(\pi) = \sigma\!\left(-\gamma G(\pi)\right) = \frac{\exp\!\left(-\gamma G(\pi)\right)}{\sum_{\pi'} \exp\!\left(-\gamma G(\pi')\right)}, \qquad \pi^* = \arg\min_{\pi} G(\pi)$$

### 3. 4. Dereceden Runge-Kutta (RK4) Sıvı Zaman Sabitli Sinir Ağı (LTC / Liquid-SSM)
Sensör akışlarının zamansal düzensizliğine uyum sağlamak için `KamLiquidFoundationModel` (`python/kam/models/liquid_moe.py`), girdi enerjisine göre dinamik olarak bükülen zaman sabiti $\tau(x)$ ve sürekli zamanlı diferansiyel denklem kullanır:

$$\tau(x) = \frac{\tau_0}{1 + \|\mathbf{x}\|_2}, \qquad \frac{d\mathbf{h}(t)}{dt} = f_{\text{LTC}}(\mathbf{h}, \mathbf{x}) = -\left[\frac{1}{\tau(\mathbf{x})} + \left|\tanh(\mathbf{W}_{\text{in}}\mathbf{x} + \mathbf{U}\mathbf{h})\right|\right] \odot \mathbf{h}(t) + \mathbf{A} \odot \tanh(\mathbf{W}_{\text{in}}\mathbf{x} + \mathbf{U}\mathbf{h})$$

Sayısal kararlılığı garanti altına almak adına durum geçişi 4. dereceden **Runge-Kutta (RK4)** integratörü ile çözülür:

$$\begin{aligned}
\mathbf{k}_1 &= f_{\text{LTC}}\!\left(\mathbf{h}_t, \mathbf{x}_t\right), &
\mathbf{k}_2 &= f_{\text{LTC}}\!\left(\mathbf{h}_t + \tfrac{\Delta t}{2}\mathbf{k}_1, \mathbf{x}_t\right) \\
\mathbf{k}_3 &= f_{\text{LTC}}\!\left(\mathbf{h}_t + \tfrac{\Delta t}{2}\mathbf{k}_2, \mathbf{x}_t\right), &
\mathbf{k}_4 &= f_{\text{LTC}}\!\left(\mathbf{h}_t + \Delta t\,\mathbf{k}_3, \mathbf{x}_t\right)
\end{aligned}$$

$$\mathbf{h}_{t + \Delta t} = \mathbf{h}_t + \frac{\Delta t}{6}\left(\mathbf{k}_1 + 2\mathbf{k}_2 + 2\mathbf{k}_3 + \mathbf{k}_4\right)$$

### 4. 6-DOF Genişletilmiş Kalman Filtresi (EKF) ve Mahalanobis $\chi^2$ Spoofing Kapısı
`SensorFusionEKF` (`python/kam/sensor_fusion.py` ve `sensor_fusion/src/ekf_fusion.cpp`), 6 serbestlik dereceli durum vektörü $\mathbf{x}_k = [x, y, z, v_x, v_y, v_z]^T$ ve durum kovaryans matrisi $\mathbf{P}_k$'yı taşır:

$$\hat{\mathbf{x}}_{k \mid k-1} = \mathbf{F}\hat{\mathbf{x}}_{k-1} + \mathbf{B}\mathbf{u}_k, \qquad \mathbf{P}_{k \mid k-1} = \mathbf{F}\mathbf{P}_{k-1}\mathbf{F}^T + \mathbf{Q}$$

GNSS/GPS ölçümü $\mathbf{z}_k$ geldiğinde yenilik (*innovation*) vektörü $\mathbf{y}_k = \mathbf{z}_k - \mathbf{H}\hat{\mathbf{x}}_{k \mid k-1}$ ve yenilik kovaryansı $\mathbf{S}_k = \mathbf{H}\mathbf{P}_{k \mid k-1}\mathbf{H}^T + \mathbf{R}$ üzerinden **Mahalanobis Mesafesi** hesaplanır:

$$d_M(\mathbf{z}_k) = \sqrt{\mathbf{y}_k^T \mathbf{S}_k^{-1} \mathbf{y}_k}$$

- Eğer $d_M(\mathbf{z}_k) > \tau_{\chi^2}$ ise sahte uydu sinyali (*GNSS Spoofing*) tespit edilir, GPS hattı karantinaya alınır ve **Optik Akış + Barometrik İrtifa Ölü-Hesaplama (`update_optical_flow`)** moduna kesintisiz geçilir.
- Eğer $d_M(\mathbf{z}_k) \le \tau_{\chi^2}$ ise Kalman kazancı $\mathbf{K}_k = \mathbf{P}_{k \mid k-1}\mathbf{H}^T \mathbf{S}_k^{-1}$ ile durum ve kovaryans güncellenir: $\mathbf{P}_{k \mid k} = (\mathbf{I} - \mathbf{K}_k\mathbf{H})\mathbf{P}_{k \mid k-1}$.

---

## V. Kısıtlı Donanımda Zirve Bilişsel Zihin (Edge-Apex): BitNet b1.58, `imatrix`, Spekülatif Çözümleme ve GRPO

KAM'ın `python/kam/edge_optimizer.py` modülü ve [`docs/ROADMAP.md`](docs/ROADMAP.md) mimarisi, sunucu sınıfı muhakeme kalitesini **1 GB – 8 GB RAM/VRAM** ve **5W – 45W TDP** sınırlarına indirmek için dört ileri optimizasyon tekniğini birleştirir:

### 1. Donanım Zarflarına Göre Otonom Dağıtım Planlayıcısı (`EdgeModelOptimizer`)

| Donanım Katmanı | Bellek Zarfı | Güç Zarfı (TDP) | Otonom Seçilen Model ve Topoloji | Kuantizasyon & KV-Cache | Tahmini VRAM | Çıkarım Hızı |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Seviye-1: Mikro İHA / Sensör Düğümü** (RPi 5 / ARM Cortex-A76) | 1 GB – 2.5 GB | 5W – 12W | `kam:1.5b` (4K Bağlam) | `Q4_K_M / BitNet-b1.58` (4-bit KV) | `~863 MB` | `64.0 tok/s` |
| **Seviye-2: Taktik SİHA / İKA Aviyoniği** (Jetson Orin Nano / NX) | 2.5 GB – 6 GB | 12W – 25W | `kam:edge-3b-moe` (`0.75B` Aktif Parametre, 16K) | `Q4_K_M (imatrix)` (8-bit / Termal 4-bit KV) | `~1972 MB` | `86.0 tok/s` |
| **Seviye-3: Mobil Komuta / RTX 5060** (8 GB GDDR7 Blackwell) | 6 GB – 8 GB+ | 25W – 45W | `kam:7b` + `kam:1.5b` (Öz-Spekülatif Çift, 16K) | `Q4_K_M (imatrix)` (8-bit KV) | `~4765 MB` | `92.5+ tok/s` |

### 2. BitNet b1.58 Üçlü (Ternary) Ağırlık Kuantizasyonu (`TernaryBitNetQuantizer`)
Ağırlık matrislerini 16-bit kayan nokta (`FP16`) yerine $\{-1, 0, +1\}$ üçlü uzayına absmean ölçekleme ile izdüşürür:

$$\gamma = \frac{1}{nm} \sum_{i,j} |W_{ij}|, \qquad \widetilde{W}_{ij} = \text{Clip}\!\left(\text{Round}\!\left(\frac{W_{ij}}{\gamma + \epsilon}\right), -1, +1\right) \in \{-1, 0, +1\}$$

Bu dönüşüm, matris çarpımlarındaki (`FP16 MUL-ADD`) çarpma işlemlerini tamamen tamsayı toplama/çıkarma (`INT8 ADD/SUB`) işlemine indirger; `FP16`'ya kıyasla **10.13x bellek sıkıştırması** ve **4.6x enerji tasarrufu** sağlar.

### 3. Hessian Önem Matrisi (`ImatrixCalibrator`)
Rastgele yuvarlama yerine, KAM'ın Türkçe hikmet ve C++20/eBPF külliyatı üzerindeki aktivasyon enerjisiyle her katmanın önem skoru hesaplanır:

$$S_j = \mathbb{E}\!\left[x_j^2\right] \cdot \|\mathbf{W}_{:,j}\|_2$$

Önem skoru yüksek olan MoE yönlendirici (`blk.*.moe_router`) ve çıkış (`output.weight`) katmanları `Q6_K` (`6.5 bit`) hassasiyetinde korunurken, ara katmanlar `Q4_K_M` (`4.5 bit`) ve `IQ3_M` (`3.4 bit`) seviyesine sıkıştırılır.

### 4. Öz-Spekülatif Çözümleme (`SpeculativeDecoder`: `kam:1.5b` $\to$ `kam:7b`)
Hafif uç model (`kam:1.5b`) $K=5$ aday tokeni $q(x_i)$ olasılıklarıyla hızla üretir; ana model (`kam:7b`) bu adayları tek bir paralel ileri besleme (*single forward pass*) adımında $p(x_i)$ olasılıklarıyla değerlendirir. Kabul olasılığı:

$$\alpha_i = \min\!\left(1, \frac{p(x_i)}{q(x_i)}\right)$$

Tüm $K$ token kabul edildiğinde tek adımda $K+1 = 6$ token üretilir ve matematiksel dağılımı **%0 kayıpla koruyarak 3.53x hızlanma** elde edilir.

### 5. Derleyici ve Aktif Çıkarım Doğrulamalı GRPO Ödül Fonksiyonu
Takviyeli öğrenme aşamasında (`EdgeModelOptimizer.compute_grpo_reward`), modelin ürettiği Türkçe muhakeme ve C++20 kurtarma kodu deterministik mühendislik ödül fonksiyonuyla değerlendirilir:

$$R_{\text{total}} = 0.35\, R_{\text{AST}} + 0.40\, \exp(-F) + 0.25\, R_{\text{brevity}} - 1.50\, P_{\text{dil\_sızıntısı}}$$

---

## VI. İkiz Çekirdek Mimarisi ve Derin Mühendislik Katmanları

<table align="center" width="100%">
  <tr>
    <td width="50%" align="center" style="border: 1px solid rgba(255,255,255,0.08); padding: 12px; border-radius: 8px;">
      <img src="assets/kam_ebpf_neural_system.jpg" alt="eBPF Silicon Nervous System" width="100%" style="border-radius: 6px;" />
      <br/>
      <strong>Linux eBPF Sinir Kancası (&lt; 12 μs)</strong><br/>
      <small>Çekirdek olaylarını lock-free SPSC RingBuffer üzerinden sıfır kopyalama ile okur.</small>
    </td>
    <td width="50%" align="center" style="border: 1px solid rgba(255,255,255,0.08); padding: 12px; border-radius: 8px;">
      <img src="assets/kam_jit_self_healing.jpg" alt="In-Memory JIT Self-Healing" width="100%" style="border-radius: 6px;" />
      <br/>
      <strong>In-Memory C++20 JIT Onarımı (41.2 ms)</strong><br/>
      <small>Kurtarma kodunu bellekte derler, AST denetiminden geçirir ve canlı sürece bağlar.</small>
    </td>
  </tr>
</table>

### 1. Linux eBPF Çekirdek Telemetrisi (`ebpf_hooks/`)
Kullanıcı alanında (*user-space*) çalışan geleneksel izleyiciler çekirdek kilitlenmelerini yakalayamaz. KAM, doğrudan Linux çekirdeğine kancalanan (`kprobe:vfs_read`, `tracepoint:syscalls:sys_enter_ioctl`, `thermal_zone0`) eBPF programları kullanır. Olaylar, önbellek satırı hizalı (`alignas(64)`) kilitlenmesiz tek-yazıcı tek-okuyucu dairesel tampon (`LockFreeRingBuffer<KernelTelemetryEvent, 1024>`) ile sıfır bellek kopyalamasıyla C++20 ana motoruna aktarılır.

### 2. İki Aşamalı AST Sandboxing ve Bellek-İçi C++20 JIT Derleyici (`core/`, `python/kam/code_mutator.py`)
Üretilen kurtarma kodu diske (`SSD/eMMC`) yazılmaz:
- **Aşama 1 — Statik AST ve Sembol Doğrulama:** Yasaklı sistem çağrıları (`system(`, `fork(`, `execve(`, `popen(`, `rm -rf`) taranır ve `extern "C" int kam_entrypoint()` giriş sembolü doğrulanır.
- **Aşama 2 — RAM İçi Derleme ve Canary Testi:** `memfd_create` ile açılan anonim bellek tanımlayıcısı üzerinde `-std=c++20 -O3 -shared -fPIC` bayraklarıyla paylaşımlı nesne oluşturulur; izole Canary testinden sıfır dönüş kodu alındığında `dlopen`/`dlsym` ile canlı veriyoluna bağlanır.

### 3. Deterministik C++20 Lock-Free Bellek Arenası (`core/include/memory_arena.hpp`)
Görev-kritik uçuş ve seyrüsefer esnasında `malloc`/`new` çağrılarının yol açtığı bellek parçalanmasını (*heap fragmentation*) ve deterministik olmayan gecikmeleri önlemek için tüm tensör ve telemetri yapıları önceden tahsis edilmiş 64-bayt önbellek hizalı `MemoryArena` üzerinde sıfır tahsisatla (*zero-allocation*) çalışır.

### 4. Paylaşımlı Uzmanlı İnce Taneli Seyrek MoE (`python/kam/models/liquid_moe.py`)
Her çıkarım adımında **1 Paylaşımlı Uzman** (`TURKISH_SOVEREIGN_REASONING_SHARED_EXPERT`) daima aktif kalarak dilbilgisi ve temel mantık bütünlüğünü korurken, `SparseMoERouter` 8 donanım uzmanından (`RF_SPECTRUM_SDR_EXPERT`, `INERTIAL_IMU_FUSION_EXPERT`, `KERNEL_EBPF_DIAGNOSTIC_EXPERT`, `JIT_MUTATION_SECURITY_EXPERT`, `THERMAL_POWER_GOVERNOR_EXPERT`, `SWARM_MESH_CONSENSUS_EXPERT`, `OPTICAL_FLOW_SPATIAL_EXPERT`, `FRISTON_ACTIVE_INFERENCE_EXPERT`) yalnızca en uygun **Top-2** uzmanı ateşler ve uzman çökmesini önlemek için yardımcı yük dengeleme kaybı ($\mathcal{L}_{\text{aux}}$) hesaplar.

---

## VII. Otonom Sürü Ağı (Swarm Mesh) ve Elektronik Harp Dirayeti

<p align="center">
  <img src="assets/kam_swarm_active_inference.jpg" alt="Autonomous Swarm Active Inference in EW Storm" width="100%" style="border-radius: 8px; box-shadow: 0 10px 35px rgba(99, 102, 241, 0.25);" />
</p>

Yoğun elektronik harp karıştırması (`-95 dBm` gürültü tabanı) veya sürü lideri (`Alpha-1`) kaybı altında `SwarmMeshController` (`python/kam/swarm_mesh.py` ve `ew_mesh/`):

1. **Dağıtık Markov Battaniyesi ve Kolektif Entropi Minimizasyonu:**
   Sürüdeki her İHA düğümü $i$, batarya kapasitesi $B_i$ ve bağlantı sinyal-gürültü oranı $\text{SNR}_i$ üzerinden kendi yerel Varyasyonel Serbest Enerjisini hesaplar ve en düşük serbest enerjili birim yeni lider seçilir:

$$F_i = 0.05 + 1.8\left(\frac{100 - B_i}{100}\right) + 0.9\left(\frac{30 - \text{SNR}_i}{40}\right), \qquad \text{Lider}^* = \arg\min_{i \in \text{Alive}} F_i$$

2. **Altın Oran (Weyl Sequence) FHSS Spektral Sıçrama:**
   Karıştırılan frekans bandı terk edilerek, tahmin edilmesi imkânsız düşük tutarsızlıklı (*low-discrepancy*) Altın Oran eşleniği ($\varphi^{-1} = \frac{\sqrt{5}-1}{2} \approx 0.6180339887$) dizisiyle `868 MHz / 433 MHz` spektrumunda kesintisiz frekans sıçraması yapılır:

$$f_k = f_{\text{base}} + \left(\left(\phi_0 + k \cdot \varphi^{-1}\right) \bmod 1\right) \cdot \Delta B_{\text{MHz}}$$

---

## VIII. Hugging Face Model Ailesi ve Doğrulanmış Türkçe Bilgi Motoru

KAM modelleri resmi olarak **Hugging Face Hub** üzerinde açık ağırlıklı GGUF formatında yayınlanmıştır ve Ollama aracılığıyla tek komutla doğrudan çalıştırılabilir:

| Model | Boyut | Mimari ve Görev Profili | Hugging Face Deposu | Tek Satır Çalıştırma Komutu |
|:---|:---|:---|:---|:---|
| [**`kam:7b`**](https://huggingface.co/bahattinyunus/kam-7b-gguf) | `4.68 GB` | Qwen 2.5 7B Bilişsel Zihin (16K Bağlam, Duru Türkçe) | `bahattinyunus/kam-7b-gguf` | `ollama run hf.co/bahattinyunus/kam-7b-gguf` |
| [**`kam:r1`**](https://huggingface.co/bahattinyunus/kam-r1-gguf) | `4.68 GB` | DeepSeek-R1 7B Zincirleme Akıl Yürütme (`<think>`) | `bahattinyunus/kam-r1-gguf` | `ollama run hf.co/bahattinyunus/kam-r1-gguf` |
| [**`kam:1.5b`**](https://huggingface.co/bahattinyunus/kam-1.5b-edge-gguf) | `986 MB` | Qwen 2.5 1.5B Mikro Uç Donanım ve Spekülatif Taslak Modeli | `bahattinyunus/kam-1.5b-edge-gguf` | `ollama run hf.co/bahattinyunus/kam-1.5b-edge-gguf` |

### Halüsinasyon Önleyici Yerel Bilgi Motoru (`LocalKnowledgeEngine`)
`python/kam/knowledge_engine.py`, `data/kam_master_dataset.json` ve `data/kam_lore_dataset.json` veri tabanlarını kullanarak sorguları Türkçe karakter duyarsız kök eşleştirme ve semantik yakınlık algoritmasıyla tarar; kesin doğrulanmış mühendislik, sibernetik, coğrafya ve Dede Korkut hikmet kayıtlarını sistem istemine (*RAG Grounding*) enjekte ederek **%0 halüsinasyon** garantisi sağlar.

---

## IX. Komuta ve Kontrol Arayüzleri (Native PyQt6, Web Kokpiti, TUI ve JSON-RPC 2.0 MCP)

<p align="center">
  <img src="assets/kam_cyber_cockpit_hud.jpg" alt="KAM Cognitive Cockpit HUD" width="95%" style="border-radius: 8px; box-shadow: 0 0 35px rgba(0, 242, 254, 0.25);" />
</p>

### 1. Yerel Masaüstü Komuta Merkezi (`desktop_ui.py` — %100 Native PyQt6)
Tarayıcı veya web sunucusuna ihtiyaç duymadan doğrudan işletim sistemi üzerinde çalışan donanım ivmeli (`PyQt6` / `QPainter`) masaüstü uygulaması:
- **60 FPS Canlı Serbest Enerji Osiloskobu:** Varyasyonel serbest enerji $F(t)$ ve entropi $S(t)$ dalga formlarını gerçek zamanlı çizer.
- **Vektörel Monolitik KAM Mühür Kadranı:** Sistemin dirlik/kaos durumuna göre renk ve açısal hız değiştiren özel çizim radar kadranı.
- **Çoklu İş Parçacıklı (`QThread`) Zihin Akışı:** Arayüzü dondurmadan `kam:7b` ve `kam:r1` modelleriyle gerçek zamanlı token akışı (*streaming*) ve `<think>` CoT görselleştirmesi sunar.
- **Canlı C++20 JIT Kod Müfettişi ve Kriz Simülatörü:** 4 kriz senaryosunu tetikler, üretilen C++20 kodunu AST doğrulamasıyla birlikte anında görüntüler.

### 2. Web Kokpiti (`web_ui.py`) ve Terminal TUI (`cli.py --dashboard`)
Uzaktan yer kontrol istasyonları için `http://127.0.0.1:8080` üzerinde çalışan gerçek zamanlı Web Kokpiti ve düşük bant genişlikli SSH bağlantıları için konsol tabanlı canlı TUI gösterge paneli mevcuttur.

### 3. Model Context Protocol (MCP) JSON-RPC 2.0 Sunucusu (`cli.py --mcp`)
Harici otonom ajanların JSON-RPC 2.0 (`initialize`, `tools/list`, `tools/call`) üzerinden KAM çekirdeğiyle konuşabilmesi için yerleşik 7 araçlı MCP sunucusu (`python/kam/mcp_server.py`) içerir:

| MCP Aracı | Girdi Parametreleri | İşlev ve Yetki Tanımı |
| :--- | :--- | :--- |
| `read_telemetry` | `{}` | Çekirdek seviyesi eBPF telemetri verilerini, VFE değerini, NPU sıcaklığını ve aktif taşıyıcı hattı okur. |
| `calculate_entropy` | `{}` | Karl Friston Serbest Enerji Prensibi ile anlık sistem entropisini ve kaos durumunu hesaplar. |
| `compile_module` | `module_name`, `cpp_source` | C++20 kurtarma kodunu iki aşamalı AST güvenlik denetiminden geçirerek bellek içinde JIT derler. |
| `deploy_topology` | `module_name` | Derlenmiş paylaşımlı kütüphaneyi canlı çalışma alanına sıcak-yama (`hot-patch`) olarak bağlar. |
| `inspect_kernel` | `{}` | Linux eBPF `kprobe`/`tracepoint` kanca sayaçlarını, SPSC RingBuffer kapasitesini ve termal bölgeleri denetler. |
| `evaluate_efe_policies` | `crisis_hint` *(opsiyonel)* | Beklenen Serbest Enerji $G(\pi)$ üzerinden epistemik/pragmatik değer ayrıştırması yaparak optimal kurtarma politikasını seçer. |
| `optimize_edge_deployment` | `ram_mb`, `tdp_watts`, `npu_temp_c` | Donanım RAM/TDP/Sıcaklık zarfına göre en uygun KAM model, `imatrix` kuantizasyon ve spekülatif çözümleme planını çıkarır. |

---

## X. Bilişsel Döngü Diyagramları, Kriz Kataloğu ve Canlı Müdahale Kaydı

### 1. Otonom Bilişsel Döngü Akış Şeması
```mermaid
graph TD
    A["Fiziksel Veriyolu: LIDAR, SDR, IMU, CAN-0, UART-2"] --> B["Linux Çekirdeği: eBPF Kancaları (kprobe, tracepoint)"]
    B -->|Mikrosaniye Altı Gecikme < 12 us| C["Lock-Free SPSC RingBuffer (Proprioception)"]
    C --> D{"Aktif Çıkarım Motoru (VFE F & EFE G(pi))"}
    D -->|Varyasyonel Serbest Enerji: F| E["Kaos Dedektörü ve Bayesçi İnanç Güncellemesi"]
    E -->|Kritik Eşik: %80+ Entropi| F["Bilişsel Zihin (kam:r1 / kam:7b / Liquid-MoE)"]
    F -->|C++20 Kurtarma Kodu Sentezi| G["İki Aşamalı AST Sandboxing (0 İhlal)"]
    G --> H["Bellek-İçi JIT Derleyici (memfd_create + Clang -O3)"]
    H -->|dlopen / dlsym Sıcak-Yama (41.2 ms)| I["Topoloji Değişimi ve Göreve Devam"]
    I -->|Dirlik Restorasyonu: %15 -> %3 Entropi| A
```

### 2. Kriz Anında Milisaniye Seviyesi Zamanlama Diyagramı (Sequence Diagram)
```mermaid
sequenceDiagram
    autonumber
    participant HW as Donanım Veriyolu (UART-2 / SDR)
    participant EBPF as Linux eBPF Kancası
    participant FEP as Aktif Çıkarım (VFE/EFE)
    participant LLM as KAM Bilişsel Zihin (RK4 / R1)
    participant JIT as C++20 In-Memory JIT

    HW->>EBPF: UART-2 File Descriptor Kopuşu (EIO)
    EBPF->>FEP: SPSC RingBuffer Anomali Olayı (11.4 μs)
    FEP->>FEP: VFE F Fırlaması (%89 Entropi) & EFE G(pi) Hesabı
    FEP->>LLM: Optimal Politika: SDR_868MHZ_FHSS_REROUTE
    LLM->>JIT: sdr_fallback_node.cpp C++20 Kodu Sentezi
    JIT->>JIT: Statik AST Denetimi + memfd_create Clang -O3 (41.2 ms)
    JIT->>HW: dlopen/dlsym Canlı Topoloji Enjeksiyonu (/telemetry/sdr)
    HW->>FEP: Telemetri Restorasyonu -> Entropi %15 (Dirlik Sağlandı)
```

### 3. Yerleşik Otonom Kriz ve Kurtarma Kataloğu (`CodeMutator`)

| Kriz Senaryosu | Tetikleyici Anomali | EFE Seçilen Politika ($\pi^*$) | Sentezlenen C++20 JIT Modülü | Otonom Onarım Sonucu |
| :--- | :--- | :--- | :--- | :--- |
| **I. Telemetri Kopuşu** | `UART-2` hat kesintisi (`%89` Entropi) | `SDR_868MHZ_FHSS_REROUTE` | `sdr_fallback_node.cpp` | `868 MHz` SDR yedek telemetri köprüsüne canlı geçiş |
| **II. Elektronik Harp** | `-95 dBm` geniş bant RF karıştırma | `EW_ANTI_JAMMING_HOPPER` | `ew_fhss_hopper.cpp` | `433/868 MHz` Altın Oran FHSS spektral sıçrama |
| **III. Termal Pik** | NPU sıcaklığının `92.4 °C`'yi aşması | `THERMAL_INT4_AWQ_DOWNGRADE` | `thermal_vision_fallback.cpp` | `INT4-AWQ` kuantizasyona geçiş (`45W -> 14.5W`) |
| **IV. CAN-Bus Spoofing** | `CAN-0` üzerinde yetkisiz `0x1BA` çerçevesi | `CAN_EBPF_PACKET_QUARANTINE` | `can_firewall_filter.cpp` | Sahte ID'nin eBPF halkasında atomik karantinası |

### 4. Canlı Kriz Müdahale Çekirdek Kaydı
```text
================================================================================
  KAM BILISSEL VE KENDI KENDINI IYILESTIREN OTONOM SISTEM MOTORU
================================================================================
[KAM-CORE]   [OK]     Bilissel cekirdek devrede. eBPF kancalari kernel'a tutundu.
[KAM-CORE]   [SYNC]   Aktif Cikarim devrede. Sistem entropisi: %3 (Dirlik ve Nizam Saglam)
[NERV-SYS]   [WARN]   UYARI: UART-2 (Telemetri) verisi kesildi. File descriptor yanit vermiyor.
[NERV-SYS]   [CRIT]   Entropi %89 seviyesine firladi. Kritik esik asildi. Donanim anomalisi.
[KAM-EFE]    [POLICY] Beklenen Serbest Enerji G(pi) minimumu: SDR_868MHZ_FHSS_REROUTE
[KAM-AGENT]  [ROUTE]  UART-2 dugumu izole edildi. SDR 868MHz FHSS yedek hatti icin C++20 rotasi yaziliyor.
[JIT-COMP]   [BUILD]  Yeni topoloji (sdr_fallback_node.cpp) bellekte derleniyor... (41.2 ms)
[JIT-COMP]   [VERIFY] Iki Asamali Guvenlik Sandboxing: AST dogrulandi (0 ihlal), Canary testi basarili.
[KAM-CORE]   [REMAP]  Veriyolu Yeniden Yonlendirildi: /telemetry/uart -> /telemetry/sdr
[KAM-CORE]   [STABLE] Iyilesme basarili. Sistem entropisi: %15. Dirlik saglandi. Goreve devam ediliyor.
================================================================================
```

---

## XI. Desteklenen Donanım Platformları ve Repo Mimarisi

| Donanım Platformu | İşlemci ve Yapay Zeka Birimi | Görev Profili | İvmelendirme ve Bellek |
| :--- | :--- | :--- | :--- |
| **NVIDIA Jetson AGX Orin Industrial** | 12x Cortex-A78AE + 2048-core Ampere | Otonom Hava/Kara Platformları | 275 TOPS INT8 / FP16 TensorRT |
| **NVIDIA Jetson Orin NX / Nano** | 8x Cortex-A78AE + 1024-core Ampere | Taktik SİHA, Sürü İHA ve Dronlar | 100 TOPS INT4-AWQ / CUDA (`kam:edge-3b-moe`) |
| **NVIDIA GeForce RTX 5060 (Blackwell)** | 8 GB GDDR7 VRAM | Yer Kontrol İstasyonu ve Derin CoT | %100 CUDA (`kam:7b` + `kam:1.5b` Spekülatif) |
| **Raspberry Pi 5 / CM4 / Rock 5B** | ARM Cortex-A76 / A55 (NEON SIMD) | Düşük Güçlü Sensör ve Telemetri Düğümü | `kam:1.5b` (BitNet b1.58) + `libbpf` Kancası |

```text
kam/
├── assets/                  # 3B donanım, stealth gövde ve kokpit görselleri ile monolitik KAM mührü
├── core/                    # C++20 ana motoru, Lock-Free Memory Arena, Watchdog ve bellek-içi JIT derleyici
├── ebpf_hooks/              # Linux çekirdek kancaları (kprobe, tracepoint, SPSC RingBuffer)
├── active_inference/        # Karl Friston Varyasyonel/Beklenen Serbest Enerji (VFE/EFE) C++20 & CUDA çözücüsü
├── llm_agent/               # C++20 TensorRT/GGUF çıkarım katmanı ve JSON-RPC 2.0 MCP sunucusu
├── ros2_bridge/             # ROS2 / DDS dinamik konu yönlendirme (topic remapping) köprüsü
├── hardware/                # CAN-Bus, UART, SPI ve SDR 868MHz/433MHz donanım soyutlama katmanı
├── sensor_fusion/           # 6-DOF Genişletilmiş Kalman Filtresi (EKF) ve Mahalanobis spoofing tespiti
├── ew_mesh/                 # Elektronik harp spektral sıçrama (FHSS) ve Raft sürü mutabakatı
├── python/kam/              # PyQt6 masaüstü arayüzü, RK4 Liquid-MoE, EFE, BitNet/imatrix ve RAG motoru
│   ├── active_inference.py  # Varyasyonel (VFE) ve Çok Ufuklu Beklenen Serbest Enerji (EFE) motoru
│   ├── code_mutator.py      # C++20 kurtarma modülü sentezleyici ve İki Aşamalı AST Sandbox doğrulayıcı
│   ├── desktop_app.py       # %100 Yerel PyQt6 60 FPS osiloskoplu masaüstü komuta merkezi
│   ├── edge_optimizer.py    # Edge-Apex dağıtım planlayıcısı, BitNet b1.58, imatrix, Spekülatif Çözümleme ve GRPO
│   ├── knowledge_engine.py  # Halüsinasyon önleyici doğrulanmış Türkçe bilgi ve hikmet motoru
│   ├── mcp_server.py        # 7 araçlı JSON-RPC 2.0 Model Context Protocol (MCP) sunucusu
│   ├── sensor_fusion.py     # Kovaryans yayılımlı 6-DOF EKF, Mahalanobis kapısı ve Optik Akış ölü-hesaplama
│   ├── swarm_mesh.py        # Dağıtık Markov Battaniyesi sürü konsensüsü ve Altın Oran FHSS üreteci
│   └── models/              # RK4 çözücülü ve Paylaşımlı Uzmanlı (Shared-Expert) Liquid-SSM MoE mimarisi
├── models/                  # kam:7b ve kam:r1 Ollama Modelfile tanımları ve yerel ağırlık ikilileri
├── data/                    # Doğrulanmış Türkçe mühendislik, sibernetik ve Dede Korkut hikmet külliyatı
├── docs/                    # Felsefi manifesto, matematiksel mimari, MCP ve Edge-Apex yol haritası belgeleri
├── tests/                   # Birim ve entegrasyon test takımı (19/19 Başarılı)
├── desktop_ui.py            # %100 Yerel PyQt6 Masaüstü Komuta Merkezi başlatıcısı
├── web_ui.py                # Tarayıcı tabanlı Web Kokpiti başlatıcısı
├── cli.py                   # Komut satırı, TUI gösterge paneli, Edge-Plan ve MCP sunucu başlatıcısı
└── CMakeLists.txt           # C++20 derleme yapılandırması
```

---

## XII. Hızlı Başlangıç ve CLI Komut Rehberi

### 1. Yerel Masaüstü Komuta Merkezini Başlatın (Native Desktop UI)
```bash
python desktop_ui.py
```

### 2. Komut Satırı (CLI), Web Kokpiti, TUI ve Analiz Modları
```bash
# Tarayici tabanli Web Kokpiti (http://127.0.0.1:8080):
python web_ui.py

# Terminal canli TUI gosterge paneli:
python cli.py --dashboard

# RK4 Liquid-SSM Sparse MoE uzerinden gercek zamanli bilissel cikarim:
python cli.py --infer

# Kisitli donanim (Edge-Apex) dagitim plani, BitNet b1.58 ve Spekulatif Cozumleme analizi:
python cli.py --edge-plan

# Karl Friston Serbest Enerji minimizasyonu egitim dongusu:
python cli.py --train

# Kriz senaryosu simulasyonlari (uav_failure, jamming_attack, can_spoofing, thermal_runaway, swarm_loss):
python cli.py --scenario swarm_loss

# Model Context Protocol (MCP) JSON-RPC 2.0 sunucusu:
python cli.py --mcp
```

### 3. Modelleri Yerelde Derleyin veya Hugging Face Üzerinden Çalıştırın
```bash
# Dogrudan Hugging Face uzerinden calistirma:
ollama run hf.co/bahattinyunus/kam-7b-gguf
ollama run hf.co/bahattinyunus/kam-r1-gguf
ollama run hf.co/bahattinyunus/kam-1.5b-edge-gguf

# Yerel Modelfile ile derleme:
ollama create kam:7b -f models/Modelfile.kam
ollama create kam:r1 -f models/Modelfile.kam-r1
```

### 4. Otomatik Test Takımını ve C++20 Çekirdeğini Derleyin
```bash
# 19/19 Birim ve Entegrasyon Testi:
python -m pytest -v

# C++20 Motoru Derlemesi:
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

---

## XIII. Teknik Dokümantasyon ve Lisans

| Belge | Kapsam |
|:---|:---|
| [**`docs/PHILOSOPHY.md`**](docs/PHILOSOPHY.md) | Bilişsel Manifesto, Dede Korkut hikmeti, Karl Friston FEP ve sibernetik dirayet |
| [**`docs/ARCHITECTURE.md`**](docs/ARCHITECTURE.md) | Matematiksel spesifikasyon, Varyasyonel/Beklenen Serbest Enerji ve AST Sandboxing |
| [**`docs/ROADMAP.md`**](docs/ROADMAP.md) | Kısıtlı donanımda (Edge-AI) zirve bilişsel model mimarisi, Liquid-SSM MoE, GRPO ve BitNet yol haritası |
| [**`docs/MCP_SPEC.md`**](docs/MCP_SPEC.md) | Model Context Protocol (MCP) JSON-RPC 2.0 araç ve telemetri entegrasyonu |

- **Lisans:** [Apache License 2.0](LICENSE)
- **Geliştirici ve Baş Mimar:** [Bahattin Yunus ÇETİN (@bahattinyunus)](https://github.com/bahattinyunus)
