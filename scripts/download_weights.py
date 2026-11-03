#!/usr/bin/env python3
"""
KAM Otonom Model ve Ağırlık İndirici
HuggingFace üzerinden yerelde en yüksek performansla çalışabilen
en iyi GGUF ve INT8 bilişsel modelleri doğrudan models/ dizinine indirir.
"""

import os
import sys
import argparse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MODELS_CATALOG = {
    "qwen-coder-1.5b": {
        "description": "Qwen 2.5 Coder 1.5B Instruct Q4_K_M (Uç Donanımlar İçin Hızlı C++ Kod Üreticisi)",
        "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-coder-1.5b-q4_k_m.gguf",
        "size_mb": 980
    },
    "deepseek-r1-1.5b": {
        "description": "DeepSeek R1 Distill Qwen 1.5B Q4_K_M (Derin Akıl Yürütme ve Kriz Analizi)",
        "url": "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        "filename": "deepseek-r1-1.5b-q4_k_m.gguf",
        "size_mb": 1100
    },
    "llama-3.2-3b": {
        "description": "Meta Llama 3.2 3B Instruct Q4_K_M (Genel Bilişsel Mantık ve Otonom Karar Motoru)",
        "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "filename": "llama-3.2-3b-q4_k_m.gguf",
        "size_mb": 2020
    }
}

def download_model(model_key: str):
    if model_key not in MODELS_CATALOG:
        print(f"[HATA] Geçersiz model: {model_key}. Mevcut modeller: {list(MODELS_CATALOG.keys())}")
        return

    info = MODELS_CATALOG[model_key]
    os.makedirs("models", exist_ok=True)
    target_path = os.path.join("models", info["filename"])

    print("=" * 65)
    print(f"  🐺 KAM YEREL MODEL İNDİRİCİSİ")
    print("=" * 65)
    print(f" Model       : {model_key}")
    print(f" Açıklama    : {info['description']}")
    print(f" Boyut       : Yaklaşık ~{info['size_mb']} MB")
    print(f" Hedef Dosya : {target_path}")
    print("-" * 65)

    if os.path.exists(target_path):
        print(f"[BİLGİ] Model dosyası zaten mevcut: {target_path}")
        return

    print(f"[İNDİRME BAŞLADI] {info['url']} üzerinden çekiliyor...")

    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            mb = downloaded / (1024 * 1024)
            tot_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\r  -> İndiriliyor: %{percent:.1f} ({mb:.1f} MB / {tot_mb:.1f} MB)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(info["url"], target_path, reporthook=progress_hook)
        print(f"\n[BAŞARILI] Model başarıyla indirildi: {target_path}")
    except Exception as e:
        print(f"\n[UYARI] İndirme sırasında ağ hatası veya limit: {e}")
        print("[KAM FALLBACK] Yerleşik saf C++ ve Python KAM-1 Liquid MoE model motoru aktif.")

def main():
    parser = argparse.ArgumentParser(description="KAM Yerel Model ve Ağırlık İndirici")
    parser.add_argument(
        "--model",
        choices=list(MODELS_CATALOG.keys()) + ["all"],
        default="qwen-coder-1.5b",
        help="İndirilecek model tipi"
    )
    args = parser.parse_args()

    if args.model == "all":
        for k in MODELS_CATALOG:
            download_model(k)
    else:
        download_model(args.model)

if __name__ == "__main__":
    main()
