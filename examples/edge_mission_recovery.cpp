// KAM Senaryosu: NPU Termal Eşik Aşımı ve Sensör Füzyon Kurtarma

#include "../core/include/kam_core.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    std::cout << "=========================================================\n";
    std::cout << "       KAM Bilişsel Görev İyileştirme Senaryosu          \n";
    std::cout << "       Hedef: Elektronik Harp & Termal Kriz Yönetimi     \n";
    std::cout << "=========================================================\n\n";

    kam::core::KamCore kam;
    kam.awaken();

    kam.step();

    std::cout << "\n[SIM] Ortam sıcaklığı ve NPU yükü artırılıyor (>85°C)...\n";
    kam.injectAnomaly("NPU-THERMAL", "Throttling eşiği aşıldı: 89°C");

    return 0;
}
