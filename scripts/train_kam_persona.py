#!/usr/bin/env python3
"""
KAM Bilişsel Zihin ve Şaman Persona Eğitim & Yapılandırma Betiği
Ollama üzerinde yerel ağırlıklar (GGUF) veya online taban modeller üzerinden
7 üyeli Egemen KAM Model Ailesini (kam:apex, kam:7b, kam:r1, kam:coder, kam:coder-nano, kam:r1-nano, kam:1.5b) derler.
"""
import sys
import os
import argparse
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def train_model(model_name: str, use_offline: bool = False) -> bool:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(root_dir, "models")
    weights_dir = os.path.join(models_dir, "weights")

    if model_name in ["kam:apex", "kam-apex", "apex"]:
        tag = "kam:apex"
        offline_file = os.path.join(models_dir, "Modelfile.kam-apex")
        online_file = os.path.join(models_dir, "Modelfile.kam-apex")
        weight_file = os.path.join(weights_dir, "kam_apex_qwen3_8b.gguf")
        desc = "Qwen3 8B Yeni Nesil Hibrit Düşünen Başbuğ Kam (5.2 GB)"
    elif model_name in ["kam:r1", "kam-r1", "r1"]:
        tag = "kam:r1"
        offline_file = os.path.join(models_dir, "Modelfile.kam-r1-offline")
        online_file = os.path.join(models_dir, "Modelfile.kam-r1")
        weight_file = os.path.join(weights_dir, "kam_r1_deepseek_7b.gguf")
        desc = "DeepSeek-R1 7B Zincirleme Akıl Yürütme (Chain-of-Thought CoT - 4.7 GB)"
    elif model_name in ["kam:7b", "kam-7b", "7b", "kam"]:
        tag = "kam:7b"
        offline_file = os.path.join(models_dir, "Modelfile.kam-offline")
        online_file = os.path.join(models_dir, "Modelfile.kam")
        weight_file = os.path.join(weights_dir, "kam_7b_qwen_foundation.gguf")
        desc = "Qwen 2.5 7B Yüksek Hızlı Bilişsel Ulu Kam Motoru (4.7 GB)"
    elif model_name in ["kam:coder", "kam-coder", "coder"]:
        tag = "kam:coder"
        offline_file = os.path.join(models_dir, "Modelfile.kam-coder")
        online_file = os.path.join(models_dir, "Modelfile.kam-coder")
        weight_file = os.path.join(weights_dir, "kam_coder_7b_qwen.gguf")
        desc = "Qwen 2.5 Coder 7B Ulu Demirci C++20 JIT, Linux eBPF ve AST Sandbox Başmimarı (4.7 GB)"
    elif model_name in ["kam:coder-nano", "kam-coder-nano", "coder-nano"]:
        tag = "kam:coder-nano"
        offline_file = os.path.join(models_dir, "Modelfile.kam-coder-nano")
        online_file = os.path.join(models_dir, "Modelfile.kam-coder-nano")
        weight_file = ""
        desc = "Qwen 2.5 Coder 1.5B Taktik Uç C++20 JIT Kod Sentezleyici (986 MB)"
    elif model_name in ["kam:r1-nano", "kam-r1-nano", "r1-nano"]:
        tag = "kam:r1-nano"
        offline_file = os.path.join(models_dir, "Modelfile.kam-r1-nano")
        online_file = os.path.join(models_dir, "Modelfile.kam-r1-nano")
        weight_file = ""
        desc = "DeepSeek-R1 1.5B Taktik Uç Zincirleme Akıl Yürütme (<think>) Motoru (1.1 GB)"
    elif model_name in ["kam:1.5b", "kam-1.5b", "1.5b"]:
        tag = "kam:1.5b"
        offline_file = os.path.join(models_dir, "Modelfile.kam-1.5b")
        online_file = os.path.join(models_dir, "Modelfile.kam-1.5b")
        weight_file = ""
        desc = "Qwen 2.5 1.5B Mikro-Uç Zihin ve Öz-Spekülatif Taslak Motoru (986 MB)"
    else:
        print(f"\033[1;31m[HATA] Bilinmeyen model adı: {model_name}.\033[0m")
        return False

    # Yalnızca gerçek (100 MB üstü) GGUF dosyası varsa ve --offline istenmişse offline Modelfile seç
    if (
        use_offline
        and weight_file
        and os.path.exists(weight_file)
        and os.path.getsize(weight_file) > 100 * 1024 * 1024
        and os.path.exists(offline_file)
    ):
        modelfile_path = offline_file
        mode_str = f"ÇEVRİMDISI YEREL GGUF ({os.path.basename(weight_file)})"
    else:
        modelfile_path = online_file
        mode_str = "OLLAMA YEREL TABAN MODELİ"

    print("\033[1;36m" + "=" * 74 + "\033[0m")
    print(f"\033[1;35m  🐺 KAM BİLİŞSEL DERLEME: {tag} ({desc}) \033[0m")
    print("\033[1;36m" + "=" * 74 + "\033[0m")
    print(f"  • Modelfile : {modelfile_path}")
    print(f"  • Kaynak    : {mode_str}")
    print(f"  • Hedef Tag : {tag}")
    print("-" * 74)

    if not os.path.exists(modelfile_path):
        print(f"\033[1;31m[HATA] Modelfile bulunamadı: {modelfile_path}\033[0m")
        return False

    print(f"\033[1;33m[KAM] Ollama üzerinde '{tag}' modeli inşa ediliyor...\033[0m")
    try:
        res = subprocess.run(
            ["ollama", "create", tag, "-f", os.path.basename(modelfile_path)],
            cwd=models_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        print(res.stdout)
        print(f"\033[1;32m[BAŞARILI] {tag} modeli başarıyla derlendi ve Ollama motoruna kaydedildi!\033[0m\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\033[1;31m[HATA] Model oluşturulamadı: {e.stderr}\033[0m\n")
        return False


def main():
    parser = argparse.ArgumentParser(description="KAM Şaman & Bilişsel Model Derleyici")
    parser.add_argument(
        "--model",
        type=str,
        default="all",
        choices=[
            "all",
            "kam:apex",
            "kam:r1",
            "kam:7b",
            "kam:coder",
            "kam:coder-nano",
            "kam:r1-nano",
            "kam:1.5b",
            "apex",
            "r1",
            "7b",
            "coder",
            "coder-nano",
            "r1-nano",
            "1.5b",
        ],
        help="Derlenecek model",
    )
    parser.add_argument("--offline", action="store_true", help="models/weights/ altındaki yerel GGUF dosyalarını kullan")
    args = parser.parse_args()

    if args.model == "all":
        for m in ["kam:apex", "kam:7b", "kam:r1", "kam:coder", "kam:coder-nano", "kam:r1-nano", "kam:1.5b"]:
            train_model(m, use_offline=args.offline)
        print("\033[1;32m[TAMAMLANDI] 7 Üyeli Egemen KAM Model Ailesi (kam:apex, kam:7b, kam:r1, kam:coder, kam:coder-nano, kam:r1-nano, kam:1.5b) hazır!\033[0m")
    else:
        train_model(args.model, use_offline=args.offline)


if __name__ == "__main__":
    main()
