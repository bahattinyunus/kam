import time
import sys
from .active_inference import ActiveInferenceEngine
from .code_mutator import CodeMutator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ANSI Renk Tanımları
RESET = "\033[0m"
CYAN = "\033[1;36m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
GREEN = "\033[1;32m"
MAGENTA = "\033[1;35m"

class KamEngine:
    def __init__(self):
        self.inference = ActiveInferenceEngine()
        self.active_telemetry = "UART-2"
        self.running = False

    def log(self, prefix: str, icon: str, message: str, color: str):
        print(f"{color}{prefix} {icon} {message}{RESET}")
        sys.stdout.flush()

    def awaken(self):
        self.running = True
        self.log("[KAM-ÇEKİRDEK]", "⚡", "Sistem ruhu uyandırıldı. eBPF kancaları kernel'a tutundu.", CYAN)
        time.sleep(0.4)
        entropy_pct = int(self.inference.entropy * 100)
        self.log("[KAM-ÇEKİRDEK]", "🌀", f"Aktif Çıkarım devrede. Sistem entropisi: %{entropy_pct} (Stabil)", CYAN)

    def run_uav_failure_ritual(self):
        self.awaken()
        time.sleep(0.5)

        # 1. Telemetri Çöküşü
        self.log("[SİNİR-SİSTEMİ]", "⚠️ ", "UYARI: UART-2 (Telemetri) verisi kesildi! File descriptor yanıt vermiyor.", YELLOW)
        time.sleep(0.4)

        # 2. Entropi Fırlaması
        chaos = self.inference.trigger_anomaly()
        chaos_pct = int(chaos * 100)
        self.log("[SİNİR-SİSTEMİ]", "🔥", f"Entropi %{chaos_pct} seviyesine fırladı. Kritik Eşik aşıldı! Kaos tespit edildi.", RED)
        time.sleep(0.4)

        # 3. LLM Ajanı Devreye Girer
        self.log("[KAM-AJAN]     ", "🧠", "Otonom iyileştirme ayini başlatılıyor...", MAGENTA)
        time.sleep(0.4)
        self.log("[KAM-AJAN]     ", "📡", "UART-2 düğümü koparıldı. İletişim için geçici olarak SDR (Yazılım Tanımlı Radyo) yedek frekansını kullanacak yeni C++ rotası yazılıyor.", MAGENTA)
        time.sleep(0.5)

        # 4. Kod Üretimi ve Bellekte Derleme
        _ = CodeMutator.generate_sdr_fallback()
        self.log("[DERLEYİCİ]    ", "⚡", "Yeni topoloji (sdr_fallback_node.cpp) bellekte derleniyor...", CYAN)
        time.sleep(0.6)

        # 5. Başarılı İyileşme
        self.active_telemetry = "SDR-YEDEK"
        self.inference.reset_equilibrium(0.15)
        self.log("[KAM-ÇEKİRDEK]", "🛡️ ", "İyileşme başarılı. Sistem entropisi: %15. Göreve devam ediliyor.", GREEN)
