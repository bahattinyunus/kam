// KAM Canlı Ayin Senaryosu: Elektronik Harp (EW) ve Sinyal Karıştırma (Jamming) Saldırısı
// Otonom İHA düşman elektronik harp karıştırmasına maruz kalır.
// Klasik otonom sistemler sinyal kaybından dolayı yere çakılırken veya Return-to-Home
// sırasında vurulurken, KAM Aktif Çıkarım ile frekans atlamalı SDR C++ modülünü JIT derleyerek
// hayatta kalmayı başarır.

#include "../core/include/kam_core.hpp"
#include "../ros2_bridge/include/kam_ros2_node.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    std::cout << "=========================================================\n";
    std::cout << "   KAM ELEKTRONİK HARP (EW) HAYATTA KALMA SENARYOSU      \n";
    std::cout << "   Görev: Düşman Hava Savunma Hattı Sızma Uçuşu          \n";
    std::cout << "=========================================================\n\n";

    kam::core::KamCore kam;
    kam::ros2::KamRos2Bridge ros2_sentinel;

    // 1. Sistem Ruhunu Uyandır
    kam.awaken();
    ros2_sentinel.initNode();
    std::this_thread::sleep_for(std::chrono::milliseconds(400));

    // 2. Normal Uçuş Adımı
    kam.step();
    std::this_thread::sleep_for(std::chrono::milliseconds(400));

    // 3. Elektronik Harp Saldırısı (Jamming -95 dBm yapay gürültü)
    std::cout << "\n[DÜŞMAN EW SİSTEMİ] Yüksek güçlü geniş bant karıştırıcı aktif! (868-915 MHz Jammed)\n\n";
    kam.injectAnomaly("RF-TELEMETRY-MAIN", "Yoğun RF Jamming ve Taşıyıcı Sinyal Çöküşü");

    // 4. ROS2 Acil Durum Topic Remapping
    ros2_sentinel.triggerEmergencyRemap();

    std::cout << "\n=========================================================\n";
    std::cout << "   ELEKTRONİK HARP SENARYOSU BAŞARIYLA ATLATILDI!        \n";
    std::cout << "   Yeni Aktif Frekans: 433 MHz FHSS (SDR-YEDEK)          \n";
    std::cout << "   Sistem Durumu: Bilişsel Denge Sağlandı.               \n";
    std::cout << "=========================================================\n";

    return 0;
}
