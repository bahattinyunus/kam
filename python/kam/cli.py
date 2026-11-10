import argparse
import json
from .engine import KamEngine
from .mcp_server import McpServer
from .tui import KamDashboard
from .model_benchmark import ModelBenchmark
from .swarm_mesh import SwarmMeshController
from .models.liquid_moe import KamLiquidFoundationModel
from .models.trainer import ActiveInferenceTrainer
from .interactive_chat import KamInteractiveChat
from .web_server import run_gui
from .edge_optimizer import (
    EdgeHardwareBudget,
    EdgeModelOptimizer,
    TernaryBitNetQuantizer,
    SpeculativeDecoder,
)
from .tactical_planner import TacticalRoutePlanner3D
from .cognitive_council import CognitiveCouncilRouter
from .ew_cognitive_radar import PulseDescriptorWord, CognitiveEwEmitterClassifier
from .intent_c2_orchestrator import IntentToTaskOrchestrator
from .neuro_symbolic_shield import FlightControlCommand, NeuroSymbolicSafetyShield
from .lyapunov_controller import LyapunovCognitiveController
from .byzantine_pqc_swarm import SwarmNodeBelief, ByzantinePqcSwarmGuard
from .terrain_matching_trn import TerrainRelativeNavigator
from .actuator_reconfigurator import ActuatorFaultReconfigurator

