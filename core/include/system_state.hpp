#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <chrono>

namespace kam::core {

enum class NodeHealth {
    ONLINE,
    DEGRADED,
    CRITICAL,
    OFFLINE,
    RECOVERED
};

struct HardwareNode {
    std::string id;             // örn: "UART-2", "SDR-PRIMARY", "CAM-FRONT"
    std::string subsystem_type; // örn: "TELEMETRY", "RADIO", "VISION"
    NodeHealth health = NodeHealth::ONLINE;
    int file_descriptor = -1;
    double packet_drop_rate = 0.0;
    double temperature_celsius = 45.0;
    bool is_primary = true;
};

struct TopologySnapshot {
    std::string active_telemetry_node;
    std::vector<std::string> active_nodes;
    double system_entropy = 0.03;      // 0.03 = %3
    double free_energy = 0.12;
    bool chaos_detected = false;
    std::chrono::system_clock::time_point timestamp;
};

class SystemState {
public:
    SystemState();

    void registerNode(const HardwareNode& node);
    void updateNodeHealth(const std::string& id, NodeHealth health, double drop_rate = 0.0);
    HardwareNode* getNode(const std::string& id);
    const std::unordered_map<std::string, HardwareNode>& getAllNodes() const;

    void setEntropy(double entropy);
    double getEntropy() const;

    void setFreeEnergy(double fe);
    double getFreeEnergy() const;

    bool isChaosCritical() const;

    void setActiveTelemetryNode(const std::string& id);
    std::string getActiveTelemetryNode() const;

    TopologySnapshot captureSnapshot() const;

private:
    std::unordered_map<std::string, HardwareNode> nodes_;
    std::string active_telemetry_node_;
    double system_entropy_ = 0.03;
    double free_energy_ = 0.12;
    const double chaos_threshold_ = 0.80; // %80 kritik eşik
};

} // namespace kam::core
