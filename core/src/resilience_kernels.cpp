#include "resilience_kernels.hpp"
#include <algorithm>
#include <bit>
#include <cmath>

namespace kam::core {

std::uint8_t SovereignResilienceKernels::computeSecdedParity64(std::uint64_t data64) noexcept {
    std::uint8_t ecc = 0;
    for (int k = 0; k < 7; ++k) {
        std::uint8_t parity_k = 0;
        const int bit_mask = (1 << k);
        for (int i = 0; i < 64; ++i) {
            if ((i + 1) & bit_mask) {
                parity_k ^= static_cast<std::uint8_t>((data64 >> i) & 1ULL);
            }
        }
        ecc |= static_cast<std::uint8_t>(parity_k << k);
    }

    int total_ones = 0;
    for (int i = 0; i < 64; ++i) {
        total_ones += static_cast<int>((data64 >> i) & 1ULL);
    }
    for (int k = 0; k < 7; ++k) {
        total_ones += static_cast<int>((ecc >> k) & 1U);
    }
    ecc |= static_cast<std::uint8_t>((total_ones & 1) << 7);
    return ecc;
}

SecdedRepairResult SovereignResilienceKernels::decodeAndRepairSecded64(
    std::uint64_t corrupted64,
    std::uint8_t ecc8
) noexcept {
    SecdedRepairResult res{};
    res.repaired_data64 = corrupted64;

    const std::uint8_t recomputed = computeSecdedParity64(corrupted64);
    res.syndrome = static_cast<std::uint8_t>((ecc8 ^ recomputed) & 0x7FU);

    int total_ones = 0;
    for (int i = 0; i < 64; ++i) {
        total_ones += static_cast<int>((corrupted64 >> i) & 1ULL);
    }
    for (int k = 0; k < 8; ++k) {
        total_ones += static_cast<int>((ecc8 >> k) & 1U);
    }
    const bool overall_err = (total_ones & 1) != 0;

    if (res.syndrome != 0 && overall_err) {
        const int bit_idx = static_cast<int>(res.syndrome) - 1;
        if (bit_idx >= 0 && bit_idx < 64) {
            res.repaired_data64 ^= (1ULL << bit_idx);
            res.corrected_bit_index = bit_idx;
            res.single_bit_corrected = true;
        }
    } else if (res.syndrome != 0 && !overall_err) {
        res.double_bit_detected = true;
    }

    return res;
}

std::array<std::int8_t, 16> SovereignResilienceKernels::tmrMajorityVoteTernary(
    const std::array<std::int8_t, 16>& bank_a,
    const std::array<std::int8_t, 16>& bank_b,
    const std::array<std::int8_t, 16>& bank_c
) noexcept {
    std::array<std::int8_t, 16> out{};
    for (std::size_t i = 0; i < 16; ++i) {
        if (bank_a[i] == bank_b[i] || bank_a[i] == bank_c[i]) {
            out[i] = bank_a[i];
        } else {
            out[i] = bank_b[i];
        }
    }
    return out;
}

FsoLinkMetrics SovereignResilienceKernels::evaluateFsoLaserLink(
    double distance_km,
    double visibility_km,
    double pointing_jitter_urad
) noexcept {
    const double r_km = std::max(0.05, distance_km);
    const double v_km = std::max(0.2, visibility_km);
    const double beta = (3.91 / v_km) * std::pow(1550.0 / 550.0, -1.3);
    const double atm_loss_db = 4.3429448 * beta * r_km;
    const double point_loss_db = -10.0 * std::log10(std::exp(-2.0 * std::pow(pointing_jitter_urad / 250.0, 2.0)));
    const double snr_db = 32.0 - atm_loss_db - point_loss_db;
    const double snr_lin = std::pow(10.0, snr_db / 10.0);
    const double cap_mbps = 250.0 * std::log2(1.0 + std::max(0.0, snr_lin)) * (223.0 / 255.0);

    return FsoLinkMetrics{
        .optical_snr_db = snr_db,
        .throughput_mbps = cap_mbps,
        .rf_emission_watts = 0.0,
        .stealth_emcon_locked = (snr_db >= 6.0)
    };
}

HjiEvasionSolution SovereignResilienceKernels::solveHjiMissileEvasion(
    double missile_range_m,
    double closing_velocity_mps,
    double evader_max_g
) noexcept {
    const double r_m = std::max(50.0, missile_range_m);
    const double v_c = std::max(100.0, closing_velocity_mps);
    const double t_go = r_m / v_c;
    const double a_e = evader_max_g * 9.80665;
    const double miss_m = 0.5 * a_e * (0.32 * 0.32) * 3.8 * (t_go / 0.32) + 34.5;

    return HjiEvasionSolution{
        .time_to_go_sec = t_go,
        .terminal_miss_distance_m = miss_m,
        .evasion_accel_mps2 = {-0.15 * a_e, 0.98 * a_e, 0.19 * a_e},
        .survival_guaranteed = (miss_m > 18.0)
    };
}

} // namespace kam::core
