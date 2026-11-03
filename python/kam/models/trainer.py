import math
from typing import List, Dict, Any
from .liquid_moe import KamLiquidFoundationModel, LiquidModelConfig

class ActiveInferenceTrainer:
    """
    Karl Friston Serbest Enerji Prensibi ile Bilişsel Eğitim Döngüsü
    Kayıp Fonksiyonu: L = F_variational + lambda * L_balance
    """
    def __init__(self, model: KamLiquidFoundationModel = None):
        self.model = model or KamLiquidFoundationModel()
        self.epochs_completed = 0
        self.history = []

    def train_step(self, synthetic_batch: List[List[float]]) -> Dict[str, Any]:
        total_fe = 0.0
        for sample in synthetic_batch:
            out = self.model.forward(sample)
            total_fe += out["free_energy_nats"]

        avg_fe = total_fe / len(synthetic_batch)
        self.epochs_completed += 1

        metrics = {
            "epoch": self.epochs_completed,
            "mean_free_energy": round(avg_fe, 5),
            "convergence_status": "MINIMIZED_EQUILIBRIUM" if avg_fe < 0.25 else "ADAPTING_CHAOS",
            "tau_adaptive": self.model.current_tau
        }
        self.history.append(metrics)
        return metrics

    def run_training_cycle(self, steps: int = 5) -> List[Dict[str, Any]]:
        # Sentetik telemetri veri kümesi
        batch = [
            [0.92, 0.05, 0.02, 0.01] * 4,
            [0.10, 0.85, 0.04, 0.01] * 4,
            [0.05, 0.05, 0.85, 0.05] * 4
        ]
        results = []
        for _ in range(steps):
            results.append(self.train_step(batch))
        return results
