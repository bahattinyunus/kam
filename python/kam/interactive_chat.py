import sys
import time
from .engine import KamEngine
from .models.liquid_moe import KamLiquidFoundationModel
from .code_mutator import CodeMutator
from .knowledge_engine import LocalKnowledgeEngine

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import sys
import time
from .engine import KamEngine
from .models.liquid_moe import KamLiquidFoundationModel
from .code_mutator import CodeMutator
from .real_llm import UniversalLLMClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

class KamInteractiveChat:
    """
    Yerel Bilişsel Yapay Zeka Terminal Arayüzü (Universal LLM + RAG + Edge Motoru)
    Ollama (Qwen2.5 / DeepSeek), Gemini API desteği ve yerel bilgi motoru.
    """
    def __init__(self):
        self.engine = KamEngine()
        self.model = KamLiquidFoundationModel()
        self.llm = UniversalLLMClient()
        self.running = True

    def run(self):
        print("\033[1;36m" + "=" * 68 + "\033[0m")
        print("\033[1;35m  🐺 KAM BİLİŞSEL ZİHİN: UNIVERSAL LLM ETKİLEŞİMLİ TERMİNAL \033[0m")
        print("\033[1;36m" + "=" * 68 + "\033[0m")
        print(f"  • Aktif LLM Motoru: \033[1;32m{self.llm.current_model}\033[0m (Backend: {self.llm.active_backend.upper()})")
        print("  • RAG Destekli Türkçe Bilgi Tabanı & Sıvı Sinir Ağı Entegrasyonu")
        print("  • Genel sohbet, felsefe, kod üretimi, coğrafya ve telemetri teşhisi")
        print("  • Çıkmak için 'exit', 'q' veya 'cikis' yazabilirsiniz.")
        print("-" * 68 + "\n")

        while self.running:
            try:
                prompt = input("\033[1;32mKAM-KULLANICI > \033[0m").strip()
                if not prompt:
                    continue

                if prompt.lower() in ["exit", "q", "quit", "cikis"]:
                    print("\033[1;33m[KAM] Bilişsel oturum kapatıldı. Ruh bekleme moduna alındı.\033[0m")
                    break

                print("\033[1;34m[KAM-ZİHİN DÜŞÜNÜYOR...]\033[0m")

                p_lower = prompt.lower()

                # Donanım kriz tespitleri için aktif telemetri tetikle
                if "uart" in p_lower and ("kop" in p_lower or "kesil" in p_lower):
                    self.engine.active_telemetry = "SDR 868MHz (Yedek Hat Aktif)"
                    self.engine.inference.trigger_anomaly()
                elif "termal" in p_lower and ("sicak" in p_lower or "92" in p_lower):
                    self.engine.inference.trigger_anomaly()

                # LLM Çıkarımı (Yerel Ollama Qwen2.5 / Gemini / RAG)
                reply = self.llm.generate(prompt)

                print(f"\n\033[1;35m[KAM-LLM ({self.llm.current_model})]\033[0m")
                print(f"\033[1;37m{reply}\033[0m\n")

                # C++ kod gerekiyorsa altına iliştir
                if "uart" in p_lower and ("kod" in p_lower or "kop" in p_lower or "c++" in p_lower):
                    print("\033[1;36m" + CodeMutator.generate_sdr_fallback() + "\033[0m\n")
                elif "termal" in p_lower and ("kod" in p_lower or "c++" in p_lower):
                    print("\033[1;36m" + CodeMutator.generate_thermal_fallback() + "\033[0m\n")

            except (KeyboardInterrupt, EOFError):
                print("\n\033[1;33m[KAM] Oturum sonlandırıldı.\033[0m")
                break

if __name__ == "__main__":
    chat = KamInteractiveChat()
    chat.run()
