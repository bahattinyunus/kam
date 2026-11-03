import argparse
import json
from .engine import KamEngine
from .mcp_server import McpServer
from .tui import KamDashboard
from .model_benchmark import ModelBenchmark

def main():
    parser = argparse.ArgumentParser(
        description="KAM: Bilişsel ve Kendi Kendini İyileştiren Otonom Sistem Motoru CLI"
    )
    parser.add_argument(
        "--scenario",
        choices=["uav_failure", "thermal_crisis", "jamming_attack", "can_spoofing", "thermal_runaway"],
        default="uav_failure",
        help="Yürütülecek simülasyon ve iyileştirme ayini senaryosu"
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
        "--mcp",
        action="store_true",
        help="MCP (Model Context Protocol) sunucu modunu başlat"
    )

    args = parser.parse_args()

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
    else:
        print("[KAM] Termal kriz senaryosu yürütülüyor...")

if __name__ == "__main__":
    main()
