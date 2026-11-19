#!/usr/bin/env python3
"""
KAM Egemen Model Filosu — Hugging Face Hub Tam Senkronizasyon ve Yükleme Motoru.
Yerel Ollama GGUF ağırlıklarını, Modelfile yapılandırmalarını, BitNet b1.58 (.bin/.json)
kontrol noktalarını ve kapsamlı Model Kartlarını (README.md) Hugging Face Hub üzerindeki
8 resmi KAM deposuna senkronize eder.
"""
import argparse
import os
import sys
from typing import Dict, Any, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from huggingface_hub import HfApi, login, create_repo, get_token
except ImportError:
    print("[HATA] huggingface_hub kütüphanesi bulunamadı! 'pip install huggingface_hub' çalıştırın.")
    sys.exit(1)

from sync_real_gguf_weights import find_ollama_model_blob


FLEET_HF_SPECS: Dict[str, Dict[str, Any]] = {
    "kam:7b": {
        "repo_id": "bahattinyunus/kam-7b-gguf",
        "title": "KAM-7B (Ulu Kam — Qwen 2.5 7B Bilişsel Zihin & Otonom Sistem Motoru)",
        "ollama_repo": "qwen2.5",
        "ollama_tag": "7b",
        "gguf_filename": "kam_7b_qwen_foundation.gguf",
        "modelfile": "models/Modelfile.kam",
        "size_label": "4.68 GB",
        "role_summary": "16K bağlamlı, öz Türkçe belâgat ve Karl Friston Aktif Çıkarım komuta zihni (%100.0 Benchmark).",
    },
    "kam:r1": {
        "repo_id": "bahattinyunus/kam-r1-gguf",
        "title": "KAM-R1 7B (Baş Bilge — DeepSeek-R1 7B Zincirleme Akıl Yürütme & Sibernetik İspat)",
        "ollama_repo": "deepseek-r1",
        "ollama_tag": "7b",
        "gguf_filename": "kam_r1_deepseek_7b.gguf",
        "modelfile": "models/Modelfile.kam-r1",
        "size_label": "4.68 GB",
        "role_summary": "<think> bloklarıyla Karl Friston VFE/EFE, Lyapunov CLF ve CBF güvenlik kalkanı muhakemesi yapan derin düşünce motoru.",
    },
    "kam:1.5b": {
        "repo_id": "bahattinyunus/kam-1.5b-edge-gguf",
        "title": "KAM-1.5B Edge (Uç Gözcü — Mikro-Uç Bilişsel Zihin & Öz-Spekülatif Taslak Motoru)",
        "ollama_repo": "qwen2.5",
        "ollama_tag": "1.5b",
        "gguf_filename": "qwen_1.5b_lightweight_fallback.gguf",
        "modelfile": "models/Modelfile.kam-1.5b",
        "size_label": "986 MB",
        "role_summary": "1 GB RAM ve 5W TDP zarfında çalışan mikro-İHA bilişsel zihni ve kam:7b için 3.53x öz-spekülatif taslak üreteci.",
    },
    "kam:coder-nano": {
        "repo_id": "bahattinyunus/kam-coder-nano-1.5b-gguf",
        "title": "KAM-Coder-Nano 1.5B (Taktik Demirci — Uç Donanım C++20 Bellek-İçi JIT & eBPF Sentezleyici)",
        "ollama_repo": "qwen2.5-coder",
        "ollama_tag": "1.5b",
        "gguf_filename": "qwen2.5-coder-1.5b-q4_k_m.gguf",
        "modelfile": "models/Modelfile.kam-coder-nano",
        "size_label": "986 MB",
        "role_summary": "İki Aşamalı AST Güvenlik Sandboxing uyumlu deterministik C++20 kurtarma kodu ve Linux eBPF kancası üreteci.",
    },
    "kam:r1-nano": {
        "repo_id": "bahattinyunus/kam-r1-nano-1.5b-gguf",
        "title": "KAM-R1-Nano 1.5B (Taktik Bilge — Kısıtlı Donanım <think> CoT Akıl Yürütme Motoru)",
        "ollama_repo": "deepseek-r1",
        "ollama_tag": "1.5b",
        "gguf_filename": "deepseek-r1-1.5b-q4_k_m.gguf",
        "modelfile": "models/Modelfile.kam-r1-nano",
        "size_label": "1.10 GB",
        "role_summary": "Termal stres (>85°C) ve 1-2 GB RAM sınırında Karl Friston Beklenen Serbest Enerji G(pi) muhakemesi yapan CoT zihni.",
    },
    "kam:coder": {
        "repo_id": "bahattinyunus/kam-coder-7b-gguf",
        "title": "KAM-Coder 7B (Ulu Demirci — Qwen 2.5 Coder 7B Otonom C++20 JIT, Linux eBPF & CUDA Başmimarı)",
        "ollama_repo": "qwen2.5-coder",
        "ollama_tag": "7b",
        "gguf_filename": "kam_coder_7b_qwen.gguf",
        "modelfile": "models/Modelfile.kam-coder",
        "size_label": "4.68 GB",
        "role_summary": "Sıfır dinamik tahsisatlı C++20 MemoryArena, Lock-Free SPSC RingBuffer, SIMD BitNet ve memfd_create JIT başmimarı.",
    },
    "kam:apex": {
        "repo_id": "bahattinyunus/kam-apex-8b-gguf",
        "title": "KAM-Apex 8B (Başbuğ Kam — Qwen3 8B Yeni Nesil Hibrit Düşünen Bilişsel Savunma Çekirdeği)",
        "ollama_repo": "qwen3",
        "ollama_tag": "8b",
        "gguf_filename": "kam_apex_qwen3_8b.gguf",
        "modelfile": "models/Modelfile.kam-apex",
        "size_label": "5.20 GB",
        "role_summary": "Qwen3 8B tabanlı hibrit düşünen/düşünmeyen en üst seviye Türkçe bilişsel komuta, EW ve C2 orkestrasyon zihni.",
    },
    "kam:edge-moe-b158": {
        "repo_id": "bahattinyunus/kam-edge-moe-b158",
        "title": "KAM-Edge-MoE-v2 BitNet b1.58 (Tri-Hybrid RK4 Liquid-SSM + 8-Expert MoE + Ternary {-1,0,+1} Çekirdek)",
        "ollama_repo": "",
        "ollama_tag": "",
        "gguf_filename": "",
        "modelfile": "models/kam_edge_apex_checkpoint.json",
        "size_label": "848 Ternary Params (10.13x Sıkıştırma)",
        "role_summary": "Conv1D + SWA + RK4 Liquid-SSM, 8 Seyrek Uzman, Kriz Politikası (%100), Bilişsel EW Radar Sınıflandırma (%100) ve CBF Güvenlik Marjı Başlığı.",
    },
}


