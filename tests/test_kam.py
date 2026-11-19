import unittest
import sys
import os
import json

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
from kam.ew_cognitive_radar import PulseDescriptorWord, CognitiveEwEmitterClassifier
from kam.intent_c2_orchestrator import IntentToTaskOrchestrator
from kam.neuro_symbolic_shield import FlightControlCommand, NeuroSymbolicSafetyShield
from kam.byzantine_pqc_swarm import SwarmNodeBelief, ByzantinePqcSwarmGuard
from kam.terrain_matching_trn import TerrainRelativeNavigator
from kam.actuator_reconfigurator import ActuatorFaultReconfigurator
from kam.covert_fso_comm import FsoLinkParameters, CovertFsoLaserTransceiver
from kam.radiation_ecc_scrubber import RadiationHardenedMemoryScrubber
from kam.differential_game_evasion import MissileEngagementState, DifferentialGameMissileEvasion
from kam.autonomous_agent import KamAutonomousAgent, HostSafetyShield

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

        cbf_code = CodeMutator.generate_cbf_safety_shield_fallback()
        self.assertIn("cbf_safety_shield.cpp", cbf_code)
        self.assertTrue(CodeMutator.validate_ast(cbf_code)["valid"])

        ew_drfm_code = CodeMutator.generate_ew_drfm_fallback()
        self.assertIn("ew_drfm_responder.cpp", ew_drfm_code)
        self.assertTrue(CodeMutator.validate_ast(ew_drfm_code)["valid"])

        c2_dag_code = CodeMutator.generate_c2_dag_fallback()
        self.assertIn("c2_task_executor.cpp", c2_dag_code)
        self.assertTrue(CodeMutator.validate_ast(c2_dag_code)["valid"])

        bft_pqc_code = CodeMutator.generate_byzantine_pqc_fallback()
        self.assertIn("byzantine_pqc_guard.cpp", bft_pqc_code)
        self.assertTrue(CodeMutator.validate_ast(bft_pqc_code)["valid"])

        trn_code = CodeMutator.generate_trn_terrain_lock_fallback()
        self.assertIn("trn_tercom_navigator.cpp", trn_code)
        self.assertTrue(CodeMutator.validate_ast(trn_code)["valid"])

        act_code = CodeMutator.generate_actuator_reconfig_fallback()
        self.assertIn("actuator_mixer_reconfig.cpp", act_code)
        self.assertTrue(CodeMutator.validate_ast(act_code)["valid"])

        fso_code = CodeMutator.generate_fso_laser_mesh_fallback()
        self.assertIn("fso_laser_mesh_link.cpp", fso_code)
        self.assertTrue(CodeMutator.validate_ast(fso_code)["valid"])

        ecc_code = CodeMutator.generate_radiation_tmr_scrubber_fallback()
        self.assertIn("radiation_tmr_scrubber.cpp", ecc_code)
        self.assertTrue(CodeMutator.validate_ast(ecc_code)["valid"])

        hji_code = CodeMutator.generate_hji_missile_evasion_fallback()
        self.assertIn("hji_evasion_maneuver.cpp", hji_code)
        self.assertTrue(CodeMutator.validate_ast(hji_code)["valid"])

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

    def test_competitor_surpassing_modules_ew_c2_ansr_rgm(self):
        # 1. Helsing Cirra üstü Bilişsel EW Radar PDW Sınıflandırıcı & Şekil Değiştiren LPI Öğrenimi
        ew = CognitiveEwEmitterClassifier()
        known_s400 = ew.classify_pdw_burst(
            PulseDescriptorWord(rf_ghz=9.2, pri_us=420.0, pw_us=1.8, aoa_deg=32.0, chirp_bw_mhz=45.0, agility_score=0.1)
        )
        self.assertEqual(known_s400["classified_emitter"], "S400_92N6E_GRAVE_STONE")
        self.assertFalse(known_s400["is_novel_shapeshifting_emitter"])

        novel_agile = ew.classify_pdw_burst(
            PulseDescriptorWord(rf_ghz=17.4, pri_us=610.0, pw_us=0.25, aoa_deg=118.0, chirp_bw_mhz=240.0, agility_score=0.92)
        )
        self.assertTrue(novel_agile["is_novel_shapeshifting_emitter"])
        self.assertIn("AGILE_SDR_THREAT", novel_agile["classified_emitter"])
        self.assertEqual(novel_agile["online_learned_emitter_count"], 1)

        # 2. Anduril Lattice & A-GRA üstü Intent-to-Task EFE Filo Orkestratörü
        orch = IntentToTaskOrchestrator()
        plan = orch.decompose_and_allocate("Sektör-4 S-400 bataryasını körelt ve vadi taarruzu icra et")
        self.assertEqual(plan["total_tasks_generated"], 4)
        self.assertEqual(plan["unique_assets_mobilized"], 4)
        assigned_ids = [t["assigned_asset"] for t in plan["task_dag_allocations"]]
        self.assertIn("Sungur-EW-1", assigned_ids)
        self.assertIn("Kizilelma-Strike-2", assigned_ids)

        # 3. DARPA ANSR & Kontrol Bariyer Fonksiyonu (CBF) Nöro-Sembolik Kalkan
        unsafe_cmd = FlightControlCommand(
            target_altitude_agl_m=8.0,   # < 30m ihlali
            airspeed_mps=14.0,           # < 22 m/s stall ihlali
            bank_angle_deg=72.0,         # > 55 deg yatış ihlali
            battery_pct=12.0,            # < 18% RTL batarya ihlali
        )
        shield_res = NeuroSymbolicSafetyShield.verify_and_project(unsafe_cmd)
        self.assertTrue(shield_res["intervention_occurred"])
        self.assertTrue(shield_res["rtl_override_active"])
        self.assertEqual(len(shield_res["symbolic_violations_prevented"]), 4)
        self.assertGreaterEqual(shield_res["safe_command"]["target_altitude_agl_m"], 30.0)
        self.assertGreaterEqual(shield_res["safe_command"]["airspeed_mps"], 22.0)

        # 4. VERSES AI AXIOM / RGM üstü Hiyerarşik Serbest Enerji ve Çevrimiçi Dirichlet Öğrenimi
        engine = ActiveInferenceEngine()
        updated_prior = engine.adapt_dirichlet_likelihood([3.0, 0.5, 0.2, 0.1])
        self.assertAlmostEqual(sum(updated_prior), 1.0, places=5)
        rgm = engine.compute_hierarchical_rgm_free_energy([0.92, 0.05, 0.02, 0.01], [0.90, 0.06, 0.03, 0.01])
        self.assertIn("f_hierarchical_rgm", rgm)
        self.assertGreaterEqual(rgm["f_hierarchical_rgm"], 0.0)

    def test_cli_advanced_flags_and_fleet(self):
        import subprocess
        # Test cli.py with --fleet
        res = subprocess.run([sys.executable, "cli.py", "--fleet"], capture_output=True, text=True, check=True)
        fleet = json.loads(res.stdout)
        self.assertEqual(fleet["total_models"], 8)
        self.assertTrue(any(m["key"] == "kam:apex" for m in fleet["models"]))

        # Test cli.py with --ew
        res_ew = subprocess.run([sys.executable, "cli.py", "--ew"], capture_output=True, text=True, check=True)
        ew_data = json.loads(res_ew.stdout)
        self.assertIn("known_emitter_sample", ew_data)
        self.assertIn("novel_agile_emitter_sample", ew_data)

        # Test cli.py with --shield
        res_shield = subprocess.run([sys.executable, "cli.py", "--shield"], capture_output=True, text=True, check=True)
        shield_data = json.loads(res_shield.stdout)
        self.assertTrue(shield_data["intervention_occurred"])

        # Test cli.py with --lyapunov
        res_clf = subprocess.run([sys.executable, "cli.py", "--lyapunov"], capture_output=True, text=True, check=True)
        clf_data = json.loads(res_clf.stdout)
        self.assertIn("nominal_stability", clf_data)
        self.assertIn("taylor_phase_space_tta", clf_data)

        # Test cli.py with --full-audit
        res_audit = subprocess.run([sys.executable, "cli.py", "--full-audit"], capture_output=True, text=True, check=True)
        audit_data = json.loads(res_audit.stdout)
        self.assertEqual(audit_data["total_mcp_tools"], 18)
        self.assertIn("byzantine_pqc_swarm", audit_data)
        self.assertIn("terrain_relative_nav", audit_data)
        self.assertIn("actuator_reconfiguration", audit_data)
        self.assertIn("covert_fso_laser_mesh", audit_data)
        self.assertIn("radiation_secded_tmr_scrubber", audit_data)
        self.assertIn("hji_differential_missile_evasion", audit_data)

    def test_byzantine_pqc_swarm_guard(self):
        beliefs = [
            SwarmNodeBelief("Alpha-1", [0.82, 0.10, 0.05, 0.03], pqc_nonce=101),
            SwarmNodeBelief("Bravo-2", [0.80, 0.11, 0.06, 0.03], pqc_nonce=102),
            SwarmNodeBelief("Charlie-3", [0.02, 0.04, 0.12, 0.82], pqc_nonce=103),  # Hain düğüm
            SwarmNodeBelief("Delta-4", [0.81, 0.09, 0.06, 0.04], pqc_nonce=104),
        ]
        res = ByzantinePqcSwarmGuard.filter_byzantine_and_fuse(beliefs)
        self.assertEqual(res["quarantined_byzantine_nodes"], ["Charlie-3"])
        self.assertEqual(len(res["trusted_nodes"]), 3)
        self.assertTrue(res["bft_resilience_bound_ok"])
        self.assertAlmostEqual(sum(res["fused_collective_belief"]), 1.0, places=3)

    def test_terrain_relative_navigation_trn(self):
        trn = TerrainRelativeNavigator.match_terrain_profile(
            true_x_km=24.5,
            true_y_km=-3.2,
            drifted_ins_x_km=25.25,
            drifted_ins_y_km=-2.70,
        )
        self.assertEqual(trn["rf_emission_watts"], 0.0)
        self.assertGreater(trn["drift_reduction_pct"], 95.0)
        self.assertGreater(trn["profile_ncc_score"], 0.99)
        self.assertLess(trn["residual_cep_error_m"], 10.0)

    def test_actuator_fault_reconfigurator(self):
        reconf = ActuatorFaultReconfigurator.reconfigure_control_allocation(
            desired_moments_lmn=[0.45, 0.60, -0.25],
            stuck_deflections_rad={0: 0.22},
        )
        self.assertTrue(reconf["control_authority_preserved"])
        self.assertLess(reconf["moment_tracking_error_l2"], 0.001)
        self.assertEqual(reconf["actuator_allocations"][0]["status"], "JAMMED_ISOLATED")
        self.assertEqual(reconf["actuator_allocations"][1]["status"], "ACTIVE_COMPENSATING")

    def test_covert_fso_laser_transceiver(self):
        fso = CovertFsoLaserTransceiver.evaluate_covert_fso_link(
            FsoLinkParameters(distance_km=4.5, visibility_km=12.0, pointing_jitter_urad=35.0)
        )
        self.assertEqual(fso["rf_emission_watts"], 0.0)
        self.assertEqual(fso["rf_probability_of_intercept_poi"], 0.0)
        self.assertEqual(fso["active_optical_mode"], "FSO_1550NM_SWIR_MEMS_LASER_LOCK")
        self.assertGreater(fso["effective_throughput_mbps"], 300.0)

        fog_fso = CovertFsoLaserTransceiver.evaluate_covert_fso_link(
            FsoLinkParameters(distance_km=4.5, visibility_km=0.4, pointing_jitter_urad=35.0)
        )
        self.assertEqual(fog_fso["active_optical_mode"], "HYBRID_SWIR_PULSE_ACOUSTIC_FALLBACK")

    def test_radiation_hardened_memory_scrubber(self):
        # 1. Tekil Bit Tersinmesi (SEU) ve 3-Bank TMR Ağırlık Onarımı
        scrub = RadiationHardenedMemoryScrubber.scrub_bitnet_weights_with_tmr(
            injected_seu_bit=19, inject_tmr_bank_corruption=True
        )
        self.assertTrue(scrub["secded_register_check"]["bit_exact_restored"])
        self.assertEqual(scrub["secded_register_check"]["flipped_bit_detected"], 19)
        self.assertEqual(scrub["tmr_bitnet_weight_scrub"]["tmr_majority_repairs"], 3)
        self.assertTrue(scrub["tmr_bitnet_weight_scrub"]["integrity_verified_100pct"])

        # 2. Çift Bit Tersinmesi (MBU) Tespiti
        word = 0x123456789ABCDEF0
        enc = RadiationHardenedMemoryScrubber.encode_secded_64(word)
        mbu_word = word ^ (1 << 5) ^ (1 << 29)
        mbu_res = RadiationHardenedMemoryScrubber.decode_and_repair_secded_64(mbu_word, enc["ecc8"])
        self.assertTrue(mbu_res["double_bit_fault"])
        self.assertEqual(mbu_res["status"], "MBU_DOUBLE_BIT_DETECTED_ESCALATE_TMR")

    def test_differential_game_missile_evasion(self):
        hji = DifferentialGameMissileEvasion.solve_hji_evasion_maneuver(
            MissileEngagementState(missile_range_m=2850.0, closing_velocity_mps=980.0, evader_max_g=9.0)
        )
        self.assertTrue(hji["platform_survival_guaranteed"])
        self.assertGreater(hji["hji_saddle_point_terminal_miss_m"], hji["warhead_lethal_radius_m"] * 2.5)
        self.assertLess(hji["unmaneuvered_pn_miss_m"], hji["warhead_lethal_radius_m"])
        self.assertEqual(len(hji["optimal_evasion_accel_mps2"]), 3)

    def test_autonomous_computer_agent_and_safety_shield(self):
        import tempfile
        agent = KamAutonomousAgent()
        tools = agent.list_agent_tools()
        self.assertGreaterEqual(len(tools), 12)

        # 1. Gerçek bilgisayar telemetrisi
        sys_info = agent.execute_tool("get_real_system_telemetry")
        self.assertEqual(sys_info["status"], "success")
        self.assertIn("hostname", sys_info)
        self.assertGreaterEqual(sys_info["cpu_logical_cores"], 1)

        # 2. Güvenlik kalkanı yıkıcı komutları engellemeli
        safe_ok, _ = HostSafetyShield.verify_command("git status")
        self.assertTrue(safe_ok)
        unsafe_ok, _ = HostSafetyShield.verify_command("rm -rf /")
        self.assertFalse(unsafe_ok)
        blocked_res = agent.execute_tool("run_shell_command", {"command": "Format-Volume -DriveLetter C"})
        self.assertEqual(blocked_res["status"], "blocked_by_safety_shield")

        # 3. Canlı Python kodu icrası
        py_res = agent.execute_tool("execute_python_code", {"code": "print(sum(i*i for i in range(1, 6)))"})
        self.assertEqual(py_res["status"], "success")
        self.assertEqual(py_res["stdout"], "55")

        # 4. Dosya yazma, düzenleme ve okuma
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "kam_agent_test.txt")
            w_res = agent.execute_tool("write_file", {"path": test_file, "content": "Kut ve Dirlik nöbeti."})
            self.assertEqual(w_res["status"], "success")
            e_res = agent.execute_tool("edit_file", {"path": test_file, "target": "nöbeti", "replacement": "kaimdir"})
            self.assertEqual(e_res["status"], "success")
            r_res = agent.execute_tool("read_file", {"path": test_file})
            self.assertIn("Kut ve Dirlik kaimdir.", r_res["content"])

        # 5. Doğal Türkçe emir refleks icrası, <tool_call> ve <codeact> ayrıştırma
        direct = agent.detect_and_execute_direct_intent("Bilgisayarın gerçek sistem durumunu ve RAM kullanımını denetle")
        self.assertGreaterEqual(len(direct), 1)
        self.assertEqual(direct[0]["tool"], "get_real_system_telemetry")

        # 6. Manus-AI Stateful CodeAct (oturumlar arası değişken koruma ve host.* köprüsü)
        agent.execute_tool("execute_python_code", {"code": "kam_persistent_var = 42"})
        stateful_res = agent.execute_tool("execute_python_code", {"code": "print(kam_persistent_var + int(host.sysinfo()['cpu_logical_cores'] >= 1))"})
        self.assertEqual(stateful_res["stdout"], "43")

        # 7. UFO² Sınıfı Win32 Fare Konumu ve Batarya/Güç Denetimi
        mouse_pos = agent.execute_tool("mouse_control", {"action": "position"})
        self.assertIn("screen_width", mouse_pos)
        self.assertGreater(mouse_pos["screen_width"], 0)
        bat_res = agent.execute_tool("os_hardware_control", {"action": "battery"})
        self.assertEqual(bat_res["status"], "success")

        # 8. Çok Adımlı Zincirleme Görev Planı (Mission Plan DAG)
        multi_steps = agent.detect_and_execute_direct_intent(
            "Fare konumunu, ekran çözünürlüğünü ve batarya güç durumunu göster."
        )
        self.assertGreaterEqual(len(multi_steps), 2)
        plan_card = KamAutonomousAgent.format_mission_plan_card(multi_steps)
        self.assertIn("MANUS-SINIFI OTONOM GÖREV PLANI", plan_card)

        parsed_calls = KamAutonomousAgent.extract_tool_calls(
            'İcra ediyorum:\n<tool_call>{"name": "execute_python_code", "arguments": {"code": "2+2"}}</tool_call>\n'
            '<codeact>print(host.sysinfo()["hostname"])</codeact>'
        )
        self.assertEqual(len(parsed_calls), 2)
        self.assertEqual(parsed_calls[0]["name"], "execute_python_code")
        self.assertEqual(parsed_calls[1]["name"], "execute_python_code")

        # 9. Tam Yetki Matrisi, Tüm Disk Sürücüleri ve Kalıcı Epizodik Hafıza
        perm_res = agent.execute_tool("os_hardware_control", {"action": "permissions"})
        self.assertTrue(perm_res["full_permissions_granted"])
        self.assertEqual(perm_res["permission_tier"], "SOVEREIGN_FULL_ADMIN_ACCESS")
        drives_res = agent.execute_tool("os_hardware_control", {"action": "drives"})
        self.assertEqual(drives_res["status"], "success")
        self.assertGreaterEqual(len(drives_res["drives"]), 1)

        mem_store = agent.remember_fact("Komutanın birincil hedefi tam otonom sistem hakimiyetidir.")
        self.assertEqual(mem_store["status"], "success")
        mem_recall = agent.recall_memories("hakimiyet")
        self.assertGreaterEqual(len(mem_recall["memories"]), 1)

        # 10. Kod Külliyatı Analizi, Dosya Güç İşlemleri (mkdir/zip) ve İnteraktif HTML5 Kokpit Üretimi
        cb_res = agent.execute_tool("analyze_codebase", {})
        self.assertEqual(cb_res["status"], "success")
        self.assertGreater(cb_res["total_lines_of_code"], 1000)
        self.assertGreater(cb_res["python_classes"], 10)

        with tempfile.TemporaryDirectory() as tmpdir2:
            sub_folder = os.path.join(tmpdir2, "kam_hq")
            mk_res = agent.execute_tool("file_power_ops", {"action": "mkdir", "source": sub_folder})
            self.assertEqual(mk_res["status"], "success")
            webapp_out = os.path.join(sub_folder, "cockpit.html")
            wa_res = agent.execute_tool("build_interactive_webapp", {"output_path": webapp_out, "launch": False})
            self.assertEqual(wa_res["status"], "success")
            self.assertTrue(os.path.isfile(webapp_out))
            zip_res = agent.execute_tool("file_power_ops", {"action": "zip", "source": sub_folder})
            self.assertEqual(zip_res["status"], "success")
            self.assertTrue(os.path.isfile(zip_res["archive_path"]))

    def test_extract_tool_calls_and_codeact_edge_cases(self):
        # 1. <think> içindeki hayalet araç çağrıları yoksayılmalı, belge sırası korunmalı
        sample = (
            '<think>Belki <tool_call>{"name": "run_shell_command", "arguments": {"command": "echo ghost"}}</tool_call></think>\n'
            'Adım 1:\n'
            '<TOOL_CALL id="1">\n```json\n{"name": "list_directory", "arguments": {"path": ".",},}\n```\n</TOOL_CALL>\n'
            'Adım 2:\n'
            '<CodeAct lang="python">\n```python\nprint(21 * 2)\n```\n</CodeAct>'
        )
        calls = KamAutonomousAgent.extract_tool_calls(sample)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["name"], "list_directory")
        self.assertEqual(calls[0]["arguments"], {"path": "."})
        self.assertEqual(calls[1]["name"], "execute_python_code")
        self.assertEqual(calls[1]["arguments"]["code"], "print(21 * 2)")

        # 2. Çevre metinli dengeli JSON + stringified arguments kurtarma
        noisy = (
            '<tool_call>Çağrı: {"name": "execute_python_code", '
            '"arguments": "{\\"code\\": \\"print(9)\\"}"} bitti.</tool_call>'
        )
        noisy_calls = KamAutonomousAgent.extract_tool_calls(noisy)
        self.assertEqual(len(noisy_calls), 1)
        self.assertEqual(noisy_calls[0]["name"], "execute_python_code")
        self.assertEqual(noisy_calls[0]["arguments"], {"code": "print(9)"})

        # 3. Kapatılmamış <codeact> kurtarma
        truncated = "Hemen çalıştırıyorum:\n<codeact>\nx = 10\nprint(x + 5)"
        trunc_calls = KamAutonomousAgent.extract_tool_calls(truncated)
        self.assertEqual(len(trunc_calls), 1)
        self.assertEqual(trunc_calls[0]["name"], "execute_python_code")
        self.assertIn("print(x + 5)", trunc_calls[0]["arguments"]["code"])

        # 4. include_fenced_code=True: py/python/powershell ve def bloğu dahil
        fenced = (
            "```py\ndef kare(n):\n    return n * n\nprint(kare(6))\n```\n"
            "```powershell\nGet-Date\n```"
        )
        self.assertEqual(KamAutonomousAgent.extract_tool_calls(fenced, include_fenced_code=False), [])
        fenced_calls = KamAutonomousAgent.extract_tool_calls(fenced, include_fenced_code=True)
        self.assertEqual(len(fenced_calls), 2)
        self.assertEqual(fenced_calls[0]["name"], "execute_python_code")
        self.assertIn("def kare", fenced_calls[0]["arguments"]["code"])
        self.assertEqual(fenced_calls[1]["name"], "run_shell_command")
        self.assertEqual(fenced_calls[1]["arguments"]["command"], "Get-Date")

    def test_react_multi_step_self_healing_and_loop_guard(self):
        import threading
        from unittest.mock import patch
        from kam.real_llm import UniversalLLMClient

        client = UniversalLLMClient(ollama_url="http://127.0.0.1:9")
        client.set_model("kam:apex")

        # Senaryo A: Bozuk <tool_call> öz-onarım -> geçerli <codeact> -> nihai yanıt
        steps_a = iter([
            ['<tool_call>{"name": "execute_python_code"'],  # kapatılmamış & bozuk
            ['<codeact>print(6 * 7)</codeact>'],
            ['Hesaplama tamamlandı: sonuç 42.'],
        ])
        with patch.object(client, "check_ollama_alive", return_value=True), \
             patch.object(client, "_stream_ollama_step", side_effect=lambda *a, **kw: next(steps_a)):
            out_a = "".join(client.generate_stream("Özel matematiksel test çalıştır"))
        self.assertIn("42", out_a)
        self.assertIn("Hesaplama tamamlandı", out_a)

        # Senaryo B: Python çalışma zamanı hatası -> öz-onarım -> başarılı icra
        client.conversation_history.clear()
        recorded_prompts = []
        steps_b = iter([
            ['<codeact>print(1 / 0)</codeact>'],
            ['<codeact>print(10 // 2)</codeact>'],
            ['Hata onarıldı, sonuç 5.'],
        ])

        def _fake_stream_b(url, target_model, messages, is_actionable, abort_event=None):
            recorded_prompts.append(messages[-1]["content"])
            return next(steps_b)

        with patch.object(client, "check_ollama_alive", return_value=True), \
             patch.object(client, "_stream_ollama_step", side_effect=_fake_stream_b):
            out_b = "".join(client.generate_stream("Bölme testi yap"))
        self.assertIn("Hata onarıldı, sonuç 5.", out_b)
        self.assertTrue(any("Hata tespit edildi" in p for p in recorded_prompts))

        # Senaryo C: Aynı araç+argüman tekrarında sonsuz döngü koruması + araçsız nihai sentez
        client.conversation_history.clear()
        steps_c = iter([
            ['<codeact>print("dup_guard")</codeact>'],
            ['<codeact>print("dup_guard")</codeact>'],
            ['<codeact>print("dup_guard")</codeact>'],
            ['Döngü sonlandırıldı, özet sunuldu.'],
        ])
        call_count = {"n": 0}

        def _fake_stream_c(*a, **kw):
            call_count["n"] += 1
            return next(steps_c)

        with patch.object(client, "check_ollama_alive", return_value=True), \
             patch.object(client, "_stream_ollama_step", side_effect=_fake_stream_c):
            out_c = "".join(client.generate_stream("Tekrar testi"))
        self.assertEqual(call_count["n"], 4)
        self.assertIn("Döngü sonlandırıldı", out_c)

        # Senaryo D: abort_event ile erken iptal -> conversation_history dengeli kalmalı
        client.conversation_history.clear()
        abort_ev = threading.Event()

        def _aborting_stream(*a, **kw):
            yield "Parça 1 "
            abort_ev.set()
            yield "Parça 2"

        with patch.object(client, "check_ollama_alive", return_value=True), \
             patch.object(client, "_stream_ollama_step", side_effect=_aborting_stream):
            out_d = "".join(client.generate_stream("İptal testi", abort_event=abort_ev))
        self.assertIn("Parça 1", out_d)
        # İptal edilmeden önce başlayan istek için tarihçe dengesiz (tekil user) kalmamalı
        if client.conversation_history:
            self.assertEqual(client.conversation_history[-1]["role"], "assistant")

    def test_model_selection_persistence_and_context_budget(self):
        from unittest.mock import patch, MagicMock
        from kam.real_llm import UniversalLLMClient

        # _match_model_name: kam:r1 asla kam:r1-nano:latest ile eşleşmemeli
        installed = ["kam:apex:latest", "kam:7b:latest", "kam:r1-nano:latest", "kam:coder:latest"]
        self.assertIsNone(UniversalLLMClient._match_model_name(installed, "kam:r1"))
        self.assertEqual(UniversalLLMClient._match_model_name(installed, "kam:apex"), "kam:apex:latest")
        self.assertEqual(UniversalLLMClient._match_model_name(installed, "kam:coder"), "kam:coder:latest")

        fake_tags = json.dumps({"models": [{"name": m} for m in installed]}).encode("utf-8")

        def _fake_urlopen(req, timeout=1.5):
            cm = MagicMock()
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = fake_tags
            cm.__enter__.return_value = resp
            cm.__exit__.return_value = False
            return cm

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            client = UniversalLLMClient(ollama_url="http://127.0.0.1:11434")
            self.assertEqual(client.current_model, "kam:apex:latest")

            for chosen, expected_backend in [
                ("kam:council", "ollama"),
                ("kam:coder", "ollama"),
                ("kam:r1", "ollama"),
                ("kam:7b", "ollama"),
                ("gemini-2.0-flash", "gemini"),
                ("kam-1-liquid-moe", "local_fallback"),
            ]:
                client.set_model(chosen)
                self.assertTrue(client.check_ollama_alive(force_refresh=True))
                self.assertEqual(client.current_model, chosen)
                self.assertEqual(client.active_backend, expected_backend)

        # 16K bağlam bütçesi kırpma testi
        huge_msgs = [{"role": "system", "content": "Sistem talimatı"}]
        for i in range(60):
            huge_msgs.append({"role": "user" if i % 2 == 0 else "assistant", "content": f"Tur {i}: " + ("A" * 2500)})
        huge_msgs.append({"role": "user", "content": "Son soru"})
        trimmed = UniversalLLMClient._trim_messages_to_budget(huge_msgs, max_context_tokens=4096, reserve_output_tokens=512)
        self.assertEqual(trimmed[0]["role"], "system")
        self.assertEqual(trimmed[-1]["content"], "Son soru")
        total_est = sum(UniversalLLMClient._estimate_tokens(m["content"]) for m in trimmed)
        self.assertLessEqual(total_est, 4096)

    def test_is_actionable_computer_query_tr_and_en(self):
        # Türkçe eylem komutları
        tr_actionable = [
            "/run git status",
            "/py print(1+1)",
            "Masaüstünde rapor.txt dosyası oluştur",
            "Bilgisayarın GPU ve VRAM kullanımını göster",
            "Ekran görüntüsü al ve kaydet",
            "Chrome tarayıcısını aç",
            "Panoyu oku",
            "Klasördeki dosyaları listele",
        ]
        for q in tr_actionable:
            self.assertTrue(KamAutonomousAgent.is_actionable_computer_query(q), f"Expected True for TR query: {q}")

        # İngilizce eylem komutları
        en_actionable = [
            "run pytest on tests",
            "list files in current directory",
            "check system info and battery",
            "open calculator",
            "take a screenshot",
            "analyze codebase lines of code",
            "kill process notepad",
            "read file README.md",
        ]
        for q in en_actionable:
            self.assertTrue(KamAutonomousAgent.is_actionable_computer_query(q), f"Expected True for EN query: {q}")

        # Eylem gerektirmeyen sohbet/hikmet soruları
        non_actionable = [
            "",
            "   ",
            "Dede Korkut kimdir?",
            "Merhaba, nasılsın?",
            "What is the philosophy of Stoicism?",
        ]
        for q in non_actionable:
            self.assertFalse(KamAutonomousAgent.is_actionable_computer_query(q), f"Expected False for query: {q}")

    def test_host_safety_shield_hardened_patterns(self):
        dangerous = [
            "Remove-Item -Recurse -Force C:\\",
            "del /f /s /q C:\\Windows\\System32",
            "bcdedit /delete {default}",
            "vssadmin delete shadows /all",
            "Clear-Disk -Number 0",
            "format C:",
            "mkfs.ext4 /dev/sda1",
        ]
        for cmd in dangerous:
            ok, _ = HostSafetyShield.verify_command(cmd)
            self.assertFalse(ok, f"Expected HostSafetyShield to block: {cmd}")

        for safe_cmd in ("git status", "python -m unittest", "dir", "Get-Process"):
            ok, _ = HostSafetyShield.verify_command(safe_cmd)
            self.assertTrue(ok, f"Expected HostSafetyShield to allow: {safe_cmd}")

    def test_cognitive_core_routing_and_rag_precision(self):
        # "ast" alt dizisi artık "hastane" / "rastgele" gibi kelimeleri kam:coder'a yönlendirmemeli
        c_hosp = CognitiveCouncilRouter.select_specialist_model("Hastane randevusu ve rastgele bir sohbet")
        self.assertEqual(c_hosp["selected_model"], "kam:7b")

        # Türkçe İ/I normalizasyonu ("İstanbul" -> "istanbul", "i stanbul" olmamalı)
        ke = LocalKnowledgeEngine()
        self.assertEqual(ke.normalize("İstanbul"), "istanbul")

        # Bilgisayar eylem komutları yanlış-pozitif RAG tetiklememeli
        self.assertIsNone(ke.query("Masaüstünde yeni dosya oluştur ve python çalıştır"))

    def test_desktop_ui_import_and_format_html_text(self):
        try:
            from kam.desktop_app import KamDesktopWindow, LLMStreamWorker
        except ImportError as exc:
            self.skipTest(f"PyQt6 unavailable in test environment: {exc}")

        self.assertTrue(hasattr(LLMStreamWorker, "cancel"))
        raw = (
            "🏛️ [BİLİŞSEL KURUL YÖNLENDİRMESİ // SEÇİLEN UZMAN: KAM:CODER | GÖREV ROLÜ: CODER]\n"
            "🧭 [MANUS-SINIFI OTONOM GÖREV PLANI // 2 ADIMLI ZİNCİRLEME İCRA]\n"
            "⚡ [OTONOM AJAN İCRASI // EXECUTE_PYTHON_CODE | DURUM: SUCCESS | 4.2 ms]\n"
            "<think>Önce doğrulama yapalım.</think>\n"
            "<codeact>print('ok')</codeact>\n"
            "```python\nx = 1 + 2\n```\n"
            "Sonuç **hazır** ve `x = 3` değerinde. <script>alert(1)</script>"
        )
        html_out = KamDesktopWindow._format_html_text(None, raw)
        self.assertIn("CODEACT // OTONOM PYTHON İCRASI", html_out)
        self.assertIn("CoT AKIL YÜRÜTME ZİNCİRİ", html_out)
        self.assertIn("<b style='color:#F8FAFC;'>hazır</b>", html_out)
        self.assertIn("x = 3", html_out)
        # XSS kaçışı doğrulanmalı
        self.assertNotIn("<script>", html_out)
        self.assertIn("&lt;script&gt;", html_out)
        # Açılan ve kapanan <div> / <b> etiketleri dengeli olmalı
        self.assertEqual(html_out.count("<div"), html_out.count("</div>"))
        self.assertEqual(html_out.count("<b"), html_out.count("</b>"))

    def test_sprint1_agent_os_mastery_tools(self):
        import tempfile
        from unittest.mock import patch, MagicMock

        agent = KamAutonomousAgent()
        tool_names = {t["name"] for t in agent.list_agent_tools()}
        self.assertIn("smart_workspace_search", tool_names)
        self.assertIn("clipboard_manager", tool_names)
        self.assertIn("system_notification", tool_names)

        # 1. smart_workspace_search: .git / __pycache__ / node_modules / ikili dosya atlanmalı
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "alpha.py"), "w", encoding="utf-8") as f:
                f.write("line1\nKAM_NEEDLE_777 = 'Dirlik'\nline3\n")
            with open(os.path.join(tmpdir, "notes.txt"), "w", encoding="utf-8") as f:
                f.write("KAM_NEEDLE_777 in txt\n")
            with open(os.path.join(tmpdir, "blob.bin"), "wb") as f:
                f.write(b"\x00\x01KAM_NEEDLE_777\x00")
            for ignored in (".git", "__pycache__", "node_modules"):
                ig_dir = os.path.join(tmpdir, ignored)
                os.makedirs(ig_dir, exist_ok=True)
                with open(os.path.join(ig_dir, "skip.py"), "w", encoding="utf-8") as f:
                    f.write("KAM_NEEDLE_777\n")

            res_all = agent.execute_tool("smart_workspace_search", {"query": r"KAM_NEEDLE_\d+", "path": tmpdir, "context_lines": 1})
            self.assertEqual(res_all["status"], "success")
            self.assertEqual(res_all["total_matches"], 2)
            self.assertTrue(all(":" in m["location"] for m in res_all["matches"]))

            res_py = agent.execute_tool("smart_workspace_search", {"query": "KAM_NEEDLE_777", "path": tmpdir, "file_pattern": "*.py"})
            self.assertEqual(res_py["status"], "success")
            self.assertEqual(res_py["total_matches"], 1)
            self.assertTrue(res_py["matches"][0]["file"].endswith("alpha.py"))

            # Boş sorgu hata döndürmeli
            res_empty = agent.execute_tool("smart_workspace_search", {"query": ""})
            self.assertEqual(res_empty["status"], "error")

            # host.smart_search CodeAct köprüsü çalışmalı
            bridge_res = agent.execute_tool(
                "execute_python_code",
                {"code": f"r = host.smart_search('KAM_NEEDLE_777', path={tmpdir!r}, file_pattern='*.py'); print(r['total_matches'])"},
            )
            self.assertEqual(bridge_res["status"], "success")
            self.assertEqual(bridge_res["stdout"], "1")

        # 2. clipboard_manager: geçersiz eylem hatası + UTF-8/Türkçe/çok-satırlı set/get (-EncodedCommand)
        bad_cb = agent.execute_tool("clipboard_manager", {"action": "invalid_op"})
        self.assertEqual(bad_cb["status"], "error")

        sample_clip = "Türkçe şğüöçıİ\n'tek tırnak' ve satır 2"
        fake_proc = MagicMock(returncode=0, stdout=sample_clip, stderr="")
        with patch("kam.autonomous_agent.subprocess.run", return_value=fake_proc) as mock_run:
            set_res = agent.execute_tool("clipboard_manager", {"action": "set", "text": sample_clip})
            self.assertEqual(set_res["status"], "success")
            self.assertEqual(set_res["action"], "set")
            called_cmd = mock_run.call_args[0][0]
            self.assertIn("-EncodedCommand", called_cmd)

            get_res = agent.execute_tool("clipboard_manager", {"action": "get"})
            self.assertEqual(get_res["status"], "success")
            self.assertEqual(get_res["text"], sample_clip)

        # 3. system_notification: boş mesaj reddi + bloklamayan Popen bildirimi
        bad_notif = agent.execute_tool("system_notification", {"title": "KAM", "message": ""})
        self.assertEqual(bad_notif["status"], "error")

        with patch("kam.autonomous_agent.subprocess.Popen") as mock_popen:
            ok_notif = agent.execute_tool("system_notification", {"title": "KAM Nöbeti", "message": "Dirlik sağlandı."})
            self.assertEqual(ok_notif["status"], "success")
            self.assertTrue(ok_notif["non_blocking"])
            mock_popen.assert_called_once()
            popen_cmd = mock_popen.call_args[0][0]
            self.assertIn("-EncodedCommand", popen_cmd)

    def test_sprint1_session_title_episodic_memory_and_attached_files(self):
        import tempfile
        from unittest.mock import patch
        from kam.real_llm import UniversalLLMClient

        # 1. generate_session_title
        self.assertEqual(UniversalLLMClient.generate_session_title(""), "Yeni Oturum")
        self.assertEqual(
            UniversalLLMClient.generate_session_title("[EKLİ DOSYA: data/uploads/rapor.txt]"),
            "Dosya: rapor.txt",
        )
        t_tr = UniversalLLMClient.generate_session_title("merhaba, istanbul tarihini özetle")
        self.assertTrue(t_tr.startswith("İ"), f"Expected Turkish capital İ, got: {t_tr}")
        t_long = UniversalLLMClient.generate_session_title("a" * 10 + " " + "kelime " * 15, max_len=36)
        self.assertLessEqual(len(t_long), 36)
        self.assertTrue(t_long.endswith("..."))

        # 2. Epizodik bellek çıkarımı & generate_stream enjeksiyonu
        client = UniversalLLMClient(ollama_url="http://127.0.0.1:9")
        client.set_model("kam:apex")
        client.agent.episodic_memory = [
            {"id": 1, "category": "tercih", "note": "Mimar Python testlerinde unittest kullanmayı tercih eder."},
            {"id": 2, "category": "donanım", "note": "İş istasyonunda RTX 5060 8GB VRAM ve 64GB RAM bulunur."},
            {"id": 3, "category": "proje", "note": "KAM çekirdeği C++20 ve eBPF ringbuffer mimarisini kullanır."},
            {"id": 4, "category": "donanım", "note": "İşlemci Ryzen 9 8945HX olarak yapılandırılmıştır."},
        ]
        hits = client._retrieve_episodic_memories("RTX 5060 VRAM donanım ve RAM durumu nedir?", top_k=3)
        self.assertGreaterEqual(len(hits), 1)
        self.assertLessEqual(len(hits), 3)
        self.assertTrue(any("RTX 5060" in h for h in hits))
        self.assertEqual(client._retrieve_episodic_memories("xqz alakasız zzz", top_k=3), [])

        captured_messages = []
        with patch.object(client, "check_ollama_alive", return_value=True), \
             patch.object(
                 client,
                 "_stream_ollama_step",
                 side_effect=lambda url, model, msgs, is_actionable, abort_event=None: (
                     captured_messages.append(msgs),
                     iter(["Anlaşıldı."]),
                 )[1],
             ):
            out = "".join(client.generate_stream("RTX 5060 VRAM bilgimi hatırla"))
        self.assertIn("Anlaşıldı.", out)
        self.assertTrue(any("RTX 5060" in m["content"] for m in captured_messages[0]))

        # 3. [EKLİ DOSYA: <yol>] metin okuma, ikili dosya tespiti ve path traversal koruması
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_path = os.path.join(tmpdir, "ornek.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("Kut ve Dirlik 12345")
            bin_path = os.path.join(tmpdir, "blob.bin")
            with open(bin_path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

            clean_p, ctx_txt = client._extract_attached_files_context(f"[EKLİ DOSYA: {txt_path}] Bunu özetle")
            self.assertEqual(clean_p, "Bunu özetle")
            self.assertIsNotNone(ctx_txt)
            self.assertIn("Kut ve Dirlik 12345", ctx_txt)

            _, ctx_bin = client._extract_attached_files_context(f"[EKLİ DOSYA: {bin_path}] İncele")
            self.assertIsNotNone(ctx_bin)
            self.assertIn("İKİLİ DOSYA", ctx_bin)

            _, ctx_trav1 = client._extract_attached_files_context("[EKLİ DOSYA: ../../etc/passwd] Oku")
            self.assertIn("ENGELLENDİ", ctx_trav1)
            _, ctx_trav2 = client._extract_attached_files_context(r"[EKLİ DOSYA: ..\..\Windows\win.ini] Oku")
            self.assertIn("ENGELLENDİ", ctx_trav2)

    def test_sprint1_bm25_knowledge_ranking_and_routing_matrix(self):
        # 1. BM25/TF-IDF nadir terim ağırlığı ve skor sıralaması
        ke = LocalKnowledgeEngine()
        rare_idf = ke.get_term_idf("ebpf")
        common_idf = ke.get_term_idf("kam")
        self.assertGreater(rare_idf, 0.0)
        self.assertGreater(rare_idf, common_idf)

        scored = ke.score_entries("Karl Friston serbest enerji ilkesi nedir?", top_k=3)
        self.assertGreaterEqual(len(scored), 1)
        self.assertIn("Friston", scored[0]["entry"]["answer"])
        if len(scored) >= 2:
            self.assertGreaterEqual(scored[0]["score"], scored[1]["score"])
        self.assertEqual(ke.score_entries("Masaüstünde dosya oluştur ve python çalıştır"), [])

        # 2. CognitiveCouncilRouter.explain_routing_matrix()
        matrix = CognitiveCouncilRouter.explain_routing_matrix()
        self.assertEqual(matrix["council_name"], "KAM-Sovereign-Cognitive-Council")
        self.assertEqual(matrix["total_specialists"], 5)
        self.assertEqual(matrix["thermal_throttle_threshold_c"], 85.0)
        self.assertEqual(matrix["low_ram_threshold_mb"], 2048)
        specialist_ids = {s["model_id"] for s in matrix["specialists"]}
        self.assertEqual(specialist_ids, {"kam:coder", "kam:r1", "kam:r1-nano", "kam:1.5b", "kam:7b"})
        self.assertIn("coding", matrix["category_routes"])
        self.assertIn("computer_use", matrix["category_routes"])

if __name__ == "__main__":
    unittest.main()
