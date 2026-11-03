#pragma once

#include "lockfree_ringbuffer.hpp"
#include <string>
#include <functional>
#include <vector>
#include <memory>

namespace kam::ebpf {

enum class KernelEventType {
    FD_HEARTBEAT,
    SOCKET_DROP,
    THERMAL_SPIKE,
    ELECTRONIC_WARFARE_JAMMING,
    HARDWARE_FAULT
};

struct KernelTelemetryEvent {
    KernelEventType type = KernelEventType::FD_HEARTBEAT;
    std::string device_name;
    int file_descriptor = -1;
    bool is_alive = true;
    double latency_us = 120.0;
    double drop_rate = 0.0;
    double npu_temp_celsius = 45.0;
    std::string error_message = "";
    uint64_t timestamp_ns = 0;
};

using TelemetryCallback = std::function<void(const KernelTelemetryEvent&)>;

class EbpfTelemetryHub {
public:
    EbpfTelemetryHub();
    ~EbpfTelemetryHub();

    // Linux çekirdeğine eBPF kancalarını bağla
    bool attachHooks();

    // Kancaları güvenle ayır
    void detachHooks();

    // Telemetri geri çağırma fonksiyonunu kaydet
    void setCallback(TelemetryCallback cb);

    // Lock-free ring buffer'dan bir sonraki olayı çek
    std::optional<KernelTelemetryEvent> popNextEvent();

    // Bir sonraki çekirdek olayını yokla
    KernelTelemetryEvent pollEvents();

    // Sentetik hata enjekte et (Simülasyon / Test amaçlı)
    void triggerSyntheticFault(const std::string& device_name, const std::string& reason);

    // Elektronik harp (EW) Jamming simülasyonu
    void triggerJammingAttack(const std::string& channel_name, double noise_floor_dbm);

    bool isAttached() const;

private:
    bool attached_ = false;
    TelemetryCallback callback_ = nullptr;
    double current_npu_temp_ = 48.0;
    LockFreeRingBuffer<KernelTelemetryEvent, 1024> event_ring_buffer_;
};

} // namespace kam::ebpf
