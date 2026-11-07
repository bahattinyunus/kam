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
from .real_llm import UniversalLLMClient
from .edge_optimizer import EdgeHardwareBudget, EdgeModelOptimizer, TernaryBitNetQuantizer, SpeculativeDecoder
from .tactical_planner import TacticalRoutePlanner3D

class KamWebHandler(SimpleHTTPRequestHandler):
    engine = None
    model = None
    llm_client = None

    def __init__(self, *args, **kwargs):
        if KamWebHandler.engine is None:
            KamWebHandler.engine = KamEngine()
        if KamWebHandler.model is None:
            KamWebHandler.model = KamLiquidFoundationModel()
        if KamWebHandler.llm_client is None:
            KamWebHandler.llm_client = UniversalLLMClient()
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
                "ebpf_events_per_sec": 3420 if entropy < 0.2 else (8940 if entropy > 0.8 else 4610),
                "jit_latency_ms": 41.2,
                "chaos_detected": entropy >= 0.80,
                "active_model": KamWebHandler.llm_client.current_model,
                "backend": KamWebHandler.llm_client.active_backend
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            models = KamWebHandler.llm_client.list_available_models()
            self.wfile.write(json.dumps({
                "models": models,
                "current_model": KamWebHandler.llm_client.current_model,
                "active_backend": KamWebHandler.llm_client.active_backend
            }, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/edge_plan":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            plan_data = {
                "tier1_micro_uav": EdgeModelOptimizer.plan_optimal_deployment(
                    EdgeHardwareBudget(ram_mb=1536, tdp_watts=8.0, npu_temp_c=55.0)
                ).__dict__,
                "tier2_tactical_siha": EdgeModelOptimizer.plan_optimal_deployment(
                    EdgeHardwareBudget(ram_mb=4096, tdp_watts=18.0, npu_temp_c=62.0)
                ).__dict__,
                "tier3_command_rtx5060": EdgeModelOptimizer.plan_optimal_deployment(
                    EdgeHardwareBudget(ram_mb=8192, tdp_watts=35.0, npu_temp_c=68.0)
                ).__dict__,
                "bitnet_b158": TernaryBitNetQuantizer.quantize_tensor([0.45, -0.41, 0.01, 0.52, -0.49]),
                "speculative_decoding": SpeculativeDecoder().verify_draft_step(
                    ["extern", '"C"', "int", "kam_entrypoint", "()"],
                    [0.92, 0.88, 0.95, 0.90, 0.94],
                    [0.94, 0.91, 0.96, 0.92, 0.95],
                ),
            }
            self.wfile.write(json.dumps(plan_data, ensure_ascii=False).encode("utf-8"))
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

        elif self.path == "/api/chat/stream":
            message = body.get("message", "").strip()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()

            try:
                for token in KamWebHandler.llm_client.generate_stream(message):
                    data = json.dumps({"token": token}, ensure_ascii=False)
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(b"data: {\"done\": true}\n\n")
                self.wfile.flush()
            except Exception as e:
                pass
            return

        elif self.path == "/api/clear_chat":
            if KamWebHandler.llm_client:
                KamWebHandler.llm_client.conversation_history.clear()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/config":
            # API Key veya Model Değiştirme
            gemini_key = body.get("gemini_key")
            selected_model = body.get("model")

            if gemini_key is not None:
                KamWebHandler.llm_client.gemini_api_key = gemini_key.strip()
                if gemini_key.strip():
                    KamWebHandler.llm_client.active_backend = "gemini"
                    KamWebHandler.llm_client.current_model = "gemini-1.5-flash"
                else:
                    KamWebHandler.llm_client.active_backend = "ollama" if KamWebHandler.llm_client.check_ollama_alive() else "local_fallback"

            if selected_model:
                KamWebHandler.llm_client.current_model = selected_model
                if "gemini" in selected_model:
                    KamWebHandler.llm_client.active_backend = "gemini"
                else:
                    KamWebHandler.llm_client.active_backend = "ollama"

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "active_backend": KamWebHandler.llm_client.active_backend,
                "current_model": KamWebHandler.llm_client.current_model
            }).encode("utf-8"))
            return

        elif self.path == "/api/crisis":
            c_type = body.get("crisis_type", "")
            reply, code = self.process_crisis(c_type)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"message": reply, "code": code}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/tactical_route":
            tx = float(body.get("target_x_km", 50.0))
            ty = float(body.get("target_y_km", 0.0))
            segs = int(body.get("num_segments", 10))
            planner = TacticalRoutePlanner3D()
            route = planner.plan_stealth_trajectory(target_xyz=(tx, ty, 580.0), num_segments=segs)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(route, ensure_ascii=False).encode("utf-8"))
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

        # Sadece açık donanım arızası ve telemetri kopması varsa donanım durumunu güncelle
        code_snippet = None
        if "uart" in p_lower and ("kop" in p_lower or "onar" in p_lower or "kesil" in p_lower):
            KamWebHandler.engine.active_telemetry = "SDR 868MHz (Yedek Hat Aktif)"
            KamWebHandler.engine.inference.reset_equilibrium(0.15)
            code_snippet = CodeMutator.generate_sdr_fallback()
        elif "termal" in p_lower and ("92" in p_lower or "asimi" in p_lower):
            code_snippet = CodeMutator.generate_thermal_fallback()

        # Doğrudan Gerçek LLM Motoruna Sor (Qwen2.5 / DeepSeek / Gemini)
        llm_reply = KamWebHandler.llm_client.generate(prompt)

        return llm_reply, code_snippet

    def process_crisis(self, c_type: str):
        if c_type == "uav_uart_cut":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "SDR-868MHz (FHSS Fallback)"
            return (
                "Kırılan Bağ Tespit Edildi: UART-2 telemetri hattı koptu, varyasyonel entropi %89 seviyesine yükseldi. "
                "Bilişsel KAM otonom onarım protokolünü devreye aldı: SDR 868MHz frekans atlamalı kurtarma köprüsü bellekte JIT derlendi ve görev hattı kesintisiz devralındı.",
                CodeMutator.generate_sdr_fallback()
            )
        elif c_type == "ew_jamming":
            KamWebHandler.engine.active_telemetry = "SDR-433MHz (Anti-Jamming Hopping)"
            return (
                "Elektronik Harp Karıştırması: Spektrumda -95 dBm geniş bant gürültü tespit edildi. "
                "FHSS bilişsel radyo topolojisi 433 MHz temiz frekans bandına sıçradı, gürültü tabanı aşılarak dirlik korundu.",
                CodeMutator.generate_ew_fhss_fallback()
            )
        elif c_type == "thermal_spike":
            return (
                "Termal Eşik Aşımı: NPU sıcaklığı 92.4°C seviyesine ulaştı. "
                "Linux eBPF termal kancası devreye girdi: Model dinamik INT4-AWQ kuantizasyon moduna çekildi, güç tüketimi 45W -> 14.5W seviyesine indirildi.",
                CodeMutator.generate_thermal_fallback()
            )
        elif c_type == "can_spoof":
            return (
                "Veriyolu Anomalisi: CAN-0 hattına yetkisiz çerçeve (ID 0x1BA) enjeksiyonu tespit edildi. "
                "Bellek-içi eBPF güvenlik filtresi (can_firewall_filter.cpp) derlenerek sahte paketler mikrosaniyede karantinaya alındı.",
                CodeMutator.generate_can_firewall_fallback()
            )
        elif c_type == "gnss_spoof":
            KamWebHandler.engine.active_telemetry = "IMU + Optik Akış (GNSS İzole)"
            return (
                "GNSS/GPS Spoofing Tespit Edildi: Mahalanobis yenilik kapısı (d_M > 16.0) aşıldı. "
                "Sahte uydu koordinatları reddedilerek gnss_optical_flow_ekf.cpp bellekte JIT derlendi; 200 Hz Optik Akış + Barometre EKF ölü-hesaplama moduna geçildi.",
                CodeMutator.generate_gnss_spoof_fallback()
            )
        elif c_type == "swarm_loss":
            KamWebHandler.engine.active_telemetry = "SDR-868.9MHz (Bravo-2 Lider)"
            return (
                "Sürü Lideri Kaybı: Alpha-1 düğümüyle bağlantı koptu. Dağıtık Markov Battaniyesi serbest enerji konsensüsü "
                "en düşük F=0.14 nats değerine sahip Bravo-2 birimini yeni lider seçti; swarm_raft_leader_handover.cpp sıcak-yama olarak bağlandı.",
                CodeMutator.generate_swarm_handover_fallback()
            )
        return "Bilinmeyen kriz tipi", None

def run_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    KamWebHandler.engine = KamEngine()
    KamWebHandler.model = KamLiquidFoundationModel()
    KamWebHandler.llm_client = UniversalLLMClient()

    server = ThreadingHTTPServer((host, port), KamWebHandler)
    url = f"http://{host}:{port}"

    print("=" * 68)
    print("  KAM BILISSEL VE OTONOM SISTEM KOMUTA MERKEZI (WEB GUI v2.5)")
    print("=" * 68)
    print(f"  * Yerel Arayuz Adresi : {url}")
    print(f"  * Aktif LLM Motoru    : {KamWebHandler.llm_client.current_model} ({KamWebHandler.llm_client.active_backend})")
    print("  * Tum telemetri ve kriz simulasyonlari web arayuzunde aktiftir.")
    print("=" * 68 + "\n")

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
