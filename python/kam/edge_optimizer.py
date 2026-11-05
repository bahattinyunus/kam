import math
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .code_mutator import CodeMutator


@dataclass(frozen=True)
class EdgeHardwareBudget:
    ram_mb: int
    tdp_watts: float
    npu_temp_c: float = 48.0
    has_gpu_or_npu: bool = True


@dataclass(frozen=True)
class EdgeDeploymentPlan:
    model_id: str
    quantization: str
    kv_cache_bits: int
    context_length: int
    speculative_draft_model: Optional[str]
    estimated_vram_mb: int
    estimated_tokens_per_sec: float
    active_params_billions: float


class EdgeModelOptimizer:
    """
    Kısıtlı uç donanım zarfına (RAM/VRAM, TDP, Sıcaklık) göre en yüksek bilişsel
    başarım sağlayan model, kuantizasyon, KV-önbellek bit derinliği ve spekülatif
    çözümleme topolojisini seçen otonom planlayıcı ve GRPO ödül hesaplayıcısı.
    """

    @staticmethod
    def estimate_memory_footprint_mb(
        active_params_b: float,
        weight_bits: float,
        context_length: int,
        kv_cache_bits: int,
        hybrid_ssm_ratio: float = 0.75,
    ) -> int:
        """
        Model ağırlıkları + Hibrit Sıvı-SSM / GQA KV-önbellek bellek tüketimini (MB) hesaplar.
        hybrid_ssm_ratio: Katmanların ne kadarının O(1) bellekli Liquid-SSM olduğu.
        """
        weight_mb = (active_params_b * 1e9 * (weight_bits / 8.0)) / (1024 * 1024)
        # Sadece dikkat (attention) katmanları (1 - hybrid_ssm_ratio) KV-cache büyütür
        attention_fraction = max(0.1, 1.0 - hybrid_ssm_ratio)
        kv_mb = (context_length * active_params_b * 18.0 * (kv_cache_bits / 16.0) * attention_fraction) / 1024.0
        runtime_overhead_mb = 140.0
        return int(math.ceil(weight_mb + kv_mb + runtime_overhead_mb))

    @classmethod
    def plan_optimal_deployment(cls, budget: EdgeHardwareBudget) -> EdgeDeploymentPlan:
        """
        Verilen donanım bütçesine sığan en yüksek kapasiteli KAM model konfigürasyonunu döndürür.
        """
        # Termal koruma: NPU 85 C üstündeyse zorunlu düşük güç / INT4 KV-Cache modu
        thermal_throttling = budget.npu_temp_c >= 85.0

        # 1. Seviye-3: 6 GB+ VRAM ve <85 C -> kam:7b + kam:1.5b Spekülatif Çözümleme
        if budget.ram_mb >= 6144 and budget.tdp_watts >= 25.0 and not thermal_throttling:
            vram = cls.estimate_memory_footprint_mb(7.6, 4.5, 16384, 8, hybrid_ssm_ratio=0.5)
            return EdgeDeploymentPlan(
                model_id="kam:7b",
                quantization="Q4_K_M (imatrix)",
                kv_cache_bits=8,
                context_length=16384,
                speculative_draft_model="kam:1.5b",
                estimated_vram_mb=vram,
                estimated_tokens_per_sec=92.5 if budget.has_gpu_or_npu else 18.0,
                active_params_billions=7.6,
            )

        # 2. Seviye-2: 2.5 GB - 6 GB RAM/VRAM -> KAM-Edge-3B-MoE (0.75B aktif parametre)
        if budget.ram_mb >= 2560 and budget.tdp_watts >= 12.0:
            q_bits = 3.5 if thermal_throttling else 4.5
            kv_bits = 4 if thermal_throttling else 8
            ctx = 8192 if thermal_throttling else 16384
            vram = cls.estimate_memory_footprint_mb(3.2, q_bits, ctx, kv_bits, hybrid_ssm_ratio=0.75)
            return EdgeDeploymentPlan(
                model_id="kam:edge-3b-moe",
                quantization="IQ3_M (imatrix)" if thermal_throttling else "Q4_K_M (imatrix)",
                kv_cache_bits=kv_bits,
                context_length=ctx,
                speculative_draft_model=None,
                estimated_vram_mb=vram,
                estimated_tokens_per_sec=86.0 if budget.has_gpu_or_npu else 28.5,
                active_params_billions=0.75,
            )

        # 3. Seviye-1: 1 GB - 2.5 GB Dar Uç Donanım -> kam:1.5b (veya BitNet b1.58)
        vram = cls.estimate_memory_footprint_mb(1.5, 4.0, 4096, 4, hybrid_ssm_ratio=0.75)
        return EdgeDeploymentPlan(
            model_id="kam:1.5b",
            quantization="Q4_K_M / BitNet-b1.58",
            kv_cache_bits=4,
            context_length=4096,
            speculative_draft_model=None,
            estimated_vram_mb=vram,
            estimated_tokens_per_sec=64.0 if budget.has_gpu_or_npu else 38.0,
            active_params_billions=1.5,
        )

    @staticmethod
    def compute_grpo_reward(
        response_text: str,
        cpp_code: Optional[str] = None,
        free_energy: float = 0.08,
    ) -> Dict[str, Any]:
        """
        Kısıtlı modelin akıl yürütme ve C++20 kod sentezini değerlendiren
        deterministik Aktif Çıkarım GRPO ödül fonksiyonu.
        """
        # 1. Dil saflığı denetimi (Çince/Kiril karakter sızıntısı cezası)
        foreign_leak = any(0x4E00 <= ord(ch) <= 0x9FFF or 0x0400 <= ord(ch) <= 0x04FF for ch in response_text)
        lang_penalty = 1.0 if foreign_leak else 0.0

        # 2. AST ve derleyici sembol ödülü
        ast_reward = 1.0
        if cpp_code:
            ast_res = CodeMutator.validate_ast(cpp_code)
            ast_reward = 1.0 if ast_res["valid"] else 0.0

        # 3. Karl Friston Serbest Enerji minimizasyonu ödülü: exp(-F)
        fe_reward = math.exp(-max(0.0, free_energy))

        # 4. Token verimliliği (aşırı uzun dolgu metin cezası)
        word_count = len(response_text.split())
        brevity_bonus = 1.0 if 10 <= word_count <= 350 else 0.7

        total_reward = (0.35 * ast_reward) + (0.40 * fe_reward) + (0.25 * brevity_bonus) - (1.5 * lang_penalty)
        return {
            "total_reward": round(total_reward, 4),
            "ast_reward": ast_reward,
            "free_energy_reward": round(fe_reward, 4),
            "foreign_leak_detected": foreign_leak,
        }
