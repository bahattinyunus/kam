# KAM Model Context Protocol (MCP) Spesifikasyonu (v2.6 — 15 Araçlı Egemen Çekirdek)

KAM, Model Context Protocol (MCP) açık standardını JSON-RPC 2.0 (`initialize`, `tools/list`, `tools/call`) üzerinden destekleyerek yerel ve uç otonom ajanların Linux eBPF telemetrisine, Karl Friston VFE/EFE motoruna, bellek-içi C++20 JIT derleyiciye ve siber-fiziksel savunma kalkanlarına doğrudan erişmesini sağlar.

---

## I. Tanımlı 15 MCP Aracı (Tools)

| # | MCP Aracı | Girdi Şeması | İşlev ve Yetki Tanımı |
| :--- | :--- | :--- | :--- |
| **1** | `read_telemetry` | `{}` | Çekirdek seviyesi eBPF telemetri verilerini, VFE değerini, NPU sıcaklığını ve aktif taşıyıcı hattı okur. |
| **2** | `calculate_entropy` | `{}` | Karl Friston Serbest Enerji Prensibi ile anlık sistem entropisini ve kaos durumunu hesaplar. |
| **3** | `compile_module` | `module_name`, `cpp_source` | C++20 kurtarma kodunu iki aşamalı AST güvenlik denetiminden geçirerek bellek içinde JIT derler. |
| **4** | `deploy_topology` | `module_name` | Derlenmiş paylaşımlı kütüphaneyi canlı çalışma alanına sıcak-yama (`hot-patch`) olarak bağlar. |
| **5** | `inspect_kernel` | `{}` | Linux eBPF `kprobe`/`tracepoint` kanca sayaçlarını, SPSC RingBuffer kapasitesini ve termal bölgeleri denetler. |
| **6** | `evaluate_efe_policies` | `crisis_hint` | Beklenen Serbest Enerji $G(\pi)$ üzerinden epistemik/pragmatik değer ayrıştırması yaparak optimal kurtarma politikasını seçer. |
| **7** | `optimize_edge_deployment` | `ram_mb`, `tdp_watts`, `npu_temp_c` | Donanım RAM/TDP/Sıcaklık zarfına göre en uygun KAM model, `imatrix` kuantizasyon ve spekülatif çözümleme planını çıkarır. |
| **8** | `plan_tactical_3d_route` | `target_x_km`, `target_y_km`, `num_segments` | 3-Boyutlu SİHA arazi maskeleme (*Nap-of-the-Earth*) ve $1/R^4$ radar sönümleme denklemiyle en güvenli stealth uçuş koridorunu hesaplar. |
| **9** | `evaluate_lyapunov_council` | `crisis_hint` | 5-Modelli Bilişsel Kurul (**Bilge** EFE + **Gözcü** Lyapunov CLF/TTA + **Demirci** C++20 JIT) ortak kriz kararını sentezler. |
| **10** | `classify_ew_radar_pdw` | `rf_ghz`, `pri_us`, `pw_us`, `aoa_deg`, `chirp_bw_mhz`, `agility_score` | Bilişsel EW PDW radar darbe analizi yapar, bilinmeyen LPI emiterleri çevrimiçi öğrenir ve DRFM aldatma + çentik (*notch*) frekans planı üretir. |
| **11** | `orchestrate_intent_c2` | `commander_intent`, `target_x_km`, `target_y_km` | Yüksek seviyeli Türkçe komutan niyetini (*Commander's Intent*) bağımlılık sıralı görev çizgesine (*Task DAG*) böler ve çoklu-alan filosuna EFE ile tahsis eder. |
| **12** | `verify_cbf_safety_shield` | `target_altitude_agl_m`, `airspeed_mps`, `bank_angle_deg`, `battery_pct` | DARPA ANSR & Kontrol Bariyer Fonksiyonu (CBF) Nöro-Sembolik Kalkanı ile kontrol komutlarını doğrular, ihlalleri güvenli zarfa izdüşürür. |
| **13** | `verify_byzantine_pqc_swarm` | `inject_byzantine_traitor` | Bizans Hata Toleranslı (BFT) Jensen-Shannon diverjans kapısı ($D_{\text{JS}} > 0.18$) ve ML-KEM-768 (Kyber $q=3329$) kuantum-sonrası kriptografi ile sürüdeki hain düğümleri karantinaya alır. |
| **14** | `localize_terrain_trn` | `true_x_km`, `true_y_km`, `drifted_ins_x_km`, `drifted_ins_y_km` | GPS/GNSS-Kör ortamda %100 pasif (0W RF) TERCOM/SITAN Sayısal Yükselti Modeli (DEM) korelasyonu ile INS kaymasını %99.4+ sönümler. |
| **15** | `reconfigure_damaged_actuators` | `jammed_actuator_index`, `jammed_angle_rad` | Kinetik kanatçık/servo sıkışması veya motor kaybında Ağırlıklı Sözde-Ters (*Weighted Moore-Penrose Pseudo-Inverse*) matrisiyle kontrol otoritesini sağlam yüzeylere yeniden dağıtır. |

---

## II. Kullanım ve İstemci Entegrasyonu

MCP sunucusunu başlatmak veya 15 aracın tam sistem denetimini çalıştırmak için:
```bash
python cli.py --mcp
python cli.py --full-audit
```

Harici bir MCP istemcisi konfigürasyonuna eklemek için:
```json
{
  "mcpServers": {
    "kam-engine": {
      "command": "python",
      "args": ["<PATH_TO_KAM>/cli.py", "--mcp"]
    }
  }
}
```
