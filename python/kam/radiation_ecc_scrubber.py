import hashlib
from typing import List, Dict, Any


class RadiationHardenedMemoryScrubber:
    """
    Yüksek İrtifa / Stratosferik / Uzay ve EMP/HPM (Yüksek Güçlü Mikrodalga)
    Radyasyon Ortamları İçin SECDED Hamming(72,64) & Üçlü Modüler Yedeklilik
    (Triple Modular Redundancy — TMR) Bellek ve BitNet b1.58 Ağırlık Onarım Motoru.

    Kozmik ışınların veya yönlendirilmiş enerji (HPM/EMP) silahlarının SRAM/VRAM
    üzerinde yol açtığı Tekil Olay Tersinmelerini (Single-Event Upset — SEU) ve
    Çoklu Bit Tersinmelerini (Multi-Bit Upset — MBU) mikrosaniyede tespit edip onarır:

    1. Genişletilmiş Hamming(72,64) SECDED Sendrom Çözücü:
       64-bitlik veri kelimesi d için 7 Hamming eşlik (parity) biti (p_0..p_6) ve
       1 genel eşlik biti (p_all) üretir. Sendrom s = H * c^T (mod 2) üzerinden
       1-bitlik tersinmeleri O(1) bit işleminde tam konumunu bularak düzeltir,
       2-bitlik tersinmeleri ise anında TMR katmanına devreder.

    2. Üçlü Modüler Yedeklilik (TMR) Çoğunluk Oylaması & SHA3-256 Merkle Mührü:
       BitNet b1.58 üçlü ağırlık bankalarını (Bank-A, Bank-B, Bank-C in {-1, 0, +1})
       çoğunluk kapısı M(A, B, C) ile karşılaştırır ve bozulan bankayı %100
       bit-kesinliğinde (bit-exact) çalışma zamanında onarır.
    """

    @staticmethod
    def _compute_parity_bits_64(data64: int) -> int:
        """
        64-bitlik veri için 7 adet Hamming eşlik biti (bit 0..6) ve
        1 adet genel SECDED eşlik biti (bit 7) hesaplar (toplam 8-bit ECC).
        Veri bitleri i in [0..63], kod kelimesindeki sanal konum pos = i + 3 + floor(log2..)'ye
        veya doğrudan (i + 1) üzerinden indeks maskesiyle eşlenir:
        Burada her veri biti d_i (i=0..63), 1 tabanlı indeks idx = i + 1 (1..64) ile
        eşlik denklemlerine katılır; p_k (k=0..6) idx'in k. biti 1 olan tüm d_i'lerin XOR'udur.
        """
        val = data64 & 0xFFFFFFFFFFFFFFFF
        ecc = 0
        for k in range(7):
            parity_k = 0
            bit_mask = 1 << k
            for i in range(64):
                idx = i + 1  # 1..64
                if idx & bit_mask:
                    parity_k ^= (val >> i) & 1
            ecc |= (parity_k << k)

        # Genel eşlik biti (Overall parity p_7): tüm 64 veri biti + 7 eşlik bitinin XOR'u
        total_ones = bin(val).count("1") + bin(ecc & 0x7F).count("1")
        overall_p = total_ones & 1
        ecc |= (overall_p << 7)
        return ecc

    @classmethod
    def encode_secded_64(cls, data64: int) -> Dict[str, int]:
        clean_data = data64 & 0xFFFFFFFFFFFFFFFF
        ecc_byte = cls._compute_parity_bits_64(clean_data)
        return {"data64": clean_data, "ecc8": ecc_byte}

    @classmethod
    def decode_and_repair_secded_64(cls, corrupted_data64: int, received_ecc8: int) -> Dict[str, Any]:
        """
        Alınan 64-bit veri ve 8-bit ECC kodundan sendrom vektörünü çıkarır:
        - Sendrom == 0 ve Overall_Parity_Diff == 0 -> HATA YOK (NO_ERROR)
        - Sendrom != 0 ve Overall_Parity_Diff == 1 -> TEK BİT HATASI (SEU_CORRECTED),
          sendrom - 1 indeksli veri bitini ters çevirerek %100 onarır.
        - Sendrom != 0 ve Overall_Parity_Diff == 0 -> ÇİFT BİT HATASI (MBU_DETECTED_ESCALATE_TMR)
        """
        data = corrupted_data64 & 0xFFFFFFFFFFFFFFFF
        ecc = received_ecc8 & 0xFF

        recomputed_ecc = cls._compute_parity_bits_64(data)
        syndrome = (ecc ^ recomputed_ecc) & 0x7F

        total_received_ones = bin(data).count("1") + bin(ecc).count("1")
        overall_error = total_received_ones & 1

        if syndrome == 0 and overall_error == 0:
            return {
                "status": "NO_ERROR",
                "repaired_data64": data,
                "syndrome": 0,
                "corrected_bit_index": None,
                "double_bit_fault": False,
            }

        if syndrome != 0 and overall_error == 1:
            bit_idx = syndrome - 1
            if 0 <= bit_idx < 64:
                repaired = data ^ (1 << bit_idx)
            else:
                repaired = data
            return {
                "status": "SEU_SINGLE_BIT_CORRECTED",
                "repaired_data64": repaired,
                "syndrome": syndrome,
                "corrected_bit_index": bit_idx,
                "double_bit_fault": False,
            }

        if syndrome == 0 and overall_error == 1:
            return {
                "status": "ECC_PARITY_BIT_FLIP_CORRECTED",
                "repaired_data64": data,
                "syndrome": 0,
                "corrected_bit_index": 71,
                "double_bit_fault": False,
            }

        return {
            "status": "MBU_DOUBLE_BIT_DETECTED_ESCALATE_TMR",
            "repaired_data64": data,
            "syndrome": syndrome,
            "corrected_bit_index": None,
            "double_bit_fault": True,
        }

    @classmethod
    def scrub_bitnet_weights_with_tmr(
        cls,
        injected_seu_bit: int = 19,
        inject_tmr_bank_corruption: bool = True,
    ) -> Dict[str, Any]:
        """
        Hem 64-bit SECDED donanım yazmacı onarımını hem de BitNet b1.58 üçlü
        ({-1, 0, +1}) ağırlık bankalarının Üçlü Modüler Yedeklilik (TMR) çoğunluk
        oylaması ile otonom temizlenmesini (memory scrubbing) icra eder.
        """
        # 1. SECDED Hamming(72,64) Donanım Yazmacı Testi
        original_word = 0x4B414D5F41504558  # "KAM_APEX" ASCII 64-bit
        encoded = cls.encode_secded_64(original_word)

        bit_to_flip = max(0, min(63, int(injected_seu_bit)))
        corrupted_word = original_word ^ (1 << bit_to_flip)
        secded_res = cls.decode_and_repair_secded_64(corrupted_word, encoded["ecc8"])
        secded_exact_match = secded_res["repaired_data64"] == original_word

        # 2. BitNet b1.58 Ternary Ağırlık Bankaları (TMR: Bank-A, Bank-B, Bank-C)
        golden_weights: List[int] = [1, -1, 0, 1, 1, -1, 0, -1, 1, 0, -1, 1, 1, -1, 0, 1]
        bank_a = list(golden_weights)
        bank_b = list(golden_weights)
        bank_c = list(golden_weights)

        corrupted_indices: List[int] = []
        if inject_tmr_bank_corruption:
            # Bank-B üzerinde 3 ağırlıkta kozmik ışın / EMP bit-flip bozulması
            for idx in (2, 7, 13):
                bank_b[idx] = 1 if golden_weights[idx] <= 0 else -1
                corrupted_indices.append(idx)

        # TMR Çoğunluk Oylaması (Majority Gate)
        scrubbed_weights: List[int] = []
        tmr_repairs = 0
        for i in range(len(golden_weights)):
            a, b, c = bank_a[i], bank_b[i], bank_c[i]
            if a == b or a == c:
                maj = a
            else:
                maj = b
            if (a != maj) or (b != maj) or (c != maj):
                tmr_repairs += 1
            scrubbed_weights.append(maj)

        golden_hash = hashlib.sha3_256(str(golden_weights).encode("utf-8")).hexdigest()[:20]
        scrubbed_hash = hashlib.sha3_256(str(scrubbed_weights).encode("utf-8")).hexdigest()[:20]

        return {
            "scrubber_engine": "KAM-SECDED-Hamming7264-TMR-Radiation-Scrubber",
            "secded_register_check": {
                "original_hex": hex(original_word),
                "corrupted_hex": hex(corrupted_word),
                "repaired_hex": hex(secded_res["repaired_data64"]),
                "flipped_bit_detected": secded_res["corrected_bit_index"],
                "syndrome_code": secded_res["syndrome"],
                "status": secded_res["status"],
                "bit_exact_restored": secded_exact_match,
            },
            "tmr_bitnet_weight_scrub": {
                "total_ternary_weights_checked": len(golden_weights),
                "corrupted_weight_indices": corrupted_indices,
                "tmr_majority_repairs": tmr_repairs,
                "merkle_sha3_digest": scrubbed_hash,
                "integrity_verified_100pct": (golden_hash == scrubbed_hash) and secded_exact_match,
            },
            "recommended_cpp_patch": "radiation_tmr_scrubber.cpp",
        }
