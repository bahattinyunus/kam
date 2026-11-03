# 🧠 KAM Modelleri ve Ağırlık Yönetimi (Model Weights & Blueprints)

Bu dizin, KAM'ın yerel bilişsel motorlarının (`kam:r1` ve `kam:7b`) yapılandırma dosyalarını (Modelfile) ve yerel GGUF model ağırlıklarını barındırır.

---

## 📂 Dizin Yapısı

```bash
models/
├── weights/                       # [YERELDE BARINDIRILIR - GITIGNORE İLE KORUNUR]
│   ├── kam_r1_deepseek_7b.gguf    # 4.68 GB DeepSeek-R1 7B Ağırlığı
│   ├── kam_7b_qwen_foundation.gguf# 4.68 GB Qwen 2.5 7B Ağırlığı
│   └── qwen_1.5b_lightweight_fallback.gguf # 986 MB Hafif Yedek Model Ağırlığı
├── Modelfile.kam-r1               # DeepSeek-R1 Çevrimiçi/Standart Reçete
├── Modelfile.kam-r1-offline       # Doğrudan weights/ altındaki GGUF'tan %100 Çevrimdışı Derleme
├── Modelfile.kam                  # Qwen 2.5 7B Standart Reçete
├── Modelfile.kam-offline          # Doğrudan weights/ altındaki GGUF'tan %100 Çevrimdışı Derleme
└── README.md                      # Bu doküman
```

---

## 🛡️ GitHub 100 MB Sınırı ve Güvenlik

GitHub, 100 MB üzerindeki dosyaları kabul etmez. Bu sebeple `.gitignore` dosyasında:
```gitignore
models/weights/
*.gguf
*.bin
*.safetensors
```
kuralları tanımlanmıştır. 

**Sonuç:** Model ağırlıkları bilgisayarınızda **fiziksel olarak `models/weights/` altında (3 model - toplam yaklaşık 10.35 GB)** durur, ancak GitHub'a push yaparken asla Git geçmişine girmez ve push hatası oluşturmaz.

---

## ⚡ Modelleri Derleme Seçenekleri

### 1. Çevrimdışı Mod (İnternetsiz - models/weights altındaki GGUF'tan):
```bash
# DeepSeek-R1 Akıl Yürütme Motoru (KAM-R1):
ollama create kam:r1 -f models/Modelfile.kam-r1-offline

# Qwen 2.5 16K Bilişsel Şaman Motoru (KAM-7B):
ollama create kam:7b -f models/Modelfile.kam-offline
```

### 2. Standart Mod (Ollama Registry Üzerinden):
```bash
ollama create kam:r1 -f models/Modelfile.kam-r1
ollama create kam:7b -f models/Modelfile.kam
```