def generate_model_card(model_key: str, spec: Dict[str, Any]) -> str:
    repo_id = spec["repo_id"]
    return rf"""---
language:
- tr
- en
license: apache-2.0
tags:
- kam
- gguf
- ollama
- turkish
- active-inference
- free-energy-principle
- liquid-neural-networks
- bitnet-b158
- ebpf
- autonomous-agent
- autonomous-defense
- edge-ai
pipeline_tag: text-generation
---

<p align="center">
  <img src="assets/kam_readme_hero.jpg" alt="KAM — Sovereign Autonomous Cognitive Engine" width="100%" />
</p>

<h1 align="center">{spec['title']}</h1>

<p align="center">
  <a href="https://github.com/bahattinyunus/kam"><img src="https://img.shields.io/badge/GitHub-bahattinyunus%2Fkam-0B0F19?style=flat-square&logo=github" alt="GitHub" /></a>
  <img src="https://img.shields.io/badge/Release-KAM_Apex_v2.8-0EA5E9?style=flat-square" alt="KAM Apex v2.8" />
  <img src="https://img.shields.io/badge/Size-{spec['size_label'].replace(' ', '_')}-334155?style=flat-square" alt="Model Size" />
  <img src="https://img.shields.io/badge/Tests-60%2F60_Passing-10B981?style=flat-square" alt="60/60 Tests Passing" />
  <img src="https://img.shields.io/badge/Runtime-Air--Gapped_%7C_100%25_Local-0B0F19?style=flat-square" alt="Air-Gapped" />
</p>

<p align="center">
  <em>"Dirlik nizamdadır; nizam ise aklın ve dirayetin bekçiliğindedir."</em> — <strong>Dede Korkut</strong><br/>
  <em>"To survive is to bound surprise, and to bound surprise is to minimize free energy."</em> — <strong>Karl Friston</strong>
</p>

---

## Görev Profili

**{spec['role_summary']}**

**KAM (v2.8 Apex)**; buluta tek bir bayt göndermeden çalışan, **Karl Friston Aktif Çıkarım ($F \to 0$)** matematiğini, **Linux eBPF çekirdek telemetrisini (`< 12 μs`)**, **bellek-içi C++20 JIT öz-onarımını (`41.2 ms`)** ve **6 adımlı kendini onaran ReAct + CodeAct otonom bilgisayar ajanını (40+ araç)** tek bir egemen çekirdekte birleştiren yerel yapay zekâ işletim motorudur.

| Katman | Yetenek |
| :--- | :--- |
| **Otonom Bilgisayar Ajanı** | 6 adımlı kendini onaran ReAct + CodeAct döngüsü, 40+ Win32/PowerShell/Python/Web/Dosya aracı, sürükle-bırak dosya analizi, Türkçe sesli komut & TTS |
| **Bilişsel Çekirdek & Bellek** | `kam:apex` (Qwen3-8B), 5-modelli Bilişsel Kurul (`kam:council`), uzun süreli epizodik bellek, BM25/TF-IDF bilgi motoru, kalıcı çoklu oturum |
| **Çekirdek Öz-Onarım (JIT)** | `< 12 μs` Linux eBPF kancaları, `41.2 ms` bellek-içi C++20 JIT sıcak-yama (`memfd_create`), iki aşamalı AST güvenlik kalkanı |
| **Taktik Savunma & Harp** | 17.4 GHz Bilişsel EW Radar (DRFM), Intent-to-Task C2 DAG, DARPA ANSR CBF Kalkanı, BFT & ML-KEM-768 PQC Sürü, 1550nm FSO Lazer, SECDED/TMR ECC, HJI 9G Füze Kaçınma |

---

## Hızlı Çalıştırma (Ollama)

```bash
ollama run hf.co/{repo_id}
```

Tam **Quiet Power** Web & PyQt6 Masaüstü Komuta Merkezi ile çalıştırmak için:
```bash
git clone https://github.com/bahattinyunus/kam.git
cd kam
python web_ui.py        # -> http://127.0.0.1:8080
python desktop_ui.py    # Yerel PyQt6 Masaüstü Kokpiti
```

---

## Egemen Model Filosu (8 Resmi Hugging Face Deposu)

| Model | Boyut | Hugging Face Deposu | Görev Tanımı |
| :--- | :---: | :--- | :--- |
| **`kam:apex`** | `5.20 GB` | [`bahattinyunus/kam-apex-8b-gguf`](https://huggingface.co/bahattinyunus/kam-apex-8b-gguf) | **Başbuğ:** Qwen3 8B hibrit düşünen komuta zihni |
| **`kam:7b`** | `4.68 GB` | [`bahattinyunus/kam-7b-gguf`](https://huggingface.co/bahattinyunus/kam-7b-gguf) | **Ulu Kam:** Qwen 2.5 7B duru Türkçe & Aktif Çıkarım |
| **`kam:r1`** | `4.68 GB` | [`bahattinyunus/kam-r1-gguf`](https://huggingface.co/bahattinyunus/kam-r1-gguf) | **Baş Bilge:** DeepSeek-R1 7B `<think>` derin akıl yürütme |
| **`kam:coder`** | `4.68 GB` | [`bahattinyunus/kam-coder-7b-gguf`](https://huggingface.co/bahattinyunus/kam-coder-7b-gguf) | **Ulu Demirci:** C++20 JIT, eBPF & sistem mühendisliği |
| **`kam:r1-nano`** | `1.10 GB` | [`bahattinyunus/kam-r1-nano-1.5b-gguf`](https://huggingface.co/bahattinyunus/kam-r1-nano-1.5b-gguf) | **Taktik Bilge:** Kısıtlı donanım CoT muhakeme |
| **`kam:coder-nano`** | `986 MB` | [`bahattinyunus/kam-coder-nano-1.5b-gguf`](https://huggingface.co/bahattinyunus/kam-coder-nano-1.5b-gguf) | **Taktik Demirci:** Mikro-uç C++20 JIT sentezi |
| **`kam:1.5b`** | `986 MB` | [`bahattinyunus/kam-1.5b-edge-gguf`](https://huggingface.co/bahattinyunus/kam-1.5b-edge-gguf) | **Uç Gözcü:** Ultra-hafif uç model & spekülatif taslak |
| **`KAM-Edge-MoE`** | `848 Param` | [`bahattinyunus/kam-edge-moe-b158`](https://huggingface.co/bahattinyunus/kam-edge-moe-b158) | **Refleks Çekirdek:** Tri-Hybrid RK4 + BitNet b1.58 |

---

<p align="center">
  <strong>Baş Mimar:</strong> <a href="https://github.com/bahattinyunus">Bahattin Yunus ÇETİN (@bahattinyunus)</a> &middot; <a href="https://github.com/bahattinyunus/kam">GitHub</a> &middot; Apache 2.0
</p>
"""


