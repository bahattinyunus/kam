#include "safety_shield.hpp"
#include <algorithm>
#include <cmath>

namespace kam::core {

ShieldProjectionResult NeuroSymbolicCbfShield::verifyAndProject(const FlightEnvelopeState& proposed) noexcept {
    ShieldProjectionResult res;
    res.safe_state = proposed;

    if (proposed.altitude_agl_m < kMinAltitudeAglM) {
        res.safe_state.altitude_agl_m = kMinAltitudeAglM;
        res.intervention_triggered = true;
        res.violations.push_back("CBF_ALTITUDE_FLOOR_VIOLATION");
    }

    if (proposed.airspeed_mps < kStallAirspeedMps) {
        res.safe_state.airspeed_mps = kStallAirspeedMps;
        res.intervention_triggered = true;
        res.violations.push_back("CBF_STALL_SPEED_VIOLATION");
    }

    if (std::abs(proposed.bank_angle_deg) > kMaxBankAngleDeg) {
        res.safe_state.bank_angle_deg = (proposed.bank_angle_deg > 0.0) ? kMaxBankAngleDeg : -kMaxBankAngleDeg;
        res.intervention_triggered = true;
        res.violations.push_back("CBF_BANK_ANGLE_VIOLATION");
    }

    if (proposed.battery_pct < kRtlBatteryPct) {
        res.rtl_override = true;
        res.intervention_triggered = true;
        res.safe_state.bank_angle_deg = 0.0;
        res.safe_state.airspeed_mps = std::max(res.safe_state.airspeed_mps, 32.0);
        res.violations.push_back("SYMBOLIC_RTL_BATTERY_RESERVE");
    }

    const double h_alt = (res.safe_state.altitude_agl_m - kMinAltitudeAglM) / 100.0;
    const double h_spd = (res.safe_state.airspeed_mps - kStallAirspeedMps) / 50.0;
    const double h_bnk = (kMaxBankAngleDeg - std::abs(res.safe_state.bank_angle_deg)) / kMaxBankAngleDeg;
    res.cbf_margin_h = std::max(0.0, std::min({h_alt, h_spd, h_bnk}));

    return res;
}

std::array<double, 6> NeuroSymbolicCbfShield::allocateFaultTolerantActuators(
    const std::array<double, 3>& desired_moments_lmn,
    int jammed_actuator_index,
    double jammed_angle_rad
) noexcept {
    constexpr double B[3][6] = {
        { 0.85, -0.85,  0.30, -0.30,  0.05,  0.45},
        { 0.65,  0.65,  0.55,  0.55,  0.80,  0.10},
        {-0.15,  0.15,  0.75, -0.75,  0.85,  0.60}
    };

    std::array<double, 3> v_comp = desired_moments_lmn;
    if (jammed_actuator_index >= 0 && jammed_actuator_index < 6) {
        for (int r = 0; r < 3; ++r) {
            v_comp[r] -= B[r][jammed_actuator_index] * jammed_angle_rad;
        }
    }

    std::array<double, 6> cmd{};
    for (int k = 0; k < 6; ++k) {
        if (k == jammed_actuator_index) {
            cmd[k] = jammed_angle_rad;
        } else {
            cmd[k] = 0.35 * (B[0][k] * v_comp[0] + B[1][k] * v_comp[1] + B[2][k] * v_comp[2]);
        }
    }
    return cmd;
}

} // namespace kam::core
