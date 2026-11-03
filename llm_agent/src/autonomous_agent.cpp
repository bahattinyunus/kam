#include "autonomous_agent.hpp"

namespace kam::llm {

AutonomousAgent::AutonomousAgent() {
    inference_engine_ = std::make_unique<TensorRtInference>();
    inference_engine_->loadEngine();
}

AutonomousAgent::~AutonomousAgent() = default;

std::string AutonomousAgent::diagnoseAndDecide(const std::string& failed_subsystem) {
    return inference_engine_->generateResponse(failed_subsystem);
}

std::string AutonomousAgent::generateMutatedCode(const std::string& failed_subsystem) {
    if (failed_subsystem.find("UART") != std::string::npos || failed_subsystem.find("TELEMETRY") != std::string::npos) {
        return CodeGenerator::generateSdrFallbackNode();
    } else if (failed_subsystem.find("THERMAL") != std::string::npos || failed_subsystem.find("NPU") != std::string::npos) {
        return CodeGenerator::generateThermalVisionFallbackNode();
    }
    return CodeGenerator::generateI2cBridgeNode();
}

} // namespace kam::llm
