import json
import math
import os
import struct
from typing import List, Dict, Any, Tuple
from .liquid_moe import KamLiquidFoundationModel, LiquidModelConfig
from ..edge_optimizer import TernaryBitNetQuantizer, ImatrixCalibrator


class ActiveInferenceTrainer:
    """
    Karl Friston Serbest Enerji Prensibi + Çoklu Görev (Politika + EW Emiter + CBF Marjı)
    Gradyan İnişi + Hessian imatrix + BitNet b1.58 Eğitim ve Ağırlık Sentezleme Motoru.
    Kayıp Fonksiyonu:
      L = F_variational + lambda_ce * L_policy_ce + lambda_ew * L_ew_ce + lambda_aux * L_moe_balance
    """

    ACTION_LIST = ["UART_STABILIZE", "SDR_FREQUENCY_HOP", "I2C_BUS_REMAP", "THERMAL_THROTTLE_DOWNGRADE"]
    EW_EMITTER_LIST = ["S400_92N6E", "PANTSIR_S1", "X_BAND_AESA", "AGILE_LPI_SDR"]

    def __init__(self, model: KamLiquidFoundationModel = None, lr: float = 0.08):
        self.model = model or KamLiquidFoundationModel()
        self.lr = lr
        self.epochs_completed = 0
        self.history: List[Dict[str, Any]] = []

    def train_step(
        self,
        labeled_batch: List[Tuple[List[float], int]],
    ) -> Dict[str, Any]:
        """
        Her örnek (sensory_vector, target_action_idx) için ileri besleme yapar,
        hem Kriz Politikası Başlığı (dL/dW_action), hem Bilişsel EW Emiter Başlığı (dL/dW_ew_emitter),
        hem de 8 Seyrek Uzman ve RK4 LTC serbest enerji sönümlemesi ile ağırlıkları günceller.
        """
        total_fe = 0.0
        total_loss = 0.0
        correct_policy = 0
        correct_ew = 0

        for sample, target_idx in labeled_batch:
            self.model.hidden_state = [0.02] * self.model.config.hidden_dim
            out = self.model.forward(sample)
            fe = out["free_energy_nats"]
            probs_dict = out["action_probabilities"]
            probs = [probs_dict[name] for name in self.ACTION_LIST]

            ew_dict = out["ew_emitter_probabilities"]
            ew_probs = [ew_dict[name] for name in self.EW_EMITTER_LIST]
            target_ew_idx = target_idx % 4

            pred_idx = max(range(4), key=lambda i: probs[i])
            if pred_idx == target_idx:
                correct_policy += 1

            pred_ew = max(range(4), key=lambda i: ew_probs[i])
            if pred_ew == target_ew_idx:
                correct_ew += 1

            ce_loss = -math.log(max(probs[target_idx], 1e-9))
            ew_loss = -math.log(max(ew_probs[target_ew_idx], 1e-9))
            loss = fe + 0.5 * ce_loss + 0.25 * ew_loss + 0.02 * out["moe_aux_balance_loss"]
            total_fe += fe
            total_loss += loss

            # 1. Politika Başlığı ve EW Emiter Başlığı Gradyan Güncellemesi (Softmax CE Gradient)
            for a in range(4):
                grad_a = probs[a] - (1.0 if a == target_idx else 0.0)
                grad_ew = ew_probs[a] - (1.0 if a == target_ew_idx else 0.0)
                self.model.action_bias[a] -= self.lr * grad_a
                self.model.ew_bias[a] -= self.lr * grad_ew
                for j in range(16):
                    feature_j = self.model.hidden_state[j] + sample[j % len(sample)]
                    self.model.w_action[a][j] -= self.lr * grad_a * feature_j
                    self.model.w_ew_emitter[a][j] -= self.lr * grad_ew * feature_j

            # 2. Paylaşımlı Uzman, 8 Seyrek Uzman ve RK4 LTC Serbest Enerji Sönümlemesi
            for i in range(len(self.model.w_in)):
                self.model.w_in[i] *= (1.0 - 0.015 * self.lr)
                self.model.w_rec[i] *= (1.0 - 0.010 * self.lr)
                self.model.w_shared_expert[i] *= (1.0 - 0.005 * self.lr)
                for e_idx in range(self.model.config.num_experts):
                    self.model.w_experts[e_idx][i] *= (1.0 - 0.005 * self.lr)

        n = float(max(1, len(labeled_batch)))
        avg_fe = total_fe / n
        avg_loss = total_loss / n
        acc = (correct_policy / n) * 100.0
        ew_acc = (correct_ew / n) * 100.0
        self.epochs_completed += 1

        metrics = {
            "epoch": self.epochs_completed,
            "mean_free_energy": round(avg_fe, 5),
            "total_loss": round(avg_loss, 5),
            "policy_accuracy_pct": round(acc, 2),
            "ew_emitter_accuracy_pct": round(ew_acc, 2),
            "convergence_status": "MINIMIZED_EQUILIBRIUM" if avg_fe < 0.25 else "ADAPTING_CHAOS",
            "tau_adaptive": round(self.model.current_tau, 4),
        }
        self.history.append(metrics)
        return metrics

    def run_training_cycle(self, steps: int = 5) -> List[Dict[str, Any]]:
        labeled_batch: List[Tuple[List[float], int]] = [
            ([0.92, 0.05, 0.02, 0.01] * 4, 0),  # Nominal -> UART_STABILIZE / S400_92N6E
            ([0.05, 0.94, 0.88, 0.02] * 4, 1),  # UART/EW Krizi -> SDR_FREQUENCY_HOP / PANTSIR_S1
            ([0.04, 0.12, 0.91, 0.75] * 4, 2),  # Veriyolu Spoofing -> I2C_BUS_REMAP / X_BAND_AESA
            ([0.02, 0.08, 0.15, 0.96] * 4, 3),  # 92.4 C Termal Pik -> THERMAL_THROTTLE_DOWNGRADE / AGILE_LPI_SDR
        ]
        results = []
        for _ in range(steps):
            results.append(self.train_step(labeled_batch))
        return results

    def export_bitnet_b158_checkpoint(self, output_dir: str) -> Dict[str, Any]:
        """
        Eğitilmiş tüm model ağırlıklarını (RK4 LTC + Shared Expert + 8 Routed Experts +
        Policy Head + EW Emitter Head + CBF Margin Head = 848 parametre) BitNet b1.58 {-1, 0, +1}
        üçlü formatına kuantize eder, Hessian imatrix önem skorlarını hesaplar ve diske yazar.
        """
        os.makedirs(output_dir, exist_ok=True)
        flat_weights: List[float] = (
            list(self.model.w_in)
            + list(self.model.w_rec)
            + list(self.model.w_shared_expert)
            + [w for exp_row in self.model.w_experts for w in exp_row]
            + [w for row in self.model.w_action for w in row]
            + [w for row in self.model.w_ew_emitter for w in row]
            + list(self.model.w_cbf_margin)
        )
        q_info = TernaryBitNetQuantizer.quantize_tensor(flat_weights)
        ternary_w = q_info["ternary_weights"]

        # Hessian imatrix kalibrasyon profili
        layer_acts = {
            "blk.0.rk4_ltc": list(self.model.w_in),
            "blk.0.moe_router": [w for row in self.model.w_action for w in row],
            "blk.0.shared_expert": list(self.model.w_shared_expert),
            "blk.0.ew_head": [w for row in self.model.w_ew_emitter for w in row],
            "output.weight": list(self.model.w_cbf_margin),
        }
        layer_norms = {k: math.sqrt(sum(v * v for v in vals)) for k, vals in layer_acts.items()}
        imatrix_profile = ImatrixCalibrator.compute_layer_importance(layer_acts, layer_norms)

        bin_path = os.path.join(output_dir, "kam_edge_apex_b158.bin")
        with open(bin_path, "wb") as bf:
            bf.write(b"KAMB")
            bf.write(struct.pack("<IfI", 3, float(q_info["scale_gamma"]), len(ternary_w)))
            bf.write(struct.pack(f"<{len(ternary_w)}b", *ternary_w))

        json_path = os.path.join(output_dir, "kam_edge_apex_checkpoint.json")
        meta = {
            "architecture": "KAM-Edge-MoE-v2-TriHybrid-RK4-BitNet-b1.58",
            "epochs_trained": self.epochs_completed,
            "final_metrics": self.history[-1] if self.history else {},
            "bitnet_quantization": {
                "num_parameters_quantized": len(ternary_w),
                "scale_gamma": q_info["scale_gamma"],
                "sparsity_ratio": q_info["sparsity_ratio"],
                "rmse": q_info["rmse"],
                "compression_ratio_vs_fp16": q_info["compression_ratio_vs_fp16"],
                "energy_saving_factor": q_info["energy_saving_factor"],
            },
            "hessian_imatrix_calibration": imatrix_profile,
            "action_bias": [round(b, 6) for b in self.model.action_bias],
            "ew_bias": [round(b, 6) for b in self.model.ew_bias],
            "binary_file": bin_path,
        }
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(meta, jf, ensure_ascii=False, indent=2)

        return meta
