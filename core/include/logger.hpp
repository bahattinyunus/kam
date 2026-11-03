#pragma once

#include <string>
#include <iostream>
#include <sstream>
#include <chrono>
#include <iomanip>
#include <mutex>

namespace kam::core {

enum class LogLevel {
    INFO,
    WARNING,
    CRITICAL,
    SUCCESS,
    RITUAL
};

enum class Subsystem {
    CORE,          // [KAM-ÇEKİRDEK]
    NERVOUS_SYS,   // [SİNİR-SİSTEMİ]
    AGENT,         // [KAM-AJAN]
    COMPILER,      // [DERLEYİCİ]
    INFERENCE      // [AKTİF-ÇIKARIM]
};

class Logger {
public:
    static Logger& instance();

    void log(Subsystem sys, LogLevel level, const std::string& message);

    void info(Subsystem sys, const std::string& message) {
        log(sys, LogLevel::INFO, message);
    }

    void warn(Subsystem sys, const std::string& message) {
        log(sys, LogLevel::WARNING, message);
    }

    void critical(Subsystem sys, const std::string& message) {
        log(sys, LogLevel::CRITICAL, message);
    }

    void success(Subsystem sys, const std::string& message) {
        log(sys, LogLevel::SUCCESS, message);
    }

    void ritual(Subsystem sys, const std::string& message) {
        log(sys, LogLevel::RITUAL, message);
    }

private:
    Logger() = default;
    std::mutex mutex_;

    std::string subsystemPrefix(Subsystem sys) const;
    std::string levelColor(LogLevel level) const;
};

} // namespace kam::core