def main():
    parser = argparse.ArgumentParser(
        description="KAM: Bilişsel ve Kendi Kendini İyileştiren Otonom Sistem Motoru CLI"
    )
    parser.add_argument(
        "--gui", "--web",
        action="store_true",
        help="KAM grafiksel web arayüzünü (Dashboard) başlat ve tarayıcıda aç"
    )
    parser.add_argument(
        "--scenario",
        choices=["uav_failure", "thermal_crisis", "jamming_attack", "can_spoofing", "thermal_runaway", "swarm_loss"],
        default="uav_failure",
        help="Yürütülecek simülasyon ve iyileştirme ayini senaryosu"
    )
    parser.add_argument(
        "--chat", "-c",
        action="store_true",
        help="KAM yerel bilişsel zihniyle interaktif terminal sohbetini başlat"
    )
    parser.add_argument(
        "--infer",
        action="store_true",
        help="KAM-1 Liquid Foundation Model üzerinden gerçek zamanlı çıkarım yap"
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Model üzerinde Karl Friston serbest enerji minimizasyonu eğitim döngüsü çalıştır"
    )
    parser.add_argument(
        "--dashboard", "-d",
        action="store_true",
        help="Canlı terminal TUI gösterge panelini (Dashboard) başlat"
    )
    parser.add_argument(
        "--benchmark", "-b",
        action="store_true",
        help="Donanım model çıkarım ve enerji verimlilik kıyaslamasını göster"
    )
    parser.add_argument(
        "--edge-plan",
        action="store_true",
        help="Kısıtlı donanım (Edge-Apex) dağıtım planlayıcısı, BitNet b1.58 ve Spekülatif Çözümleme analizi"
    )
    parser.add_argument(
        "--tactical-route",
        action="store_true",
        help="3B SİHA Radar Sönümleme ve Aktif Çıkarım vadi süzülüş (Nap-of-the-Earth) rota planlaması"
    )
    parser.add_argument(
        "--council",
        action="store_true",
        help="5-Modelli Bilişsel Kurul (Bilge + Gözcü Lyapunov CLF + Demirci JIT) ortak kriz kararı"
    )
    parser.add_argument(
        "--ew", "--radar",
        action="store_true",
        help="Bilişsel EW Radar PDW sınıflandırıcısı, LPI çevrimiçi tehdit öğrenimi ve DRFM aldatma analizi"
    )
    parser.add_argument(
        "--c2", "--orchestrate",
        type=str,
        nargs="?",
        const="Sektör-4 S-400 bataryasını körelt ve vadi taarruzu icra et",
        help="Komutan niyetini (Intent-to-Task DAG) çoklu alan İHA/SİHA/EW filosuna tahsis et"
    )
    parser.add_argument(
        "--shield", "--cbf",
        action="store_true",
        help="DARPA ANSR & CBF Nöro-Sembolik Uçuş Güvenlik Kalkanı uçuş zarfı doğrulaması"
    )
    parser.add_argument(
        "--lyapunov", "--clf",
        action="store_true",
        help="Lyapunov CLF asimptotik kararlılık denetimi ve 2. Dereceden Taylor TTA kriz öngörüsü"
    )
    parser.add_argument(
        "--fleet", "--sovereign-fleet",
        action="store_true",
        help="KAM 8-Modelli Egemen Savunma Filosu (Hugging Face Sovereign Fleet) manifestosu"
    )
    parser.add_argument(
        "--bft-swarm", "--pqc",
        action="store_true",
        help="Bizans Hata Toleranslı (BFT) Markov Battaniyesi ve ML-KEM-768 Kuantum-Dirençli Sürü Doğrulaması"
    )
    parser.add_argument(
        "--trn", "--tercom",
        action="store_true",
        help="GPS-Kör Ortamda %100 Pasif Arazi Referanslı Seyrüsefer (TRN / TERCOM DEM Korelasyonu)"
    )
    parser.add_argument(
        "--actuator", "--reconfig",
        action="store_true",
        help="Kinetik Hasar ve Eyleyici Sıkışması Altında Ağırlıklı Sözde-Ters (Pseudo-Inverse) Kontrol Dağıtımı"
    )
    parser.add_argument(
        "--full-audit",
        action="store_true",
        help="KAM 15-Modüllü Bütünsel Otonom Bekâ ve Siber-Fiziksel Öz-Onarım Tam Denetim Raporu"
    )
    parser.add_argument(
        "--export-metrics",
        action="store_true",
        help="Prometheus formatında telemetri metriklerini yazdır"
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="MCP (Model Context Protocol) sunucu modunu başlat"
    )

    args = parser.parse_args()

    if args.gui:
        run_gui()
        return

    if args.chat:
        chat = KamInteractiveChat()
        chat.run()
        return

    if args.edge_plan:
        profiles = {
            "Tier-1 (Mikro İHA / 1.5GB RAM / 8W)": EdgeModelOptimizer.plan_optimal_deployment(
                EdgeHardwareBudget(ram_mb=1536, tdp_watts=8.0, npu_temp_c=55.0)
            ).__dict__,
            "Tier-2 (Taktik SİHA / 4GB RAM / 18W)": EdgeModelOptimizer.plan_optimal_deployment(
                EdgeHardwareBudget(ram_mb=4096, tdp_watts=18.0, npu_temp_c=62.0)
            ).__dict__,
            "Tier-3 (Mobil Komuta RTX 5060 / 8GB / 35W)": EdgeModelOptimizer.plan_optimal_deployment(
                EdgeHardwareBudget(ram_mb=8192, tdp_watts=35.0, npu_temp_c=68.0)
            ).__dict__,
            "Speculative_Decoding": SpeculativeDecoder().verify_draft_step(
                ["extern", '"C"', "int", "kam_entrypoint", "()"],
                [0.92, 0.88, 0.95, 0.90, 0.94],
                [0.94, 0.91, 0.96, 0.92, 0.95],
            ),
            "BitNet_b158_Sample": TernaryBitNetQuantizer.quantize_tensor([0.42, -0.38, 0.02, 0.51, -0.49, 0.01]),
        }
        print(json.dumps(profiles, indent=2, ensure_ascii=False))
        return

    if args.tactical_route:
        planner = TacticalRoutePlanner3D()
        route = planner.plan_stealth_trajectory()
        print(json.dumps(route, indent=2, ensure_ascii=False))
        return

    if args.council:
        council = CognitiveCouncilRouter()
        verdict = council.synthesize_council_verdict(crisis_hint="THERMAL")
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
        return

    if args.ew:
        ew = CognitiveEwEmitterClassifier()
        pdw_known = PulseDescriptorWord(rf_ghz=9.2, pri_us=420.0, pw_us=1.8, aoa_deg=32.0, chirp_bw_mhz=45.0, agility_score=0.1)
        res_known = ew.classify_pdw_burst(pdw_known)
        pdw_novel = PulseDescriptorWord(rf_ghz=17.4, pri_us=610.0, pw_us=0.25, aoa_deg=118.0, chirp_bw_mhz=240.0, agility_score=0.92)
        res_novel = ew.classify_pdw_burst(pdw_novel)
        out = {
            "module": "KAM Bilişsel Elektronik Harp & Radar PDW Sınıflandırıcı (Cirra-Üstü)",
            "known_emitter_sample": res_known,
            "novel_agile_emitter_sample": res_novel,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if args.c2:
        orch = IntentToTaskOrchestrator()
        plan = orch.decompose_and_allocate(args.c2)
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    if args.shield:
        unsafe_cmd = FlightControlCommand(
            target_altitude_agl_m=12.0,
            airspeed_mps=15.0,
            bank_angle_deg=68.0,
            battery_pct=14.0,
        )
        shield_res = NeuroSymbolicSafetyShield.verify_and_project(unsafe_cmd)
        print(json.dumps(shield_res, indent=2, ensure_ascii=False))
        return

    if args.lyapunov:
        clf = LyapunovCognitiveController()
        stable_eval = clf.evaluate_stability_step([0.05, 0.02, 0.01, 0.01, 0.0, 0.0], free_energy=0.04)
        chaos_eval = clf.evaluate_stability_step([1.8, -1.5, 2.1, 0.9, -0.8, 1.2], free_energy=1.65)
        tta = clf.forecast_time_to_anomaly([62.0, 68.0, 75.0, 83.0], critical_threshold=85.0, sample_dt_sec=1.0)
        out = {
            "controller": "KAM-Lyapunov-CLF-Sontag-Damping",
            "nominal_stability": stable_eval.__dict__,
            "chaotic_disturbance": chaos_eval.__dict__,
            "taylor_phase_space_tta": tta,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if args.fleet:
        fleet_data = {
            "fleet_name": "KAM Sovereign Defense AI Fleet (Hugging Face Hub)",
            "total_models": 8,
            "fleet_size_gb": "20.83 GB GGUF + 848-Param BitNet b1.58",
            "models": [
                {
                    "key": "kam:apex",
                    "repo": "https://huggingface.co/bahattinyunus/kam-apex-8b-gguf",
                    "base": "Qwen3-8B",
                    "size": "5.20 GB",
                    "role": "Başbuğ Kam - Hibrit Düşünen Komuta Zihni, C2 & EW Orkestrasyonu",
                },
                {
                    "key": "kam:7b",
                    "repo": "https://huggingface.co/bahattinyunus/kam-7b-gguf",
                    "base": "Qwen2.5-7B",
                    "size": "4.68 GB",
                    "role": "Ulu Kam - 16K Bağlam Duru Türkçe & Karl Friston Aktif Çıkarım",
                },
                {
                    "key": "kam:r1",
                    "repo": "https://huggingface.co/bahattinyunus/kam-r1-gguf",
                    "base": "DeepSeek-R1-7B",
                    "size": "4.68 GB",
                    "role": "Baş Bilge - <think> CoT Akıl Yürütme, CLF/CBF Sibernetik İspat",
                },
                {
                    "key": "kam:coder",
                    "repo": "https://huggingface.co/bahattinyunus/kam-coder-7b-gguf",
                    "base": "Qwen2.5-Coder-7B",
                    "size": "4.68 GB",
                    "role": "Ulu Demirci - C++20 JIT, Linux eBPF & CUDA Başmimarı",
                },
                {
                    "key": "kam:coder-nano",
                    "repo": "https://huggingface.co/bahattinyunus/kam-coder-nano-1.5b-gguf",
                    "base": "Qwen2.5-Coder-1.5B",
                    "size": "986 MB",
                    "role": "Taktik Demirci - Uç C++20 JIT & AST Güvenli Kurtarma Kod Üreteci",
                },
                {
                    "key": "kam:r1-nano",
                    "repo": "https://huggingface.co/bahattinyunus/kam-r1-nano-1.5b-gguf",
                    "base": "DeepSeek-R1-1.5B",
                    "size": "1.10 GB",
                    "role": "Taktik Bilge - Kısıtlı Donanım (>85°C, 1.5GB RAM) CoT Zihni",
                },
                {
                    "key": "kam:1.5b",
                    "repo": "https://huggingface.co/bahattinyunus/kam-1.5b-edge-gguf",
                    "base": "Qwen2.5-1.5B",
                    "size": "986 MB",
                    "role": "Uç Gözcü - Mikro-Uç Zihin & 3.53x Öz-Spekülatif Taslak Motoru",
                },
                {
                    "key": "kam:edge-moe-b158",
                    "repo": "https://huggingface.co/bahattinyunus/kam-edge-moe-b158",
                    "base": "Tri-Hybrid RK4 Liquid-SSM MoE",
                    "size": "848 Ternary Params",
                    "role": "BitNet b1.58 {-1,0,+1} Kriz Politikası + EW Sınıflandırma + CBF Marjı",
                },
            ],
        }
        print(json.dumps(fleet_data, indent=2, ensure_ascii=False))
        return

    if args.bft_swarm:
        beliefs = [
            SwarmNodeBelief("Alpha-1", [0.82, 0.10, 0.05, 0.03], pqc_nonce=101),
            SwarmNodeBelief("Bravo-2", [0.80, 0.11, 0.06, 0.03], pqc_nonce=102),
            SwarmNodeBelief("Charlie-3", [0.02, 0.04, 0.12, 0.82], pqc_nonce=103),  # Bizans haini
            SwarmNodeBelief("Delta-4", [0.81, 0.09, 0.06, 0.04], pqc_nonce=104),
        ]
        res = ByzantinePqcSwarmGuard.filter_byzantine_and_fuse(beliefs)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.trn:
        trn_res = TerrainRelativeNavigator.match_terrain_profile()
        print(json.dumps(trn_res, indent=2, ensure_ascii=False))
        return

    if args.actuator:
        act_res = ActuatorFaultReconfigurator.reconfigure_control_allocation()
        print(json.dumps(act_res, indent=2, ensure_ascii=False))
        return

    if args.full_audit:
        mcp = McpServer()
        audit = {
            "audit_title": "KAM Egemen Bilişsel Savunma Çekirdeği — 15-Araçlı Tam Sistem Denetimi",
            "total_mcp_tools": len(mcp.list_tools()["tools"]),
            "ebpf_kernel_status": mcp.call_tool("inspect_kernel", {}),
            "active_inference_efe": mcp.call_tool("evaluate_efe_policies", {"crisis_hint": "SDR"}),
            "ew_cognitive_radar": mcp.call_tool(
                "classify_ew_radar_pdw",
                {"rf_ghz": 17.4, "pri_us": 610.0, "pw_us": 0.25, "aoa_deg": 118.0, "chirp_bw_mhz": 240.0, "agility_score": 0.92},
            ),
            "c2_intent_dag": mcp.call_tool(
                "orchestrate_intent_c2",
                {"commander_intent": "Sektör-4 S-400 bataryasını körelt ve vadi taarruzu icra et"},
            ),
            "cbf_safety_shield": mcp.call_tool(
                "verify_cbf_safety_shield",
                {"target_altitude_agl_m": 12.0, "airspeed_mps": 15.0, "bank_angle_deg": 68.0, "battery_pct": 14.0},
            ),
            "byzantine_pqc_swarm": mcp.call_tool("verify_byzantine_pqc_swarm", {"inject_byzantine_traitor": True}),
            "terrain_relative_nav": mcp.call_tool("localize_terrain_trn", {}),
            "actuator_reconfiguration": mcp.call_tool("reconfigure_damaged_actuators", {}),
        }
        print(json.dumps(audit, indent=2, ensure_ascii=False))
        return

    if args.infer:
        model = KamLiquidFoundationModel()
        sensory_telemetry = [0.02, 0.03, 0.15, 0.80, 48.0, 1.2, 0.05, 0.9] * 2
        result = model.forward(sensory_telemetry)
        print("\n" + "=" * 65)
        print("  🐺 KAM-1 LIQUID MOE COGNITIVE FOUNDATION MODEL ÇIKARIMI")
        print("=" * 65)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("=" * 65 + "\n")
        return

    if args.train:
        trainer = ActiveInferenceTrainer(lr=0.12)
        print("\n[KAM-1 MODEL] Karl Friston Serbest Enerji & BitNet b1.58 Eğitimi Başlatılıyor...")
        history = trainer.run_training_cycle(steps=12)
        for h in history:
            print(
                f"  • Epok {h['epoch']:02d}: VFE = {h['mean_free_energy']} nats | "
                f"Kayıp = {h['total_loss']} | İsabet = %{h['policy_accuracy_pct']} | "
                f"Durum: {h['convergence_status']} | Tau: {h['tau_adaptive']:.3f}s"
            )
        print("[KAM-1 MODEL] Eğitim tamamlandı. Ağırlıklar BitNet b1.58 {-1, 0, +1} biçimine uyarlandı.\n")
        return

    if args.export_metrics:
        print("# HELP kam_entropy Karl Friston aktif cikarim kaos orani\n# TYPE kam_entropy gauge\nkam_entropy 0.03\n")
        print("# HELP kam_free_energy Varyasyonel serbest enerji puani\n# TYPE kam_free_energy gauge\nkam_free_energy 0.12\n")
        print("# HELP kam_active_nodes_total Aktif calisan donanim dugum sayisi\n# TYPE kam_active_nodes_total gauge\nkam_active_nodes_total 6\n")
        return

    if args.benchmark:
        ModelBenchmark.print_benchmark_table()
        return

    if args.dashboard:
        dash = KamDashboard()
        dash.simulate_live_dashboard()
        return

    if args.mcp:
        server = McpServer()
        print(json.dumps(server.list_tools(), indent=2, ensure_ascii=False))
        return

    engine = KamEngine()
    if args.scenario == "uav_failure":
        engine.run_uav_failure_ritual()
    elif args.scenario == "jamming_attack":
        print("\033[1;35m[KAM-ELEKTRONİK-HARP] Sinyal karıştırma simülasyonu başlatılıyor...\033[0m")
        engine.run_uav_failure_ritual()
    elif args.scenario == "can_spoofing":
        print("\033[1;31m[KAM-CAN-GÜVENLİK] CAN-0 veriyolunda yetkisiz ID (0x1BA) saptandı! JIT filtre devrede.\033[0m")
        engine.run_uav_failure_ritual()
    elif args.scenario == "thermal_runaway":
        print("\033[1;33m[KAM-TERMAL] NPU 92°C eşiği aşıldı! Model INT4-AWQ moduna çekiliyor.\033[0m")
        engine.run_uav_failure_ritual()
    elif args.scenario == "swarm_loss":
        print("\033[1;36m[KAM-SÜRÜ-KONSENSÜS] Sürü lideri kaybı simüle ediliyor...\033[0m")
        controller = SwarmMeshController()
        new_leader = controller.simulate_leader_loss()
        print(f"\033[1;32m[KONSENSÜS TAMAMLANDI] Yeni Sürü Lideri: {new_leader} (Aktif Frekans: 868.9 MHz)\033[0m")
        engine.run_uav_failure_ritual()
    else:
        print("[KAM] Termal kriz senaryosu yürütülüyor...")

if __name__ == "__main__":
    main()
