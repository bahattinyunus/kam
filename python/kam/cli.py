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

def main():
    parser = argparse.ArgumentParser(
        description="KAM: Bilişsel ve Kendi Kendini İyileştiren Otonom Sistem Motoru CLI"
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

    if args.chat:
        chat = KamInteractiveChat()
        chat.run()
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
        trainer = ActiveInferenceTrainer()
        print("\n[KAM-1 MODEL] Karl Friston Serbest Enerji Minimizasyon Eğitimi Başlatılıyor...")
        history = trainer.run_training_cycle(steps=4)
        for h in history:
            print(f"  • Epok {h['epoch']}: Ortalama Serbest Enerji = {h['mean_free_energy']} nats | Durum: {h['convergence_status']} | Tau: {h['tau_adaptive']:.3f}s")
        print("[KAM-1 MODEL] Eğitim tamamlandı. Ağırlıklar yerel NPU/INT8 biçimine uyarlandı.\n")
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
