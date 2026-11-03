import math
from typing import List, Tuple

class ActiveInferenceEngine:
    """
    Karl Friston'un Free Energy Principle (Serbest Enerji Prensibi) Python Motoru
    F = D_KL(q(s) || p(s)) - E_q[ln p(o|s)]
    """
    def __init__(self):
        self.prior_beliefs = [0.95, 0.03, 0.015, 0.005]
        self.observations = [0.94, 0.04, 0.015, 0.005]
        self.entropy = 0.03

    def kl_divergence(self, q: List[float], p: List[float]) -> float:
        eps = 1e-12
        kl = 0.0
        for qi, pi in zip(q, p):
            qi_clamped = max(qi, eps)
            pi_clamped = max(pi, eps)
            kl += qi_clamped * math.log(qi_clamped / pi_clamped)
        return kl

    def compute_free_energy(self, observations: List[float] = None) -> float:
        if observations:
            self.observations = observations
        kl = self.kl_divergence(self.observations, self.prior_beliefs)
        accuracy = sum(o * math.log(max(o, 1e-12)) for o in self.observations)
        fe = max(0.0, kl - accuracy)
        return fe

    def trigger_anomaly(self) -> float:
        # Donanım kesintisi: Gözlemler tamamen çöküş durumuna kaydı
        self.observations = [0.01, 0.02, 0.08, 0.89]
        self.entropy = 0.89
        return self.entropy

    def reset_equilibrium(self, stabilized_entropy: float = 0.15):
        self.entropy = stabilized_entropy
        self.observations = [0.88, 0.08, 0.03, 0.01]
