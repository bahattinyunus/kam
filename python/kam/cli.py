import argparse
import json
from .engine import KamEngine
from .mcp_server import McpServer
from .tui import KamDashboard

def main():
    parser = argparse.ArgumentParser(
        description="KAM: Bilişsel ve Kendi Kendini İyileştiren Otonom Sistem Motoru CLI"
    )
    parser.add_argument(
        "--scenario",
        choices=["uav_failure", "thermal_crisis", "jamming_attack"],
        default="uav_failure",
        help="Yürütülecek simülasyon ve iyileştirme ayini senaryosu"
    )
    parser.add_argument(
        "--dashboard", "-d",
        action="store_true",
        help="Canlı terminal TUI gösterge panelini (Dashboard) başlat"
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="MCP (Model Context Protocol) sunucu modunu başlat"
    )

    args = parser.parse_args()

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
    else:
        print("[KAM] Termal kriz senaryosu yürütülüyor...")

if __name__ == "__main__":
    main()
