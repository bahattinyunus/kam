from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass(frozen=True)
class FlightControlCommand:
    target_altitude_agl_m: float
    airspeed_mps: float
    bank_angle_deg: float
    battery_pct: float


class NeuroSymbolicSafetyShield:
    """
    DARPA ANSR (Assured Neuro-Symbolic Learning and Reasoning) ve Kontrol Bariyer
    Fonksiyonları (Control Barrier Functions - CBF: h(x) >= 0) tabanlı
    Nöro-Sembolik Güvenlik Kalkanı.

    Hiçbir nöral ağ (RK4 Liquid-MoE) veya LLM (kam:7b / kam:r1) çıktısının
    fiziksel uçuş zarfını (stall hızı, minimum irtifa, yatış açısı, batarya RTL rezervi)
    ihlal etmesine izin vermez; ihlal eden komutu matematiksel olarak en yakın
    güvenli komuta izdüşürür (CBF Quadratic Projection).
    """

    MIN_AGL_ALTITUDE_M = 30.0
    MAX_AGL_ALTITUDE_M = 4500.0
    MIN_STALL_SPEED_MPS = 22.0
    MAX_STRUCTURAL_SPEED_MPS = 115.0
    MAX_BANK_ANGLE_DEG = 55.0
    MIN_BATTERY_RTL_PCT = 18.0

    @classmethod
    def verify_and_project(cls, proposed: FlightControlCommand) -> Dict[str, Any]:
        violations: List[str] = []

        # 1. İrtifa Bariyeri: h_1(x) = z_agl - z_min >= 0
        safe_alt = proposed.target_altitude_agl_m
        if safe_alt < cls.MIN_AGL_ALTITUDE_M:
            violations.append(f"CBF_ALTITUDE_FLOOR_VIOLATION ({safe_alt}m < {cls.MIN_AGL_ALTITUDE_M}m)")
            safe_alt = cls.MIN_AGL_ALTITUDE_M
        elif safe_alt > cls.MAX_AGL_ALTITUDE_M:
            violations.append(f"CBF_ALTITUDE_CEILING_VIOLATION ({safe_alt}m > {cls.MAX_AGL_ALTITUDE_M}m)")
            safe_alt = cls.MAX_AGL_ALTITUDE_M

        # 2. Perdövites (Stall) ve Yapısal Hız Zarfı: h_2(x) = v - v_stall >= 0
        safe_speed = proposed.airspeed_mps
        if safe_speed < cls.MIN_STALL_SPEED_MPS:
            violations.append(f"CBF_STALL_SPEED_VIOLATION ({safe_speed} m/s < {cls.MIN_STALL_SPEED_MPS} m/s)")
            safe_speed = cls.MIN_STALL_SPEED_MPS
        elif safe_speed > cls.MAX_STRUCTURAL_SPEED_MPS:
            violations.append(f"CBF_OVERSPEED_VIOLATION ({safe_speed} m/s > {cls.MAX_STRUCTURAL_SPEED_MPS} m/s)")
            safe_speed = cls.MAX_STRUCTURAL_SPEED_MPS

        # 3. Maksimum Yatış (Bank Angle) Zarfı: h_3(x) = phi_max - |phi| >= 0
        safe_bank = proposed.bank_angle_deg
        if abs(safe_bank) > cls.MAX_BANK_ANGLE_DEG:
            violations.append(f"CBF_BANK_ANGLE_VIOLATION ({safe_bank} deg)")
            safe_bank = cls.MAX_BANK_ANGLE_DEG if safe_bank > 0 else -cls.MAX_BANK_ANGLE_DEG

        # 4. Batarya Zorunlu Eve Dönüş (RTL) Sembolik Kuralı
        rtl_triggered = False
        if proposed.battery_pct < cls.MIN_BATTERY_RTL_PCT:
            violations.append(f"SYMBOLIC_RTL_BATTERY_RESERVE ({proposed.battery_pct}% < {cls.MIN_BATTERY_RTL_PCT}%)")
            rtl_triggered = True
            safe_bank = 0.0
            safe_speed = 32.0  # Maksimum menzil (endurance) süzülüş hızı

        cbf_margin = min(
            safe_alt - cls.MIN_AGL_ALTITUDE_M,
            safe_speed - cls.MIN_STALL_SPEED_MPS,
            cls.MAX_BANK_ANGLE_DEG - abs(safe_bank),
        )

        return {
            "shield": "KAM-ANSR-NeuroSymbolic-CBF-Shield",
            "intervention_occurred": len(violations) > 0,
            "symbolic_violations_prevented": violations,
            "rtl_override_active": rtl_triggered,
            "cbf_safety_margin": round(max(0.0, cbf_margin), 3),
            "safe_command": {
                "target_altitude_agl_m": round(safe_alt, 2),
                "airspeed_mps": round(safe_speed, 2),
                "bank_angle_deg": round(safe_bank, 2),
            },
        }
