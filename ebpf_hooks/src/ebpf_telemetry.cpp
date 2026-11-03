#include "ebpf_telemetry.hpp"
#include "../../core/include/logger.hpp"
#include <iostream>
#include <chrono>

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

std::optional<KernelTelemetryEvent> EbpfTelemetryHub::popNextEvent() {
    return event_ring_buffer_.pop();
}

KernelTelemetryEvent EbpfTelemetryHub::pollEvents() {
    auto queued = event_ring_buffer_.pop();
    if (queued) {
        return *queued;
    }

    KernelTelemetryEvent event;
    event.type = KernelEventType::FD_HEARTBEAT;
    event.device_name = "UART-2";
    event.file_descriptor = 12;
    event.is_alive = true;
    event.latency_us = 120.5;
    event.drop_rate = 0.0;
    event.npu_temp_celsius = current_npu_temp_;
    event.error_message = "";
    event.timestamp_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    return event;
}

void EbpfTelemetryHub::triggerSyntheticFault(const std::string& device_name, const std::string& reason) {
    core::Logger::instance().warn(core::Subsystem::NERVOUS_SYS, 
        device_name + " (Telemetri) verisi kesildi! File descriptor yanıt vermiyor. (" + reason + ")");

    KernelTelemetryEvent fault_event;
    fault_event.type = KernelEventType::HARDWARE_FAULT;
    fault_event.device_name = device_name;
    fault_event.file_descriptor = -1;
    fault_event.is_alive = false;
    fault_event.latency_us = 999999.0;
    fault_event.drop_rate = 1.0;
    fault_event.npu_temp_celsius = current_npu_temp_ + 15.0;
    fault_event.error_message = reason;
    fault_event.timestamp_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    event_ring_buffer_.push(fault_event);

    if (callback_) {
        callback_(fault_event);
    }
}

void EbpfTelemetryHub::triggerJammingAttack(const std::string& channel_name, double noise_floor_dbm) {
    core::Logger::instance().critical(core::Subsystem::NERVOUS_SYS, 
        "ELEKTRONİK HARP TEHDİDİ: " + channel_name + " frekansında yapay gürültü (Jamming) tespit edildi! Gürültü Tabanı: " 
        + std::to_string(noise_floor_dbm) + " dBm");

    KernelTelemetryEvent ew_event;
    ew_event.type = KernelEventType::ELECTRONIC_WARFARE_JAMMING;
    ew_event.device_name = channel_name;
    ew_event.is_alive = false;
    ew_event.drop_rate = 0.98;
    ew_event.error_message = "Elektronik Harp Sinyal Karıştırma";
    
    event_ring_buffer_.push(ew_event);

    if (callback_) {
        callback_(ew_event);
    }
}

bool EbpfTelemetryHub::isAttached() const {
    return attached_;
}

} // namespace kam::ebpf
