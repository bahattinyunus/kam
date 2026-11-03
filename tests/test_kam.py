import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from kam.active_inference import ActiveInferenceEngine
from kam.code_mutator import CodeMutator
from kam.mcp_server import McpServer
from kam.engine import KamEngine
from kam.tui import render_bar
from kam.hardware_bus import HardwareBusSimulator, CanMessage
from kam.model_benchmark import ModelBenchmark
from kam.sensor_fusion import SensorFusionEKF
from kam.swarm_mesh import SwarmMeshController
from kam.models.liquid_moe import KamLiquidFoundationModel
from kam.models.trainer import ActiveInferenceTrainer

class TestKam(unittest.TestCase):
    def test_active_inference_normal_and_anomaly(self):
        engine = ActiveInferenceEngine()
        self.assertAlmostEqual(engine.entropy, 0.03, places=2)
        fe = engine.compute_free_energy()
        self.assertGreaterEqual(fe, 0.0)

        # Anomali enjeksiyonu
        chaos = engine.trigger_anomaly()
        self.assertGreaterEqual(chaos, 0.80)

        # İyileşme
        engine.reset_equilibrium(0.15)
        self.assertAlmostEqual(engine.entropy, 0.15, places=2)

    def test_code_mutator(self):
        sdr_code = CodeMutator.generate_sdr_fallback()
        self.assertIn("sdr_fallback_node.cpp", sdr_code)
        self.assertIn("kam_entrypoint", sdr_code)

        thermal_code = CodeMutator.generate_thermal_fallback()
        self.assertIn("thermal_vision_fallback.cpp", thermal_code)

    def test_mcp_server(self):
        mcp = McpServer()
        tools = mcp.list_tools()
        self.assertIn("tools", tools)
        tool_names = [t["name"] for t in tools["tools"]]
        self.assertIn("read_telemetry", tool_names)
        self.assertIn("calculate_entropy", tool_names)
        self.assertIn("compile_module", tool_names)
        self.assertIn("deploy_topology", tool_names)

        # Tool execution test
        res = mcp.call_tool("read_telemetry", {})
        self.assertEqual(res["active_telemetry"], "UART-2")

        res_deploy = mcp.call_tool("deploy_topology", {"module_name": "sdr_fallback_node"})
        self.assertEqual(res_deploy["status"], "deployed")
        self.assertEqual(res_deploy["active_channel"], "SDR-YEDEK")

    def test_engine_flow(self):
        engine = KamEngine()
        engine.awaken()
        self.assertTrue(engine.running)
        self.assertEqual(engine.active_telemetry, "UART-2")

    def test_tui_render_bar(self):
        bar_green = render_bar(0.05)
        self.assertIn("5%", bar_green)
        bar_red = render_bar(0.89)
        self.assertIn("89%", bar_red)

    def test_hardware_bus_simulator(self):
        bus = HardwareBusSimulator()
        valid_msg = CanMessage(can_id=0x100, payload=b"\x01\x02\x03\x04")
        self.assertTrue(bus.is_can_packet_valid(valid_msg))

        spoofed_msg = CanMessage(can_id=0x1BA, payload=b"\xFF\xFF")
        self.assertFalse(bus.is_can_packet_valid(spoofed_msg))
        self.assertEqual(bus.filtered_spoofed_packets, 1)

    def test_model_benchmark_data(self):
        benchmarks = ModelBenchmark.get_benchmarks()
        self.assertIn("INT8", benchmarks)
        self.assertIn("INT4-AWQ", benchmarks)
        self.assertGreater(benchmarks["INT4-AWQ"].tokens_per_second, benchmarks["INT8"].tokens_per_second)

    def test_sensor_fusion_ekf_and_spoofing(self):
        ekf = SensorFusionEKF()
        ekf.predict(dt=0.1, ax=1.0)
        self.assertGreater(ekf.vx, 15.0)

        # Normal GPS güncellemesi
        ok = ekf.update_gps(1.5, 0.0, 100.0)
        self.assertTrue(ok)
        self.assertFalse(ekf.dead_reckoning)

        # GPS Spoofing Sıçraması (100 metre aniden kayma)
        spoof_ok = ekf.update_gps(250.0, 0.0, 100.0)
        self.assertFalse(spoof_ok)
        self.assertTrue(ekf.dead_reckoning)

    def test_swarm_mesh_consensus(self):
        swarm = SwarmMeshController()
        self.assertEqual(swarm.active_leader, "Alpha-1")

        new_leader = swarm.simulate_leader_loss()
        self.assertNotEqual(new_leader, "Alpha-1")
        self.assertTrue(swarm.drones[new_leader].is_leader)

    def test_liquid_foundation_model_inference_and_routing(self):
        model = KamLiquidFoundationModel()
        sensory = [0.1, 0.2, 0.8, 0.05] * 4
        out = model.forward(sensory)

        self.assertIn("model", out)
        self.assertEqual(len(out["active_experts"]), 2)
        self.assertGreater(out["free_energy_nats"], 0.0)
        self.assertIn("selected_optimal_action", out)

    def test_active_inference_trainer(self):
        trainer = ActiveInferenceTrainer()
        history = trainer.run_training_cycle(steps=2)
        self.assertEqual(len(history), 2)
        self.assertIn("mean_free_energy", history[0])

if __name__ == "__main__":
    unittest.main()
