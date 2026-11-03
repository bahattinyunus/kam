#!/usr/bin/env python3
"""
KAM Bilişsel Zihin ve Şaman Persona Eğitim & Yapılandırma Betiği
Ollama üzerinde yerel ağırlıklar (GGUF) veya online taban modeller üzerinden
kam:r1 (DeepSeek-R1 CoT Akıl Yürütme) ve kam:7b (Qwen 2.5 Hızlı Bilişsel Motor) modellerini derler.
"""
import sys
import os
import argparse
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def train_model(model_name: str, use_offline: bool = True) -> bool:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(root_dir, "models")
    weights_dir = os.path.join(models_dir, "weights")

    if model_name in ["kam:r1", "kam-r1", "r1"]:
        tag = "kam:r1"
        offline_file = os.path.join(models_dir, "Modelfile.kam-r1-offline")
        online_file = os.path.join(models_dir, "Modelfile.kam-r1")
        weight_file = os.path.join(weights_dir, "kam_r1_deepseek_7b.gguf")
        desc = "DeepSeek-R1 7B Zincirleme Akıl Yürütme (Chain-of-Thought CoT)"
    elif model_name in ["kam:7b", "kam-7b", "7b", "kam"]:
        tag = "kam:7b"
        offline_file = os.path.join(models_dir, "Modelfile.kam-offline")
        online_file = os.path.join(models_dir, "Modelfile.kam")
        weight_file = os.path.join(weights_dir, "kam_7b_qwen_foundation.gguf")
        desc = "Qwen 2.5 7B Yüksek Hızlı Bilişsel Şaman Motoru"
    else:
        print(f"\033[1;31m[HATA] Bilinmeyen model adı: {model_name}. ('kam:r1' veya 'kam:7b' seçiniz)\033[0m")
        return False

    # Modelfile seçimi (çevrimdışı GGUF var mı?)
    if use_offline and os.path.exists(weight_file) and os.path.exists(offline_file):
        modelfile_path = offline_file
        mode_str = f"ÇEVRİMDISI YEREL GGUF ({os.path.basename(weight_file)})"
    else:
        modelfile_path = online_file
        mode_str = "ONLİNE REGISTRY REPO"

    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print(f"\033[1;35m  🐺 KAM BİLİŞSEL DERLEME: {tag} ({desc}) \033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print(f"  • Modelfile : {modelfile_path}")
    print(f"  • Kaynak    : {mode_str}")
    print(f"  • Hedef Tag : {tag}")
    print("-" * 70)

    if not os.path.exists(modelfile_path):
        print(f"\033[1;31m[HATA] Modelfile bulunamadı: {modelfile_path}\033[0m")
        return False

    print(f"\033[1;33m[KAM] Ollama üzerinde '{tag}' modeli inşa ediliyor...\033[0m")
    try:
        # Modelfile'ın bulunduğu dizinde çalıştır ki göreceli path'ler (./weights/...) doğru çözülsün
        res = subprocess.run(
            ["ollama", "create", tag, "-f", os.path.basename(modelfile_path)],
            cwd=models_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )
        print(res.stdout)
        print(f"\033[1;32m[BAŞARILI] {tag} modeli başarıyla derlendi ve Ollama motoruna kaydedildi!\033[0m\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\033[1;31m[HATA] Model oluşturulamadı: {e.stderr}\033[0m\n")
        return False

def main():
    parser = argparse.ArgumentParser(description="KAM Şaman & Bilişsel Model Derleyici")
    parser.add_argument("--model", type=str, default="all", choices=["all", "kam:r1", "kam:7b", "r1", "7b"],
                        help="Derlenecek model (all, kam:r1, kam:7b)")
    parser.add_argument("--online", action="store_true", help="Yerel GGUF yerine online Ollama registry tabanını kullan")
    args = parser.parse_args()

    use_offline = not args.online

    if args.model in ["all"]:
        s1 = train_model("kam:r1", use_offline=use_offline)
        s2 = train_model("kam:7b", use_offline=use_offline)
        if s1 and s2:
            print("\033[1;32m[TAMAMLANDI] Hem kam:r1 hem de kam:7b zihinleri hazır ve göreve amade!\033[0m")
    else:
        train_model(args.model, use_offline=use_offline)

if __name__ == "__main__":
    main()
