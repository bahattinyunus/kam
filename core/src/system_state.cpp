#include "system_state.hpp"

namespace kam::core {

SystemState::SystemState() 
    : active_telemetry_node_("UART-2") {
    // Varsayılan standart düğümler
    registerNode({"UART-2", "TELEMETRY", NodeHealth::ONLINE, 12, 0.0, 42.0, true});
    registerNode({"SDR-YEDEK", "RADIO", NodeHealth::ONLINE, 14, 0.0, 39.0, false});
    registerNode({"IMU-1", "NAVIGATION", NodeHealth::ONLINE, 8, 0.0, 40.0, true});
    registerNode({"CAM-FRONT", "VISION", NodeHealth::ONLINE, 19, 0.0, 48.0, true});
}

void SystemState::registerNode(const HardwareNode& node) {
    nodes_[node.id] = node;
}

void SystemState::updateNodeHealth(const std::string& id, NodeHealth health, double drop_rate) {
    auto it = nodes_.find(id);
    if (it != nodes_.end()) {
        it->second.health = health;
        it->second.packet_drop_rate = drop_rate;
    }
}

HardwareNode* SystemState::getNode(const std::string& id) {
    auto it = nodes_.find(id);
    if (it != nodes_.end()) {
        return &it->second;
    }
    return nullptr;
}

const std::unordered_map<std::string, HardwareNode>& SystemState::getAllNodes() const {
    return nodes_;
}

void SystemState::setEntropy(double entropy) {
    system_entropy_ = entropy;
}

double SystemState::getEntropy() const {
    return system_entropy_;
}

void SystemState::setFreeEnergy(double fe) {
    free_energy_ = fe;
}

double SystemState::getFreeEnergy() const {
    return free_energy_;
}

bool SystemState::isChaosCritical() const {
    return system_entropy_ >= chaos_threshold_;
}

void SystemState::setActiveTelemetryNode(const std::string& id) {
    active_telemetry_node_ = id;
}

std::string SystemState::getActiveTelemetryNode() const {
    return active_telemetry_node_;
}

TopologySnapshot SystemState::captureSnapshot() const {
    TopologySnapshot snap;
    snap.active_telemetry_node = active_telemetry_node_;
    snap.system_entropy = system_entropy_;
    snap.free_energy = free_energy_;
    snap.chaos_detected = isChaosCritical();
    snap.timestamp = std::chrono::system_clock::now();

    for (const auto& [name, node] : nodes_) {
        if (node.health == NodeHealth::ONLINE || node.health == NodeHealth::RECOVERED) {
            snap.active_nodes.push_back(name);
        }
    }
    return snap;
}

} // namespace kam::core
