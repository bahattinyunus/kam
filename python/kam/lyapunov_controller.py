import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class LyapunovStabilityReport:
    lyapunov_v: float
    lyapunov_dv_dt: float
    decay_margin: float
    is_asymptotically_stable: bool
    stabilizing_control_gain: float
    recommended_damping_action: str


class LyapunovCognitiveController:
    """
    Aleksandr Lyapunov'un Kontrol-Lyapunov Fonksiyonu (CLF) ile Karl Friston'un
    Varyasyonel Serbest Enerjisini (F) birleştiren Asimptotik Kararlılık Denetleyicisi
    ve Faz Uzayı Kriz Öngörücüsü (Pre-Crisis Time-To-Anomaly Forecaster).

    Lyapunov Aday Fonksiyonu:
      V(e, F) = 0.5 * e^T * P * e + alpha * F(o, q) > 0
    Üstel Asimptotik Kararlılık Koşulu:
      dV/dt + lambda * V <= 0
    """

    def __init__(self, alpha_fe: float = 1.25, lambda_decay: float = 0.85):
        self.alpha_fe = alpha_fe
        self.lambda_decay = lambda_decay
        self.p_weights = [1.5, 1.5, 2.0, 1.0, 1.0, 1.2]
        self.prev_v: Optional[float] = None

    def compute_lyapunov_function(self, state_error: List[float], free_energy: float) -> float:
        """
        V(e, F) = 0.5 * sum(P_i * e_i^2) + alpha * F
        """
        quad_energy = 0.0
        for i, err in enumerate(state_error):
            p_i = self.p_weights[i % len(self.p_weights)]
            quad_energy += 0.5 * p_i * (err * err)
        v_val = quad_energy + self.alpha_fe * max(0.0, free_energy)
        return round(v_val, 6)

    def evaluate_stability_step(
        self,
        state_error: List[float],
        free_energy: float,
        dt: float = 0.05,
    ) -> LyapunovStabilityReport:
        """
        Anlık durum hatası e ve serbest enerji F için V ve dV/dt hesaplar.
        Eğer dV/dt + lambda * V > 0 ise (sistem kaosa sürükleniyorsa), Sontag evrensel
        formülüyle sistemi tekrar kararlı çekim bölgesine (attractor basin) bastıracak
        sönümleme kazancını (stabilizing_control_gain) sentezler.
        """
        v_now = self.compute_lyapunov_function(state_error, free_energy)
        if self.prev_v is None:
            dv_dt = (-1.15 * self.lambda_decay * v_now) if v_now <= 0.35 else (0.25 * v_now)
        else:
            dv_dt = (v_now - self.prev_v) / max(dt, 1e-5)
        self.prev_v = v_now

        # Kararlılık eşiği: dV/dt + lambda * V <= 0
        stability_lhs = dv_dt + self.lambda_decay * v_now
        is_stable = stability_lhs <= 1e-4

        if is_stable:
            control_gain = 0.0
            action = "ATTRACTOR_EQUILIBRIUM_HOLD"
        else:
            # Sontag CLF sönümleme darbesi: u_gain = (dV/dt + lambda * V) / (1 + V)
            control_gain = round(stability_lhs / (1.0 + v_now), 4)
            action = "CLF_EMERGENCY_ENTROPY_DAMPING_JIT"

        return LyapunovStabilityReport(
            lyapunov_v=round(v_now, 5),
            lyapunov_dv_dt=round(dv_dt, 5),
            decay_margin=round(-stability_lhs, 5),
            is_asymptotically_stable=is_stable,
            stabilizing_control_gain=control_gain,
            recommended_damping_action=action,
        )

    @staticmethod
    def forecast_time_to_anomaly(
        series: List[float],
        critical_threshold: float,
        sample_dt_sec: float = 0.1,
    ) -> Dict[str, Any]:
        """
        2. Dereceden Taylor Faz Uzayı Ekstrapolasyonu:
        x(t + tau) = x_t + v_t * tau + 0.5 * a_t * tau^2
        Sensör/Termal/Entropi serisinin kritik eşiği (örn. 85 °C veya %80 Entropi)
        kaç saniye sonra aşacağını kriz gerçekleşmeden ÖNCE tahmin eder (Preemptive Self-Healing).
        """
        if not series:
            return {
                "current_value": 0.0,
                "velocity_per_sec": 0.0,
                "acceleration_per_sec2": 0.0,
                "estimated_tta_sec": None,
                "preemptive_alert": False,
            }

        x_t = series[-1]
        if x_t >= critical_threshold:
            return {
                "current_value": round(x_t, 4),
                "velocity_per_sec": 0.0,
                "acceleration_per_sec2": 0.0,
                "estimated_tta_sec": 0.0,
                "preemptive_alert": True,
            }

        dt = max(sample_dt_sec, 1e-4)
        v_t = (series[-1] - series[-2]) / dt if len(series) >= 2 else 0.0
        if len(series) >= 3:
            v_prev = (series[-2] - series[-3]) / dt
            a_t = (v_t - v_prev) / dt
        else:
            a_t = 0.0

        gap = critical_threshold - x_t
        tta_sec: Optional[float] = None

        if v_t > 1e-6 or a_t > 1e-6:
            if abs(a_t) < 1e-5:
                tta_sec = gap / v_t if v_t > 0 else None
            else:
                # 0.5 * a * tau^2 + v * tau - gap = 0
                disc = v_t * v_t + 2.0 * a_t * gap
                if disc >= 0.0:
                    root1 = (-v_t + math.sqrt(disc)) / a_t
                    root2 = (-v_t - math.sqrt(disc)) / a_t
                    pos_roots = [r for r in (root1, root2) if r > 0.0]
                    if pos_roots:
                        tta_sec = min(pos_roots)

        preemptive = tta_sec is not None and tta_sec <= 15.0
        return {
            "current_value": round(x_t, 4),
            "velocity_per_sec": round(v_t, 4),
            "acceleration_per_sec2": round(a_t, 4),
            "estimated_tta_sec": round(tta_sec, 3) if tta_sec is not None else None,
            "preemptive_alert": preemptive,
        }
