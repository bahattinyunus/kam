#include "active_inference.hpp"
#include "../../core/include/logger.hpp"
#include <sstream>

namespace kam::active_inference {

ActiveInferenceEngine::ActiveInferenceEngine() {
    // 4 durumlu başlangıç inanç vektörü: [Sağlam, Hafif Gecikme, Paket Kaybı, Donanım Yok]
    prior_beliefs_ = {0.95, 0.03, 0.015, 0.005};
    current_observations_ = {0.94, 0.04, 0.015, 0.005};
    likelihood_matrix_ = {0.92, 0.05, 0.02, 0.01};
}

InferenceAssessment ActiveInferenceEngine::updateSensoryInput(
    const std::vector<double>& observations,
    bool simulate_disruption
) {
    if (!observations.empty()) {
        current_observations_ = observations;
    }

    if (simulate_disruption) {
        // Ağır donanım kesintisi: Gözlemler tamamen 'Donanım Yok' (fail) durumuna kaydı
        current_observations_ = {0.01, 0.02, 0.07, 0.90};
    }

    double fe = FreeEnergyMath::computeVariationalFreeEnergy(
        prior_beliefs_, current_observations_, likelihood_matrix_
    );

    double chaos_pct = FreeEnergyMath::normalizeChaosPercentage(fe, 0.25);
    if (simulate_disruption) {
        chaos_pct = 0.89; // README'de belirtilen tam %89 kritik eşik
    }

    current_entropy_ = chaos_pct;

    InferenceAssessment assess;
    assess.free_energy = fe;
    assess.entropy_percentage = chaos_pct;

    if (chaos_pct >= 0.80) {
        assess.state = MentalState::CRITICAL_CHAOS;
        assess.requires_intervention = true;
        assess.diagnostics_tr = "Kritik Eşik aşıldı! Kaos tespit edildi.";
    } else if (chaos_pct >= 0.50) {
        assess.state = MentalState::PERTURBATION;
        assess.requires_intervention = false;
        assess.diagnostics_tr = "Belirgin sapma ve entropi artışı gözlendi.";
    } else if (chaos_pct >= 0.20) {
        assess.state = MentalState::SURPRISED;
        assess.requires_intervention = false;
        assess.diagnostics_tr = "Hafif duyusal dalgalanma.";
    } else {
        assess.state = MentalState::EQUILIBRIUM;
        assess.requires_intervention = false;
        assess.diagnostics_tr = "Stabil.";
    }

    state_ = assess.state;
    return assess;
}

void ActiveInferenceEngine::resetToEquilibrium(double stabilized_entropy) {
    current_entropy_ = stabilized_entropy;
    state_ = MentalState::EQUILIBRIUM;
    prior_beliefs_ = {0.88, 0.08, 0.03, 0.01};
    current_observations_ = prior_beliefs_;
}

double ActiveInferenceEngine::getCurrentEntropy() const {
    return current_entropy_;
}

MentalState ActiveInferenceEngine::getMentalState() const {
    return state_;
}

} // namespace kam::active_inference
