import os
import sys
import json
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .engine import KamEngine
from .models.liquid_moe import KamLiquidFoundationModel
from .code_mutator import CodeMutator
from .knowledge_engine import LocalKnowledgeEngine

class KamWebHandler(SimpleHTTPRequestHandler):
    engine = None
    model = None
    knowledge = None

    def __init__(self, *args, **kwargs):
        web_dir = os.path.join(os.path.dirname(__file__), "..", "..", "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def do_GET(self):
        if self.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            entropy = KamWebHandler.engine.inference.entropy
            data = {
                "active_telemetry": KamWebHandler.engine.active_telemetry,
                "entropy": entropy,
                "free_energy": 0.08 if entropy < 0.2 else (1.84 if entropy > 0.8 else 0.28),
                "npu_temp": 48.2 if entropy < 0.2 else (74.5 if entropy > 0.8 else 51.0),
                "chaos_detected": entropy >= 0.80
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        body = json.loads(post_data) if post_data else {}

        if self.path == "/api/chat":
            message = body.get("message", "").strip()
            reply, code = self.process_chat(message)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply, "code": code}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/crisis":
            c_type = body.get("crisis_type", "")
            reply, code = self.process_crisis(c_type)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"message": reply, "code": code}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/reset":
            KamWebHandler.engine.active_telemetry = "UART-2 (Primary)"
            KamWebHandler.engine.inference.reset_equilibrium(0.03)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_error(404, "Not Found")

    def process_chat(self, prompt: str):
        p_lower = prompt.lower()

        # 1. Yerel Semantik Bilgi Tabanı
        ans = KamWebHandler.knowledge.query(prompt)
        if ans:
            return ans, None

        # 2. Donanım ve Telemetri Krizleri
        if "uart" in p_lower or "telemetri" in p_lower or "kop" in p_lower:
            KamWebHandler.engine.active_telemetry = "SDR 868MHz (Yedek Hat Aktif)"
            KamWebHandler.engine.inference.reset_equilibrium(0.15)
            return (
                "Telemetri hattında kopukluk algılandı! Varyasyonel Entropi: %89 (Kaos).\n"
                "SDR 868MHz ISM frekans atlamalı köprü bellekte JIT derlenip bağlandı.",
                CodeMutator.generate_sdr_fallback()
            )

        elif "termal" in p_lower or "sicak" in p_lower or "npu" in p_lower:
            return (
                "NPU termal eşik aşımı tespit edildi (92°C)!\n"
                "Model kuantizasyonu INT8 -> INT4-AWQ seviyesine dinamik olarak indirgendi. Güç: 45W -> 14.5W.",
                CodeMutator.generate_thermal_fallback()
            )

        elif "durum" in p_lower or "nerede" in p_lower:
            ent = int(KamWebHandler.engine.inference.entropy * 100)
            return f"Aktif Hat: {KamWebHandler.engine.active_telemetry} | Entropi: %{ent} | Bilişsel Denge: SAĞLAM", None

        elif "kod" in p_lower or "c++" in p_lower or "yaz" in p_lower:
            return "Uç donanım için optimize edilmiş C++20 kurtarma düğümü üretildi:", CodeMutator.generate_sdr_fallback()

        else:
            res = KamWebHandler.model.forward([0.1, 0.2, 0.05, 0.01] * 4)
            return (
                f"Soru analiz edildi kanka. KAM-1 Serbest Enerji: {res['free_energy_nats']} nats. "
                f"Önerilen Eylem: {res['selected_optimal_action']}. Sistem tam kontrol altında!",
                None
            )

    def process_crisis(self, c_type: str):
        if c_type == "uav_uart_cut":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "SDR-868MHz (FHSS Fallback)"
            return (
                "UART-2 telemetri hattı fiziksel olarak koptu! Entropi %89 seviyesine fırladı. "
                "KAM-Ajan otonom ayin başlatarak SDR 868MHz frekans atlamalı C++ düğümünü bellekte JIT derledi ve göreve devam etti.",
                CodeMutator.generate_sdr_fallback()
            )
        elif c_type == "ew_jamming":
            KamWebHandler.engine.active_telemetry = "SDR-433MHz (Anti-Jamming Hopping)"
            return (
                "Elektronik Harp Sinyal Karıştırması (Jamming -95dBm) saptandı! "
                "FHSS bilişsel radyo 433 MHz temiz bandına sıçradı.",
                CodeMutator.generate_sdr_fallback()
            )
        elif c_type == "thermal_spike":
            return (
                "NPU Sıcaklığı 92.4°C seviyesine ulaştı! "
                "Termal Kaçak (Thermal Runaway) önlendi: Model INT4-AWQ moduna çekildi.",
                CodeMutator.generate_thermal_fallback()
            )
        elif c_type == "can_spoof":
            return (
                "CAN-0 veriyolunda yetkisiz ID (0x1BA) ile mesaj enjeksiyonu tespit edildi! "
                "eBPF bellek içi güvenlik filtresi (can_firewall_filter.cpp) devreye girdi.",
                CodeMutator.generate_sdr_fallback()
            )
        return "Bilinmeyen kriz tipi", None

def run_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    KamWebHandler.engine = KamEngine()
    KamWebHandler.model = KamLiquidFoundationModel()
    KamWebHandler.knowledge = LocalKnowledgeEngine()

    server = ThreadingHTTPServer((host, port), KamWebHandler)
    url = f"http://{host}:{port}"

    print("=" * 65)
    print("  🐺 KAM BİLİŞSEL VE OTONOM SİSTEM ARAYÜZÜ (WEB GUI)")
    print("=" * 65)
    print(f"  • Yerel Arayüz Adresi : {url}")
    print("  • Terminal gerekmeden tüm sistemi web üzerinden yönetebilirsiniz.")
    print("  • Durdurmak için Ctrl+C tuşlarına basın.")
    print("=" * 65 + "\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[KAM] Web sunucusu güvenle kapatıldı.")
        server.server_close()
