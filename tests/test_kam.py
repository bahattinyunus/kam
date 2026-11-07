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
from kam.knowledge_engine import LocalKnowledgeEngine
from kam.edge_optimizer import (
    EdgeHardwareBudget,
    EdgeModelOptimizer,
    TernaryBitNetQuantizer,
    ImatrixCalibrator,
    SpeculativeDecoder,
)
from kam.tactical_planner import TacticalRoutePlanner3D
from kam.lyapunov_controller import LyapunovCognitiveController
from kam.cognitive_council import CognitiveCouncilRouter

class TestKam(unittest.TestCase):
    def test_active_inference_normal_and_anomaly(self):
        engine = ActiveInferenceEngine()
        self.assertAlmostEqual(engine.entropy, 0.03, places=2)
        fe = engine.compute_free_energy()
        self.assertGreaterEqual(fe, 0.0)

        # Nominal durumda optimal politika NOMINAL_UART_MONITOR olmalı
        nominal_plan = engine.select_optimal_policy()
        self.assertEqual(nominal_plan["optimal_policy"], "NOMINAL_UART_MONITOR")

        # Anomali enjeksiyonu
        chaos = engine.trigger_anomaly()
        self.assertGreaterEqual(chaos, 0.80)

        # Kriz durumunda EFE (Beklenen Serbest Enerji) politikası seçimi
        crisis_plan = engine.select_optimal_policy(crisis_hint="SDR")
        self.assertEqual(crisis_plan["optimal_policy"], "SDR_868MHZ_FHSS_REROUTE")
        self.assertEqual(crisis_plan["recommended_cpp_module"], "sdr_fallback_node.cpp")
        self.assertGreater(crisis_plan["optimal_probability"], 0.25)

        # İyileşme
        engine.reset_equilibrium(0.15)
        self.assertAlmostEqual(engine.entropy, 0.15, places=2)

    def test_code_mutator(self):
        sdr_code = CodeMutator.generate_sdr_fallback()
        self.assertIn("sdr_fallback_node.cpp", sdr_code)
        self.assertIn("kam_entrypoint", sdr_code)
        self.assertTrue(CodeMutator.validate_ast(sdr_code)["valid"])

        thermal_code = CodeMutator.generate_thermal_fallback()
        self.assertIn("thermal_vision_fallback.cpp", thermal_code)
        self.assertTrue(CodeMutator.validate_ast(thermal_code)["valid"])

        ew_code = CodeMutator.generate_ew_fhss_fallback()
        self.assertIn("ew_fhss_hopper.cpp", ew_code)
        self.assertTrue(CodeMutator.validate_ast(ew_code)["valid"])

        can_code = CodeMutator.generate_can_firewall_fallback()
        self.assertIn("can_firewall_filter.cpp", can_code)
        self.assertTrue(CodeMutator.validate_ast(can_code)["valid"])

        gnss_code = CodeMutator.generate_gnss_spoof_fallback()
        self.assertIn("gnss_optical_flow_ekf.cpp", gnss_code)
        self.assertTrue(CodeMutator.validate_ast(gnss_code)["valid"])

        swarm_code = CodeMutator.generate_swarm_handover_fallback()
        self.assertIn("swarm_raft_leader_handover.cpp", swarm_code)
        self.assertTrue(CodeMutator.validate_ast(swarm_code)["valid"])

    def test_code_mutator_ast_sandbox(self):
        unsafe_code = 'extern "C" int kam_entrypoint() { system("rm -rf /"); return 0; }'
        res = CodeMutator.validate_ast(unsafe_code)
        self.assertFalse(res["valid"])
        self.assertGreater(len(res["violations"]), 0)

    def test_mcp_server(self):
        mcp = McpServer()
        tools = mcp.list_tools()
        self.assertIn("tools", tools)
        tool_names = [t["name"] for t in tools["tools"]]
        self.assertIn("read_telemetry", tool_names)
        self.assertIn("calculate_entropy", tool_names)
        self.assertIn("compile_module", tool_names)
        self.assertIn("deploy_topology", tool_names)
        self.assertIn("inspect_kernel", tool_names)
        self.assertIn("evaluate_efe_policies", tool_names)
        self.assertIn("optimize_edge_deployment", tool_names)

        # Tool execution test
        res = mcp.call_tool("read_telemetry", {})
        self.assertEqual(res["active_telemetry"], "UART-2")

        # AST Sandbox rejection in compile_module
        bad_compile = mcp.call_tool(
            "compile_module",
            {"module_name": "evil", "cpp_source": 'int main() { system("rm -rf /"); }'},
        )
        self.assertEqual(bad_compile["status"], "rejected_by_ast_sandbox")

        # JSON-RPC 2.0 protocol test
        rpc_init = mcp.handle_jsonrpc({"jsonrpc": "2.0", "id": 10, "method": "initialize"})
        self.assertEqual(rpc_init["id"], 10)
        self.assertIn("protocolVersion", rpc_init["result"])

        rpc_call = mcp.handle_jsonrpc({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "inspect_kernel", "arguments": {}},
        })
        self.assertEqual(rpc_call["result"]["ringbuffer_capacity"], 1024)

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
        self.assertLess(ekf.last_mahalanobis_distance, 5.0)

        # GPS Spoofing Sıçraması (100 metre aniden kayma)
        spoof_ok = ekf.update_gps(250.0, 0.0, 100.0)
        self.assertFalse(spoof_ok)
        self.assertTrue(ekf.dead_reckoning)
        self.assertEqual(ekf.spoofing_events_detected, 1)

        # Optik akış ve barometre ile ölü-hesaplama (Dead-Reckoning) güncellemesi
        state = ekf.update_optical_flow(vx_flow=16.2, vy_flow=0.4, baro_alt_z=100.5, dt=0.1)
        self.assertTrue(state.dead_reckoning)
        self.assertGreater(state.x, 1.5)

    def test_swarm_mesh_consensus(self):
        swarm = SwarmMeshController()
        self.assertEqual(swarm.active_leader, "Alpha-1")

        hops = swarm.generate_fhss_hop_sequence(num_hops=6, base_freq_mhz=868.0, bandwidth_mhz=2.0)
        self.assertEqual(len(hops), 6)
        self.assertTrue(all(868.0 <= f <= 870.0 for f in hops))

        new_leader = swarm.simulate_leader_loss()
        self.assertNotEqual(new_leader, "Alpha-1")
        self.assertEqual(new_leader, "Bravo-2")
        self.assertTrue(swarm.drones[new_leader].is_leader)
        telemetry = swarm.get_swarm_telemetry()
        self.assertEqual(telemetry["alive_units"], 3)

    def test_liquid_foundation_model_inference_and_routing(self):
        model = KamLiquidFoundationModel()
        sensory = [0.1, 0.2, 0.8, 0.05] * 4
        out = model.forward(sensory)

        self.assertIn("model", out)
        self.assertEqual(out["ode_solver"], "RK4")
        self.assertEqual(out["shared_expert"], "TURKISH_SOVEREIGN_REASONING_SHARED_EXPERT")
        self.assertEqual(len(out["active_experts"]), 2)
        self.assertGreater(out["free_energy_nats"], 0.0)
        self.assertGreaterEqual(out["moe_aux_balance_loss"], 0.0)
        self.assertIn("selected_optimal_action", out)

    def test_active_inference_trainer(self):
        trainer = ActiveInferenceTrainer()
        history = trainer.run_training_cycle(steps=2)
        self.assertEqual(len(history), 2)
        self.assertIn("mean_free_energy", history[0])

    def test_local_knowledge_engine(self):
        ke = LocalKnowledgeEngine()
        ans = ke.query("tr nin başkentii neresi")
        self.assertIsNotNone(ans)
        self.assertIn("Ankara", ans)

        ans_paris = ke.query("Fransa başkenti")
        self.assertIsNotNone(ans_paris)
        self.assertIn("Paris", ans_paris)

    def test_kam_master_knowledge(self):
        ke = LocalKnowledgeEngine()
        ans = ke.query("karl friston serbest enerji")
        self.assertIsNotNone(ans)
        self.assertIn("Friston", ans)

        ans_ebpf = ke.query("ebpf kancasi ne ise yarar")
        self.assertIsNotNone(ans_ebpf)
        self.assertIn("eBPF", ans_ebpf)

    def test_edge_model_optimizer(self):
        opt = EdgeModelOptimizer()

        # Tier-1 Ultra Kisitli Donanim (1.5 GB RAM, 8W TDP)
        tier1 = opt.plan_optimal_deployment(EdgeHardwareBudget(ram_mb=1536, tdp_watts=8.0, npu_temp_c=60.0))
        self.assertEqual(tier1.model_id, "kam:1.5b")
        self.assertLessEqual(tier1.estimated_vram_mb, 1536)

        # Tier-2 Taktik Uc Donanim (4 GB RAM, 18W TDP)
        tier2 = opt.plan_optimal_deployment(EdgeHardwareBudget(ram_mb=4096, tdp_watts=18.0, npu_temp_c=65.0))
        self.assertEqual(tier2.model_id, "kam:edge-3b-moe")
        self.assertAlmostEqual(tier2.active_params_billions, 0.75, places=2)

        # Tier-3 Komuta Donanimi (8 GB RAM, 35W TDP) + Speculative Decoding
        tier3 = opt.plan_optimal_deployment(EdgeHardwareBudget(ram_mb=8192, tdp_watts=35.0, npu_temp_c=70.0))
        self.assertEqual(tier3.model_id, "kam:7b")
        self.assertEqual(tier3.speculative_draft_model, "kam:1.5b")

        # Termal koruma altinda 4-bit KV-Cache aktivasyonu
        throttled = opt.plan_optimal_deployment(EdgeHardwareBudget(ram_mb=4096, tdp_watts=18.0, npu_temp_c=90.0))
        self.assertEqual(throttled.kv_cache_bits, 4)

        # GRPO Aktif Cikarim Odul Fonksiyonu
        valid_cpp = CodeMutator.generate_sdr_fallback()
        reward_good = opt.compute_grpo_reward(
            response_text="Karl Friston Serbest Enerji Ilkesi geregince SDR yedek dugumu sentezlendi.",
            cpp_code=valid_cpp,
            free_energy=0.08,
        )
        reward_bad = opt.compute_grpo_reward(
            response_text="Sistem hatasi 中文字",
            cpp_code='extern "C" int kam_entrypoint() { system("rm -rf /"); }',
            free_energy=0.92,
        )
        self.assertGreater(reward_good["total_reward"], reward_bad["total_reward"])
        self.assertFalse(reward_good["foreign_leak_detected"])
        self.assertTrue(reward_bad["foreign_leak_detected"])

    def test_bitnet_imatrix_and_speculative_decoding(self):
        # 1. BitNet b1.58 Ternary Quantization
        weights = [0.45, -0.42, 0.01, 0.52, -0.48, -0.02, 0.39, -0.41]
        q_res = TernaryBitNetQuantizer.quantize_tensor(weights)
        self.assertEqual(len(q_res["ternary_weights"]), len(weights))
        self.assertTrue(all(w in (-1, 0, 1) for w in q_res["ternary_weights"]))
        self.assertGreater(q_res["compression_ratio_vs_fp16"], 10.0)
        self.assertEqual(q_res["energy_saving_factor"], 4.6)

        # 2. Hessian imatrix Calibration
        profile = ImatrixCalibrator.compute_layer_importance(
            layer_activations={
                "blk.0.moe_router": [1.2, -1.1, 0.9, 1.4],
                "blk.3.ffn_mid": [0.1, -0.1, 0.05, 0.08],
                "output.weight": [0.8, 0.9, -0.7, 0.85],
            },
            layer_weight_norms={"blk.0.moe_router": 2.5, "blk.3.ffn_mid": 0.8, "output.weight": 2.2},
        )
        self.assertEqual(profile["blk.0.moe_router"]["assigned_quantization"], "Q6_K")
        self.assertEqual(profile["output.weight"]["assigned_quantization"], "Q6_K")
        self.assertEqual(profile["blk.3.ffn_mid"]["assigned_quantization"], "IQ3_M")

        # 3. Self-Speculative Decoding (kam:1.5b -> kam:7b)
        spec_dec = SpeculativeDecoder()
        step_res = spec_dec.verify_draft_step(
            draft_tokens=["constexpr", "uint32_t", "freq", "=", "868000000"],
            draft_probs_q=[0.90, 0.85, 0.88, 0.95, 0.91],
            target_probs_p=[0.92, 0.89, 0.90, 0.96, 0.93],
        )
        self.assertEqual(step_res["num_generated_single_pass"], 6)
        self.assertEqual(step_res["acceptance_rate"], 1.0)
        self.assertGreater(step_res["speedup_factor"], 2.0)

    def test_tactical_3d_route_planner_and_mcp(self):
        planner = TacticalRoutePlanner3D()
        res = planner.plan_stealth_trajectory(
            start_xyz=(0.0, 0.0, 620.0),
            target_xyz=(50.0, 0.0, 580.0),
            num_segments=10,
        )
        self.assertEqual(res["planner"], "KAM-3D-EFE-Stealth-Navigator")
        self.assertEqual(len(res["waypoints"]), 11)
        self.assertGreater(res["mission_survival_probability_pct"], 75.0)
        self.assertLess(res["max_radar_exposure_risk"], 0.5)

        mcp = McpServer()
        mcp_route = mcp.call_tool("plan_tactical_3d_route", {"target_x_km": 45.0, "num_segments": 8})
        self.assertEqual(len(mcp_route["waypoints"]), 9)

    def test_lyapunov_stability_and_cognitive_council(self):
        clf = LyapunovCognitiveController()
        # 1. Kararlı (azalan hata ve düşük serbest enerji) adım
        r1 = clf.evaluate_stability_step([0.05, 0.02, 0.01, 0.01, 0.0, 0.0], free_energy=0.04)
        self.assertTrue(r1.is_asymptotically_stable)
        self.assertEqual(r1.recommended_damping_action, "ATTRACTOR_EQUILIBRIUM_HOLD")

        # 2. Kaotik sıçrama -> Sontag CLF sönümleme kazancı devreye girmeli
        r2 = clf.evaluate_stability_step([1.8, -1.5, 2.1, 0.9, -0.8, 1.2], free_energy=1.65)
        self.assertFalse(r2.is_asymptotically_stable)
        self.assertGreater(r2.stabilizing_control_gain, 0.0)
        self.assertEqual(r2.recommended_damping_action, "CLF_EMERGENCY_ENTROPY_DAMPING_JIT")

        # 3. 2. Dereceden Taylor Faz Uzayı Kriz Öngörüsü (TTA)
        tta = clf.forecast_time_to_anomaly([62.0, 68.0, 75.0, 83.0], critical_threshold=85.0, sample_dt_sec=1.0)
        self.assertIsNotNone(tta["estimated_tta_sec"])
        self.assertLess(tta["estimated_tta_sec"], 1.0)
        self.assertTrue(tta["preemptive_alert"])

        # 4. 5-Modelli Bilişsel Kurul Yönlendiricisi (kam:coder, kam:r1, kam:r1-nano, kam:1.5b, kam:7b)
        c_code = CognitiveCouncilRouter.select_specialist_model("C++20 JIT ve eBPF kancası yaz")
        self.assertEqual(c_code["selected_model"], "kam:coder")

        c_math = CognitiveCouncilRouter.select_specialist_model("Karl Friston serbest enerji denklemini ispatla")
        self.assertEqual(c_math["selected_model"], "kam:r1")

        c_nano = CognitiveCouncilRouter.select_specialist_model("Lyapunov denklemini hesapla", ram_mb=1536, npu_temp_c=88.0)
        self.assertEqual(c_nano["selected_model"], "kam:r1-nano")

        c_edge = CognitiveCouncilRouter.select_specialist_model("Durum raporu ver", ram_mb=1536, npu_temp_c=88.0)
        self.assertEqual(c_edge["selected_model"], "kam:1.5b")

        c_main = CognitiveCouncilRouter.select_specialist_model("Dede Korkut töresi ve dirlik nedir?")
        self.assertEqual(c_main["selected_model"], "kam:7b")

        council = CognitiveCouncilRouter()
        verdict = council.synthesize_council_verdict(crisis_hint="THERMAL")
        self.assertEqual(verdict["council_status"], "UNANIMOUS_SOVEREIGN_INTERVENTION")
        self.assertTrue(verdict["demirci_jit_synthesis"]["ast_verified"])

if __name__ == "__main__":
    unittest.main()
