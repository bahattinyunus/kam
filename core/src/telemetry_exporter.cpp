#include "telemetry_exporter.hpp"

namespace kam::core {

std::string TelemetryExporter::exportPrometheusMetrics(const SystemState& state) {
    std::stringstream ss;
    ss << "# HELP kam_entropy Karl Friston aktif cikarim kaos yuzdesi\n";
    ss << "# TYPE kam_entropy gauge\n";
    ss << "kam_entropy " << state.getEntropy() << "\n\n";

    ss << "# HELP kam_free_energy Varyasyonel serbest enerji puani\n";
    ss << "# TYPE kam_free_energy gauge\n";
    ss << "kam_free_energy " << state.getFreeEnergy() << "\n\n";

    ss << "# HELP kam_chaos_critical Kaos kritik esik durumu (0 veya 1)\n";
    ss << "# TYPE kam_chaos_critical gauge\n";
    ss << "kam_chaos_critical " << (state.isChaosCritical() ? 1 : 0) << "\n\n";

    ss << "# HELP kam_active_nodes_total Aktif calisan donanim dugum sayisi\n";
    ss << "# TYPE kam_active_nodes_total gauge\n";
    ss << "kam_active_nodes_total " << state.getAllNodes().size() << "\n";

    return ss.str();
}

std::string TelemetryExporter::exportJsonSnapshot(const SystemState& state) {
    auto snap = state.captureSnapshot();
    std::stringstream ss;
    ss << "{"
       << "\"active_telemetry\":\"" << snap.active_telemetry_node << "\","
       << "\"entropy\":" << snap.system_entropy << ","
       << "\"free_energy\":" << snap.free_energy << ","
       << "\"chaos_critical\":" << (snap.chaos_detected ? "true" : "false") << ","
       << "\"active_nodes_count\":" << snap.active_nodes.size()
       << "}";
    return ss.str();
}

} // namespace kam::core
