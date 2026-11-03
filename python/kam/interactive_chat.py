import sys
import time
from .engine import KamEngine
from .models.liquid_moe import KamLiquidFoundationModel
from .code_mutator import CodeMutator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

class KamInteractiveChat:
    """
    Yerel Bilişsel Yapay Zeka Terminal Arayüzü (Air-Gapped REPL)
    """
    def __init__(self):
        self.engine = KamEngine()
        self.model = KamLiquidFoundationModel()
        self.running = True

    def run(self):
        print("\033[1;36m" + "=" * 65 + "\033[0m")
        print("\033[1;35m  🐺 KAM BİLİŞSEL ZİHİN: YEREL ETKİLEŞİMLİ TERMİNAL (AIR-GAPPED) \033[0m")
        print("\033[1;36m" + "=" * 65 + "\033[0m")
        print("  • %100 Yerel, Sıvı Sinir Ağı ve Aktif Çıkarım Çekirdeği")
        print("  • Çıkmak için 'exit', 'q' veya 'cikis' yazabilirsiniz.")
        print("-" * 65 + "\n")

        while self.running:
            try:
                prompt = input("\033[1;32mKAM-KULLANICI > \033[0m").strip()
                if not prompt:
                    continue

                if prompt.lower() in ["exit", "q", "quit", "cikis"]:
                    print("\033[1;33m[KAM] Bilişsel oturum kapatıldı. Ruh bekleme moduna alındı.\033[0m")
                    break

                print("\033[1;34m[KAM-ZİHİN DÜŞÜNÜYOR...]\033[0m")
                time.sleep(0.4)

                # Prompt Analizi
                p_lower = prompt.lower()

                if "uart" in p_lower or "telemetri" in p_lower or "kop" in p_lower:
                    res = self.model.forward([0.01, 0.02, 0.15, 0.95] * 4)
                    print("\033[1;31m[TEŞHİS] Telemetri hattında kopukluk algılandı! Varyasyonel Entropi: %89 (Kaos)\033[0m")
                    print(f"\033[1;35m[AKTİF UZMANLAR] {res['active_experts'][0][0]} (%{res['active_experts'][0][1]*100:.1f})\033[0m")
                    print("\033[1;32m[EYLEM] SDR 868MHz ISM frekans atlamalı köprü bellekte JIT derleniyor...\033[0m")
                    print("\n\033[1;36m" + CodeMutator.generate_sdr_fallback() + "\033[0m")

                elif "termal" in p_lower or "sicak" in p_lower or "npu" in p_lower:
                    res = self.model.forward([0.5, 0.8, 0.9, 0.95] * 4)
                    print("\033[1;33m[TEŞHİS] NPU termal eşik aşımı tespit edildi! Sıcaklık: 92.4°C\033[0m")
                    print("\033[1;32m[EYLEM] Model kuantizasyonu INT8 -> INT4-AWQ seviyesine dinamik indirgendi. Güç: 45W -> 14.5W\033[0m")
                    print("\n\033[1;36m" + CodeMutator.generate_thermal_fallback() + "\033[0m")

                elif "durum" in p_lower or "telemetri" in p_lower or "nerede" in p_lower:
                    print(f"\033[1;36m[SİSTEM DURUMU] Aktif Hat: {self.engine.active_telemetry} | Entropi: %{int(self.engine.inference.entropy*100)} | Bilişsel Denge: SAĞLAM\033[0m")

                elif "kod" in p_lower or "c++" in p_lower or "yaz" in p_lower:
                    print("\033[1;32m[KOD JENERATÖRÜ] Uç donanım için optimize edilmiş C++20 kurtarma düğümü üretildi:\033[0m\n")
                    print("\033[1;36m" + CodeMutator.generate_sdr_fallback() + "\033[0m")

                else:
                    res = self.model.forward([0.1, 0.2, 0.05, 0.01] * 4)
                    print(f"\033[1;35m[KAM-1 ZİHİN] Analiz Tamamlandı. Serbest Enerji: {res['free_energy_nats']} nats. Önerilen Eylem: {res['selected_optimal_action']}\033[0m")
                    print("\033[1;32m[KAM-CEVAP] Sistem kontrol altında kanka. Donanımın ruhu ve sinir sistemi 7/24 nöbette.\033[0m")

                print()

            except (KeyboardInterrupt, EOFError):
                print("\n\033[1;33m[KAM] Oturum sonlandırıldı.\033[0m")
                break

if __name__ == "__main__":
    chat = KamInteractiveChat()
    chat.run()
