# KAM Model Context Protocol (MCP) Spesifikasyonu 📡

KAM, Anthropic / Model Context Protocol (MCP) açık standardını destekleyerek yerel ve uç LLM modellerinin otonom sistem telemetrisine doğrudan erişmesini sağlar.

---

## 🛠️ Tanımlı MCP Araçları (Tools)

### 1. `read_telemetry`
- **Açıklama:** Kernel seviyesi eBPF telemetri verilerini, dosya tanımlayıcı sağlık durumunu ve aktif hatları okur.
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
- **Açıklama:** Karl Friston'un serbest enerji prensibi ile anlık sistem kaos yüzdesini hesaplar.
- **Örnek Yanıt:**
```json
{
  "entropy_pct": 3,
  "chaos_detected": false
}
```

### 3. `compile_module`
- **Açıklama:** Üretilen C++20 kaynak kodunu bellek içinde JIT derler ve doğrular.
- **Parametreler:**
  - `module_name` (string): Modül adı (örn: `sdr_fallback_node`).
  - `cpp_source` (string): C++20 kaynak kodu.

### 4. `deploy_topology`
- **Açıklama:** Canlı ROS2/C++ topolojisini günceller ve yeni düğümü sisteme bağlar.
- **Parametreler:**
  - `module_name` (string): Yüklenecek modül adı.

---

## ⚡ Kullanım ve Entegrasyon
MCP modunda çalıştırmak için:
```bash
python cli.py --mcp
```
Claude Desktop veya harici bir MCP istemcisi konfigürasyonuna eklemek için:
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