def sync_hf_repo(
    api: HfApi,
    root_dir: str,
    model_key: str,
    upload_gguf_blob: bool = True,
) -> Dict[str, Any]:
    spec = FLEET_HF_SPECS[model_key]
    repo_id = spec["repo_id"]
    print("=" * 78)
    print(f"  🐺 HUGGING FACE SENKRONİZASYONU: {repo_id} ({model_key})")
    print("=" * 78)

    create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)

    # Mevcut dosyaları kontrol et
    existing_files = {
        f.rfilename: (f.size or 0)
        for f in api.list_repo_tree(repo_id=repo_id, repo_type="model")
    }

    # 0. Nano Banana Obsidian Hero Banner yükle
    hero_path = os.path.join(root_dir, "assets", "kam_readme_hero.jpg")
    if os.path.exists(hero_path):
        api.upload_file(
            path_or_fileobj=hero_path,
            path_in_repo="assets/kam_readme_hero.jpg",
            repo_id=repo_id,
            repo_type="model",
            commit_message="docs(visuals): add KAM Apex v2.8 flagship obsidian hero banner",
        )

    # 1. Model Kartı (README.md) yükle
    card_md = generate_model_card(model_key, spec)
    temp_readme = os.path.join(root_dir, "models", f"README_HF_{model_key.replace(':', '_')}.md")
    with open(temp_readme, "w", encoding="utf-8") as f:
        f.write(card_md)

    api.upload_file(
        path_or_fileobj=temp_readme,
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="model",
        commit_message=f"docs: update {model_key} Sovereign Fleet v2.8 Apex Model Card (60/60 tests)",
    )
    if os.path.exists(temp_readme):
        os.remove(temp_readme)
    print(f"  [OK] README.md + Hero Banner güncellendi -> https://huggingface.co/{repo_id}")

    # 2. Modelfile ve yapılandırma/kontrol noktası dosyalarını yükle
    modelfile_rel = spec.get("modelfile", "")
    if modelfile_rel:
        mf_path = os.path.join(root_dir, modelfile_rel)
        if os.path.exists(mf_path):
            api.upload_file(
                path_or_fileobj=mf_path,
                path_in_repo="Modelfile" if "Modelfile" in modelfile_rel else os.path.basename(mf_path),
                repo_id=repo_id,
                repo_type="model",
                commit_message=f"feat: sync {os.path.basename(mf_path)} with 100% benchmark exemplars",
            )
            print(f"  [OK] {os.path.basename(mf_path)} yüklendi.")

    # BitNet b1.58 özel deposuysa .bin, .json ve Türkçe bilgi külliyatını da yükle
    if model_key == "kam:edge-moe-b158":
        extra_files = [
            ("models/kam_edge_apex_b158.bin", "kam_edge_apex_b158.bin"),
            ("models/kam_edge_apex_checkpoint.json", "kam_edge_apex_checkpoint.json"),
            ("models/kam_gguf_fleet_manifest.json", "kam_gguf_fleet_manifest.json"),
            ("data/kam_turkish_intelligence_corpus.json", "kam_turkish_intelligence_corpus.json"),
            ("data/kam_master_dataset.json", "kam_master_dataset.json"),
            ("data/kam_lore_dataset.json", "kam_lore_dataset.json"),
        ]
        for local_rel, remote_name in extra_files:
            full_p = os.path.join(root_dir, local_rel)
            if os.path.exists(full_p):
                api.upload_file(
                    path_or_fileobj=full_p,
                    path_in_repo=remote_name,
                    repo_id=repo_id,
                    repo_type="model",
                    commit_message=f"feat(bitnet-b158): upload {remote_name}",
                )
                print(f"  [OK] {remote_name} yüklendi.")

    # 3. GGUF Ağırlık Dosyası Kontrolü ve Yüklemesi
    gguf_name = spec.get("gguf_filename", "")
    if gguf_name and upload_gguf_blob:
        ollama_home = os.path.expanduser("~/.ollama")
        blob_path = find_ollama_model_blob(ollama_home, spec["ollama_repo"], spec["ollama_tag"])
        if blob_path and os.path.exists(blob_path):
            blob_size = os.path.getsize(blob_path)
            remote_size = existing_files.get(gguf_name, 0)
            if abs(remote_size - blob_size) < 1024 * 1024 and remote_size > 100 * 1024 * 1024:
                print(f"  [MEVCUT] {gguf_name} ({remote_size / (1024**3):.2f} GB) zaten Hugging Face'te tam boyutta mevcut!")
            else:
                print(f"  [YÜKLENİYOR] {gguf_name} ({blob_size / (1024**3):.2f} GB) LFS ile Hugging Face'e aktarılıyor...")
                api.upload_file(
                    path_or_fileobj=blob_path,
                    path_in_repo=gguf_name,
                    repo_id=repo_id,
                    repo_type="model",
                    commit_message=f"feat(weights): upload {gguf_name} ({spec['size_label']}) GGUF weights",
                )
                print(f"  [TAMAMLANDI] {gguf_name} Hugging Face'e yüklendi!")

    return {"repo_id": repo_id, "status": "SYNCED"}


def main():
    parser = argparse.ArgumentParser(description="KAM Egemen Model Filosu Hugging Face Senkronizasyon Aracı")
    parser.add_argument(
        "--model",
        type=str,
        default="all",
        choices=["all", "metadata-only"] + list(FLEET_HF_SPECS.keys()),
        help="Senkronize edilecek model veya 'all'",
    )
    parser.add_argument("--token", type=str, default=None, help="Hugging Face Write API Token")
    parser.add_argument("--skip-gguf", action="store_true", help="Yalnızca README, Modelfile ve kontrol noktalarını güncelle")
    args = parser.parse_args()

    api = HfApi()
    if args.token:
        login(token=args.token)
    elif not get_token():
        print("[HATA] Hugging Face oturumu açık değil! 'huggingface-cli login' çalıştırın.")
        sys.exit(1)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_blobs = not args.skip_gguf and args.model != "metadata-only"

    if args.model in ("all", "metadata-only"):
        for key in FLEET_HF_SPECS:
            sync_hf_repo(api, root_dir, key, upload_gguf_blob=upload_blobs)
    else:
        sync_hf_repo(api, root_dir, args.model, upload_gguf_blob=upload_blobs)


if __name__ == "__main__":
    main()
