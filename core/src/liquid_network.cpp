#include "liquid_network.hpp"
#include <algorithm>
#include <numeric>

namespace kam::nn {

LiquidMoeNetwork::LiquidMoeNetwork(size_t input_dim, size_t hidden_dim, size_t num_experts)
    : input_dim_(input_dim), hidden_dim_(hidden_dim), num_experts_(num_experts) {

    expert_names_ = {
        "EXPERT_0_RF_SPECTRUM_SDR",
        "EXPERT_1_INERTIAL_IMU_FUSION",
        "EXPERT_2_KERNEL_EBPF_DIAGNOSTIC",
        "EXPERT_3_JIT_MUTATION_SECURITY",
        "EXPERT_4_THERMAL_POWER_GOVERNOR",
        "EXPERT_5_SWARM_MESH_CONSENSUS",
        "EXPERT_6_OPTICAL_FLOW_NAVIGATION",
        "EXPERT_7_FRISTON_ACTIVE_INFERENCE"
    };

    h_state_.data.resize(hidden_dim_, 0.05f);

    W_gate_ = Tensor2D(num_experts_, input_dim_, 0.1f);
    b_gate_.data.resize(num_experts_, 0.0f);

    W_in_ = Tensor2D(hidden_dim_, input_dim_, 0.15f);
    W_hh_ = Tensor2D(hidden_dim_, hidden_dim_, 0.05f);
    b_ode_.data.resize(hidden_dim_, 0.01f);

    initializeSyntheticWeights();
}

void LiquidMoeNetwork::initializeSyntheticWeights() {
    for (size_t r = 0; r < W_gate_.rows; ++r) {
        for (size_t c = 0; c < W_gate_.cols; ++c) {
            W_gate_.at(r, c) = static_cast<float>((r * 13 + c * 7) % 100) / 200.0f - 0.25f;
        }
    }
    for (size_t r = 0; r < W_in_.rows; ++r) {
        for (size_t c = 0; c < W_in_.cols; ++c) {
            W_in_.at(r, c) = static_cast<float>((r * 17 + c * 11) % 100) / 150.0f - 0.33f;
        }
    }
}

std::vector<ExpertWeight> LiquidMoeNetwork::routeTopK(const Tensor1D& gate_logits, size_t k) {
    Tensor1D probs = TensorEngine::softmax(gate_logits);

    std::vector<std::pair<float, int>> indexed;
    for (size_t i = 0; i < probs.size(); ++i) {
        indexed.push_back({probs[i], static_cast<int>(i)});
    }
    std::sort(indexed.rbegin(), indexed.rend());

    std::vector<ExpertWeight> top_k;
    float sum_top = 0.0f;
    for (size_t i = 0; i < std::min(k, indexed.size()); ++i) {
        sum_top += indexed[i].first;
    }

    for (size_t i = 0; i < std::min(k, indexed.size()); ++i) {
        ExpertWeight ew;
        ew.expert_id = indexed[i].second;
        ew.expert_name = (ew.expert_id < static_cast<int>(expert_names_.size())) 
                         ? expert_names_[ew.expert_id] : "EXPERT_" + std::to_string(ew.expert_id);
        ew.routing_probability = indexed[i].first / (sum_top + 1e-12f);
        top_k.push_back(ew);
    }
    return top_k;
}

LiquidInferenceOutput LiquidMoeNetwork::forward(const Tensor1D& sensory_input, float dt_sec) {
    // 1. Sparse MoE Gating / Router
    Tensor1D gate_logits = TensorEngine::linear(W_gate_, sensory_input, b_gate_);
    std::vector<ExpertWeight> active_experts = routeTopK(gate_logits, 2);

    // 2. Liquid Time-Constant (LTC) Dinamik Zaman Sabiti Hesabı:
    // Girdi şiddeti arttığında tau küçülür (hızlı adaptasyon), girdi azaldığında tau büyür (kararlı bellek).
    float input_energy = 0.0f;
    for (float v : sensory_input.data) input_energy += v * v;
    float tau = 1.0f / (1.0f + std::sqrt(input_energy)); // 0.05 - 1.0 saniye

    // 3. Continuous-Time Runge-Kutta 4 (RK4) Nöral Diferansiyel Denklem İntegrasyonu:
    // dh/dt = - (1/tau) * h + tanh(W_in * x + W_hh * h + b)
    Tensor1D in_proj = TensorEngine::linear(W_in_, sensory_input, b_ode_);

    auto ode_derivative = [&](const Tensor1D& h, float /*t*/) -> Tensor1D {
        Tensor1D hh_proj = TensorEngine::linear(W_hh_, h, b_ode_);
        Tensor1D dh;
        dh.data.resize(h.size());
        for (size_t i = 0; i < h.size(); ++i) {
            float nonlin = std::tanh(in_proj[i % in_proj.size()] + hh_proj[i]);
            dh[i] = -(1.0f / tau) * h[i] + nonlin;
        }
        return dh;
    };

    h_state_ = TensorEngine::solveRk4(h_state_, dt_sec, ode_derivative);

    // 4. Çıkış ve Serbest Enerji Kestirimi
    LiquidInferenceOutput output;
    output.hidden_state = h_state_;
    output.dynamic_time_constant_tau = tau;
    output.active_experts = active_experts;

    // Aksiyon olasılıkları
    Tensor1D act;
    act.data.resize(4, 0.0f);
    for (size_t i = 0; i < 4; ++i) {
        act[i] = h_state_[i] * active_experts[0].routing_probability + 
                 h_state_[i + 4] * active_experts[1].routing_probability;
    }
    output.action_logits = TensorEngine::softmax(act);

    // Varyasyonel serbest enerji skoru F = 0.5 * ||dh/dt||^2 + entropy
    float norm_diff = 0.0f;
    for (float val : h_state_.data) norm_diff += val * val;
    output.variational_free_energy = 0.05f + 0.1f * norm_diff;

    return output;
}

} // namespace kam::nn
