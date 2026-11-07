import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class PolicyEvaluation:
    policy_name: str
    expected_free_energy_g: float
    epistemic_value: float
    pragmatic_value: float
    action_probability: float
    recommended_cpp_module: str


class ActiveInferenceEngine:
    """
    Karl Friston'un Free Energy Principle (Serbest Enerji Prensibi) Python Motoru.
    1. Varyasyonel Serbest Enerji (VFE):
       F = D_KL(q(s) || p(s)) - E_q[ln p(o|s)]
    2. Beklenen Serbest Enerji (EFE) ve Çok Ufuklu Politika Seçimi:
       G(pi) = -Epistemik_Deger(Bilgi_Kazanimi) - Pragmatik_Deger(Dirlik_Tercihi)
       P(pi) = Softmax(-gamma * G(pi))
    """

    POLICY_CATALOG: Dict[str, Dict[str, Any]] = {
        "NOMINAL_UART_MONITOR": {
            "predicted_obs": [0.93, 0.04, 0.02, 0.01],
            "info_gain_base": 0.12,
            "cost": 0.02,
            "cpp_module": "nominal_telemetry_guard.cpp",
        },
        "SDR_868MHZ_FHSS_REROUTE": {
            "predicted_obs": [0.90, 0.06, 0.03, 0.01],
            "info_gain_base": 0.85,
            "cost": 0.15,
            "cpp_module": "sdr_fallback_node.cpp",
        },
        "EW_ANTI_JAMMING_HOPPER": {
            "predicted_obs": [0.89, 0.07, 0.03, 0.01],
            "info_gain_base": 0.82,
            "cost": 0.18,
            "cpp_module": "ew_fhss_hopper.cpp",
        },
        "THERMAL_INT4_AWQ_DOWNGRADE": {
            "predicted_obs": [0.91, 0.05, 0.03, 0.01],
            "info_gain_base": 0.76,
            "cost": 0.12,
            "cpp_module": "thermal_vision_fallback.cpp",
        },
        "CAN_EBPF_PACKET_QUARANTINE": {
            "predicted_obs": [0.92, 0.05, 0.02, 0.01],
            "info_gain_base": 0.88,
            "cost": 0.10,
            "cpp_module": "can_firewall_filter.cpp",
        },
        "GNSS_OPTICAL_FLOW_DEAD_RECKONING": {
            "predicted_obs": [0.91, 0.06, 0.02, 0.01],
            "info_gain_base": 0.86,
            "cost": 0.11,
            "cpp_module": "gnss_optical_flow_ekf.cpp",
        },
        "SWARM_RAFT_LEADER_HANDOVER": {
            "predicted_obs": [0.90, 0.06, 0.03, 0.01],
            "info_gain_base": 0.84,
            "cost": 0.13,
            "cpp_module": "swarm_raft_leader_handover.cpp",
        },
    }

    def __init__(self, precision_gamma: float = 4.0):
        # Durum uzayı: [Dirlik/Nominal, Spektral_Gürültü, Termal_Stres, Donanım_Çöküşü]
        self.prior_beliefs = [0.95, 0.03, 0.015, 0.005]
        self.posterior_beliefs = [0.94, 0.04, 0.015, 0.005]
        self.observations = [0.94, 0.04, 0.015, 0.005]
        self.entropy = 0.03
        self.precision_gamma = precision_gamma

    @staticmethod
    def _normalize(dist: List[float]) -> List[float]:
        eps = 1e-12
        clamped = [max(v, eps) for v in dist]
        total = sum(clamped)
        return [v / total for v in clamped]

    def kl_divergence(self, q: List[float], p: List[float]) -> float:
        eps = 1e-12
        kl = 0.0
        for qi, pi in zip(q, p):
            qi_clamped = max(qi, eps)
            pi_clamped = max(pi, eps)
            kl += qi_clamped * math.log(qi_clamped / pi_clamped)
        return kl

    def shannon_entropy(self, dist: Optional[List[float]] = None) -> float:
        target = self._normalize(dist if dist is not None else self.observations)
        return -sum(p * math.log(p) for p in target)

    def update_beliefs_bayes(self, observations: List[float], learning_rate: float = 0.65) -> List[float]:
        """
        Duyusal gözlem o geldiğinde içsel inanç dağılımı q(s)'yi Bayesçi varyasyonel
        adım ile günceller.
        """
        obs_norm = self._normalize(observations)
        self.observations = obs_norm
        blended = [
            (1.0 - learning_rate) * q_i + learning_rate * o_i
            for q_i, o_i in zip(self.posterior_beliefs, obs_norm)
        ]
        self.posterior_beliefs = self._normalize(blended)
        return self.posterior_beliefs

    def compute_free_energy(self, observations: Optional[List[float]] = None) -> float:
        """
        Varyasyonel Serbest Enerji (VFE):
        F = D_KL(q(s) || p(s)) - E_q[ln p(o|s)]
        """
        if observations is not None:
            self.update_beliefs_bayes(observations)
        kl = self.kl_divergence(self.posterior_beliefs, self.prior_beliefs)
        accuracy = sum(
            q_i * math.log(max(o_i, 1e-12))
            for q_i, o_i in zip(self.posterior_beliefs, self.observations)
        )
        fe = max(0.0, kl - accuracy)
        return fe

    def compute_expected_free_energy(
        self,
        policy_name: str,
        crisis_hint: Optional[str] = None,
        horizon_steps: int = 3,
    ) -> Dict[str, float]:
        """
        Beklenen Serbest Enerji (EFE):
        G(pi) = sum_tau [ -Epistemik_Deger(pi, tau) - Pragmatik_Deger(pi, tau) ]
        """
        spec = self.POLICY_CATALOG.get(policy_name, self.POLICY_CATALOG["NOMINAL_UART_MONITOR"])
        pred_obs = self._normalize(spec["predicted_obs"])

        # Pragmatik değer: Tercih edilen dirlik dağılımı p(o) ile beklenen gözlem uyumu
        pragmatic_single = sum(
            o_pred * math.log(max(p_pref, 1e-12))
            for o_pred, p_pref in zip(pred_obs, self.prior_beliefs)
        ) - spec["cost"]

        # Epistemik değer: Mevcut kaos/belirsizlik yüksekken kurtarma politikalarının bilgi kazanımı artar
        uncertainty_drive = 0.15 + 1.85 * self.entropy
        if self.entropy < 0.25 and policy_name == "NOMINAL_UART_MONITOR":
            contextual_bonus = 0.65
        elif crisis_hint and crisis_hint.upper() in policy_name:
            contextual_bonus = 0.75
        else:
            contextual_bonus = 0.0

        epistemic_single = spec["info_gain_base"] * uncertainty_drive + contextual_bonus

        # Ufuk (horizon) boyunca zaman indirimli (discounted) toplam
        discount = sum(0.9 ** t for t in range(max(1, horizon_steps)))
        epistemic_total = epistemic_single * discount
        pragmatic_total = pragmatic_single * discount

        # G(pi) ne kadar düşükse politika o kadar optimaldir
        g_value = -epistemic_total - pragmatic_total
        return {
            "G": round(g_value, 4),
            "epistemic_value": round(epistemic_total, 4),
            "pragmatic_value": round(pragmatic_total, 4),
        }

    def select_optimal_policy(self, crisis_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Tüm aday politikalar için G(pi) hesaplar ve P(pi) = Softmax(-gamma * G(pi))
        ile en düşük beklenen serbest enerjili eylem planını seçer.
        """
        raw_evals = []
        for p_name, spec in self.POLICY_CATALOG.items():
            efe = self.compute_expected_free_energy(p_name, crisis_hint=crisis_hint)
            raw_evals.append((p_name, efe, spec["cpp_module"]))

        # Softmax(-gamma * G)
        logits = [-self.precision_gamma * item[1]["G"] for item in raw_evals]
        max_logit = max(logits)
        exp_logits = [math.exp(l - max_logit) for l in logits]
        sum_exp = sum(exp_logits) + 1e-12

        evaluations: List[PolicyEvaluation] = []
        for idx, (p_name, efe, cpp_mod) in enumerate(raw_evals):
            prob = exp_logits[idx] / sum_exp
            evaluations.append(
                PolicyEvaluation(
                    policy_name=p_name,
                    expected_free_energy_g=efe["G"],
                    epistemic_value=efe["epistemic_value"],
                    pragmatic_value=efe["pragmatic_value"],
                    action_probability=round(prob, 4),
                    recommended_cpp_module=cpp_mod,
                )
            )

        evaluations.sort(key=lambda e: e.expected_free_energy_g)
        best = evaluations[0]
        return {
            "optimal_policy": best.policy_name,
            "recommended_cpp_module": best.recommended_cpp_module,
            "expected_free_energy_g": best.expected_free_energy_g,
            "optimal_probability": best.action_probability,
            "candidates": [
                {
                    "policy": ev.policy_name,
                    "G": ev.expected_free_energy_g,
                    "epistemic": ev.epistemic_value,
                    "pragmatic": ev.pragmatic_value,
                    "prob": ev.action_probability,
                    "cpp_module": ev.recommended_cpp_module,
                }
                for ev in evaluations
            ],
        }

    def trigger_anomaly(self) -> float:
        # Donanım kesintisi: Gözlemler tamamen çöküş durumuna kaydı
        self.update_beliefs_bayes([0.01, 0.02, 0.08, 0.89], learning_rate=0.85)
        self.entropy = 0.89
        return self.entropy

    def reset_equilibrium(self, stabilized_entropy: float = 0.15):
        self.entropy = stabilized_entropy
        self.update_beliefs_bayes([0.88, 0.08, 0.03, 0.01], learning_rate=0.90)

