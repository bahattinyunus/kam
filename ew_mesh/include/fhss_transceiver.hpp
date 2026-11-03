#pragma once

#include <vector>
#include <string>
#include <cstdint>
#include <array>

namespace kam::radio {

struct ChannelStatus {
    uint32_t channel_index;
    double frequency_mhz;
    double rssi_dbm;
    double noise_floor_dbm;
    bool is_jammed;
};

struct RadioPacket {
    uint32_t sequence_num;
    uint32_t hopping_channel;
    uint8_t payload[64];
    uint32_t crc32;
};

class FhssTransceiver {
public:
    explicit FhssTransceiver(uint32_t hop_seed = 0x4B414D31);

    // Spektral tarama yap ve kanalların gürültü durumunu güncelle
    void performSpectralScan();

    // Bir sonraki temiz frekansa atla (Cognitive Hopping)
    double hopToNextCleanFrequency();

    // Düşman karıştırması simüle et
    void simulateJammerOnBand(double start_mhz, double end_mhz, double power_dbm = -35.0);

    // Aktif frekansı al
    double getCurrentFrequency() const;

    // Engellenen kanal sayısını al
    size_t getJammedChannelCount() const;

    // Paket iletim başarısı oranı
    double getPacketDeliveryRatio() const;

private:
    uint32_t seed_;
    uint32_t current_channel_idx_ = 0;
    std::vector<ChannelStatus> channels_;
    double current_freq_mhz_ = 868.1;
    uint64_t transmitted_packets_ = 0;
    uint64_t dropped_packets_ = 0;

    void initializeChannels();
};

} // namespace kam::radio
