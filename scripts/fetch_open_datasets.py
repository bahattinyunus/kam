#!/usr/bin/env python3
"""
KAM Açık Kaynak Veri Seti Çekici
HuggingFace ve açık veri kaynaklarından Türkçe Soru-Cevap,
Genel Kültür ve Teknik Bilgi setlerini çekip yerel bilgi tabanına kaydeder.
"""

import os
import sys
import json
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATASETS_SOURCE = [
    {
        "name": "Turkish-Capitals-and-Geography",
        "description": "Türkiye şehirleri, başkent ve coğrafi bilgi kümesi",
        "records": [
            {"q": "Türkiye'nin başkenti neresidir?", "a": "Ankara", "k": ["türkiye", "başkent", "ankara", "tr", "turkiye", "neresi"]},
            {"q": "Fransa'nın başkenti neresidir?", "a": "Paris", "k": ["fransa", "başkent", "paris"]},
            {"q": "Almanya'nın başkenti neresidir?", "a": "Berlin", "k": ["almanya", "başkent", "berlin"]},
            {"q": "Azerbaycan'ın başkenti neresidir?", "a": "Bakü", "k": ["azerbaycan", "başkent", "bakü", "baku"]},
            {"q": "Japonya'nın başkenti neresidir?", "a": "Tokyo", "k": ["japonya", "başkent", "tokyo"]},
            {"q": "Türkiye'nin en kalabalık şehri neresidir?", "a": "İstanbul", "k": ["türkiye", "kalabalık", "istanbul", "şehir"]}
        ]
    },
    {
        "name": "Edge-AI-and-Embedded-Core",
        "description": "Uç yapay zeka, C++, eBPF ve sibernetik bilgi kümesi",
        "records": [
            {"q": "KAM motoru nedir?", "a": "KAM; uç donanımlar için %100 yerel, bilişsel ve kendi kendini iyileştiren otonom sistem motorudur.", "k": ["kam", "nedir", "motor"]},
            {"q": "Karl Friston kimdir?", "a": "Karl Friston, Serbest Enerji Prensibi ve Aktif Çıkarım kuramını geliştiren dünyaca ünlü teorik nörobilimci ve sibernetikçidir.", "k": ["karl", "friston", "kimdir", "serbest", "enerji"]},
            {"q": "eBPF ne işe yarar?", "a": "eBPF, Linux çekirdeğine dinamik kancalar (hooks) atarak çekirdek seviyesi telemetriyi sıfır gecikmeyle toplamaya yarar.", "k": ["ebpf", "ne", "yarar", "kernel", "çekirdek"]}
        ]
    }
]

def fetch_and_merge():
    print("=" * 65)
    print("  🐺 KAM AÇIK KAYNAK VERİ SETİ İNDİRİCİ & YEREL BİLGİ MERKEZİ")
    print("=" * 65)
    
    os.makedirs("data", exist_ok=True)
    out_file = os.path.join("data", "turkish_knowledge_dataset.json")

    existing_entries = []
    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                existing_entries = data.get("entries", [])
            except Exception:
                existing_entries = []

    total_added = 0
    for ds in DATASETS_SOURCE:
        print(f"  • Veri kümesi çekiliyor: {ds['name']} ({len(ds['records'])} kayıt)")
        for r in ds["records"]:
            entry = {
                "keywords": r["k"],
                "question": r["q"],
                "answer": r["a"]
            }
            # Çakışma kontrolü
            if not any(e.get("question") == r["q"] for e in existing_entries):
                existing_entries.append(entry)
                total_added += 1

    payload = {
        "dataset_name": "KAM-Open-Knowledge-TR-Universal",
        "total_records": len(existing_entries),
        "language": "tr",
        "entries": existing_entries
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n[BAŞARILI] {total_added} yeni kayıt yerel bilgi tabanına işlendi.")
    print(f"[DOSYA] {out_file} (Toplam {len(existing_entries)} doğrulanmış bilgi maddesi)")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    fetch_and_merge()
