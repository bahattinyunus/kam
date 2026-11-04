# KAM Mimari ve Matematiksel Spesifikasyon Dokümanı

Bu belge, **KAM (Uç Donanımlar İçin Bilişsel ve Kendi Kendini İyileştiren Otonom Sistem Motoru)** çekirdeğinin matematiksel altyapısını, çekirdek (kernel) kancalarını ve bellek-içi derleyici mimarisini tanımlar.

---

## I. Aktif Çıkarım (Active Inference) ve Serbest Enerji Prensibi

KAM, sistem kararlılığını Karl Friston'un formüle ettiği **Serbest Enerji Prensibi (Free Energy Principle)** ile sağlar. Bir otonom sistemin görev bekası, çevresel ve donanımsal entropisini minimize etmesiyle mümkündür.

### 1.1. Varyasyonel Serbest Enerji (VFE)
Sistemin içsel inanç durumu $q(s)$ ile gerçek duyusal gözlemleri $o$ arasındaki serbest enerji $F$:

$$F = D_{KL}(q(s) \parallel p(s)) - \mathbb{E}_{q}[\ln p(o|s)]$$

Burada:
- $D_{KL}(q(s) \parallel p(s))$: **Karmaşıklık (Complexity)** cezasıdır. İçsel inancın öncül denge durumlarından ne kadar saptığını ölçer.
- $\mathbb{E}_{q}[\ln p(o|s)]$: **Doğruluk (Accuracy)** terimidir. Gözlemlerin mevcut durumla ne derece örtüştüğünü gösterir.

### 1.2. Beklenen Serbest Enerji (Expected Free Energy - EFE)
Gelecekteki politika adımı $\pi$ için öngörülen belirsizlik $G(\pi)$:

$$G(\pi) = \sum_{\tau} G(\pi, \tau)$$

$$G(\pi, \tau) \approx -\underbrace{\mathbb{E}_{Q(o_\tau, s_\tau|\pi)}[\ln Q(s_\tau|\pi) - \ln Q(s_\tau|o_\tau, \pi)]}_{\text{Epistemik Değer (Belirsizlik Giderme)}} - \underbrace{\mathbb{E}_{Q(o_\tau|\pi)}[\ln P(o_\tau)]}_{\text{Pragmatik Değer (Dirlik ve Görev İcrası)}}$$

KAM Bilişsel Ajanı, donanım çöktüğünde rastgele bir failsafe eylemi yerine, **$G(\pi)$ değerini minimize eden en uygun donanım düğümünü (SDR, FHSS, I2C, vb.) seçer.**

---

## II. Linux eBPF Sinir Sistemi Mimarisi

KAM, çekirdek seviyesindeki telemetriyi kullanıcı alanına aktarmak için Linux **eBPF (Extended Berkeley Packet Filter)** mimarisinden faydalanır:

```text
[Linux Kernel Space]
   ├── sys_enter_read / write (Tracepoint)
   ├── vfs_read / vfs_write (kprobe)
   └── thermal_zone_temp (uprobe / sysfs hook)
            │
            ▼ (Lock-Free eBPF Ring Buffer < 12 μs)
[KAM User-Space C++20 Core]
   ├── LockFreeRingBuffer<KernelTelemetryEvent, 1024>
   └── ActiveInferenceEngine::updateSensoryInput()
```

Kullanılan Lock-Free SPSC Ring Buffer, çalışma zamanında dinamik bellek tahsisatı (`malloc`/`new`) yapmadan mikrosaniye altı gecikmeyle çekirdek olaylarını bilişsel motora aktarır.

---

## III. İki Aşamalı Güvenlik Sandboxing ve JIT Sıcak Yama (Hot-Patching)

Otonom kod mutasyonu (`code_mutator.cpp` / `code_mutator.py`) aşağıdaki deterministik doğrulama hattından geçer:

1. **Statik AST ve Sembol Doğrulama:** Kaynak kodda yasaklı sistem çağrıları (`system`, `fork`, `execve`) denetlenir ve `kam_entrypoint` sembolü doğrulanır.
2. **Bellek-İçi Derleme:** Clang/LLVM `-O3 -shared -fPIC` bayraklarıyla paylaşımlı kütüphane doğrudan RAM içinde (`memfd_create`) oluşturulur.
3. **Canary Yürütme:** Modül canlı veriyoluna bağlanmadan önce izole bir sanal adres alanında test edilir.
4. **Atomik Geri Alma (Safe Rollback):** Yeni modül sıfır dönüş kodu (`0`) vermezse, sistem kesintisiz olarak bir önceki doğrulanmış ikiliye (`active_binary_`) geri döner.
