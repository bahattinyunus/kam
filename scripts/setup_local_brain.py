#!/usr/bin/env python3
"""
KAM Yerel Beyin Kurulum Orkestratörü
Kullanıcının bilgisayarında en yüksek performanslı yerel yapay zeka ve bilişsel motoru hazırlar.
"""

import os
import sys
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# scripts dizinini sys.path'e ekle
sys.path.insert(0, os.path.dirname(__file__))

def setup():
    print("=" * 65)
    print("  🐺 KAM YEREL YAPAY ZEKA VE BİLİŞSEL BEYİN KURULUMU")
    print("=" * 65)
    print("  • Yerel İkili Ağırlık Dosyaları Hazırlanıyor...")
    
    # 1. Ağırlıkları üret
    import generate_local_weights
    generate_local_weights.generate_weights()

    # 2. Dizin kontrolü
    for d in ["models", "data", "assets"]:
        if os.path.exists(d):
            count = len(os.listdir(d))
            print(f"  • [{d}/] dizini hazır ({count} dosya).")

    print("-" * 65)
    print("  [BAŞARILI] KAM Yerel Bilişsel Motoru Kullanıma Hazır!")
    print("  Çalıştırmak için:")
    print("    python cli.py --chat       # İnteraktif Türkçe Bilişsel Terminal")
    print("    python cli.py --dashboard  # Canlı TUI Gösterge Paneli")
    print("    python cli.py --infer      # Sıvı Sinir Ağı Çıkarımı")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    setup()
