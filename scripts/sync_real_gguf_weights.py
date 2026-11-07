#!/usr/bin/env python3
"""
KAM Gerçek GGUF Ağırlık Senkronizasyon ve Çevrimdışı Depo Motoru.
Yerel Ollama deposundaki (~/.ollama/models) gerçek çok-gigabaytlık GGUF model
ağırlıklarını (Qwen3 8B, Qwen2.5 7B, DeepSeek-R1 7B, Qwen2.5-Coder 7B,
DeepSeek-R1 1.5B, Qwen2.5-Coder 1.5B, Qwen2.5 1.5B -> ~21.5 GB) doğrudan
repo içindeki models/weights/ dizinine çıkarır ve doğrular.
"""
import json
import os
import shutil
import sys
from typing import Dict, Any, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


MODEL_TARGETS = [
    {
        "ollama_repo": "qwen3",
        "ollama_tag": "8b",
        "target_filename": "kam_apex_qwen3_8b.gguf",
        "title": "KAM-Apex 8B (Qwen3 8B Hibrit Düşünen Başbuğ Zihin)",
    },
    {
        "ollama_repo": "qwen2.5",
        "ollama_tag": "7b",
        "target_filename": "kam_7b_qwen_foundation.gguf",
        "title": "KAM-7B (Qwen 2.5 7B Ulu Kam Bilişsel Zihin)",
    },
    {
        "ollama_repo": "deepseek-r1",
        "ollama_tag": "7b",
        "target_filename": "kam_r1_deepseek_7b.gguf",
        "title": "KAM-R1 7B (DeepSeek-R1 7B Baş Bilge CoT Muhakeme)",
    },
    {
        "ollama_repo": "qwen2.5-coder",
        "ollama_tag": "7b",
        "target_filename": "kam_coder_7b_qwen.gguf",
        "title": "KAM-Coder 7B (Qwen 2.5 Coder 7B Ulu Demirci C++20/eBPF Başmimarı)",
    },
    {
        "ollama_repo": "deepseek-r1",
        "ollama_tag": "1.5b",
        "target_filename": "deepseek-r1-1.5b-q4_k_m.gguf",
        "title": "KAM-R1-Nano 1.5B (DeepSeek-R1 1.5B Taktik Bilge CoT)",
    },
    {
        "ollama_repo": "qwen2.5-coder",
        "ollama_tag": "1.5b",
        "target_filename": "qwen2.5-coder-1.5b-q4_k_m.gguf",
        "title": "KAM-Coder-Nano 1.5B (Qwen 2.5 Coder 1.5B Taktik Demirci)",
    },
    {
        "ollama_repo": "qwen2.5",
        "ollama_tag": "1.5b",
        "target_filename": "qwen_1.5b_lightweight_fallback.gguf",
        "title": "KAM-1.5B (Qwen 2.5 1.5B Uç Gözcü & Spekülatif Taslak)",
    },
]


def find_ollama_model_blob(ollama_home: str, repo: str, tag: str) -> str:
    manifest_path = os.path.join(
        ollama_home, "models", "manifests", "registry.ollama.ai", "library", repo, tag
    )
    if not os.path.exists(manifest_path):
        return ""
    with open(manifest_path, "r", encoding="utf-8") as mf:
        data = json.load(mf)
    for layer in data.get("layers", []):
        if layer.get("mediaType") == "application/vnd.ollama.image.model":
            digest = layer.get("digest", "")
            blob_name = digest.replace(":", "-")
            blob_path = os.path.join(ollama_home, "models", "blobs", blob_name)
            if os.path.exists(blob_path):
                return blob_path
    return ""


def sync_all_weights(copy_blobs: bool = True) -> Dict[str, Any]:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_dir = os.path.join(root_dir, "models", "weights")
    os.makedirs(weights_dir, exist_ok=True)

    ollama_home = os.path.expanduser("~/.ollama")
    synced_models: List[Dict[str, Any]] = []
    total_bytes = 0

    print("=" * 78)
    print("  🐺 KAM GERÇEK GGUF MODEL AĞIRLIKLARI SENKRONİZASYON MOTORU (models/weights/)")
    print("=" * 78)

    for item in MODEL_TARGETS:
        blob_path = find_ollama_model_blob(ollama_home, item["ollama_repo"], item["ollama_tag"])
        target_path = os.path.join(weights_dir, item["target_filename"])

        if not blob_path:
            print(f"  [ATLANDI] {item['ollama_repo']}:{item['ollama_tag']} henüz Ollama deposunda yok.")
            continue

        blob_size = os.path.getsize(blob_path)
        size_gb = blob_size / (1024 ** 3)

        if copy_blobs:
            need_copy = True
            if os.path.exists(target_path) and os.path.getsize(target_path) == blob_size:
                need_copy = False

            if need_copy:
                if os.path.exists(target_path):
                    os.remove(target_path)
                print(f"  [AKTARILIYOR] {item['title']} ({size_gb:.2f} GB) -> {item['target_filename']}...")
                try:
                    os.link(blob_path, target_path)
                except OSError:
                    shutil.copyfile(blob_path, target_path)

        final_size = os.path.getsize(target_path) if os.path.exists(target_path) else blob_size
        total_bytes += final_size
        synced_models.append({
            "model": f"{item['ollama_repo']}:{item['ollama_tag']}",
            "title": item["title"],
            "filename": item["target_filename"],
            "size_gb": round(final_size / (1024 ** 3), 2),
            "blob_source": os.path.basename(blob_path),
        })
        print(f"  [HAZIR] {item['target_filename']:<36} | Boyut: {final_size / (1024 ** 3):.2f} GB")

    manifest_out = {
        "total_models": len(synced_models),
        "total_size_gb": round(total_bytes / (1024 ** 3), 2),
        "models": synced_models,
    }
    manifest_file = os.path.join(root_dir, "models", "kam_gguf_fleet_manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_out, f, ensure_ascii=False, indent=2)

    print("-" * 78)
    print(f"  🏆 TOPLAM YEREL GGUF AĞIRLIK KAPASİTESİ: {manifest_out['total_size_gb']:.2f} GB ({len(synced_models)} Model)")
    print("=" * 78)
    return manifest_out


if __name__ == "__main__":
    sync_all_weights(copy_blobs=True)
