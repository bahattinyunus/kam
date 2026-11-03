// KAM-1 Liquid Foundation Model & Continuous Neural ODE C++20 Gösterimi

#include "../core/include/liquid_network.hpp"
#include <iostream>
#include <iomanip>

int main() {
    std::cout << "=========================================================\n";
    std::cout << "   KAM-1 LIQUID FOUNDATION MODEL & NEURAL ODE RK4        \n";
    std::cout << "   Sürekli Zaman Akışkan Sinir Ağı & Top-2 Sparse MoE   \n";
    std::cout << "=========================================================\n\n";

    kam::nn::LiquidMoeNetwork net(16, 32, 8);

    // 16 boyutlu sensör telemetri vektörü
    kam::nn::Tensor1D sensory_stream;
    sensory_stream.data = {
        0.05f, 0.12f, 0.88f, 0.02f, 48.0f, 1.4f, 0.01f, 0.95f,
        0.10f, 0.20f, 0.70f, 0.05f, 52.0f, 1.8f, 0.02f, 0.90f
    };

    std::cout << "[GİRDİ AKIŞI] 16 kanallı duyusal telemetri akışı besleniyor...\n";
    auto out = net.forward(sensory_stream, 0.05f);

    std::cout << "\n[ÇIKARIM SONUÇLARI]\n";
    std::cout << "  • Dinamik Zaman Sabiti (LTC Tau) : " << std::fixed << std::setprecision(4) << out.dynamic_time_constant_tau << " saniye\n";
    std::cout << "  • Varyasyonel Serbest Enerji (F): " << out.variational_free_energy << " nats\n";
    std::cout << "  • Top-2 Aktif Nöral Uzmanlar    :\n";
    for (const auto& exp : out.active_experts) {
        std::cout << "     -> [" << exp.expert_name << "] Ağırlık: %" 
                  << std::setprecision(2) << (exp.routing_probability * 100.0f) << "\n";
    }

    std::cout << "\n=========================================================\n";
    std::cout << "   KAM-1 SAF C++20 TENSÖR ÇIKARIMI BAŞARIYLA TAMAMLANDI! \n";
    std::cout << "=========================================================\n";

    return 0;
}
