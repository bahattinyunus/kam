import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from kam.active_inference import ActiveInferenceEngine
from kam.code_mutator import CodeMutator
from kam.mcp_server import McpServer
from kam.engine import KamEngine

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

if __name__ == "__main__":
    unittest.main()
