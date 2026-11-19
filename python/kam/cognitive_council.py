import re
from typing import Dict, Any, List, Optional, Tuple
from .active_inference import ActiveInferenceEngine
from .code_mutator import CodeMutator
from .lyapunov_controller import LyapunovCognitiveController


class CognitiveCouncilRouter:
    """
    KAM 5-Modelli Bilişsel Kurul (Sovereign Council) ve Otonom Uzman Yönlendiricisi.
    Yerel Ollama/GGUF ailesindeki 5 uzman modeli (kam:7b, kam:r1, kam:coder, kam:r1-nano, kam:1.5b)
    görev tipine, donanım RAM/TDP zarfına ve NPU sıcaklığına göre otonom orkestre eder:
      - kam:coder   -> C++20 Bellek-İçi JIT, Linux eBPF, CUDA/SIMD, Türkçe/İngilizce kodlama ve CodeAct/Bilgisayar-Kullanımı
      - kam:r1      -> Derin matematiksel ispat, Karl Friston VFE/EFE, taktik/EW planlama ve çok adımlı CoT (<think>)
      - kam:r1-nano -> Kısıtlı donanımda (1-2 GB RAM / >85°C termal stres) hızlı CoT ve taktik muhakeme
      - kam:1.5b    -> Milisaniye altı taktik uç karar ve kam:7b için öz-spekülatif taslak üretimi
      - kam:7b      -> Duru Türkçe belâgat, Dede Korkut hikmeti ve başmühendislik sentezi
    """

    # Geriye dönük uyumluluk için korunur (sözcük sınırı tabanlı regex ile desteklenir)
    CODE_KEYWORDS = (
        "c++", "cpp", "jit", "kod", "code", "ebpf", "kprobe", "memfd", "dlopen",
        "arena", "simd", "cuda", "ast", "entrypoint", "struct", "sınıf", "class",
        "python", "rust", "javascript", "typescript", "sql", "debug", "refactor",
    )
    REASONING_KEYWORDS = (
        "ispat", "kanıt", "prove", "proof", "matematik", "math", "denklem", "equation",
        "friston", "lyapunov", "formül", "formula", "hesapla", "calculate", "solve",
        "analiz", "analyze", "mahalanobis", "kalman", "entropi", "entropy", "serbest enerji",
        "integral", "türev", "derivative", "olasılık", "probability", "teorem", "theorem",
    )

    _TR_MAP = str.maketrans({
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s",
        "Ğ": "g", "ğ": "g",
        "Ü": "u", "ü": "u",
        "Ö": "o", "ö": "o",
        "Ç": "c", "ç": "c",
        "Â": "a", "â": "a",
        "Î": "i", "î": "i",
        "Û": "u", "û": "u",
    })

    # Kodlama, hata ayıklama, sistem mimarisi ve yazılım mühendisliği kalıpları (TR + EN)
    _CODE_PATTERNS: Tuple[Tuple[re.Pattern, float], ...] = tuple(
        (re.compile(pat), weight)
        for pat, weight in [
            # Programlama dilleri & ekosistemler
            (r"\b(?:cpp20|cpp|python|rust|javascript|typescript|golang|csharp|kotlin|swift|bash|powershell)\b", 2.0),
            (r"\b(?:ebpf|kprobe|tracepoint|memfd|dlopen|cuda|simd|wasm|tokio|pytorch|numpy|fastapi|django|flask|react|nextjs)\b", 2.0),
            (r"\b(?:jit|entrypoint|struct|mutex|async|await|regex|dockerfile|graphql|sql)\b", 1.8),
            # Kesin sözcük sınırı: "ast" -> "Kastamonu/hastane/fast/last/master" ile ASLA eşleşmez
            (r"\bast\b", 2.0),
            (r"\b(?:arena|lock-free|spsc|ringbuffer)\b", 1.8),
            # Türkçe & İngilizce kodlama eylemleri ve kavramları
            (r"\bkod(?:u|un|unu|la\w*|lar\w*)?\b", 1.8),
            (r"\b(?:code|coding|codebase|codeact)\b", 1.8),
            (r"\b(?:programla\w*|fonksiyon\w*|function\w*|algoritma\w*|algorithm\w*|betik\w*|script\w*)\b", 1.7),
            (r"\b(?:refactor\w*|debug\w*|hata ayikla\w*|derle\w*|compile\w*|birim test\w*|unit test\w*)\b", 2.0),
            (r"\b(?:typeerror|syntaxerror|valueerror|keyerror|attributeerror|traceback|segfault|stacktrace)\b", 2.2),
            (r"\b(?:web scraper|quicksort|mergesort|binary search|linked list|api endpoint|git diff|git commit|pull request)\b", 2.0),
            (r"\b(?:class|sinif(?:i|in|lar\w*)?)\b", 1.3),
            (r"\b(?:html|css|json|yaml|xml)\b", 1.2),
            (r"```", 2.5),
            (r"\b(?:def |import |const |fn |#include|extern\s+\"c\")", 2.2),
        ]
    )

    # Bilgisayar kullanımı (Computer-Use / Host Automation) kalıpları (TR + EN)
    _COMPUTER_USE_PATTERNS: Tuple[Tuple[re.Pattern, float], ...] = tuple(
        (re.compile(pat), weight)
        for pat, weight in [
            (r"\b(?:ekran goruntusu\w*|screenshot\w*)\b", 2.2),
            (r"\b(?:masaustu\w*|desktop)\b", 1.6),
            (r"\b(?:dosya\w*|klasor\w*)\s+(?:olustur\w*|yaz\w*|sil\w*|oku\w*|listele\w*|tasi\w*|kopyala\w*|ara\w*|ac\w*|ziple\w*)", 2.2),
            (r"\b(?:create|write|read|delete|list|open|search|find|move|copy)\s+(?:a\s+|the\s+|my\s+)?(?:file|files|folder|directory)\b", 2.2),
            (r"\b(?:chrome|firefox|edge|notepad|tarayici\w*|browser)\b", 1.7),
            (r"\b(?:uygulama\w*|program\w*|pencere\w*)\s+(?:ac\w*|kapat\w*|baslat\w*|odakla\w*)", 2.0),
            (r"\b(?:open|launch|close|kill|focus)\s+(?:chrome|firefox|notepad|terminal|app|browser|window|vscode)\b", 2.2),
            (r"\b(?:fare\w*|mouse|tikla\w*|click|klavye\w*|hotkey|kisayol\w*|clipboard|pano\w*)\b", 1.7),
            (r"\b(?:ses(?:i|ini)?\s+(?:ac|kapat|kis|artir|yap)|volume|parlaklik\w*|brightness)\b", 1.8),
            (r"\b(?:surec\w*\s+(?:listele\w*|sonlandir\w*|kapat\w*|goster\w*)|running process\w*)\b", 2.0),
            (r"\b(?:ram kullanimi\w*|ram usage|cpu kullanimi\w*|cpu usage|disk alani\w*|disk usage|batarya\w*|battery)\b", 1.8),
            (r"\b(?:komut calistir\w*|run shell|shell command|sistem telemetri\w*|system telemetry)\b", 2.2),
            (r"\b(?:web(?:'?de|'?te)?\s+ara\w*|search\s+(?:the\s+)?web|search\s+for)\b", 1.8),
        ]
    )

    # Matematik, mantık, bilimsel çıkarım ve derin muhakeme kalıpları (TR + EN)
    _REASONING_PATTERNS: Tuple[Tuple[re.Pattern, float], ...] = tuple(
        (re.compile(pat), weight)
        for pat, weight in [
            (r"\b(?:ispat\w*|kanit\w*|prove|proof|teorem\w*|theorem)\b", 2.2),
            (r"\b(?:matematik\w*|math\w*|denklem\w*|equation\w*|formul\w*|formula\w*)\b", 2.0),
            (r"\b(?:integral\w*|turev\w*|derivative\w*|diferansiyel\w*|differential|matris\w*|matrix|eigenvalue\w*|ozdeger\w*)\b", 2.2),
            (r"\b(?:olasilik\w*|probability|istatistik\w*|statistics|polinom\w*|polynomial|logaritma\w*|logarithm|trigonometri\w*)\b", 2.0),
            (r"\b(?:friston\w*|lyapunov\w*|mahalanobis\w*|kalman\w*|entropi\w*|entropy|serbest enerji|free energy)\b", 2.2),
            (r"\b(?:varyasyonel\w*|variational|bayes\w*|shannon\w*|markov\w*|optimizasyon\w*|optimization)\b", 1.9),
            (r"\b(?:hesapla\w*|calculate|compute|solve|adim adim|step by step)\b", 1.7),
            (r"\b(?:irrational|irrasyonel\w*|asal sayi\w*|prime number\w*|ucgen\w*|geometri\w*)\b", 1.8),
            (r"\b(?:mantik\w*|logic\w*|analiz\w*|analyze|analysis|karsilastir\w*|compare)\b", 1.4),
            (r"\b(?:x\^2|sqrt\(|sin\(|cos\(|tan\(|log\(|dx\b|dy\b)", 2.0),
        ]
    )

    # Taktik, elektronik harp (EW), otonom filo ve savunma görev kalıpları (TR + EN)
    _TACTICAL_PATTERNS: Tuple[Tuple[re.Pattern, float], ...] = tuple(
        (re.compile(pat), weight)
        for pat, weight in [
            (r"\b(?:taktik\w*|tactical)\b", 2.0),
            (r"\b(?:s-?400|radar\w*|elektronik harp|electronic warfare|\bew\b|karistirma\w*|jamming|spoofing)\b", 2.2),
            (r"\b(?:fhss|sdr|drfm|pdw|hji|cbf|bft|pqc|trn)\b", 2.0),
            (r"\b(?:siha\w*|iha\w*|uav\b|drone\w*|swarm\b|suru\w*\s+(?:lider|konsensus|mesh|rota|iha|siha))\b", 2.0),
            (r"\b(?:rota planla\w*|route plan\w*|stealth|kacinma manevra\w*|evasion|fuze\w*|missile\w*)\b", 2.2),
            (r"\b(?:taarruz\w*|sektor-?\d+|tehdit\w*|threat\w*|gps spoofing|dead reckoning|filo orkestrasyon\w*)\b", 2.0),
        ]
    )

    def __init__(self):
        self.inference = ActiveInferenceEngine()
        self.lyapunov = LyapunovCognitiveController()

    @classmethod
    def _normalize_prompt(cls, prompt: str) -> str:
        if not prompt or not isinstance(prompt, str):
            return ""
        text = prompt.translate(cls._TR_MAP).lower().replace("\u0307", "")
        text = text.replace("c++20", "cpp20").replace("c++", "cpp").replace("c#", "csharp")
        return text

    @classmethod
    def _score_patterns(cls, text: str, patterns: Tuple[Tuple[re.Pattern, float], ...]) -> float:
        score = 0.0
        for regex, weight in patterns:
            if regex.search(text):
                score += weight
        return score

    @classmethod
    def select_specialist_model(
        cls,
        prompt: str,
        ram_mb: int = 8192,
        npu_temp_c: float = 48.0,
    ) -> Dict[str, Any]:
        norm = cls._normalize_prompt(prompt)
        thermal_throttled = npu_temp_c >= 85.0 or ram_mb <= 2048

        code_score = cls._score_patterns(norm, cls._CODE_PATTERNS)
        computer_score = cls._score_patterns(norm, cls._COMPUTER_USE_PATTERNS)
        reasoning_score = cls._score_patterns(norm, cls._REASONING_PATTERNS)
        tactical_score = cls._score_patterns(norm, cls._TACTICAL_PATTERNS)

        # 1. Yazılım, C++20 JIT, eBPF, hata ayıklama ve çok dilli kod sentezi
        if code_score > 0.0 and code_score >= reasoning_score and code_score >= tactical_score:
            return {
                "selected_model": "kam:coder",
                "role": "Demirci (C++20 JIT, eBPF & Çok Dilli Kod Uzmanı)",
                "reason": "İstemde kod sentezi, hata ayıklama veya sistem programlama tespit edildi.",
                "category": "coding",
                "thermal_throttled": thermal_throttled,
            }

        # 2. Bilgisayar kullanımı (Computer-Use / CodeAct / Host Otomasyonu)
        if computer_score > 0.0 and computer_score >= reasoning_score and computer_score >= tactical_score:
            if thermal_throttled:
                return {
                    "selected_model": "kam:1.5b",
                    "role": "Uç Gözcü (1.5B Hızlı Bilgisayar-Kullanımı & Uç Zihin)",
                    "reason": "Kısıtlı bellek/termal zarf altında hızlı bilgisayar-kullanımı yürütmesi seçildi.",
                    "category": "computer_use",
                    "thermal_throttled": thermal_throttled,
                }
            return {
                "selected_model": "kam:coder",
                "role": "Demirci (CodeAct & Otonom Bilgisayar-Kullanımı Uzmanı)",
                "reason": "İstemde doğrudan bilgisayar/dosya/uygulama otomasyonu (CodeAct) tespit edildi.",
                "category": "computer_use",
                "thermal_throttled": thermal_throttled,
            }

        # 3. Taktik, EW, otonom rota ve sürü görev muhakemesi
        if tactical_score > 0.0 and tactical_score >= reasoning_score:
            if thermal_throttled:
                return {
                    "selected_model": "kam:r1-nano",
                    "role": "Taktik Bilge (1.5B CoT Taktik & EW Muhakeme)",
                    "reason": "Kısıtlı bellek/termal zarf altında taktik/EW muhakemesi seçildi.",
                    "category": "tactical",
                    "thermal_throttled": thermal_throttled,
                }
            return {
                "selected_model": "kam:r1",
                "role": "Baş Bilge (7B DeepSeek-R1 Taktik, EW & Görev Muhakemesi)",
                "reason": "Taktik rota, elektronik harp veya otonom görev planlaması tespit edildi.",
                "category": "tactical",
                "thermal_throttled": thermal_throttled,
            }

        # 4. Derin matematiksel ispat, Friston/Lyapunov ve çok adımlı akıl yürütme
        if reasoning_score > 0.0:
            if thermal_throttled:
                return {
                    "selected_model": "kam:r1-nano",
                    "role": "Taktik Bilge (1.5B CoT Zincirleme Akıl Yürütme)",
                    "reason": "Kısıtlı bellek/termal zarf altında derin CoT muhakemesi seçildi.",
                    "category": "reasoning",
                    "thermal_throttled": thermal_throttled,
                }
            return {
                "selected_model": "kam:r1",
                "role": "Baş Bilge (7B DeepSeek-R1 CoT Akıl Yürütme)",
                "reason": "Matematiksel/sibernetik derin muhakeme tespit edildi.",
                "category": "reasoning",
                "thermal_throttled": thermal_throttled,
            }

        # 5. Kısıtlı donanım / termal stres altında hızlı uç model
        if thermal_throttled:
            return {
                "selected_model": "kam:1.5b",
                "role": "Uç Gözcü (1.5B Hızlı Mikro-Uç Zihin)",
                "reason": "Düşük bellek/yüksek sıcaklık zarfı nedeniyle hızlı uç model seçildi.",
                "category": "edge_tactical",
                "thermal_throttled": thermal_throttled,
            }

        # 6. Varsayılan: Duru Türkçe belâgat, Dede Korkut hikmeti ve genel komuta
        return {
            "selected_model": "kam:7b",
            "role": "Ulu Kam (7B Duru Türkçe Hikmet ve Komuta Zihni)",
            "reason": "Genel komuta, hikmet ve mimari sentez görevi.",
            "category": "general",
            "thermal_throttled": thermal_throttled,
        }

    @classmethod
    def explain_routing_matrix(cls) -> Dict[str, Any]:
        """
        5-Modelli Egemen Bilişsel Kurul filosu için yapılandırılmış yetenek,
        eşik ve yönlendirme telemetrisini döndürür.
        """
        specialists = [
            {
                "model_id": "kam:coder",
                "codename": "Demirci",
                "role": "C++20 JIT, eBPF, Çok Dilli Kod & CodeAct Bilgisayar-Kullanımı Uzmanı",
                "categories": ["coding", "computer_use"],
                "min_ram_mb": 4096,
                "thermal_fallback": "kam:1.5b",
                "strengths": [
                    "C++20 / eBPF / CUDA / SIMD / AST kod sentezi",
                    "Python, Rust, JS/TS, SQL hata ayıklama ve yeniden düzenleme",
                    "Otonom CodeAct bilgisayar, dosya ve uygulama otomasyonu",
                ],
                "pattern_count": len(cls._CODE_PATTERNS) + len(cls._COMPUTER_USE_PATTERNS),
            },
            {
                "model_id": "kam:r1",
                "codename": "Baş Bilge",
                "role": "DeepSeek-R1 7B Derin Matematiksel İspat, Taktik & EW Muhakeme",
                "categories": ["reasoning", "tactical"],
                "min_ram_mb": 4096,
                "thermal_fallback": "kam:r1-nano",
                "strengths": [
                    "Karl Friston VFE/EFE ve Lyapunov kararlılık ispatları",
                    "Çok adımlı (<think>) matematik, olasılık ve türev/integral çözümü",
                    "3D taktik rota, elektronik harp (EW) ve İHA sürüsü görev planlama",
                ],
                "pattern_count": len(cls._REASONING_PATTERNS) + len(cls._TACTICAL_PATTERNS),
            },
            {
                "model_id": "kam:r1-nano",
                "codename": "Taktik Bilge",
                "role": "1.5B Kısıtlı Bellek/Termal Zarf CoT & Taktik Muhakeme",
                "categories": ["reasoning", "tactical"],
                "min_ram_mb": 1024,
                "thermal_fallback": "kam:1.5b",
                "strengths": [
                    "<=2048 MB RAM veya >=85°C NPU sıcaklığında zincirleme akıl yürütme",
                    "Düşük gecikmeli taktik ve matematiksel karar desteği",
                ],
                "pattern_count": len(cls._REASONING_PATTERNS) + len(cls._TACTICAL_PATTERNS),
            },
            {
                "model_id": "kam:1.5b",
                "codename": "Uç Gözcü",
                "role": "1.5B Milisaniye Altı Taktik Uç Karar & Spekülatif Taslak",
                "categories": ["edge_tactical", "computer_use"],
                "min_ram_mb": 1024,
                "thermal_fallback": None,
                "strengths": [
                    "Termal/RAM kısıtında kesintisiz uç komuta ve bilgisayar-kullanımı",
                    "kam:7b için öz-spekülatif (self-speculative) taslak token üretimi",
                ],
                "pattern_count": len(cls._COMPUTER_USE_PATTERNS),
            },
            {
                "model_id": "kam:7b",
                "codename": "Ulu Kam",
                "role": "7B Duru Türkçe Hikmet, Belâgat ve Başmühendislik Komuta Zihni",
                "categories": ["general"],
                "min_ram_mb": 4096,
                "thermal_fallback": "kam:1.5b",
                "strengths": [
                    "Dede Korkut hikmeti, Kutadgu Bilig töresi ve duru Türkçe anlatım",
                    "Genel komuta, mimari sentez ve yüksek bağlamlı sohbet",
                ],
                "pattern_count": 0,
            },
        ]

        category_routes = {
            "coding": {
                "normal_model": "kam:coder",
                "throttled_model": "kam:coder",
                "pattern_count": len(cls._CODE_PATTERNS),
            },
            "computer_use": {
                "normal_model": "kam:coder",
                "throttled_model": "kam:1.5b",
                "pattern_count": len(cls._COMPUTER_USE_PATTERNS),
            },
            "tactical": {
                "normal_model": "kam:r1",
                "throttled_model": "kam:r1-nano",
                "pattern_count": len(cls._TACTICAL_PATTERNS),
            },
            "reasoning": {
                "normal_model": "kam:r1",
                "throttled_model": "kam:r1-nano",
                "pattern_count": len(cls._REASONING_PATTERNS),
            },
            "edge_tactical": {
                "normal_model": "kam:7b",
                "throttled_model": "kam:1.5b",
                "pattern_count": 0,
            },
            "general": {
                "normal_model": "kam:7b",
                "throttled_model": "kam:1.5b",
                "pattern_count": 0,
            },
        }

        return {
            "council_name": "KAM-Sovereign-Cognitive-Council",
            "total_specialists": len(specialists),
            "thermal_throttle_threshold_c": 85.0,
            "low_ram_threshold_mb": 2048,
            "routing_priority": [
                "coding",
                "computer_use",
                "tactical",
                "reasoning",
                "edge_tactical",
                "general",
            ],
            "specialists": specialists,
            "category_routes": category_routes,
            "supported_crisis_hints": [
                "SDR", "THERMAL", "DRFM", "EW", "CAN", "GNSS",
                "BFT", "SWARM", "CBF", "TRN", "ACTUATOR", "FSO",
                "RADIATION", "HJI",
            ],
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
        series = telemetry_series if telemetry_series else [58.0, 66.0, 75.5, 83.0]
        errs = state_error if state_error else [0.12, -0.08, 0.15, 0.04, -0.03, 0.05]

        # 1. Bilge: Beklenen Serbest Enerji (EFE) Politikası
        self.inference.trigger_anomaly()
        efe_decision = self.inference.select_optimal_policy(crisis_hint=crisis_hint)
        fe_val = self.inference.compute_free_energy()

        # 2. Gözcü: Lyapunov Asimptotik Kararlılık ve Faz Uzayı TTA Tahmini
        clf_report = self.lyapunov.evaluate_stability_step(errs, fe_val)
        tta_report = self.lyapunov.forecast_time_to_anomaly(series, critical_threshold=85.0, sample_dt_sec=0.5)

        # 3. Demirci: C++20 JIT Kod Sentezi ve AST Denetimi
        hint_up = (crisis_hint or "SDR").upper()
        if "THERMAL" in hint_up:
            cpp_code = CodeMutator.generate_thermal_fallback()
        elif "DRFM" in hint_up:
            cpp_code = CodeMutator.generate_ew_drfm_fallback()
        elif "EW" in hint_up or "JAM" in hint_up:
            cpp_code = CodeMutator.generate_ew_fhss_fallback()
        elif "CAN" in hint_up:
            cpp_code = CodeMutator.generate_can_firewall_fallback()
        elif "GNSS" in hint_up or "GPS" in hint_up:
            cpp_code = CodeMutator.generate_gnss_spoof_fallback()
        elif "BFT" in hint_up or "PQC" in hint_up or "BYZANTINE" in hint_up:
            cpp_code = CodeMutator.generate_byzantine_pqc_fallback()
        elif "SWARM" in hint_up:
            cpp_code = CodeMutator.generate_swarm_handover_fallback()
        elif "CBF" in hint_up or "SHIELD" in hint_up:
            cpp_code = CodeMutator.generate_cbf_safety_shield_fallback()
        elif "TRN" in hint_up or "TERRAIN" in hint_up:
            cpp_code = CodeMutator.generate_trn_terrain_lock_fallback()
        elif "ACTUATOR" in hint_up:
            cpp_code = CodeMutator.generate_actuator_reconfig_fallback()
        elif "FSO" in hint_up or "LASER" in hint_up:
            cpp_code = CodeMutator.generate_fso_laser_mesh_fallback()
        elif "RADIATION" in hint_up or "ECC" in hint_up or "TMR" in hint_up:
            cpp_code = CodeMutator.generate_radiation_tmr_scrubber_fallback()
        elif "HJI" in hint_up or "MISSILE" in hint_up or "EVASION" in hint_up:
            cpp_code = CodeMutator.generate_hji_missile_evasion_fallback()
        else:
            cpp_code = CodeMutator.generate_sdr_fallback()

        ast_validation = CodeMutator.validate_ast(cpp_code)
        self.inference.reset_equilibrium(0.14)

        preview_lines = cpp_code.splitlines() if cpp_code else [""]
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
                "cpp_module_preview": preview_lines[0],
            },
        }
