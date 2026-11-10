#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace kam::core {

struct FlightEnvelopeState {
    double altitude_agl_m{120.0};
    double airspeed_mps{38.0};
    double bank_angle_deg{0.0};
    double battery_pct{85.0};
};

struct ShieldProjectionResult {
    FlightEnvelopeState safe_state;
    double cbf_margin_h{1.0};
    bool intervention_triggered{false};
    bool rtl_override{false};
    std::vector<std::string> violations;
};

class NeuroSymbolicCbfShield {
public:
    static constexpr double kMinAltitudeAglM = 30.0;
    static constexpr double kStallAirspeedMps = 22.0;
    static constexpr double kMaxBankAngleDeg = 55.0;
    static constexpr double kRtlBatteryPct = 18.0;

    // Kontrol Bariyer Fonksiyonu h(x) >= 0 kuadratik izdüşüm denetimi
    static ShieldProjectionResult verifyAndProject(const FlightEnvelopeState& proposed) noexcept;

    // Kinetik eyleyici sıkışması altında 3 eksenli moment telafisi
    static std::array<double, 6> allocateFaultTolerantActuators(
        const std::array<double, 3>& desired_moments_lmn,
        int jammed_actuator_index,
        double jammed_angle_rad
    ) noexcept;
};

} // namespace kam::core
