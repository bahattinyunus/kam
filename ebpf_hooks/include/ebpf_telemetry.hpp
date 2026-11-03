#pragma once

#include <string>
#include <functional>
#include <vector>
#include <memory>

namespace kam::ebpf {

struct KernelTelemetryEvent {
    std::string device_name;
    int file_descriptor;
    bool is_alive;
    double latency_us;
    double drop_rate;
    double npu_temp_celsius;
    std::string error_message;
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

    // Bir sonraki çekirdek olayını yokla
    KernelTelemetryEvent pollEvents();

    // Simülasyon / Test amaçlı çekirdek hatası enjekte et
    void triggerSyntheticFault(const std::string& device_name, const std::string& reason);

    bool isAttached() const;

private:
    bool attached_ = false;
    TelemetryCallback callback_ = nullptr;
    double current_npu_temp_ = 48.0;
};

} // namespace kam::ebpf
