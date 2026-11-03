#pragma once

#include <string>
#include <vector>
#include <functional>
#include <memory>
#include "../../core/include/system_state.hpp"

namespace kam::ros2 {

enum class QosPolicy {
    RELIABLE,
    BEST_EFFORT,
    TRANSIENT_LOCAL,
    SENSOR_DATA
};

struct Ros2TopicMapping {
    std::string original_topic;
    std::string remapped_topic;
    QosPolicy qos;
    bool is_active;
};

class KamRos2Bridge {
public:
    KamRos2Bridge(const std::string& node_name = "kam_autonomous_sentinel");
    ~KamRos2Bridge();

    // ROS2 Düğümünü başlat
    bool initNode();

    // Dinamik Topic Remapping (Örn: /telemetry/uart -> /telemetry/sdr)
    bool remapTopic(const std::string& from_topic, const std::string& to_topic, QosPolicy qos);

    // Aktif eşlemeleri listele
    std::vector<Ros2TopicMapping> getActiveMappings() const;

    // Telemetri mesajını DDS veri yoluna gönder
    bool publishTelemetrySnapshot(const core::TopologySnapshot& snapshot);

    // Kriz anında ROS2 Failsafe yerine dinamik canlı topolojiye geç
    void triggerEmergencyRemap();

private:
    std::string node_name_;
    bool is_initialized_ = false;
    std::vector<Ros2TopicMapping> mappings_;
};

} // namespace kam::ros2
