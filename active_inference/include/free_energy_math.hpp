#pragma once

#include <vector>
#include <cmath>

namespace kam::active_inference {

class FreeEnergyMath {
public:
    // Shannon Entropisi: H(X) = -sum(p_i * log2(p_i))
    static double computeShannonEntropy(const std::vector<double>& probabilities);

    // Kullback-Leibler (KL) Iraksaması: D_KL(Q || P) = sum(q_i * ln(q_i / p_i))
    static double computeKLDivergence(const std::vector<double>& q, const std::vector<double>& p);

    // Varyasyonel Serbest Enerji (Variational Free Energy):
    // F = D_KL(q(s) || p(s)) - E_q[ln p(o|s)]
    static double computeVariationalFreeEnergy(
        const std::vector<double>& prior_beliefs,
        const std::vector<double>& sensory_evidence,
        const std::vector<double>& likelihood
    );

    // Beklenen Serbest Enerji (Expected Free Energy - EFE):
    // G(pi) = -Epistemik_Deger(Bilgi_Kazanimi) - Pragmatik_Deger(Tercih_Edilen_Dirlik_Uyumu)
    static double computeExpectedFreeEnergy(
        const std::vector<double>& predicted_observations,
        const std::vector<double>& preferred_prior_beliefs,
        double epistemic_info_gain,
        double control_cost = 0.05
    );

    // Aday politikalar arasından en düşük G(pi) değerine sahip optimal politikanın indeksini seçer
    static size_t selectOptimalPolicyIndex(const std::vector<double>& policy_efe_values);

    // Entropiyi yüzdeye normalize et (0.0 - 1.0)
    static double normalizeChaosPercentage(double free_energy, double baseline_fe = 0.15);
};

} // namespace kam::active_inference
