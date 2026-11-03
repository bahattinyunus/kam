#pragma once

#include "tensorrt_inference.hpp"
#include "code_generator.hpp"
#include <string>
#include <memory>

namespace kam::llm {

class AutonomousAgent {
public:
    AutonomousAgent();
    ~AutonomousAgent();

    // Arızayı teşhis et ve Türkçe karar gerekçesini açıkla
    std::string diagnoseAndDecide(const std::string& failed_subsystem);

    // Gereken yedek C++ kodunu üret
    std::string generateMutatedCode(const std::string& failed_subsystem);

private:
    std::unique_ptr<TensorRtInference> inference_engine_;
};

} // namespace kam::llm
