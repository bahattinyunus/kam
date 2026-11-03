class CodeMutator:
    """
    KAM Bilişsel Ajanı tarafından anlık üretilen C++ düğüm şablonları
    """
    @staticmethod
    def generate_sdr_fallback() -> str:
        return '''// [KAM-OTO-MUTASYON] sdr_fallback_node.cpp
// Üretim Nedeni: UART-2 Telemetri Kesintisi
#include <iostream>
extern "C" {
int kam_entrypoint() {
    std::cout << "[SDR-TOPOLOJİ] SDR 868MHz telemetri köprüsü aktifleştirildi.\\n";
    return 0;
}
}
'''

    @staticmethod
    def generate_thermal_fallback() -> str:
        return '''// [KAM-OTO-MUTASYON] thermal_vision_fallback.cpp
// Üretim Nedeni: NPU Termal Eşik Aşımı
#include <iostream>
extern "C" {
int kam_entrypoint() {
    std::cout << "[TERMAL-FÜZYON] Lidar + IMU düşük güç moduna geçildi.\\n";
    return 0;
}
}
'''
