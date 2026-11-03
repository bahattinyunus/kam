#pragma once

#include <chrono>
#include <atomic>
#include <thread>
#include <functional>
#include <string>

namespace kam::core {

using PanicHandler = std::function<void(const std::string& reason)>;

class AutonomousWatchdog {
public:
    explicit AutonomousWatchdog(std::chrono::milliseconds timeout_ms = std::chrono::milliseconds(2500));
    ~AutonomousWatchdog();

    // Watchdog bekçisini başlat
    void start();

    // Kalp atışını besle (Pet the dog)
    void heartbeat();

    // Bekçiyi durdur
    void stop();

    // Panik tetikleme fonksiyonunu ayarla
    void setPanicHandler(PanicHandler handler);

    // Watchdog durumunu sorgula
    bool isAlive() const;
    int64_t getMillisSinceLastHeartbeat() const;

private:
    std::chrono::milliseconds timeout_ms_;
    std::atomic<bool> running_{false};
    std::atomic<int64_t> last_heartbeat_timestamp_ms_{0};
    std::thread monitor_thread_;
    PanicHandler panic_handler_ = nullptr;

    void monitorLoop();
};

} // namespace kam::core
