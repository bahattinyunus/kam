#pragma once

#include <string>

namespace kam::llm {

enum class RecoveryStrategy {
    SDR_FALLBACK,
    I2C_BRIDGE,
    THERMAL_LOW_POWER_FUSION
};

class CodeGenerator {
public:
    static std::string generateSdrFallbackNode();
    static std::string generateI2cBridgeNode();
    static std::string generateThermalVisionFallbackNode();

    static std::string generateCodeByStrategy(RecoveryStrategy strategy);
};

} // namespace kam::llm
