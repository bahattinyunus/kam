// KAM Otonom İyileştirme Senaryosu: İHA Telemetri Hattı Kesintisi
// Bu senaryo, README.md dosyasında açıklanan 'Canlı Ayin' terminal akışını simüle eder.

#include "../core/include/kam_core.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    std::cout << "=========================================================\n";
    std::cout << "       KAM (Bilişsel Otonom Sistem Motoru) Başlatılıyor   \n";
    std::cout << "       Hedef Platform: Otonom İHA (NVIDIA Jetson Edge)   \n";
    std::cout << "=========================================================\n\n";

    kam::core::KamCore kam;

    // 1. Sistem Ruhunu Uyandır
    kam.awaken();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 2. Rutin Çalışma
    kam.step();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 3. Telemetri Arızası Enjekte Et (UART-2 kesintisi)
    kam.injectAnomaly("UART-2", "Baudrate çöküşü ve FD yanıt vermiyor");

    std::cout << "\n=========================================================\n";
    std::cout << "       Senaryo Başarıyla Tamamlandı.                     \n";
    std::cout << "       Aktif Hat: " << kam.getState().getActiveTelemetryNode() << "\n";
    std::cout << "       Nihai Entropi: %" << (kam.getState().getEntropy() * 100.0) << "\n";
    std::cout << "=========================================================\n";

    return 0;
}
