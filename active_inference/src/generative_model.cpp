#include "generative_model.hpp"
#include <limits>
#include <algorithm>
#include <numeric>

namespace kam::active_inference {

GenerativeModel::GenerativeModel(size_t num_states, size_t num_observations)
    : num_states_(num_states), num_observations_(num_observations) {
    initializeDefaultMatrices();
}

void GenerativeModel::initializeDefaultMatrices() {
    // 4 Durum: 0: Optimal, 1: Gecikmeli, 2: Paket Kaybı, 3: Donanım Koptu
    // 4 Gözlem: 0: Sağlam Sinyal, 1: Jitter, 2: Bozuk Paket, 3: Tam Kesinti

    // A Matrisi (Likelihood P(o|s)) - Boyut: 4x4
    A_ = {
        {0.92, 0.05, 0.02, 0.01},  // Gözlem 0
        {0.05, 0.85, 0.08, 0.02},  // Gözlem 1
        {0.02, 0.08, 0.82, 0.08},  // Gözlem 2
        {0.01, 0.02, 0.08, 0.89}   // Gözlem 3
    };

    // B Matrisi: 4 Aksiyon için geçiş dinamikleri P(s'|s, u)
    // 0: UART-2 Retry (Donanım koptuysa durumu düzeltemez)
    // 1: SDR Hopping (Donanım kopukken bile durumu Optimal/Gecikmeliye taşır)
    // 2: I2C Remap
    // 3: Thermal Downgrade
    B_.resize(4, std::vector<std::vector<double>>(num_states_, std::vector<double>(num_states_, 0.25)));

    // Aksiyon 0: UART-2 Retry
    B_[0] = {
        {0.80, 0.10, 0.05, 0.00},
        {0.15, 0.70, 0.15, 0.00},
        {0.05, 0.15, 0.60, 0.10},
        {0.00, 0.05, 0.20, 0.90} // Kopuksa %90 kopuk kalır
    };

    // Aksiyon 1: SDR_FREQUENCY_HOP_ACTIVATE (Fallback kurtarıcı)
    B_[1] = {
        {0.75, 0.60, 0.50, 0.65}, // Kopuk durumdan bile %65 ihtimalle normale döner
        {0.20, 0.30, 0.35, 0.25},
        {0.05, 0.08, 0.12, 0.08},
        {0.00, 0.02, 0.03, 0.02}
    };

    // Aksiyon 2: I2C Bus Remap
    B_[2] = {
        {0.60, 0.50, 0.40, 0.45},
        {0.30, 0.35, 0.40, 0.35},
        {0.08, 0.12, 0.15, 0.15},
        {0.02, 0.03, 0.05, 0.05}
    };

    // Aksiyon 3: Thermal Throttle Downgrade
    B_[3] = {
        {0.50, 0.60, 0.50, 0.40},
        {0.40, 0.30, 0.35, 0.40},
        {0.08, 0.08, 0.10, 0.15},
        {0.02, 0.02, 0.05, 0.05}
    };

    // C Vektörü (Tercih Edilen Gözlemler: Hedef Sağlam Sinyal = yüksek tercih)
    C_ = {2.5, 0.5, -1.5, -5.0};

    // D Vektörü (Başlangıç inancı)
    D_ = {0.95, 0.03, 0.015, 0.005};
}

double GenerativeModel::computeExpectedFreeEnergy(
    int action_idx,
    const std::vector<double>& current_beliefs,
    double& out_epistemic,
    double& out_pragmatic
) {
    const double eps = 1e-12;

    // 1. Sonraki Beklenen Durum Dağılımı: qs_next = B[u] * current_beliefs
    std::vector<double> qs_next(num_states_, 0.0);
    for (size_t next_s = 0; next_s < num_states_; ++next_s) {
        for (size_t s = 0; s < num_states_; ++s) {
            qs_next[next_s] += B_[action_idx][next_s][s] * current_beliefs[s];
        }
    }

    // 2. Beklenen Gözlem Dağılımı: qo_next = A * qs_next
    std::vector<double> qo_next(num_observations_, 0.0);
    for (size_t o = 0; o < num_observations_; ++o) {
        for (size_t s = 0; s < num_states_; ++s) {
            qo_next[o] += A_[o][s] * qs_next[s];
        }
    }

    // 3. Pragmatik Değer: - sum(qo_next[o] * C[o])
    out_pragmatic = 0.0;
    for (size_t o = 0; o < num_observations_; ++o) {
        out_pragmatic += qo_next[o] * C_[o];
    }

    // 4. Epistemik Değer (Belirsizlik Azaltma / Bilgi Kazancı):
    // E_{qo}[ H(s) - H(s|o) ]
    double entropy_s = 0.0;
    for (size_t s = 0; s < num_states_; ++s) {
        double p = std::max(qs_next[s], eps);
        entropy_s -= p * std::log(p);
    }

    double cond_entropy = 0.0;
    for (size_t o = 0; o < num_observations_; ++o) {
        double prob_o = std::max(qo_next[o], eps);
        double sub_ent = 0.0;
        for (size_t s = 0; s < num_states_; ++s) {
            double post_s = (A_[o][s] * qs_next[s]) / prob_o;
            post_s = std::max(post_s, eps);
            sub_ent -= post_s * std::log(post_s);
        }
        cond_entropy += prob_o * sub_ent;
    }
    out_epistemic = entropy_s - cond_entropy;

    // G(pi) = - Epistemic - Pragmatic
    double expected_free_energy = -out_epistemic - out_pragmatic;
    return expected_free_energy;
}

PolicyAction GenerativeModel::selectOptimalPolicy(const std::vector<double>& current_beliefs) {
    PolicyAction best_policy;
    best_policy.action_id = -1;
    best_policy.expected_free_energy = std::numeric_limits<double>::infinity();

    for (size_t u = 0; u < B_.size(); ++u) {
        double epistemic = 0.0;
        double pragmatic = 0.0;
        double g = computeExpectedFreeEnergy(static_cast<int>(u), current_beliefs, epistemic, pragmatic);

        if (g < best_policy.expected_free_energy) {
            best_policy.action_id = static_cast<int>(u);
            best_policy.name_tr = (u < action_names_.size()) ? action_names_[u] : "ACTION_" + std::to_string(u);
            best_policy.expected_free_energy = g;
            best_policy.epistemic_value = epistemic;
            best_policy.pragmatic_value = pragmatic;
        }
    }

    return best_policy;
}

} // namespace kam::active_inference
