#include "kam_ros2_node.hpp"
#include "../../core/include/logger.hpp"
#include <iostream>

namespace kam::ros2 {

KamRos2Bridge::KamRos2Bridge(const std::string& node_name)
    : node_name_(node_name) {
    mappings_.push_back({"/uav/telemetry/uart", "/uav/telemetry/active", QosPolicy::RELIABLE, true});
    mappings_.push_back({"/uav/vision/compressed", "/uav/vision/active", QosPolicy::SENSOR_DATA, true});
}

KamRos2Bridge::~KamRos2Bridge() = default;

bool KamRos2Bridge::initNode() {
    is_initialized_ = true;
    core::Logger::instance().info(core::Subsystem::CORE, 
        "ROS2 / DDS Bilişsel Köprü (" + node_name_ + ") başlatıldı. Dinamik QoS devrede.");
    return true;
}

bool KamRos2Bridge::remapTopic(const std::string& from_topic, const std::string& to_topic, QosPolicy qos) {
    for (auto& m : mappings_) {
        if (m.original_topic == from_topic) {
            m.remapped_topic = to_topic;
            m.qos = qos;
            m.is_active = true;
            core::Logger::instance().info(core::Subsystem::CORE, 
                "ROS2 Konu Yeniden Yönlendirildi: " + from_topic + " -> " + to_topic);
            return true;
        }
    }
    mappings_.push_back({from_topic, to_topic, qos, true});
    return true;
}

std::vector<Ros2TopicMapping> KamRos2Bridge::getActiveMappings() const {
    return mappings_;
}

bool KamRos2Bridge::publishTelemetrySnapshot(const core::TopologySnapshot& snapshot) {
    (void)snapshot;
    // DDS Middleware / rmw_fastrtps yayını simülasyonu
    return true;
}

void KamRos2Bridge::triggerEmergencyRemap() {
    core::Logger::instance().warn(core::Subsystem::NERVOUS_SYS, 
        "ROS2 Acil Durum: Klasik Failsafe kilitlendi. Canlı telemetri rotası /uav/telemetry/sdr hattına aktarılıyor.");
    remapTopic("/uav/telemetry/uart", "/uav/telemetry/sdr", QosPolicy::BEST_EFFORT);
}

} // namespace kam::ros2
