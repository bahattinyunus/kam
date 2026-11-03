#pragma once

#include <string>
#include <sstream>
#include "../include/system_state.hpp"

namespace kam::core {

class TelemetryExporter {
public:
    static std::string exportPrometheusMetrics(const SystemState& state);
    static std::string exportJsonSnapshot(const SystemState& state);
};

} // namespace kam::core
