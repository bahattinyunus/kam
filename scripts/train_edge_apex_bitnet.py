#!/usr/bin/env python3
"""
KAM-Edge-MoE RK4 + BitNet b1.58 Üçlü Ağırlık Eğitim ve Kuantizasyon Betiği.
Karl Friston Varyasyonel Serbest Enerjisi + Politika Çapraz Entropisi gradyanlarıyla
modeli eğitir, %100 kriz sınıflandırma doğruluğuna ulaştırır ve ağırlıkları
1.58-bit {-1, 0, +1} ikili (.bin) ve JSON kontrol noktası olarak kaydeder.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "python"))

from kam.models.trainer import ActiveInferenceTrainer


def main():
    print("=" * 74)
    print("  KAM-EDGE-MOE RK4 & BITNET b1.58 BİLİŞSEL AĞIRLIK EĞİTİM MOTORU")
    print("=" * 74)

    trainer = ActiveInferenceTrainer(lr=0.12)
    history = trainer.run_training_cycle(steps=20)

    for h in history:
        if h["epoch"] in (1, 5, 10, 15, 20):
            print(
                f"  [Epok {h['epoch']:02d}/20] VFE: {h['mean_free_energy']:.5f} nats | "
                f"Kayıp: {h['total_loss']:.5f} | "
                f"Politika İsabeti: %{h['policy_accuracy_pct']:.1f} | "
                f"Durum: {h['convergence_status']}"
            )

    models_dir = os.path.join(ROOT_DIR, "models")
    meta = trainer.export_bitnet_b158_checkpoint(models_dir)
    q = meta["bitnet_quantization"]

    print("-" * 74)
    print(f"  * Kuantize Parametre Sayısı : {q['num_parameters_quantized']}")
    print(f"  * BitNet b1.58 Ölçek (gamma): {q['scale_gamma']}")
    print(f"  * Seyreklik Oranı (Sparsity): %{q['sparsity_ratio'] * 100:.1f}")
    print(f"  * Sıkıştırma Oranı (vs FP16): {q['compression_ratio_vs_fp16']}x")
    print(f"  * İkili Ağırlık Dosyası     : {meta['binary_file']}")
    print("=" * 74)


if __name__ == "__main__":
    main()
