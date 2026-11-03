#!/usr/bin/env python3
"""
KAM Bilisel Zihin ve Saman Persona Egitim & Yapilandirma Scripti
Ollama uzerinde qwen2.5:7b tabanli kam:7b ozel modelini derler ve kaydeder.
"""
import sys
import os
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def train_kam_persona():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    modelfile_path = os.path.join(root_dir, "models", "Modelfile.kam")
    lore_path = os.path.join(root_dir, "data", "kam_lore_dataset.json")

    print("\033[1;36m" + "=" * 65 + "\033[0m")
    print("\033[1;35m  🐺 KAM BİLİŞSEL ZİHİN: ŞAMAN PERSONA MODEL DERLEME (kam:7b) \033[0m")
    print("\033[1;36m" + "=" * 65 + "\033[0m")
    print(f"  • Modelfile: {modelfile_path}")
    print(f"  • Kadim Bilgi Korpusu: {lore_path}")
    print("  • Taban Model: qwen2.5:7b (NVIDIA RTX VRAM Hızlandırmalı)")
    print("-" * 65 + "\n")

    if not os.path.exists(modelfile_path):
        print(f"\033[1;31m[HATA] Modelfile bulunamadi: {modelfile_path}\033[0m")
        return False

    print("\033[1;33m[KAM] Ollama üzerinde kam:7b modeli oluşturuluyor...\033[0m")
    try:
        res = subprocess.run(["ollama", "create", "kam:7b", "-f", modelfile_path], capture_output=True, text=True, check=True)
        print(res.stdout)
        print("\033[1;32m[BASARILI] kam:7b ozel bilişsel modeli başarıyla derlendi ve belleğe yazıldı!\033[0m")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\033[1;31m[HATA] Model olusturulamadi: {e.stderr}\033[0m")
        return False

if __name__ == "__main__":
    train_kam_persona()
