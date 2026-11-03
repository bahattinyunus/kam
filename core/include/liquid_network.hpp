#pragma once

#include "tensor_engine.hpp"
#include <string>
#include <vector>
#include <memory>

namespace kam::nn {

struct ExpertWeight {
    int expert_id;
    std::string expert_name;
    float routing_probability;
};

struct LiquidInferenceOutput {
    Tensor1D hidden_state;
    Tensor1D action_logits;
    float variational_free_energy;
    std::vector<ExpertWeight> active_experts; // Top-2 Aktif Uzman
    float dynamic_time_constant_tau;
};

class LiquidMoeNetwork {
public:
    LiquidMoeNetwork(size_t input_dim = 16, size_t hidden_dim = 32, size_t num_experts = 8);

    // Bir zaman adımı sürekli akışkan çıkarımı (Liquid Step)
    LiquidInferenceOutput forward(const Tensor1D& sensory_input, float dt_sec = 0.05f);

    // Rastgele ağırlıkları başlat
    void initializeSyntheticWeights();

    // Uzman isimleri listesi
    const std::vector<std::string>& getExpertNames() const { return expert_names_; }

private:
    size_t input_dim_;
    size_t hidden_dim_;
    size_t num_experts_;

    Tensor1D h_state_; // Nöral gizli durum

    // Gating / Router Ağı (Top-2 MoE)
    Tensor2D W_gate_;
    Tensor1D b_gate_;

    // Nöral ODE Ağırlıkları
    Tensor2D W_in_;
    Tensor2D W_hh_;
    Tensor1D b_ode_;

    std::vector<std::string> expert_names_;

    // Top-k uzman seçimi
    std::vector<ExpertWeight> routeTopK(const Tensor1D& gate_logits, size_t k = 2);
};

} // namespace kam::nn
