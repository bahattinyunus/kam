#pragma once

#include <vector>
#include <string>
#include <cmath>

namespace kam::active_inference {

// A-Matrisi: Olabilirlik (Likelihood P(o|s))
// B-Matrisi: Durum Geçişleri (Transition Dynamics P(s_{t+1}|s_t, u))
// C-Vektörü: Tercih Edilen Gözlemler (Prior Preferences ln P(o))
// D-Vektörü: Başlangıç İnancı (Initial Beliefs P(s_0))

struct PolicyAction {
    int action_id;
    std::string name_tr;
    double expected_free_energy; // G(pi) - ne kadar düşükse o kadar iyi
    double epistemic_value;      // Belirsizliği giderme potansiyeli
    double pragmatic_value;      // Hedefe ve stabiliteye ulaşma skoru
};

class GenerativeModel {
public:
    GenerativeModel(size_t num_states = 4, size_t num_observations = 4);

    // Matrisleri ve öncülleri kur
    void initializeDefaultMatrices();

    // Beklenen Serbest Enerji (Expected Free Energy - EFE) G(pi) hesapla
    double computeExpectedFreeEnergy(
        int action_idx,
        const std::vector<double>& current_beliefs,
        double& out_epistemic,
        double& out_pragmatic
    );

    // En optimal aksiyonu seç (Argmin G(pi))
    PolicyAction selectOptimalPolicy(const std::vector<double>& current_beliefs);

    // Matris erişimcileri
    const std::vector<std::vector<double>>& getA() const { return A_; }
    const std::vector<std::vector<std::vector<double>>>& getB() const { return B_; }
    const std::vector<double>& getC() const { return C_; }
    const std::vector<double>& getD() const { return D_; }

private:
    size_t num_states_;
    size_t num_observations_;

    // A[obs][state]
    std::vector<std::vector<double>> A_;
    // B[action][next_state][current_state]
    std::vector<std::vector<std::vector<double>>> B_;
    // C[obs]
    std::vector<double> C_;
    // D[state]
    std::vector<double> D_;

    std::vector<std::string> action_names_ = {
        "UART-2_RETRY",
        "SDR_FREQUENCY_HOP_ACTIVATE",
        "I2C_BUS_REMAP",
        "THERMAL_THROTTLE_DOWNGRADE"
    };
};

} // namespace kam::active_inference
