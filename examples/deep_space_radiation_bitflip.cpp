// KAM Canlı Ayin Senaryosu: Derin Uzay Radyasyonu ve Bellek Bit-Flip Kurtarma
// Uzay aracının NPU ve ana işlemci biriminde kozmik radyasyon nedeniyle bit-flip oluşur.
// eBPF kancaları bellek entropisindeki anomalileri sezer ve güvenli bellek-içi mikro-derleme ile
// arızalı hesaplama düğümünü izole eder.

#include "../core/include/kam_core.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    std::cout << "=========================================================\n";
    std::cout << "   KAM DERİN UZAY (DEEP SPACE) RADYASYON VE BİT-FLİP     \n";
    std::cout << "   Görev: Jüpiter Yörünge Girişi & Radyasyon Kuşağı     \n";
    std::cout << "=========================================================\n\n";

    kam::core::KamCore kam;
    kam.awaken();

    std::cout << "\n[RADYASYON PROBU] Yüksek enerjili proton akısı tespit edildi (SEU Bit-Flip)!\n";
    kam.injectAnomaly("NPU-REG-A3", "Kozmik Işın SEU: L1 Veri Önbellek Bozulması");

    return 0;
}
