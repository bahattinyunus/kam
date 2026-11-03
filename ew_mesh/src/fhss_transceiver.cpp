#include "fhss_transceiver.hpp"
#include "../../core/include/logger.hpp"
#include <iostream>

namespace kam::radio {

FhssTransceiver::FhssTransceiver(uint32_t hop_seed)
    : seed_(hop_seed) {
    initializeChannels();
}

void FhssTransceiver::initializeChannels() {
    // 868.0 MHz - 870.0 MHz aralığında 20 frekans kanalı (100 kHz adımlarla)
    channels_.clear();
    for (uint32_t i = 0; i < 20; ++i) {
        ChannelStatus ch;
        ch.channel_index = i;
        ch.frequency_mhz = 868.05 + (i * 0.1);
        ch.rssi_dbm = -75.0;
        ch.noise_floor_dbm = -110.0;
        ch.is_jammed = false;
        channels_.push_back(ch);
    }
    current_freq_mhz_ = channels_[0].frequency_mhz;
}

void FhssTransceiver::performSpectralScan() {
    // Gürültü tabanı -80 dBm'den yüksekse kanal karıştırılmış sayılır
    for (auto& ch : channels_) {
        if (ch.noise_floor_dbm > -80.0) {
            ch.is_jammed = true;
        } else {
            ch.is_jammed = false;
        }
    }
}

double FhssTransceiver::hopToNextCleanFrequency() {
    performSpectralScan();

    for (size_t attempt = 0; attempt < channels_.size(); ++attempt) {
        current_channel_idx_ = (current_channel_idx_ + 7) % channels_.size();
        if (!channels_[current_channel_idx_].is_jammed) {
            current_freq_mhz_ = channels_[current_channel_idx_].frequency_mhz;
            core::Logger::instance().info(core::Subsystem::CORE, 
                "BİLİŞSEL SDR: Karıştırılmamış temiz frekansa atlandı: " + 
                std::to_string(current_freq_mhz_) + " MHz (Kanal: " + 
                std::to_string(current_channel_idx_) + ")");
            return current_freq_mhz_;
        }
    }

    core::Logger::instance().critical(core::Subsystem::NERVOUS_SYS, 
        "TÜM KANALLAR BLOKE EDİLDİ! Acil durum ISM bandı atlaması başlatılıyor.");
    return current_freq_mhz_;
}

void FhssTransceiver::simulateJammerOnBand(double start_mhz, double end_mhz, double power_dbm) {
    for (auto& ch : channels_) {
        if (ch.frequency_mhz >= start_mhz && ch.frequency_mhz <= end_mhz) {
            ch.noise_floor_dbm = power_dbm;
            ch.is_jammed = true;
        }
    }
}

double FhssTransceiver::getCurrentFrequency() const {
    return current_freq_mhz_;
}

size_t FhssTransceiver::getJammedChannelCount() const {
    size_t count = 0;
    for (const auto& ch : channels_) {
        if (ch.is_jammed) count++;
    }
    return count;
}

double FhssTransceiver::getPacketDeliveryRatio() const {
    if (transmitted_packets_ == 0) return 1.0;
    return static_cast<double>(transmitted_packets_ - dropped_packets_) / transmitted_packets_;
}

} // namespace kam::radio
