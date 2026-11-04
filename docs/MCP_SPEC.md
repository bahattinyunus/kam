# KAM Model Context Protocol (MCP) Spesifikasyonu

KAM, Model Context Protocol (MCP) açık standardını JSON-RPC 2.0 üzerinden destekleyerek yerel ve uç otonom ajanların sistem telemetrisine, entropi hesabına ve bellek-içi derleyiciye doğrudan erişmesini sağlar.

---

## I. Tanımlı MCP Araçları (Tools)

### 1. `read_telemetry`
- **Açıklama:** Çekirdek seviyesi eBPF telemetri verilerini, dosya tanımlayıcı sağlık durumunu ve aktif iletişim hatlarını okur.
- **Parametreler:** Yok.
- **Örnek Yanıt:**
```json
{
  "active_telemetry": "UART-2",
  "entropy": 0.03,
  "status": "HEALTHY"
}
```

### 2. `calculate_entropy`
- **Açıklama:** Karl Friston'un Serbest Enerji Prensibi ile anlık sistem entropi yüzdesini ve anomali durumunu hesaplar.
- **Örnek Yanıt:**
```json
{
  "entropy_pct": 3,
  "chaos_detected": false
}
```

### 3. `compile_module`
- **Açıklama:** Üretilen C++20 kaynak kodunu AST güvenlik denetiminden geçirerek bellek içinde JIT derler.
- **Parametreler:**
  - `module_name` (`string`): Modül adı (örn. `sdr_fallback_node`).
  - `cpp_source` (`string`): C++20 kaynak kodu.

### 4. `deploy_topology`
- **Açıklama:** Derlenmiş paylaşımlı kütüphaneyi canlı çalışma alanına sıcak-yama (`hot-patch`) olarak bağlar ve veri yolunu yeniden yönlendirir.
- **Parametreler:**
  - `module_name` (`string`): Yüklenecek modül adı.

### 5. `inspect_kernel`
- **Açıklama:** Linux eBPF `kprobe`/`tracepoint` kanca sayaçlarını ve NPU termal bölgelerini denetler.

---

## II. Kullanım ve İstemci Entegrasyonu

MCP sunucusunu `stdio` modunda başlatmak için:
```bash
python cli.py --mcp
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
