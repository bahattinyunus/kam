#!/usr/bin/env python3
"""
KAM Bilisel Zihin ve Saman Persona Kapsamli Olcumleme & Benchmark Araci
Modelin Turkce akiciligini, teknik derinligini, cikarim hizini ve felsefi kimligini test eder.
"""
import sys
import os
import time
import json
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from kam.real_llm import UniversalLLMClient

BENCHMARK_PROMPTS = [
    {
        "category": "KİMLİK & HİKMET FELSEFESİ",
        "prompt": "Adın neden KAM, varoluşsal amacın nedir ve mimarın kimdir?",
        "expected_keywords": ["kam", "bahattin yunus", "serbest enerji", "otonom", "dirlik"]
    },
    {
        "category": "KARL FRISTON SERBEST ENERJİ",
        "prompt": "Karl Friston'un Serbest Enerji Prensibini ve Aktif Çıkarımı bir mühendise matematiksel ve mantıksal olarak açıkla.",
        "expected_keywords": ["entropi", "varyasyonel", "kl", "inanç", "eylem", "sürpriz"]
    },
    {
        "category": "C++20 SİBERNETİK KOD",
        "prompt": "Uç donanımlar için C++20 standardında std::span ve concepts kullanan küçük ve güvenli bir Memory Arena sınıfı yaz.",
        "expected_keywords": ["template", "class", "size_t", "align", "span", "return"]
    },
    {
        "category": "eBPF KERNEL SİNİR SİSTEMİ",
        "prompt": "Linux eBPF kancaları sistemin silikon sinir sisteminde tam olarak ne yapar?",
        "expected_keywords": ["kprobe", "tracepoint", "ringbuffer", "çekirdek", "mikrosaniye"]
    },
    {
        "category": "TÜRKÇE DOĞRULANMIŞ BİLGİ",
        "prompt": "Türkiye'nin başkenti neresidir ve neden orası seçilmiştir?",
        "expected_keywords": ["ankara", "1923", "meclis", "anadolu", "atatürk"]
    }
]

def run_evaluation():
    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print("\033[1;35m  🐺 KAM BİLİŞSEL ZİHİN KAPSAMLI BENCHMARK VE DEĞERLENDİRME SÜİTİ \033[0m")
    print("\033[1;36m" + "=" * 70 + "\033[0m")

    client = UniversalLLMClient()
    print(f"  • Aktif Model       : \033[1;32m{client.current_model}\033[0m")
    print(f"  • Aktif Backend     : \033[1;32m{client.active_backend.upper()}\033[0m")
    print(f"  • Bilgi Korpusu     : \033[1;32m{len(client.knowledge.knowledge_base)} kayıtlı gerçek bilgi\033[0m")
    print("-" * 70 + "\n")

    scores = []
    total_tokens = 0
    total_time = 0.0

    for i, test in enumerate(BENCHMARK_PROMPTS, 1):
        print(f"\033[1;33m[{i}/5] TEST ALANI: {test['category']}\033[0m")
        print(f"\033[1;34mSoru: {test['prompt']}\033[0m")

        client.conversation_history.clear()  # Her test bağımsız ve temiz bağlamla yürütülür
        t0 = time.time()
        reply = client.generate(test["prompt"])
        elapsed = time.time() - t0

        approx_tokens = len(reply.split()) * 1.3
        tokens_per_sec = approx_tokens / max(0.1, elapsed)
        total_tokens += approx_tokens
        total_time += elapsed

        # Doğruluk / Anahtar kelime denetimi
        r_lower = reply.lower()
        matched = [kw for kw in test["expected_keywords"] if kw in r_lower]
        accuracy = (len(matched) / len(test["expected_keywords"])) * 100

        print(f"\033[1;32mHız: {tokens_per_sec:.1f} token/s | Süre: {elapsed:.2f}s | Doğruluk Uyumu: %{accuracy:.0f}\033[0m")
        print("\033[0;37m" + (reply[:300] + "..." if len(reply) > 300 else reply) + "\033[0m\n")

        scores.append(accuracy)

    avg_score = sum(scores) / len(scores)
    avg_speed = total_tokens / max(0.1, total_time)

    print("\033[1;36m" + "=" * 70 + "\033[0m")
    print(f"\033[1;35m  🏆 BENCHMARK SONUCU: GENEL BİLİŞSEL PUAN: %{avg_score:.1f} / 100\033[0m")
    print(f"  ⚡ Ortalama Çıkarım Hızı: {avg_speed:.1f} token/s (NVIDIA RTX 5060 Hızlandırmalı)")
    print("\033[1;36m" + "=" * 70 + "\033[0m\n")
    return avg_score >= 70

if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
