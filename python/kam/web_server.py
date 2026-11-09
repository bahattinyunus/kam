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
from .ew_cognitive_radar import PulseDescriptorWord, CognitiveEwEmitterClassifier
from .intent_c2_orchestrator import IntentToTaskOrchestrator
from .neuro_symbolic_shield import FlightControlCommand, NeuroSymbolicSafetyShield
from .lyapunov_controller import LyapunovCognitiveController

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

        elif self.path == "/api/fleet_manifest":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            fleet_data = {
                "fleet_name": "KAM Sovereign Defense AI Fleet (Hugging Face Hub)",
                "total_models": 8,
                "fleet_size_gb": "20.83 GB GGUF + 848-Param BitNet b1.58",
                "huggingface_author": "bahattinyunus",
                "models": [
                    {
                        "key": "kam:apex",
                        "repo_id": "bahattinyunus/kam-apex-8b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-apex-8b-gguf",
                        "base_model": "Qwen3-8B",
                        "size": "5.20 GB",
                        "role": "Başbuğ Kam — Hibrit Düşünen Komuta Zihni, C2 & EW Orkestrasyonu",
                        "offline_gguf": "kam_apex_qwen3_8b.gguf"
                    },
                    {
                        "key": "kam:7b",
                        "repo_id": "bahattinyunus/kam-7b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-7b-gguf",
                        "base_model": "Qwen2.5-7B",
                        "size": "4.68 GB",
                        "role": "Ulu Kam — 16K Bağlam Duru Türkçe & Karl Friston Aktif Çıkarım",
                        "offline_gguf": "kam_7b_qwen_foundation.gguf"
                    },
                    {
                        "key": "kam:r1",
                        "repo_id": "bahattinyunus/kam-r1-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-r1-gguf",
                        "base_model": "DeepSeek-R1-7B",
                        "size": "4.68 GB",
                        "role": "Baş Bilge — <think> CoT Akıl Yürütme, CLF/CBF Sibernetik İspat",
                        "offline_gguf": "kam_r1_deepseek_7b.gguf"
                    },
                    {
                        "key": "kam:coder",
                        "repo_id": "bahattinyunus/kam-coder-7b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-coder-7b-gguf",
                        "base_model": "Qwen2.5-Coder-7B",
                        "size": "4.68 GB",
                        "role": "Ulu Demirci — C++20 JIT, Linux eBPF & CUDA Başmimarı",
                        "offline_gguf": "kam_coder_7b_qwen.gguf"
                    },
                    {
                        "key": "kam:coder-nano",
                        "repo_id": "bahattinyunus/kam-coder-nano-1.5b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-coder-nano-1.5b-gguf",
                        "base_model": "Qwen2.5-Coder-1.5B",
                        "size": "986 MB",
                        "role": "Taktik Demirci — Uç C++20 JIT & AST Güvenli Kurtarma Kod Üreteci",
                        "offline_gguf": "qwen2.5-coder-1.5b-q4_k_m.gguf"
                    },
                    {
                        "key": "kam:r1-nano",
                        "repo_id": "bahattinyunus/kam-r1-nano-1.5b-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-r1-nano-1.5b-gguf",
                        "base_model": "DeepSeek-R1-1.5B",
                        "size": "1.10 GB",
                        "role": "Taktik Bilge — Kısıtlı Donanım (>85°C, 1.5GB RAM) CoT Zihni",
                        "offline_gguf": "deepseek-r1-1.5b-q4_k_m.gguf"
                    },
                    {
                        "key": "kam:1.5b",
                        "repo_id": "bahattinyunus/kam-1.5b-edge-gguf",
                        "url": "https://huggingface.co/bahattinyunus/kam-1.5b-edge-gguf",
                        "base_model": "Qwen2.5-1.5B",
                        "size": "986 MB",
                        "role": "Uç Gözcü — Mikro-Uç Zihin & 3.53x Öz-Spekülatif Taslak Motoru",
                        "offline_gguf": "qwen_1.5b_lightweight_fallback.gguf"
                    },
                    {
                        "key": "kam:edge-moe-b158",
                        "repo_id": "bahattinyunus/kam-edge-moe-b158",
                        "url": "https://huggingface.co/bahattinyunus/kam-edge-moe-b158",
                        "base_model": "Tri-Hybrid RK4 Liquid-SSM MoE",
                        "size": "848 Ternary Params",
                        "role": "BitNet b1.58 {-1,0,+1} Kriz Politikası + EW Sınıflandırma + CBF Marjı",
                        "offline_gguf": "kam_edge_apex_checkpoint.json"
                    }
                ]
            }
            self.wfile.write(json.dumps(fleet_data, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/lyapunov_status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            clf = LyapunovCognitiveController()
            e = KamWebHandler.engine.inference.entropy
            state_vec = [e, e * 0.5, 0.01, 0.01, 0.0, 0.0]
            fe = 0.08 if e < 0.2 else (1.84 if e > 0.8 else 0.28)
            res = clf.evaluate_stability_step(state_vec, free_energy=fe)
            temp = 48.2 if e < 0.2 else (76.4 if e > 0.8 else 52.0)
            tta = clf.forecast_time_to_anomaly([temp - 6.0, temp - 3.0, temp - 1.0, temp], critical_threshold=85.0, sample_dt_sec=1.0)
            out = {
                "entropy": e,
                "stability": res.__dict__,
                "time_to_anomaly": tta,
            }
            self.wfile.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
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

        elif self.path == "/api/ew_radar":
            pdw = PulseDescriptorWord(
                rf_ghz=float(body.get("rf_ghz", 9.2)),
                pri_us=float(body.get("pri_us", 420.0)),
                pw_us=float(body.get("pw_us", 1.8)),
                aoa_deg=float(body.get("aoa_deg", 32.0)),
                chirp_bw_mhz=float(body.get("chirp_bw_mhz", 45.0)),
                agility_score=float(body.get("agility_score", 0.1)),
            )
            classifier = CognitiveEwEmitterClassifier()
            res = classifier.classify_pdw_burst(pdw)
            code = CodeMutator.generate_ew_drfm_fallback()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"classification": res, "countermeasure_code": code}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/c2_intent":
            intent = body.get("commander_intent", "Sektör-4 S-400 bataryasını körelt ve vadi taarruzu icra et")
            tx = float(body.get("target_x_km", 50.0))
            ty = float(body.get("target_y_km", 0.0))
            orchestrator = IntentToTaskOrchestrator()
            plan = orchestrator.decompose_and_allocate(intent, target_x_km=tx, target_y_km=ty)
            code = CodeMutator.generate_c2_dag_fallback()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"c2_plan": plan, "executor_code": code}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/safety_shield":
            cmd = FlightControlCommand(
                target_altitude_agl_m=float(body.get("target_altitude_agl_m", 12.0)),
                airspeed_mps=float(body.get("airspeed_mps", 15.0)),
                bank_angle_deg=float(body.get("bank_angle_deg", 68.0)),
                battery_pct=float(body.get("battery_pct", 14.0)),
            )
            shield_res = NeuroSymbolicSafetyShield.verify_and_project(cmd)
            code = CodeMutator.generate_cbf_safety_shield_fallback()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"shield_result": shield_res, "cbf_code": code}, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/lyapunov_status":
            clf = LyapunovCognitiveController()
            e = KamWebHandler.engine.inference.entropy
            state_vec = body.get("state_vector", [e, e * 0.5, 0.01, 0.01, 0.0, 0.0])
            fe = float(body.get("free_energy", 0.08 if e < 0.2 else (1.84 if e > 0.8 else 0.28)))
            res = clf.evaluate_stability_step(state_vec, free_energy=fe)
            temp = float(body.get("temperature", 48.2 if e < 0.2 else (76.4 if e > 0.8 else 52.0)))
            tta = clf.forecast_time_to_anomaly([temp - 6.0, temp - 3.0, temp - 1.0, temp], critical_threshold=85.0, sample_dt_sec=1.0)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"entropy": e, "stability": res.__dict__, "time_to_anomaly": tta}, ensure_ascii=False).encode("utf-8"))
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
        elif c_type == "ew_radar_threat":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "DRFM Aldatıcı Karıştırıcı (17.4GHz)"
            return (
                "Bilişsel Radar Tehdidi Tespit Edildi: 17.4 GHz LPI çevik darbe dizisi algılandı. "
                "Çevrimiçi darbe kelimesi (PDW) sınıflandırıcısı tehdidi öğrendi; ew_drfm_responder.cpp JIT derlenerek 8 adet tutarlı sahte hedef üretildi ve spektruma basıldı.",
                CodeMutator.generate_ew_drfm_fallback()
            )
        elif c_type == "cbf_envelope_breach":
            KamWebHandler.engine.inference.trigger_anomaly()
            KamWebHandler.engine.active_telemetry = "CBF Kalkanı (RTL Devrede)"
            return (
                "Uçuş Güvenlik Zarfı İhlali: DARPA ANSR & CBF Nöro-Sembolik Kalkanı h(x) < 0 bariyer ihlali saptadı. "
                "İrtifa < 30m, stall sürati < 22 m/s ve batarya <%18 ihlalleri engellenerek cbf_safety_shield.cpp ile komuta güvenli sınıra izdüşürüldü ve Eve Dönüş (RTL) devreye alındı.",
                CodeMutator.generate_cbf_safety_shield_fallback()
            )
        elif c_type == "intent_c2_mission":
            KamWebHandler.engine.active_telemetry = "C2 Çoklu Alan Ağı (DAG Aktif)"
            return (
                "Komutan Niyeti Göreve Bölündü: 'S-400 radarını körelt ve vadi taarruzu icra et' emri DAG grafiğine çevrildi. "
                "c2_task_executor.cpp üzerinden Sungur-EW-1, Kizilelma-Strike-2, Bayraktar-TB3 ve ANKA unsurlarına bağımlılık sırasıyla otonom tahsis yapıldı.",
                CodeMutator.generate_c2_dag_fallback()
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
