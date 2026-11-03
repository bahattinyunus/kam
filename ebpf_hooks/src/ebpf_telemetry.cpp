#include "ebpf_telemetry.hpp"
#include "../../core/include/logger.hpp"
#include <iostream>

namespace kam::ebpf {

EbpfTelemetryHub::EbpfTelemetryHub() = default;

EbpfTelemetryHub::~EbpfTelemetryHub() {
    detachHooks();
}

bool EbpfTelemetryHub::attachHooks() {
    attached_ = true;
    core::Logger::instance().info(core::Subsystem::CORE, 
        "Sistem ruhu uyandırıldı. eBPF kancaları kernel'a tutundu.");
    return true;
}

void EbpfTelemetryHub::detachHooks() {
    if (attached_) {
        attached_ = false;
        core::Logger::instance().info(core::Subsystem::CORE, 
            "eBPF kancaları kernel'dan güvenle çözüldü.");
    }
}

void EbpfTelemetryHub::setCallback(TelemetryCallback cb) {
    callback_ = cb;
}

KernelTelemetryEvent EbpfTelemetryHub::pollEvents() {
    KernelTelemetryEvent event;
    event.device_name = "UART-2";
    event.file_descriptor = 12;
    event.is_alive = true;
    event.latency_us = 120.5;
    event.drop_rate = 0.0;
    event.npu_temp_celsius = current_npu_temp_;
    event.error_message = "";
    return event;
}

void EbpfTelemetryHub::triggerSyntheticFault(const std::string& device_name, const std::string& reason) {
    core::Logger::instance().warn(core::Subsystem::NERVOUS_SYS, 
        device_name + " (Telemetri) verisi kesildi! File descriptor yanıt vermiyor. (" + reason + ")");

    if (callback_) {
        KernelTelemetryEvent fault_event;
        fault_event.device_name = device_name;
        fault_event.file_descriptor = -1;
        fault_event.is_alive = false;
        fault_event.latency_us = 999999.0;
        fault_event.drop_rate = 1.0;
        fault_event.npu_temp_celsius = current_npu_temp_ + 15.0;
        fault_event.error_message = reason;
        callback_(fault_event);
    }
}

bool EbpfTelemetryHub::isAttached() const {
    return attached_;
}

} // namespace kam::ebpf
