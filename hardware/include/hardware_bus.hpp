#pragma once

#include <string>
#include <vector>
#include <cstdint>
#include <functional>

namespace kam::hardware {

enum class BusType {
    UART,
    SPI,
    I2C,
    CAN_BUS,
    SDR_RADIO
};

struct CanFrame {
    uint32_t id = 0;
    uint8_t dlc = 8;
    uint8_t data[8] = {0};
    bool is_extended = false;
    uint64_t timestamp_us = 0;
};

struct BusHealthMetrics {
    BusType type;
    std::string device_path;
    bool is_connected = true;
    double bus_load_percentage = 12.5;
    uint64_t error_frames_count = 0;
    uint64_t total_packets = 0;
    double jitter_us = 14.2;
};

using CanFrameCallback = std::function<void(const CanFrame&)>;

class HardwareBusController {
public:
    HardwareBusController();
    ~HardwareBusController();

    // Veriyolu arayüzünü bağla
    bool openBus(BusType type, const std::string& device_node);

    // CAN Veriyolundan paket gönder
    bool sendCanFrame(const CanFrame& frame);

    // CAN Veriyolundan paket dinle
    void registerCanCallback(CanFrameCallback cb);

    // Veriyolu sağlık telemetrisini al
    BusHealthMetrics getHealthMetrics(BusType type) const;

    // CAN Bus Spoofing / DoS Enjeksiyonu Simülasyonu
    void injectCanSpoofingAttack(uint32_t rogue_can_id);

    // Hata durumunu sıfırla
    void resetBus(BusType type);

private:
    CanFrameCallback can_callback_ = nullptr;
    BusHealthMetrics can_metrics_;
    BusHealthMetrics uart_metrics_;
    BusHealthMetrics sdr_metrics_;
};

} // namespace kam::hardware
