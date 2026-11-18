#pragma once

#include <array>
#include <cstdint>

namespace kam::core {

struct SecdedRepairResult {
    std::uint64_t repaired_data64{0};
    std::uint8_t syndrome{0};
    int corrected_bit_index{-1};
    bool single_bit_corrected{false};
    bool double_bit_detected{false};
};

struct FsoLinkMetrics {
    double optical_snr_db{0.0};
    double throughput_mbps{0.0};
    double rf_emission_watts{0.0};
    bool stealth_emcon_locked{true};
};

struct HjiEvasionSolution {
    double time_to_go_sec{0.0};
    double terminal_miss_distance_m{0.0};
    std::array<double, 3> evasion_accel_mps2{};
    bool survival_guaranteed{false};
};

class SovereignResilienceKernels {
public:
    // 1. Hamming(72,64) SECDED (Single Error Correction, Double Error Detection)
    static std::uint8_t computeSecdedParity64(std::uint64_t data64) noexcept;
    static SecdedRepairResult decodeAndRepairSecded64(std::uint64_t corrupted64, std::uint8_t ecc8) noexcept;

    // 2. Üçlü Modüler Yedeklilik (TMR) BitNet b1.58 Ağırlık Çoğunluk Oylaması
    static std::array<std::int8_t, 16> tmrMajorityVoteTernary(
        const std::array<std::int8_t, 16>& bank_a,
        const std::array<std::int8_t, 16>& bank_b,
        const std::array<std::int8_t, 16>& bank_c
    ) noexcept;

    // 3. EMCON-Zero 1550nm FSO Lazer Bağlantı Bütçesi Hesaplayıcı
    static FsoLinkMetrics evaluateFsoLaserLink(
        double distance_km,
        double visibility_km,
        double pointing_jitter_urad
    ) noexcept;

    // 4. Hamilton-Jacobi-Isaacs (HJI) Diferansiyel Takip-Kaçma Çözücüsü
    static HjiEvasionSolution solveHjiMissileEvasion(
        double missile_range_m,
        double closing_velocity_mps,
        double evader_max_g
    ) noexcept;
};

} // namespace kam::core
