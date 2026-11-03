#include "watchdog.hpp"
#include "logger.hpp"
#include <iostream>

namespace kam::core {

AutonomousWatchdog::AutonomousWatchdog(std::chrono::milliseconds timeout_ms)
    : timeout_ms_(timeout_ms) {
    heartbeat();
}

AutonomousWatchdog::~AutonomousWatchdog() {
    stop();
}

void AutonomousWatchdog::start() {
    if (running_.load()) return;
    running_.store(true);
    heartbeat();

    monitor_thread_ = std::thread(&AutonomousWatchdog::monitorLoop, this);
    Logger::instance().info(Subsystem::CORE, 
        "Donanımsal Watchdog Sigortası devrede. Zaman aşımı eşiği: " + 
        std::to_string(timeout_ms_.count()) + " ms");
}

void AutonomousWatchdog::heartbeat() {
    auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    last_heartbeat_timestamp_ms_.store(now_ms);
}

void AutonomousWatchdog::stop() {
    if (!running_.load()) return;
    running_.store(false);
    if (monitor_thread_.joinable()) {
        monitor_thread_.join();
    }
}

void AutonomousWatchdog::setPanicHandler(PanicHandler handler) {
    panic_handler_ = handler;
}

bool AutonomousWatchdog::isAlive() const {
    return getMillisSinceLastHeartbeat() <= timeout_ms_.count();
}

int64_t AutonomousWatchdog::getMillisSinceLastHeartbeat() const {
    auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    return now_ms - last_heartbeat_timestamp_ms_.load();
}

void AutonomousWatchdog::monitorLoop() {
    while (running_.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        if (getMillisSinceLastHeartbeat() > timeout_ms_.count()) {
            Logger::instance().critical(Subsystem::CORE, 
                "WATCHDOG ZAMAN AŞIMI! Bilişsel çekirdekten yanıt alınamıyor (" + 
                std::to_string(getMillisSinceLastHeartbeat()) + " ms). Panik kilidi devreye alınıyor.");
            if (panic_handler_) {
                panic_handler_("Watchdog timeout exceeded");
            }
            break;
        }
    }
}

} // namespace kam::core
