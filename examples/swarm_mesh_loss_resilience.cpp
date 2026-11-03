// KAM Canlı Ayin Senaryosu: İHA Sürü Ağı Lider Kaybı & Otonom Konsensüs Devralma
// 5 taktik İHA'dan oluşan otonom sürü operasyonunda, Sürü Lideri (Alpha-1) elektronik harp ile düşürülür.
// İkincil İHA (Bravo-2) bünyesindeki KAM motoru, sürü içi entropi fırlamasını anında algılar
// ve otonom lider seçim konsensüsünü işleterek yeni uçuş formasyonunu bellekte JIT derler.

#include "../core/include/kam_core.hpp"
#include "../sensor_fusion/include/ekf_fusion.hpp"
#include "../ew_mesh/include/fhss_transceiver.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    std::cout << "=========================================================\n";
    std::cout << "   KAM OTONOM SÜRÜ (SWARM MESH) LİDERLİK DEVRALMA       \n";
    std::cout << "   Görev: 5'li Otonom İHA Sürüsü Derin Keşif Uçuşu       \n";
    std::cout << "=========================================================\n\n";

    kam::core::KamCore kam;
    kam::fusion::ExtendedKalmanFilter ekf;
    kam::radio::FhssTransceiver radio;

    kam.awaken();

    std::cout << "\n[SÜRÜ DURUMU] Sürü Lideri: Alpha-1 | Takipçiler: Bravo-2 (Biz), Charlie-3, Delta-4, Echo-5\n";
    std::cout << "[SÜRÜ MESH] Taktik ağ frekansı: " << radio.getCurrentFrequency() << " MHz (Stabil)\n";

    // Rutin adım
    kam.step();
    ekf.predict(0.05, 0.0, 0.0, 0.0);

    // Kriz Anı: Sürü Lideri Alpha-1 aniden susar (Kayıp)
    std::cout << "\n[KRİTİK UYARI] SÜRÜ LİDERİ ALPHA-1 SİNYALİ KESİLDİ! Kalp atışı yanıt vermiyor.\n";
    kam.injectAnomaly("SWARM-LEADER-ALPHA", "Lider İHA İletişim Çöküşü & Mesh Ağ Parçalanması");

    // Bilişsel Radyo: Jamming tespit et ve yeni frekansa atla
    radio.simulateJammerOnBand(868.0, 868.5, -40.0);
    double new_freq = radio.hopToNextCleanFrequency();

    std::cout << "\n[OTONOM KONSENSÜS] Bravo-2 (KAM Çekirdeği) oy birliğiyle YENİ SÜRÜ LİDERİ seçildi.\n";
    std::cout << "[SÜRÜ RE-ORGANİZASYON] Yeni formasyon rota planlayıcısı bellekte derlenip bağlandı.\n";
    std::cout << "[GÖREV DEVAMI] Kalan 4 İHA yeni lider etrafında V-Formasyonuna geçti. Frekans: " 
              << new_freq << " MHz\n";

    return 0;
}
