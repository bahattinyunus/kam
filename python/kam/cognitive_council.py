from typing import Dict, Any, List, Optional
from .active_inference import ActiveInferenceEngine
from .code_mutator import CodeMutator
from .lyapunov_controller import LyapunovCognitiveController


class CognitiveCouncilRouter:
    """
    KAM 5-Modelli Bilişsel Kurul (Sovereign Council) ve Otonom Uzman Yönlendiricisi.
    Yerel Ollama/GGUF ailesindeki 5 uzman modeli (kam:7b, kam:r1, kam:coder, kam:r1-nano, kam:1.5b)
    görev tipine, donanım RAM/TDP zarfına ve NPU sıcaklığına göre otonom orkestre eder:
      - kam:coder   -> C++20 Bellek-İçi JIT, Linux eBPF, CUDA/SIMD ve AST Sandbox kod sentezi
      - kam:r1      -> Derin matematiksel ispat, Karl Friston VFE/EFE ve çok adımlı CoT (<think>)
      - kam:r1-nano -> Kısıtlı donanımda (1-2 GB RAM / >85°C termal stres) hızlı CoT muhakemesi
      - kam:1.5b    -> Milisaniye altı taktik uç karar ve kam:7b için öz-spekülatif taslak üretimi
      - kam:7b      -> Duru Türkçe belâgat, Dede Korkut hikmeti ve başmühendislik sentezi
    """

    CODE_KEYWORDS = (
        "c++", "cpp", "jit", "kod", "code", "ebpf", "kprobe", "memfd", "dlopen",
        "arena", "simd", "cuda", "ast", "entrypoint", "struct", "sınıf", "class",
    )
    REASONING_KEYWORDS = (
        "neden", "ispat", "matematik", "denklem", "friston", "lyapunov", "formül",
        "hesapla", "analiz", "mahalanobis", "kalman", "entropi", "serbest enerji",
    )

    def __init__(self):
        self.inference = ActiveInferenceEngine()
        self.lyapunov = LyapunovCognitiveController()

    @classmethod
    def select_specialist_model(
        cls,
        prompt: str,
        ram_mb: int = 8192,
        npu_temp_c: float = 48.0,
    ) -> Dict[str, Any]:
        p_low = prompt.lower()
        thermal_throttled = npu_temp_c >= 85.0 or ram_mb <= 2048

        if any(k in p_low for k in cls.CODE_KEYWORDS):
            return {
                "selected_model": "kam:coder",
                "role": "Demirci (C++20 JIT & Linux eBPF Kod Uzmanı)",
                "reason": "İstemde C++20/eBPF/JIT/mimari kod sentezi tespit edildi.",
            }

        if any(k in p_low for k in cls.REASONING_KEYWORDS):
            if thermal_throttled:
                return {
                    "selected_model": "kam:r1-nano",
                    "role": "Taktik Bilge (1.5B CoT Zincirleme Akıl Yürütme)",
                    "reason": "Kısıtlı bellek/termal zarf altında derin CoT muhakemesi seçildi.",
                }
            return {
                "selected_model": "kam:r1",
                "role": "Baş Bilge (7B DeepSeek-R1 CoT Akıl Yürütme)",
                "reason": "Matematiksel/sibernetik derin muhakeme tespit edildi.",
            }

        if thermal_throttled:
            return {
                "selected_model": "kam:1.5b",
                "role": "Uç Gözcü (1.5B Hızlı Mikro-Uç Zihin)",
                "reason": "Düşük bellek/yüksek sıcaklık zarfı nedeniyle hızlı uç model seçildi.",
            }

        return {
            "selected_model": "kam:7b",
            "role": "Ulu Kam (7B Duru Türkçe Hikmet ve Komuta Zihni)",
            "reason": "Genel komuta, hikmet ve mimari sentez görevi.",
        }

    def synthesize_council_verdict(
        self,
        crisis_hint: str = "SDR",
        telemetry_series: Optional[List[float]] = None,
        state_error: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Üçlü Bilişsel Kurul (Bilge + Demirci + Gözcü) ortak karar sentezi:
          1. Bilge (EFE Politika Seçici): G(pi) minimizasyonu ile optimal politikayı bulur.
          2. Gözcü (Lyapunov CLF & TTA): Asimptotik kararlılığı ve kriz süresini (TTA) ölçer.
          3. Demirci (C++20 JIT Mutator): AST Sandbox onaylı kurtarma modülünü üretir.
        """
        series = telemetry_series or [58.0, 66.0, 75.5, 83.0]
        errs = state_error or [0.12, -0.08, 0.15, 0.04, -0.03, 0.05]

        # 1. Bilge: Beklenen Serbest Enerji (EFE) Politikası
        self.inference.trigger_anomaly()
        efe_decision = self.inference.select_optimal_policy(crisis_hint=crisis_hint)
        fe_val = self.inference.compute_free_energy()

        # 2. Gözcü: Lyapunov Asimptotik Kararlılık ve Faz Uzayı TTA Tahmini
        clf_report = self.lyapunov.evaluate_stability_step(errs, fe_val)
        tta_report = self.lyapunov.forecast_time_to_anomaly(series, critical_threshold=85.0, sample_dt_sec=0.5)

        # 3. Demirci: C++20 JIT Kod Sentezi ve AST Denetimi
        hint_up = crisis_hint.upper()
        if "THERMAL" in hint_up:
            cpp_code = CodeMutator.generate_thermal_fallback()
        elif "EW" in hint_up or "JAM" in hint_up:
            cpp_code = CodeMutator.generate_ew_fhss_fallback()
        elif "CAN" in hint_up:
            cpp_code = CodeMutator.generate_can_firewall_fallback()
        elif "GNSS" in hint_up or "GPS" in hint_up:
            cpp_code = CodeMutator.generate_gnss_spoof_fallback()
        elif "SWARM" in hint_up:
            cpp_code = CodeMutator.generate_swarm_handover_fallback()
        else:
            cpp_code = CodeMutator.generate_sdr_fallback()

        ast_validation = CodeMutator.validate_ast(cpp_code)
        self.inference.reset_equilibrium(0.14)

        return {
            "council_status": "UNANIMOUS_SOVEREIGN_INTERVENTION",
            "bilge_efe_policy": {
                "specialist_model": "kam:r1 / kam:r1-nano",
                "optimal_policy": efe_decision["optimal_policy"],
                "expected_free_energy_g": efe_decision["expected_free_energy_g"],
                "recommended_cpp_module": efe_decision["recommended_cpp_module"],
            },
            "gozcu_lyapunov_stability": {
                "specialist_model": "kam:1.5b",
                "lyapunov_v": clf_report.lyapunov_v,
                "lyapunov_dv_dt": clf_report.lyapunov_dv_dt,
                "is_asymptotically_stable": clf_report.is_asymptotically_stable,
                "stabilizing_control_gain": clf_report.stabilizing_control_gain,
                "damping_action": clf_report.recommended_damping_action,
                "tta_forecast": tta_report,
            },
            "demirci_jit_synthesis": {
                "specialist_model": "kam:coder",
                "ast_verified": ast_validation["valid"],
                "violations": ast_validation["violations"],
                "cpp_module_preview": cpp_code.splitlines()[0],
            },
        }
