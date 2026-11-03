#pragma once

#include "free_energy_math.hpp"
#include <vector>
#include <string>

namespace kam::active_inference {

enum class MentalState {
    EQUILIBRIUM,      // Dengeli (%0 - %20 entropi)
    SURPRISED,        // Şaşırma / Değişim (%21 - %50 entropi)
    PERTURBATION,     // Sapma (%51 - %79 entropi)
    CRITICAL_CHAOS    // Kaos Eşiği Aşıldı (>= %80 entropi)
};

struct InferenceAssessment {
    double free_energy;
    double entropy_percentage; // 0.03 = %3, 0.89 = %89
    MentalState state;
    bool requires_intervention;
    std::string diagnostics_tr;
};

class ActiveInferenceEngine {
public:
    ActiveInferenceEngine();

    // Duyusal gözlemleri işle ve içsel inançları güncelle
    InferenceAssessment updateSensoryInput(
        const std::vector<double>& observations,
        bool simulate_disruption = false
    );

    // İyileşme sonrası inançları sıfırla ve yeni topolojiye uyum sağla
    void resetToEquilibrium(double stabilized_entropy = 0.15);

    double getCurrentEntropy() const;
    MentalState getMentalState() const;

private:
    std::vector<double> prior_beliefs_;
    std::vector<double> current_observations_;
    std::vector<double> likelihood_matrix_;
    double current_entropy_ = 0.03;
    MentalState state_ = MentalState::EQUILIBRIUM;
};

} // namespace kam::active_inference
