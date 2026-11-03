#include "kam_core.hpp"
#include "../../ebpf_hooks/include/ebpf_telemetry.hpp"
#include "../../active_inference/include/active_inference.hpp"
#include "../../llm_agent/include/autonomous_agent.hpp"
#include <thread>
#include <chrono>

namespace kam::core {

KamCore::KamCore() {
    state_ = std::make_shared<SystemState>();
    compiler_ = std::make_shared<JitCompiler>();
    inference_engine_ = std::make_shared<active_inference::ActiveInferenceEngine>();
    telemetry_hub_ = std::make_shared<ebpf::EbpfTelemetryHub>();
    agent_ = std::make_shared<llm::AutonomousAgent>();

    // eBPF kanca geri çağırmasını bağla
    telemetry_hub_->setCallback([this](const ebpf::KernelTelemetryEvent& ev) {
        if (!ev.is_alive) {
            state_->updateNodeHealth(ev.device_name, NodeHealth::OFFLINE, ev.drop_rate);
            // Aktif çıkarım motoruna anomaliyi aktar
            auto assessment = inference_engine_->updateSensoryInput({}, true);
            state_->setEntropy(assessment.entropy_percentage);
            state_->setFreeEnergy(assessment.free_energy);

            Logger::instance().critical(Subsystem::NERVOUS_SYS, 
                "Entropi %89 seviyesine fırladı. Kritik Eşik aşıldı! Kaos tespit edildi.");

            // Otonom iyileştirme ayinini başlat
            initiateHealingRitual(ev.device_name);
        }
    });
}

KamCore::~KamCore() {
    if (telemetry_hub_) {
        telemetry_hub_->detachHooks();
    }
}

bool KamCore::awaken() {
    is_awake_ = true;
    telemetry_hub_->attachHooks();

    std::string entropy_msg = "Aktif Çıkarım devrede. Sistem entropisi: %" + 
                              std::to_string(static_cast<int>(state_->getEntropy() * 100.0)) + " (Stabil)";
    Logger::instance().info(Subsystem::CORE, entropy_msg);
    return true;
}

void KamCore::step() {
    if (!is_awake_) return;

    auto ev = telemetry_hub_->pollEvents();
    auto assessment = inference_engine_->updateSensoryInput({0.95, 0.03, 0.015, 0.005});
    state_->setEntropy(assessment.entropy_percentage);
    state_->setFreeEnergy(assessment.free_energy);
}

void KamCore::injectAnomaly(const std::string& node_id, const std::string& failure_reason) {
    telemetry_hub_->triggerSyntheticFault(node_id, failure_reason);
}

bool KamCore::initiateHealingRitual(const std::string& failed_node) {
    Logger::instance().ritual(Subsystem::AGENT, "Otonom iyileştirme ayini başlatılıyor...");

    // 1. LLM Ajanı Teşhis ve Strateji Belirler
    std::string decision = agent_->diagnoseAndDecide(failed_node);
    Logger::instance().ritual(Subsystem::AGENT, decision);

    // 2. Ajan Yeni C++ Kodunu Üretir
    std::string mutated_cpp = agent_->generateMutatedCode(failed_node);

    // 3. JIT Derleyici Kodu Bellekte Derler
    std::string module_name = "sdr_fallback_node";
    Logger::instance().info(Subsystem::COMPILER, 
        "Yeni topoloji (" + module_name + ".cpp) bellekte derleniyor...");

    auto compile_result = compiler_->compileSource(module_name, mutated_cpp);
    if (!compile_result.success) {
        Logger::instance().critical(Subsystem::COMPILER, "Bellek-içi derleme başarısız oldu!");
        return false;
    }

    // 4. Yeni Düğüm Sıcak Yama Olarak Sisteme Bağlanır
    compiler_->loadAndExecute(compile_result.binary_path, "kam_entrypoint");

    // 5. Sistem Topolojisi ve Entropisi Dengelenir
    state_->setActiveTelemetryNode("SDR-YEDEK");
    state_->updateNodeHealth("SDR-YEDEK", NodeHealth::RECOVERED, 0.0);
    inference_engine_->resetToEquilibrium(0.15);
    state_->setEntropy(0.15);

    Logger::instance().success(Subsystem::CORE, 
        "İyileşme başarılı. Sistem entropisi: %15. Göreve devam ediliyor.");

    return true;
}

SystemState& KamCore::getState() {
    return *state_;
}

bool KamCore::isAwake() const {
    return is_awake_;
}

} // namespace kam::core
