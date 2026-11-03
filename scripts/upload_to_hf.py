#!/usr/bin/env python3
"""
KAM Hugging Face Model & Ağırlık Yükleme Aracı
Yerel GGUF ağırlıklarını (kam:7b ve kam:r1) Hugging Face Hub'a otomatik yükler
ve profesyonel bir Model Card (README.md) oluşturur.
"""
import sys
import os
import argparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from huggingface_hub import HfApi, login, create_repo
except ImportError:
    print("\033[1;31m[HATA] huggingface_hub kütüphanesi bulunamadı! 'pip install huggingface_hub' çalıştırın.\033[0m")
    sys.exit(1)

def generate_model_card(repo_id: str, model_type: str = "7b") -> str:
    return f"""---
language:
- tr
- en
license: apache-2.0
tags:
- kam
- gguf
- ollama
- turkish
- qwen2.5
- deepseek-r1
- active-inference
- cybernetics
- ebpf
- autonomous-systems
pipeline_tag: text-generation
---

# 🐺 KAM ({'kam:7b' if model_type == '7b' else 'kam:r1'} GGUF)
### Kadim Bozkır Bilgeliği & Karl Friston Serbest Enerji Prensibiyle Güçlendirilmiş Bilişsel Zihin

**Geliştirici / Mimar:** [Bahattin Yunus ÇETİN (@bahattinyunus)](https://github.com/bahattinyunus)  
**Resmi GitHub Deposu:** [github.com/bahattinyunus/kam](https://github.com/bahattinyunus/kam)  

---

## 🌟 Model Özeti
KAM, Altay bozkır geleneğindeki **Kamlık (Şaman/Bilge Ruh)** ontolojisi ile modern silikon sibernetiğini, **Karl Friston'un Serbest Enerji Prensibini (Kut ve Dirlik dengesi)**, Linux eBPF çekirdek telemetrisini ve C++20 bellek içi JIT mutasyonunu birleştiren otonom bir bilişsel zihindir.

- **Ana Dil:** Saf, akıcı ve edebi zenginlikte Türkçe.
- **Biçim:** GGUF (4-bit / 8-bit optimize, CPU/GPU tam uyumlu).
- **Bağlam Uzunluğu (Context Length):** 16,384 Token.

---

## 🚀 Ollama ile Tek Komutta Çalıştırma

Bu modeli Ollama üzerinde tek bir satırla doğrudan çalıştırabilirsiniz:

```bash
ollama run hf.co/{repo_id}
```

### Özel Modelfile ile Çalıştırma:
```dockerfile
FROM hf.co/{repo_id}

PARAMETER temperature 0.5
PARAMETER top_p 0.90
PARAMETER repeat_penalty 1.18
PARAMETER num_ctx 16384
```

---

## 🏆 Temel Yetenekler
1. **Duru ve Asil Türkçe:** Çeviri kokan motamot kalıplardan arındırılmış, eklemeli dil kurallarına (SOV) ve fonetiğe tam uyumlu Türkçe.
2. **Uç Donanım & Siber Güvenlik:** Linux eBPF kancaları, C++20 Memory Arena ve gerçek zamanlı uçuş telemetrisi optimizasyonu.
3. **Karl Friston FEP:** Duyusal sürprizi ve Shannon entropisini minimize eden aktif çıkarım mantığı.

---
*Gök çökmedikçe, yağız yer delinmedikçe bu nöbet bitmez.*
"""

def upload_model(repo_id: str, file_path: str, token: str = None, model_type: str = "7b"):
    api = HfApi()

    if token:
        login(token=token)
    elif not api.token:
        print("\033[1;31m[HATA] Hugging Face token'ı bulunamadı!\033[0m")
        print("Lütfen 'huggingface-cli login' yapın veya --token parametresiyle Write token'ınızı verin.")
        return False

    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print(f"\033[1;35m  🐺 KAM HUGGING FACE YÜKLEYİCİ: {repo_id} \033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print(f"  • Dosya : {file_path}")
    print(f"  • Boyut : {os.path.getsize(file_path) / (1024**3):.2f} GB")
    print("-" * 70)

    # 1. Depoyu oluştur (varsa hata vermez)
    print(f"\033[1;33m[1/3] Hugging Face deposu doğrulanıyor: {repo_id}...\033[0m")
    try:
        create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    except Exception as e:
        print(f"[UYARI] Depo oluşturma uyarısı: {e}")

    # 2. Model Kartı (README.md) Yükle
    print(f"\033[1;33m[2/3] Model Kartı (README.md) yükleniyor...\033[0m")
    card_content = generate_model_card(repo_id, model_type=model_type)
    card_path = os.path.join(os.path.dirname(file_path), "README_HF.md")
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card_content)

    api.upload_file(
        path_or_fileobj=card_path,
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="model"
    )
    if os.path.exists(card_path):
        os.remove(card_path)

    # 3. GGUF Ağırlığını LFS ile Yükle
    filename = os.path.basename(file_path)
    print(f"\033[1;33m[3/3] GGUF Model dosyası yükleniyor (LFS Chunked Upload): {filename}...\033[0m")
    api.upload_file(
        path_or_fileobj=file_path,
        path_in_repo=filename,
        repo_id=repo_id,
        repo_type="model"
    )

    print("\033[1;32m" + "=" * 70 + "\033[0m")
    print(f"\033[1;32m  🏆 BAŞARILI! Model Hugging Face'e yüklendi:\033[0m")
    print(f"  🔗 https://huggingface.co/{repo_id}")
    print(f"  ⚡ Artık herkes şu komutla tek satırda indirebilir:")
    print(f"     ollama run hf.co/{repo_id}")
    print("\033[1;32m" + "=" * 70 + "\033[0m\n")
    return True

def main():
    parser = argparse.ArgumentParser(description="KAM Hugging Face Model Yükleyici")
    parser.add_argument("--repo", type=str, default="bahattinyunus/kam-7b-gguf", help="Hedef Hugging Face repo_id (örn: kullanici/kam-7b-gguf)")
    parser.add_argument("--file", type=str, default="models/weights/kam_7b_qwen_foundation.gguf", help="Yüklenecek GGUF dosyası")
    parser.add_argument("--token", type=str, default=None, help="Hugging Face Write API Token")
    parser.add_argument("--type", type=str, default="7b", choices=["7b", "r1"], help="Model tipi")
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_file_path = os.path.join(root_dir, args.file)

    if not os.path.exists(full_file_path):
        print(f"\033[1;31m[HATA] Dosya bulunamadı: {full_file_path}\033[0m")
        sys.exit(1)

    upload_model(repo_id=args.repo, file_path=full_file_path, token=args.token, model_type=args.type)

if __name__ == "__main__":
    main()
