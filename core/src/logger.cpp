#include "logger.hpp"

namespace kam::core {

Logger& Logger::instance() {
    static Logger inst;
    return inst;
}

std::string Logger::subsystemPrefix(Subsystem sys) const {
    switch (sys) {
        case Subsystem::CORE:        return "[KAM-ÇEKİRDEK]";
        case Subsystem::NERVOUS_SYS: return "[SİNİR-SİSTEMİ]";
        case Subsystem::AGENT:       return "[KAM-AJAN]     ";
        case Subsystem::COMPILER:    return "[DERLEYİCİ]    ";
        case Subsystem::INFERENCE:   return "[AKTİF-ÇIKARIM]";
        default:                     return "[KAM]          ";
    }
}

std::string Logger::levelColor(LogLevel level) const {
    switch (level) {
        case LogLevel::INFO:     return "\033[1;36m"; // Parlak Cyan
        case LogLevel::WARNING:  return "\033[1;33m"; // Parlak Sarı
        case LogLevel::CRITICAL: return "\033[1;31m"; // Parlak Kırmızı
        case LogLevel::SUCCESS:  return "\033[1;32m"; // Parlak Yeşil
        case LogLevel::RITUAL:   return "\033[1;35m"; // Parlak Magenta
        default:                 return "\033[0m";
    }
}

void Logger::log(Subsystem sys, LogLevel level, const std::string& message) {
    std::lock_guard<std::mutex> lock(mutex_);

    const std::string color = levelColor(level);
    const std::string reset = "\033[0m";
    const std::string prefix = subsystemPrefix(sys);

    std::string icon = "";
    switch (level) {
        case LogLevel::INFO:     icon = "⚡"; break;
        case LogLevel::WARNING:  icon = "⚠️ "; break;
        case LogLevel::CRITICAL: icon = "🔥"; break;
        case LogLevel::SUCCESS:  icon = "🛡️ "; break;
        case LogLevel::RITUAL:   icon = "🧠"; break;
    }

    std::cout << color << prefix << " " << icon << " " << message << reset << std::endl;
}

} // namespace kam::core
