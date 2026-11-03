#!/usr/bin/env python3
"""
KAM Kaggle Veri Tabanı & Model Entegrasyon Merkezi
Kaggle API üzerinden Türkçe veri setleri, NLP korpusları ve açık modelleri yönetir.
"""
import sys
import os
import argparse
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def check_kaggle_status():
    kaggle_dir = os.path.expanduser("~/.kaggle")
    kaggle_file = os.path.join(kaggle_dir, "kaggle.json")
    print("\033[1;36m" + "=" * 65 + "\033[0m")
    print("\033[1;35m  🐺 KAM KAGGLE BAĞLANTI & KİMLİK DOĞRULAMA DURUMU \033[0m")
    print("\033[1;36m" + "=" * 65 + "\033[0m")
    print(f"  • Anahtar Konumu: {kaggle_file}")

    if not os.path.exists(kaggle_file):
        print("\033[1;31m[HATA] kaggle.json bulunamadı!\033[0m")
        return False

    print("  • Durum: kaggle.json tespit edildi.")
    print("\033[1;33m[KAM] Kaggle sunucularına el sıkışma isteği gönderiliyor...\033[0m")
    try:
        res = subprocess.run(["kaggle", "datasets", "list", "-s", "turkish", "-p", "1"], capture_output=True, text=True, check=True, encoding="utf-8", errors="replace")
        print("\033[1;32m[BAŞARILI] Kaggle API bağlantısı kusursuz! Kimlik doğrulandı.\033[0m")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\033[1;31m[HATA] Kaggle kimlik doğrulama başarısız: {e.stderr}\033[0m")
        return False

def search_datasets(query: str):
    print(f"\033[1;34m[KAGGLE] '{query}' araması yapılıyor...\033[0m\n")
    try:
        subprocess.run(["kaggle", "datasets", "list", "-s", query], check=True)
    except Exception as e:
        print(f"\033[1;31m[HATA] Arama başarısız: {e}\033[0m")

def download_dataset(dataset_slug: str, target_dir: str = "data/kaggle"):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest = os.path.join(root_dir, target_dir)
    os.makedirs(dest, exist_ok=True)
    print(f"\033[1;33m[KAGGLE] Veri seti indiriliyor: {dataset_slug} -> {dest}\033[0m")
    try:
        subprocess.run(["kaggle", "datasets", "download", "-d", dataset_slug, "-p", dest, "--unzip"], check=True)
        print(f"\033[1;32m[BAŞARILI] Veri seti indirildi ve çıkartıldı: {dest}\033[0m")
    except Exception as e:
        print(f"\033[1;31m[HATA] İndirme başarısız: {e}\033[0m")

def main():
    parser = argparse.ArgumentParser(description="KAM Kaggle Hub Veri Yöneticisi")
    parser.add_argument("action", choices=["status", "search", "download"], help="İşlem türü")
    parser.add_argument("param", nargs="?", default="turkish", help="Arama terimi veya veri seti slug'ı")
    args = parser.parse_args()

    if args.action == "status":
        check_kaggle_status()
    elif args.action == "search":
        search_datasets(args.param)
    elif args.action == "download":
        download_dataset(args.param)

if __name__ == "__main__":
    main()
