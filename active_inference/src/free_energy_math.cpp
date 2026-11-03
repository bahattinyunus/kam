#include "free_energy_math.hpp"
#include <algorithm>
#include <numeric>

namespace kam::active_inference {

double FreeEnergyMath::computeShannonEntropy(const std::vector<double>& probabilities) {
    double entropy = 0.0;
    const double eps = 1e-12;
    for (double p : probabilities) {
        if (p > eps) {
            entropy -= p * std::log2(p);
        }
    }
    return entropy;
}

double FreeEnergyMath::computeKLDivergence(const std::vector<double>& q, const std::vector<double>& p) {
    double kl = 0.0;
    const double eps = 1e-12;
    size_t n = std::min(q.size(), p.size());
    for (size_t i = 0; i < n; ++i) {
        double qi = std::max(q[i], eps);
        double pi = std::max(p[i], eps);
        kl += qi * std::log(qi / pi);
    }
    return kl;
}

double FreeEnergyMath::computeVariationalFreeEnergy(
    const std::vector<double>& prior_beliefs,
    const std::vector<double>& sensory_evidence,
    const std::vector<double>& likelihood
) {
    double kl_complexity = computeKLDivergence(sensory_evidence, prior_beliefs);

    double accuracy = 0.0;
    const double eps = 1e-12;
    size_t n = std::min(sensory_evidence.size(), likelihood.size());
    for (size_t i = 0; i < n; ++i) {
        double lk = std::max(likelihood[i], eps);
        accuracy += sensory_evidence[i] * std::log(lk);
    }

    // F = Complexity - Accuracy
    double free_energy = kl_complexity - accuracy;
    return (free_energy < 0.0) ? 0.0 : free_energy;
}

double FreeEnergyMath::normalizeChaosPercentage(double free_energy, double baseline_fe) {
    // Serbest enerjiyi [0.0 - 1.0] aralığında entropi yüzdesine dönüştür
    double diff = free_energy / baseline_fe;
    double chaos = 1.0 - std::exp(-0.25 * diff);
    return std::clamp(chaos, 0.01, 1.0);
}

} // namespace kam::active_inference
