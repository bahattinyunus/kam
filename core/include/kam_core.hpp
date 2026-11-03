#pragma once

#include "system_state.hpp"
#include "jit_compiler.hpp"
#include "logger.hpp"
#include <memory>
#include <string>

namespace kam::active_inference {
    class ActiveInferenceEngine;
}

namespace kam::ebpf {
    class EbpfTelemetryHub;
}

namespace kam::llm {
    class AutonomousAgent;
}

namespace kam::core {

class KamCore {
public:
    KamCore();
    ~KamCore();

    // Sistem ruhunu uyandır ve kernel kancalarını bağla
    bool awaken();

    // Bir bilişsel döngü adımı işlet
    void step();

    // Kaos / Anomali simüle et veya tetikle
    void injectAnomaly(const std::string& node_id, const std::string& failure_reason);

    // Otonom iyileştirme ayinini (Self-Healing Ritual) yürüt
    bool initiateHealingRitual(const std::string& failed_node);

    // Sistem durumunu al
    SystemState& getState();

    // Çalışma durumunu sorgula
    bool isAwake() const;

private:
    bool is_awake_ = false;
    std::shared_ptr<SystemState> state_;
    std::shared_ptr<JitCompiler> compiler_;
    std::shared_ptr<active_inference::ActiveInferenceEngine> inference_engine_;
    std::shared_ptr<ebpf::EbpfTelemetryHub> telemetry_hub_;
    std::shared_ptr<llm::AutonomousAgent> agent_;
};

} // namespace kam::core
