#include "hardware_bus.hpp"
#include "../../core/include/logger.hpp"
#include <iostream>

namespace kam::hardware {

HardwareBusController::HardwareBusController() {
    can_metrics_ = {BusType::CAN_BUS, "/dev/can0", true, 8.5, 0, 10240, 12.0};
    uart_metrics_ = {BusType::UART, "/dev/ttyTHS1", true, 18.0, 0, 48200, 25.4};
    sdr_metrics_ = {BusType::SDR_RADIO, "sdr0:868MHz", true, 4.0, 0, 9500, 8.1};
}

HardwareBusController::~HardwareBusController() = default;

bool HardwareBusController::openBus(BusType type, const std::string& device_node) {
    core::Logger::instance().info(core::Subsystem::CORE, 
        "Donanım Veriyolu Arayüzü Bağlandı: " + device_node);
    return true;
}

bool HardwareBusController::sendCanFrame(const CanFrame& frame) {
    can_metrics_.total_packets++;
    if (can_callback_) {
        can_callback_(frame);
    }
    return true;
}

void HardwareBusController::registerCanCallback(CanFrameCallback cb) {
    can_callback_ = cb;
}

BusHealthMetrics HardwareBusController::getHealthMetrics(BusType type) const {
    switch (type) {
        case BusType::CAN_BUS: return can_metrics_;
        case BusType::UART: return uart_metrics_;
        case BusType::SDR_RADIO: return sdr_metrics_;
        default: return can_metrics_;
    }
}

void HardwareBusController::injectCanSpoofingAttack(uint32_t rogue_can_id) {
    can_metrics_.bus_load_percentage = 98.4;
    can_metrics_.error_frames_count += 450;
    core::Logger::instance().critical(core::Subsystem::NERVOUS_SYS, 
        "CAN BUS ANOMALİSİ: Yetkisiz CAN-ID (0x" + std::to_string(rogue_can_id) + 
        ") üzerinden mesaj enjeksiyonu ve veriyolu taşması (Bus Flood) tespit edildi!");
}

void HardwareBusController::resetBus(BusType type) {
    if (type == BusType::CAN_BUS) {
        can_metrics_.bus_load_percentage = 11.2;
        can_metrics_.error_frames_count = 0;
    }
}

} // namespace kam::hardware
