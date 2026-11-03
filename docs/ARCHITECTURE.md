# KAM Mimari ve Matematiksel Spesifikasyon Dokümanı 🐺⚡

Bu belge, **KAM (Uç Donanımlar İçin Bilişsel ve Kendi Kendini İyileştiren Otonom Sistem Motoru)** çekirdeğinin matematiksel altyapısını, kernel kancalarını ve bellek-içi derleyici mimarisini açıklar.

---

## 1. Aktif Çıkarım (Active Inference) ve Serbest Enerji Prensibi

KAM, sistem kararlılığını Karl Friston'un formüle ettiği **Serbest Enerji Prensibi (Free Energy Principle)** ile sağlar. Bir otonom sistemin hayatta kalması, çevresel ve donanımsal entropisini minimize etmesiyle mümkündür.

### 1.1. Varyasyonel Serbest Enerji (VFE)
Sistemin içsel inanç durumu $q(s)$ ile gerçek duyusal gözlemleri $o$ arasındaki serbest enerji $F$:

$$F = D_{KL}(q(s) \parallel p(s)) - \mathbb{E}_{q}[\ln p(o|s)]$$

Burada:
- $D_{KL}(q(s) \parallel p(s))$: **Karmaşıklık (Complexity)** cezasıdır. İçsel inancın öncül durumlardan ne kadar saptığını ölçer.
- $\mathbb{E}_{q}[\ln p(o|s)]$: **Doğruluk (Accuracy)** terimidir. Gözlemlerin mevcut durumla ne derece örtüştüğünü gösterir.

### 1.2. Beklenen Serbest Enerji (Expected Free Energy - EFE)
Gelecekteki politika adımı $\pi$ için öngörülen belirsizlik $G(\pi)$:

$$G(\pi) = \sum_{\tau} G(\pi, \tau)$$

$$G(\pi, \tau) \approx -\underbrace{\mathbb{E}_{Q(o_\tau, s_\tau|\pi)}[\ln Q(s_\tau|\pi) - \ln Q(s_\tau|o_\tau, \pi)]}_{\text{Epistemik Değer (Belirsizlik Giderme)}} - \underbrace{\mathbb{E}_{Q(o_\tau|\pi)}[\ln P(o_\tau)]}_{\text{Pragmatik Değer (Hedefe Ulaşma)}}$$

KAM Ajanı, donanım çöktüğünde rastgele bir failsafe eylemi yerine, **$G(\pi)$ değerini minimize eden en uygun donanım düğümünü (SDR, I2C, vb.) seçer.**

---

## 2. eBPF Sinir Sistemi Mimarisi

KAM, çekirdek seviyesindeki telemetriyi kullanıcı alanına aktarmak için Linux **eBPF (Extended Berkeley Packet Filter)** mimarisinden faydalanır:

```
[Linux Kernel Space]
   ├── sys_enter_read / write (Tracepoint)
   ├── vfs_read / vfs_write (kprobe)
   └── thermal_zone_temp (uprobe / sysfs hook)
            │
            ▼ (Lock-Free eBPF Ring Buffer)
[KAM User-Space C++20 Core]
   ├── LockFreeRingBuffer<KernelTelemetryEvent, 1024>
   └── ActiveInferenceEngine::updateSensoryInput()
```

Kullanılan Lock-Free SPSC Ring Buffer, bellek tahsisatı (dynamic allocation) yapmadan mikrosaniye altı gecikmeyle çekirdek olaylarını bilişsel motora aktarır.

---

## 3. İki Aşamalı Güvenlik Sandboxing & JIT Sıcak Yama (Hot-Patching)

Otonom kod mutasyonu (`code_mutator.cpp`) risk barındırır. KAM bu riski şu adımlarla bertaraf eder:

1. **AST Doğrulama:** Kaynak kodda tehlikeli bellek ihlali yapabilecek kalıplar ve giriş sembolleri (`kam_entrypoint`) denetlenir.
2. **Bellek İçi Derleme:** Clang/GCC `-O3 -shared -fPIC` bayraklarıyla paylaşımlı obje oluşturulur.
3. **Canary Çalıştırma:** Modül canlı veriyoluna bağlanmadan önce izole bir fonksiyonda yoklanır.
4. **Güvenli Geri Alma (Safe Rollback):** Eğer yeni modül sıfır dönüş kodu vermezse, sistem otomatik olarak bir önceki çalışan güvenli ikiliye (`active_binary_`) geri döner.
